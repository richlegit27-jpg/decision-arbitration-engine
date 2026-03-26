from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
    stream_with_context,
)
from openai import OpenAI

# =========================================================
# PATHS / APP
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
PREFERENCES_FILE = DATA_DIR / "nova_preferences.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)

# =========================================================
# CONFIG
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"
WEB_ENABLED = os.getenv("NOVA_ENABLE_WEB", "true").lower() in {"1", "true", "yes", "on"}
PORT = int(os.getenv("PORT", "5001"))

client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        client = None

MAX_SESSION_MESSAGES = 200
MAX_CONTEXT_MESSAGES = 18
MAX_MEMORY_ITEMS = 200
MAX_MEMORY_PROMPT_ITEMS = 8
MAX_ARTIFACTS = 300
MAX_TEXT_LEN = 12000

store_lock = Lock()

# =========================================================
# JSON / FILE SAFETY
# =========================================================


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return default
        return json.loads(raw)
    except Exception:
        return default


def safe_write_json(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def ensure_files() -> None:
    if not SESSIONS_FILE.exists():
        safe_write_json(SESSIONS_FILE, {"sessions": []})
    if not MEMORY_FILE.exists():
        safe_write_json(MEMORY_FILE, {"items": []})
    if not PREFERENCES_FILE.exists():
        safe_write_json(PREFERENCES_FILE, default_preferences())
    if not ARTIFACTS_FILE.exists():
        safe_write_json(ARTIFACTS_FILE, {"artifacts": []})


# =========================================================
# NORMALIZATION
# =========================================================


def clamp_text(value: Any, limit: int = MAX_TEXT_LEN) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").strip()
    if len(text) > limit:
        text = text[:limit]
    return text


def canonical_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def clean_whitespace(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value).strip()


def trim_line_runs(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def lower_tokens(value: str) -> List[str]:
    return re.findall(r"[a-z0-9_./:-]{2,}", value.lower())


# =========================================================
# DEFAULT PREFERENCES
# =========================================================


def default_preferences() -> Dict[str, Any]:
    return {
        "style": {
            "tldr": True,
            "concise": True,
            "powerShell_first": True,
            "full_file_only": True,
            "show_file_paths": True,
            "solution_first": True,
            "prefer_endgame_style": True,
            "no_fluff": True,
        },
        "contracts": {
            "default": "direct",
            "coding": "full_file_only",
            "research": "summary_with_sources",
            "planning": "steps_only",
            "builder": "solution_first",
            "files": "grounded_answer",
        },
        "routing": {
            "prefer_fast_brain_for_simple": True,
            "prefer_deep_brain_for_files": True,
            "prefer_deep_brain_for_research": True,
            "prefer_deep_brain_for_building": True,
            "prefer_deep_brain_for_code": True,
        },
        "ui": {
            "show_router_debug": True,
            "show_trace_badges": True,
            "show_artifacts_panel": True,
            "auto_artifact_on_code": True,
            "auto_artifact_on_doc": True,
        },
        "updated_at": now_iso(),
    }


def deep_merge_dict(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            deep_merge_dict(dst[key], value)
        else:
            dst[key] = value
    return dst


# =========================================================
# STORAGE LOAD / SAVE
# =========================================================


def load_sessions() -> Dict[str, Any]:
    payload = safe_read_json(SESSIONS_FILE, {"sessions": []})
    if not isinstance(payload, dict):
        payload = {"sessions": []}
    payload.setdefault("sessions", [])
    if not isinstance(payload["sessions"], list):
        payload["sessions"] = []
    return payload


def save_sessions(payload: Dict[str, Any]) -> None:
    safe_write_json(SESSIONS_FILE, payload)


def load_memory() -> Dict[str, Any]:
    payload = safe_read_json(MEMORY_FILE, {"items": []})
    if not isinstance(payload, dict):
        payload = {"items": []}
    payload.setdefault("items", [])
    if not isinstance(payload["items"], list):
        payload["items"] = []
    return payload


def save_memory(payload: Dict[str, Any]) -> None:
    safe_write_json(MEMORY_FILE, payload)


def load_preferences() -> Dict[str, Any]:
    payload = safe_read_json(PREFERENCES_FILE, default_preferences())
    if not isinstance(payload, dict):
        payload = default_preferences()
    merged = default_preferences()
    deep_merge_dict(merged, payload)
    return merged


def save_preferences(payload: Dict[str, Any]) -> None:
    payload["updated_at"] = now_iso()
    safe_write_json(PREFERENCES_FILE, payload)


def load_artifacts() -> Dict[str, Any]:
    payload = safe_read_json(ARTIFACTS_FILE, {"artifacts": []})
    if not isinstance(payload, dict):
        payload = {"artifacts": []}
    payload.setdefault("artifacts", [])
    if not isinstance(payload["artifacts"], list):
        payload["artifacts"] = []
    return payload


def save_artifacts(payload: Dict[str, Any]) -> None:
    safe_write_json(ARTIFACTS_FILE, payload)


# =========================================================
# SESSION / MEMORY HELPERS
# =========================================================


def create_session(title: str = "New Chat") -> Dict[str, Any]:
    stamp = now_iso()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": stamp,
        "updated_at": stamp,
        "pinned": False,
        "messages": [],
    }


def get_session_by_id(payload: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    for session in payload.get("sessions", []):
        if session.get("id") == session_id:
            return session
    return None


def normalize_message(role: str, content: str, route: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": clamp_text(content),
        "created_at": now_iso(),
        "route": route or {},
    }


def auto_title_from_text(text: str) -> str:
    text = clean_whitespace(clamp_text(text, 120))
    return text[:60] if text else "New Chat"


def session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    messages = session.get("messages", [])
    preview = ""
    for msg in reversed(messages):
        content = clamp_text(msg.get("content", ""), 140)
        if content:
            preview = content
            break

    last_route = {}
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and isinstance(msg.get("route"), dict) and msg.get("route"):
            last_route = msg.get("route", {})
            break

    return {
        "id": session.get("id"),
        "title": session.get("title", "New Chat"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned")),
        "message_count": len(messages),
        "preview": preview,
        "last_route": last_route,
    }


def detect_memory_kind(text: str) -> str:
    t = text.lower()
    if "prefer" in t or "always" in t or "from now on" in t or "going forward" in t:
        return "preference"
    if "project" in t or "nova" in t or "app" in t or "build" in t:
        return "project"
    if "working on" in t or "goal" in t or "trying to" in t:
        return "task"
    return "note"


def maybe_extract_memory_items(user_text: str) -> List[Dict[str, Any]]:
    text = clamp_text(user_text, 2000)
    lowered = text.lower()
    out: List[Dict[str, Any]] = []

    patterns: List[Tuple[str, str]] = [
        (r"\bi prefer\s+(.+)", "preference"),
        (r"\bfrom now on\s+(.+)", "preference"),
        (r"\bgoing forward\s+(.+)", "preference"),
        (r"\bi am working on\s+(.+)", "project"),
        (r"\bmy project is\s+(.+)", "project"),
        (r"\bi want\s+(.+)", "task"),
    ]

    for pattern, kind in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        value = clean_whitespace(clamp_text(match.group(1), 220))
        if len(value) < 6:
            continue
        out.append(
            {
                "id": str(uuid.uuid4()),
                "kind": kind,
                "value": value,
                "created_at": now_iso(),
                "pinned": False,
            }
        )

    return out[:3]


def memory_relevance_score(item: Dict[str, Any], text: str) -> float:
    value = clean_whitespace(str(item.get("value", "")))
    if not value:
        return 0.0

    lower_text = text.lower()
    score = 0.0

    kind = item.get("kind", "note")
    if kind == "preference":
        score += 2.0
    elif kind == "project":
        score += 1.6
    elif kind == "task":
        score += 1.2
    else:
        score += 0.7

    if item.get("pinned"):
        score += 1.0

    value_tokens = [token for token in lower_tokens(value) if len(token) >= 3]
    for token in value_tokens[:20]:
        if token in lower_text:
            score += 0.35

    canon_value = canonical_text(value)
    canon_text = canonical_text(lower_text)
    if canon_value and canon_value in canon_text:
        score += 0.75

    return round(score, 3)


def select_relevant_memory(user_text: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []

    for item in items:
        score = memory_relevance_score(item, user_text)
        if score <= 0:
            continue
        enriched = dict(item)
        enriched["score"] = score
        ranked.append(enriched)

    ranked.sort(
        key=lambda x: (x.get("score", 0), bool(x.get("pinned")), x.get("created_at", "")),
        reverse=True,
    )
    return ranked[:MAX_MEMORY_PROMPT_ITEMS]


# =========================================================
# ROUTING / CONTRACTS
# =========================================================


@dataclass
class RouteDecision:
    lane: str
    mode: str
    contract: str
    reason: str
    tools: List[str]
    confidence: float


def contains_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def choose_route(user_text: str, prefs: Dict[str, Any], session: Optional[Dict[str, Any]] = None) -> RouteDecision:
    text = user_text.lower().strip()
    tools: List[str] = []
    lane = "fast"
    mode = "chat"
    contract = prefs.get("contracts", {}).get("default", "direct")
    reason = "default direct response"
    confidence = 0.62

    code_terms = [
        "smff",
        ".py",
        ".js",
        ".css",
        ".html",
        ".json",
        "full file",
        "full files",
        "replace file",
        "rewrite file",
        "fix",
        "bug",
        "error",
        "stack trace",
        "endpoint",
        "route",
        "api",
        "function",
        "class",
        "flask",
        "fastapi",
        "javascript",
        "python",
        "css",
        "html",
        "code",
    ]
    research_terms = [
        "research",
        "compare",
        "sources",
        "citations",
        "latest",
        "current",
        "today",
        "web",
        "search",
        "look up",
        "find out",
        "news",
    ]
    planning_terms = [
        "plan",
        "roadmap",
        "steps",
        "next move",
        "next moves",
        "strategy",
        "architecture",
        "checklist",
    ]
    files_terms = [
        "file",
        "document",
        "pdf",
        "spreadsheet",
        "slides",
        "attachment",
        "upload",
        "uploaded",
    ]
    builder_terms = [
        "build",
        "create",
        "make",
        "implement",
        "add",
        "upgrade",
        "feature",
        "engine",
        "panel",
        "artifact",
        "system",
    ]

    if contains_any(text, code_terms):
        mode = "code"
        contract = prefs.get("contracts", {}).get("coding", "full_file_only")
        lane = "deep" if prefs.get("routing", {}).get("prefer_deep_brain_for_code", True) else "fast"
        reason = "code-edit intent detected"
        tools = ["memory"]
        confidence = 0.92

    elif contains_any(text, research_terms):
        mode = "research"
        contract = prefs.get("contracts", {}).get("research", "summary_with_sources")
        lane = "deep"
        reason = "research/freshness intent detected"
        tools = ["memory"]
        if WEB_ENABLED:
            tools.append("web")
        confidence = 0.9

    elif contains_any(text, files_terms):
        mode = "files"
        contract = prefs.get("contracts", {}).get("files", "grounded_answer")
        lane = "deep" if prefs.get("routing", {}).get("prefer_deep_brain_for_files", True) else "fast"
        reason = "file-aware intent detected"
        tools = ["memory", "files"]
        confidence = 0.85

    elif contains_any(text, planning_terms):
        mode = "planning"
        contract = prefs.get("contracts", {}).get("planning", "steps_only")
        lane = "fast"
        reason = "planning intent detected"
        tools = ["memory"]
        confidence = 0.82

    elif contains_any(text, builder_terms):
        mode = "builder"
        contract = prefs.get("contracts", {}).get("builder", "solution_first")
        lane = "deep" if prefs.get("routing", {}).get("prefer_deep_brain_for_building", True) else "fast"
        reason = "build/upgrade intent detected"
        tools = ["memory"]
        confidence = 0.84

    elif len(text) < 30 and prefs.get("routing", {}).get("prefer_fast_brain_for_simple", True):
        lane = "fast"
        mode = "chat"
        contract = prefs.get("contracts", {}).get("default", "direct")
        reason = "short prompt fast-lane optimization"
        tools = []
        confidence = 0.76

    if "latest" in text or "today" in text or "current" in text:
        if WEB_ENABLED and "web" not in tools:
            tools.append("web")
        if mode == "chat":
            mode = "research"
            contract = prefs.get("contracts", {}).get("research", "summary_with_sources")
        lane = "deep"
        reason = "freshness-sensitive request"
        confidence = max(confidence, 0.88)

    return RouteDecision(
        lane=lane,
        mode=mode,
        contract=contract,
        reason=reason,
        tools=tools,
        confidence=round(confidence, 3),
    )


# =========================================================
# SYSTEM PROMPT / CONTEXT
# =========================================================


def build_system_prompt(
    prefs: Dict[str, Any],
    decision: RouteDecision,
    selected_memory: List[Dict[str, Any]],
) -> str:
    style = prefs.get("style", {})
    instructions: List[str] = []

    instructions.append("You are Nova, a disciplined AI execution assistant.")
    instructions.append("Be direct, useful, structured, and reliable.")
    instructions.append("Never mention hidden chain-of-thought.")
    instructions.append("Do not over-explain when a direct answer is enough.")
    instructions.append(f"Current lane: {decision.lane}.")
    instructions.append(f"Current mode: {decision.mode}.")
    instructions.append(f"Output contract: {decision.contract}.")

    if style.get("tldr", True):
        instructions.append("Use a TLDR when it helps the user move faster.")
    if style.get("concise", True):
        instructions.append("Keep answers concise and high-signal.")
    if style.get("powerShell_first", True):
        instructions.append("Use PowerShell commands when shell commands are needed.")
    if style.get("full_file_only", True):
        instructions.append("When editing files, prefer full-file replacements over patches.")
    if style.get("show_file_paths", True):
        instructions.append("Show clear file paths when replacing files.")
    if style.get("solution_first", True):
        instructions.append("Lead with the action or answer first, then the supporting detail.")
    if style.get("prefer_endgame_style", True):
        instructions.append("Use an endgame/final-pass mindset.")
    if style.get("no_fluff", True):
        instructions.append("Remove fluff, hedging, filler, and repeated reassurance.")

    if decision.contract == "full_file_only":
        instructions.append("Return full-file output only when code/file replacement is requested.")
    elif decision.contract == "steps_only":
        instructions.append("Return a clean numbered sequence of steps.")
    elif decision.contract == "summary_with_sources":
        instructions.append("Return a grounded summary and clearly separate unsupported guesses.")
    elif decision.contract == "solution_first":
        instructions.append("Start with the recommended move immediately.")
    elif decision.contract == "grounded_answer":
        instructions.append("Stay grounded to the available context and avoid unsupported invention.")

    if selected_memory:
        instructions.append("Relevant saved user memory:")
        for item in selected_memory:
            instructions.append(f"- [{item.get('kind', 'note')}] {item.get('value', '')}")

    return "\n".join(instructions)


def recent_context_messages(session: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not session:
        return []

    context: List[Dict[str, str]] = []
    for msg in session.get("messages", [])[-MAX_CONTEXT_MESSAGES:]:
        role = msg.get("role", "user")
        if role not in {"system", "user", "assistant"}:
            continue
        content = clamp_text(msg.get("content", ""), 6000)
        if content:
            context.append({"role": role, "content": content})
    return context


# =========================================================
# POST PROCESSOR / BRAIN POLISH
# =========================================================


def maybe_add_tldr(content: str) -> str:
    stripped = content.strip()
    if not stripped:
        return stripped
    if stripped.lower().startswith("tldr:"):
        return stripped

    first_line = stripped.splitlines()[0].strip()
    summary = first_line[:180]
    return f"TLDR: {summary}\n\n{stripped}"


def remove_fluff_lines(content: str) -> str:
    banned_prefixes = [
        "of course,",
        "absolutely,",
        "certainly,",
        "here's a polished",
        "i'd be happy to",
        "let's dive in",
        "great question",
    ]

    kept: List[str] = []
    for line in content.splitlines():
        raw = line.strip()
        lower = raw.lower()
        if any(lower.startswith(prefix) for prefix in banned_prefixes):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def enforce_steps_contract(content: str) -> str:
    stripped_lines = [line.strip("- ").strip() for line in content.splitlines() if line.strip()]
    if not stripped_lines:
        return content.strip()

    if re.search(r"^\s*1\.", content, flags=re.MULTILINE):
        return content.strip()

    rebuilt = []
    for idx, line in enumerate(stripped_lines[:12], start=1):
        rebuilt.append(f"{idx}. {line}")
    return "\n".join(rebuilt).strip()


def enforce_direct_contract(content: str) -> str:
    return trim_line_runs(remove_fluff_lines(content))


def enforce_full_file_contract(content: str) -> str:
    return trim_line_runs(content)


def post_process_response(text: str, prefs: Dict[str, Any], decision: RouteDecision) -> str:
    content = clamp_text(text, 20000).replace("\r\n", "\n")
    content = trim_line_runs(content)
    content = remove_fluff_lines(content)

    if decision.contract == "steps_only":
        content = enforce_steps_contract(content)
    elif decision.contract == "full_file_only":
        content = enforce_full_file_contract(content)
    else:
        content = enforce_direct_contract(content)

    if prefs.get("style", {}).get("tldr", True) and decision.mode in {"planning", "builder", "research"}:
        content = maybe_add_tldr(content)

    return trim_line_runs(content)


# =========================================================
# FALLBACK / MODEL EXECUTION
# =========================================================


def generate_direct_fallback(user_text: str, decision: RouteDecision, prefs: Dict[str, Any]) -> str:
    style = prefs.get("style", {})
    ps = style.get("powerShell_first", True)

    if decision.mode == "code":
        body = (
            "TLDR: Nova hit safe fallback mode, so I am not pretending the live model succeeded.\n\n"
            "The backend stayed stable and the request was classified as code mode.\n"
            "The clean next move is to keep the shell untouched and continue with direct full-file replacements only."
        )
        if ps:
            body += "\n\nPowerShell run:\n```powershell\npython C:\\Users\\Owner\\nova\\app.py\n```"
        return body

    if decision.mode == "planning":
        return (
            "TLDR: keep the next move tight.\n\n"
            "1. Do not touch the visual shell again.\n"
            "2. Upgrade the execution layer only.\n"
            "3. Keep routing visible and lightweight.\n"
            "4. Add artifacts only after the shell feels stable.\n"
            "5. Keep fallback behavior clean and honest."
        )

    if decision.mode == "builder":
        return (
            "TLDR: the builder route stayed alive, but the live model call failed.\n\n"
            "Best move is to continue with focused backend and response-layer upgrades, not another layout rewrite."
        )

    return (
        "TLDR: Nova entered safe fallback mode.\n\n"
        "The live model response was unavailable, so this is a direct fallback instead of a broken or fake answer."
    )


def openai_nonstream(messages: List[Dict[str, str]], model_name: str) -> str:
    if client is None:
        raise RuntimeError("OpenAI client not configured.")

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.3,
    )
    content = response.choices[0].message.content
    return content or ""


def sse_event(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# =========================================================
# ARTIFACTS
# =========================================================


def artifact_type_from_content(content: str) -> str:
    text = content.strip()

    code_fence = re.match(r"^```([a-zA-Z0-9_+-]*)", text)
    if code_fence:
        lang = code_fence.group(1).strip().lower() or "text"
        return f"code/{lang}"

    if re.search(r"(?m)^(from\s+\w+\s+import|import\s+\w+|def\s+\w+\(|class\s+\w+\()", text):
        return "code/python"
    if re.search(r"(?m)^(const\s+\w+|let\s+\w+|function\s+\w+\(|\(\)\s*=>|\{\s*$)", text):
        return "code/javascript"
    if re.search(r"(?m)^<(!doctype|html|div|head|body)\b", text.lower()):
        return "code/html"
    if re.search(r"(?m)^(:root\s*\{|[.#a-zA-Z0-9_-]+\s*\{)", text):
        return "code/css"

    return "document"


def extract_artifact_title(content: str, fallback: str = "Artifact") -> str:
    first = ""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("TLDR:"):
            continue
        if line.startswith("```"):
            continue
        first = line
        break

    if not first:
        return fallback

    first = re.sub(r"^[#*\->\d.\s]+", "", first).strip()
    first = clean_whitespace(first)
    if not first:
        return fallback
    return first[:80]


def normalize_artifact_content(content: str) -> str:
    text = content.replace("\r\n", "\n").strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()

    return text


def should_auto_create_artifact(decision: RouteDecision, prefs: Dict[str, Any], assistant_text: str) -> bool:
    ui = prefs.get("ui", {})
    if decision.mode == "code" and ui.get("auto_artifact_on_code", True):
        return True
    if decision.mode in {"builder", "planning", "files"} and ui.get("auto_artifact_on_doc", True):
        return True

    if "```" in assistant_text:
        return True

    return False


def build_artifact(
    session_id: str,
    user_text: str,
    assistant_text: str,
    decision: RouteDecision,
) -> Dict[str, Any]:
    normalized = normalize_artifact_content(assistant_text)
    artifact_type = artifact_type_from_content(assistant_text)
    title_seed = extract_artifact_title(normalized or assistant_text, fallback=f"{decision.mode.title()} Artifact")

    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "title": title_seed,
        "type": artifact_type,
        "content": normalized,
        "source_prompt": clamp_text(user_text, 300),
        "route_mode": decision.mode,
        "contract": decision.contract,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def persist_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    with store_lock:
        payload = load_artifacts()
        payload["artifacts"].insert(0, artifact)
        payload["artifacts"] = payload["artifacts"][:MAX_ARTIFACTS]
        save_artifacts(payload)
    return artifact


def get_artifact_by_id(payload: Dict[str, Any], artifact_id: str) -> Optional[Dict[str, Any]]:
    for artifact in payload.get("artifacts", []):
        if artifact.get("id") == artifact_id:
            return artifact
    return None


def artifact_summary(artifact: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": artifact.get("id"),
        "session_id": artifact.get("session_id"),
        "title": artifact.get("title", "Artifact"),
        "type": artifact.get("type", "document"),
        "route_mode": artifact.get("route_mode", "chat"),
        "contract": artifact.get("contract", "direct"),
        "source_prompt": artifact.get("source_prompt", ""),
        "created_at": artifact.get("created_at"),
        "updated_at": artifact.get("updated_at"),
        "preview": clamp_text(artifact.get("content", ""), 180),
    }


# =========================================================
# TRACE / EXECUTION PACKAGING
# =========================================================


def route_trace_payload(
    decision: RouteDecision,
    selected_memory: List[Dict[str, Any]],
    latency_ms: int = 0,
    used_tools: Optional[List[str]] = None,
    model_name: Optional[str] = None,
    fallback_used: bool = False,
    artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "lane": decision.lane,
        "mode": decision.mode,
        "contract": decision.contract,
        "reason": decision.reason,
        "confidence": decision.confidence,
        "tools": used_tools or decision.tools,
        "memory_used": [
            {
                "id": item.get("id"),
                "kind": item.get("kind"),
                "value": item.get("value"),
                "score": item.get("score", 0),
            }
            for item in selected_memory
        ],
        "model": model_name or OPENAI_MODEL,
        "latency_ms": int(latency_ms),
        "fallback_used": bool(fallback_used),
        "artifact": artifact_summary(artifact) if artifact else None,
    }


def prepare_chat_run(
    user_text: str,
    session_id: Optional[str],
    model_name: Optional[str],
) -> Tuple[Dict[str, Any], Dict[str, Any], RouteDecision, List[Dict[str, Any]], List[Dict[str, str]]]:
    prefs = load_preferences()
    sessions_payload = load_sessions()
    memory_payload = load_memory()

    session = get_session_by_id(sessions_payload, session_id) if session_id else None

    decision = choose_route(user_text, prefs, session=session)
    selected_memory = select_relevant_memory(user_text, memory_payload.get("items", []))
    system_prompt = build_system_prompt(prefs, decision, selected_memory)

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(recent_context_messages(session))
    messages.append({"role": "user", "content": user_text})

    return prefs, sessions_payload, decision, selected_memory, messages


def persist_chat_exchange(
    session_id: Optional[str],
    user_text: str,
    assistant_text: str,
    trace: Dict[str, Any],
) -> Dict[str, Any]:
    with store_lock:
        payload = load_sessions()
        session = get_session_by_id(payload, session_id) if session_id else None

        if not session:
            session = create_session(title=auto_title_from_text(user_text))
            payload["sessions"].insert(0, session)

        if not session.get("messages"):
            session["title"] = auto_title_from_text(user_text)

        session["messages"].append(normalize_message("user", user_text))
        session["messages"].append(normalize_message("assistant", assistant_text, trace))
        session["messages"] = session["messages"][-MAX_SESSION_MESSAGES:]
        session["updated_at"] = now_iso()

        save_sessions(payload)

    extracted = maybe_extract_memory_items(user_text)
    if extracted:
        with store_lock:
            mem_payload = load_memory()
            existing = {canonical_text(item.get("value", "")) for item in mem_payload.get("items", [])}

            for item in extracted:
                canon = canonical_text(item.get("value", ""))
                if canon and canon not in existing:
                    mem_payload["items"].append(item)
                    existing.add(canon)

            mem_payload["items"] = mem_payload["items"][-MAX_MEMORY_ITEMS:]
            save_memory(mem_payload)

    return session


# =========================================================
# ROUTES - UI / STATIC
# =========================================================


@app.route("/")
def index() -> Any:
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon() -> Any:
    return ("", 204)


@app.route("/static/<path:filename>")
def static_files(filename: str) -> Any:
    return send_from_directory(STATIC_DIR, filename)


# =========================================================
# ROUTES - HEALTH / MODELS / STATE
# =========================================================


@app.get("/api/health")
def api_health() -> Any:
    sessions_payload = load_sessions()
    artifacts_payload = load_artifacts()
    return jsonify(
        {
            "ok": True,
            "app": "Nova",
            "model": OPENAI_MODEL,
            "model_connected": bool(client is not None),
            "web_enabled": WEB_ENABLED,
            "sessions": len(sessions_payload.get("sessions", [])),
            "artifacts": len(artifacts_payload.get("artifacts", [])),
            "key_prefix": OPENAI_API_KEY[:7] + "..." if OPENAI_API_KEY else "",
            "time": now_iso(),
        }
    )


@app.get("/api/models")
def api_models() -> Any:
    return jsonify(
        {
            "ok": True,
            "default": OPENAI_MODEL,
            "models": [OPENAI_MODEL, "gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini"],
        }
    )


@app.get("/api/state")
def api_state() -> Any:
    payload = load_sessions()
    prefs = load_preferences()
    artifacts_payload = load_artifacts()

    sessions = [session_summary(s) for s in payload.get("sessions", [])]
    sessions.sort(
        key=lambda x: (not x.get("pinned", False), x.get("updated_at", "")),
        reverse=False,
    )

    artifacts = [artifact_summary(a) for a in artifacts_payload.get("artifacts", [])[:25]]

    return jsonify(
        {
            "ok": True,
            "sessions": sessions,
            "preferences": prefs,
            "default_model": OPENAI_MODEL,
            "web_enabled": WEB_ENABLED,
            "artifacts": artifacts,
        }
    )


# =========================================================
# ROUTES - PREFERENCES
# =========================================================


@app.get("/api/preferences")
def api_get_preferences() -> Any:
    return jsonify({"ok": True, "preferences": load_preferences()})


@app.post("/api/preferences")
def api_update_preferences() -> Any:
    data = request.get_json(silent=True) or {}
    incoming = data.get("preferences", data)

    if not isinstance(incoming, dict):
        return jsonify({"ok": False, "error": "preferences payload must be an object"}), 400

    with store_lock:
        prefs = load_preferences()
        deep_merge_dict(prefs, incoming)
        save_preferences(prefs)

    return jsonify({"ok": True, "preferences": prefs})


# =========================================================
# ROUTES - MEMORY
# =========================================================


@app.get("/api/memory")
def api_get_memory() -> Any:
    payload = load_memory()
    items = payload.get("items", [])
    items.sort(
        key=lambda x: (not bool(x.get("pinned")), x.get("created_at", "")),
        reverse=False,
    )
    return jsonify({"ok": True, "items": items})


@app.post("/api/memory")
@app.post("/api/memory/add")
def api_add_memory() -> Any:
    data = request.get_json(silent=True) or {}
    value = clean_whitespace(clamp_text(data.get("value"), 400))
    kind = clean_whitespace(clamp_text(data.get("kind"), 50)) or detect_memory_kind(value)
    pinned = bool(data.get("pinned", False))

    if not value:
        return jsonify({"ok": False, "error": "value is required"}), 400

    item = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "value": value,
        "pinned": pinned,
        "created_at": now_iso(),
    }

    with store_lock:
        payload = load_memory()
        payload["items"].append(item)
        payload["items"] = payload["items"][-MAX_MEMORY_ITEMS:]
        save_memory(payload)

    return jsonify({"ok": True, "item": item, "items": payload["items"]})


@app.post("/api/memory/delete")
def api_delete_memory() -> Any:
    data = request.get_json(silent=True) or {}
    item_id = clamp_text(data.get("id"), 100)

    if not item_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    with store_lock:
        payload = load_memory()
        before = len(payload.get("items", []))
        payload["items"] = [item for item in payload.get("items", []) if item.get("id") != item_id]
        save_memory(payload)

    deleted = before - len(payload["items"])
    return jsonify({"ok": True, "deleted": deleted})


# =========================================================
# ROUTES - SESSIONS
# =========================================================


@app.post("/api/session/new")
def api_session_new() -> Any:
    data = request.get_json(silent=True) or {}
    title = clean_whitespace(clamp_text(data.get("title"), 100)) or "New Chat"

    with store_lock:
        payload = load_sessions()
        session = create_session(title=title)
        payload["sessions"].insert(0, session)
        save_sessions(payload)

    return jsonify({"ok": True, "session": session, "summary": session_summary(session)})


@app.post("/api/session/delete")
def api_session_delete() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = clamp_text(data.get("session_id"), 100)

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    with store_lock:
        payload = load_sessions()
        before = len(payload.get("sessions", []))
        payload["sessions"] = [s for s in payload.get("sessions", []) if s.get("id") != session_id]
        save_sessions(payload)

    return jsonify({"ok": True, "deleted": before - len(payload["sessions"])})


@app.post("/api/session/rename")
def api_session_rename() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = clamp_text(data.get("session_id"), 100)
    title = clean_whitespace(clamp_text(data.get("title"), 100))

    if not session_id or not title:
        return jsonify({"ok": False, "error": "session_id and title are required"}), 400

    with store_lock:
        payload = load_sessions()
        session = get_session_by_id(payload, session_id)
        if not session:
            return jsonify({"ok": False, "error": "session not found"}), 404
        session["title"] = title
        session["updated_at"] = now_iso()
        save_sessions(payload)

    return jsonify({"ok": True, "summary": session_summary(session)})


@app.post("/api/session/duplicate")
def api_session_duplicate() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = clamp_text(data.get("session_id"), 100)

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    with store_lock:
        payload = load_sessions()
        source = get_session_by_id(payload, session_id)
        if not source:
            return jsonify({"ok": False, "error": "session not found"}), 404

        clone = json.loads(json.dumps(source))
        clone["id"] = str(uuid.uuid4())
        clone["title"] = f"{source.get('title', 'Chat')} Copy"
        clone["created_at"] = now_iso()
        clone["updated_at"] = now_iso()

        for msg in clone.get("messages", []):
            msg["id"] = str(uuid.uuid4())

        payload["sessions"].insert(0, clone)
        save_sessions(payload)

    return jsonify({"ok": True, "session": clone, "summary": session_summary(clone)})


@app.post("/api/session/pin")
def api_session_pin() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = clamp_text(data.get("session_id"), 100)
    pinned = bool(data.get("pinned", True))

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    with store_lock:
        payload = load_sessions()
        session = get_session_by_id(payload, session_id)
        if not session:
            return jsonify({"ok": False, "error": "session not found"}), 404
        session["pinned"] = pinned
        session["updated_at"] = now_iso()
        save_sessions(payload)

    return jsonify({"ok": True, "summary": session_summary(session)})


@app.get("/api/chat/<session_id>")
def api_get_chat(session_id: str) -> Any:
    payload = load_sessions()
    session = get_session_by_id(payload, session_id)
    if not session:
        return jsonify({"ok": False, "error": "session not found"}), 404
    return jsonify({"ok": True, "session": session})


# =========================================================
# ROUTES - ARTIFACTS
# =========================================================


@app.get("/api/artifacts")
def api_get_artifacts() -> Any:
    payload = load_artifacts()
    session_id = clamp_text(request.args.get("session_id"), 100)
    artifacts = payload.get("artifacts", [])

    if session_id:
        artifacts = [a for a in artifacts if a.get("session_id") == session_id]

    return jsonify(
        {
            "ok": True,
            "artifacts": [artifact_summary(a) for a in artifacts[:100]],
        }
    )


@app.get("/api/artifact/<artifact_id>")
def api_get_artifact(artifact_id: str) -> Any:
    payload = load_artifacts()
    artifact = get_artifact_by_id(payload, artifact_id)
    if not artifact:
        return jsonify({"ok": False, "error": "artifact not found"}), 404
    return jsonify({"ok": True, "artifact": artifact})


@app.post("/api/artifact/create")
def api_create_artifact() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = clamp_text(data.get("session_id"), 100)
    title = clamp_text(data.get("title"), 120) or "Artifact"
    artifact_type = clamp_text(data.get("type"), 80) or "document"
    content = clamp_text(data.get("content"), 40000)
    source_prompt = clamp_text(data.get("source_prompt"), 300)
    route_mode = clamp_text(data.get("route_mode"), 50) or "manual"
    contract = clamp_text(data.get("contract"), 50) or "direct"

    if not content:
        return jsonify({"ok": False, "error": "content is required"}), 400

    artifact = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "title": title,
        "type": artifact_type,
        "content": content,
        "source_prompt": source_prompt,
        "route_mode": route_mode,
        "contract": contract,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    persist_artifact(artifact)
    return jsonify({"ok": True, "artifact": artifact, "summary": artifact_summary(artifact)})


@app.post("/api/artifact/delete")
def api_delete_artifact() -> Any:
    data = request.get_json(silent=True) or {}
    artifact_id = clamp_text(data.get("artifact_id"), 100)

    if not artifact_id:
        return jsonify({"ok": False, "error": "artifact_id is required"}), 400

    with store_lock:
        payload = load_artifacts()
        before = len(payload.get("artifacts", []))
        payload["artifacts"] = [a for a in payload.get("artifacts", []) if a.get("id") != artifact_id]
        save_artifacts(payload)

    return jsonify({"ok": True, "deleted": before - len(payload["artifacts"])})


# =========================================================
# CHAT ROUTES
# =========================================================


@app.post("/api/chat")
def api_chat() -> Any:
    data = request.get_json(silent=True) or {}
    user_text = clamp_text(data.get("content"), MAX_TEXT_LEN)
    session_id = clamp_text(data.get("session_id"), 100)
    model_name = clamp_text(data.get("model"), 100) or OPENAI_MODEL

    if not user_text:
        return jsonify({"ok": False, "error": "content is required"}), 400

    started = time.perf_counter()
    fallback_used = False

    prefs, _, decision, selected_memory, messages = prepare_chat_run(user_text, session_id, model_name)

    try:
        assistant_text = openai_nonstream(messages, model_name)
    except Exception:
        fallback_used = True
        assistant_text = generate_direct_fallback(user_text, decision, prefs)

    assistant_text = post_process_response(assistant_text, prefs, decision)

    temp_session_id = session_id or str(uuid.uuid4())
    artifact: Optional[Dict[str, Any]] = None
    if should_auto_create_artifact(decision, prefs, assistant_text):
        artifact = build_artifact(temp_session_id, user_text, assistant_text, decision)
        persist_artifact(artifact)

    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = route_trace_payload(
        decision=decision,
        selected_memory=selected_memory,
        latency_ms=latency_ms,
        used_tools=list(decision.tools),
        model_name=model_name,
        fallback_used=fallback_used,
        artifact=artifact,
    )

    session = persist_chat_exchange(session_id, user_text, assistant_text, trace)

    if artifact and artifact.get("session_id") != session.get("id"):
        artifact["session_id"] = session.get("id")
        artifact["updated_at"] = now_iso()
        with store_lock:
            payload = load_artifacts()
            found = get_artifact_by_id(payload, artifact["id"])
            if found:
                found["session_id"] = artifact["session_id"]
                found["updated_at"] = artifact["updated_at"]
                save_artifacts(payload)

    return jsonify(
        {
            "ok": True,
            "session_id": session.get("id"),
            "content": assistant_text,
            "route": trace,
            "session": session,
            "artifact": artifact_summary(artifact) if artifact else None,
        }
    )


@app.post("/api/chat/stream")
def api_chat_stream() -> Any:
    data = request.get_json(silent=True) or {}
    user_text = clamp_text(data.get("content"), MAX_TEXT_LEN)
    session_id = clamp_text(data.get("session_id"), 100)
    model_name = clamp_text(data.get("model"), 100) or OPENAI_MODEL

    if not user_text:
        return jsonify({"ok": False, "error": "content is required"}), 400

    def generate() -> Any:
        started = time.perf_counter()
        fallback_used = False

        prefs, _, decision, selected_memory, messages = prepare_chat_run(user_text, session_id, model_name)

        yield sse_event(
            "start",
            {
                "ok": True,
                "route": route_trace_payload(
                    decision=decision,
                    selected_memory=selected_memory,
                    latency_ms=0,
                    used_tools=list(decision.tools),
                    model_name=model_name,
                    fallback_used=False,
                    artifact=None,
                ),
            },
        )

        full_text = ""

        try:
            if client is None:
                raise RuntimeError("OpenAI client not configured.")

            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
                stream=True,
            )

            for chunk in stream:
                delta = ""
                try:
                    delta = chunk.choices[0].delta.content or ""
                except Exception:
                    delta = ""

                if not delta:
                    continue

                full_text += delta
                yield sse_event("delta", {"delta": delta})

        except Exception:
            fallback_used = True
            full_text = generate_direct_fallback(user_text, decision, prefs)
            yield sse_event("delta", {"delta": full_text})

        full_text = post_process_response(full_text, prefs, decision)

        temp_session_id = session_id or str(uuid.uuid4())
        artifact: Optional[Dict[str, Any]] = None
        if should_auto_create_artifact(decision, prefs, full_text):
            artifact = build_artifact(temp_session_id, user_text, full_text, decision)
            persist_artifact(artifact)

        latency_ms = int((time.perf_counter() - started) * 1000)
        trace = route_trace_payload(
            decision=decision,
            selected_memory=selected_memory,
            latency_ms=latency_ms,
            used_tools=list(decision.tools),
            model_name=model_name,
            fallback_used=fallback_used,
            artifact=artifact,
        )

        session = persist_chat_exchange(session_id, user_text, full_text, trace)

        if artifact and artifact.get("session_id") != session.get("id"):
            artifact["session_id"] = session.get("id")
            artifact["updated_at"] = now_iso()
            with store_lock:
                payload = load_artifacts()
                found = get_artifact_by_id(payload, artifact["id"])
                if found:
                    found["session_id"] = artifact["session_id"]
                    found["updated_at"] = artifact["updated_at"]
                    save_artifacts(payload)

        yield sse_event(
            "done",
            {
                "ok": True,
                "content": full_text,
                "session_id": session.get("id"),
                "route": trace,
                "artifact": artifact_summary(artifact) if artifact else None,
            },
        )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# =========================================================
# ERROR HANDLER
# =========================================================


@app.errorhandler(404)
def handle_404(err: Exception) -> Any:
    if request.path.startswith("/api/"):
        return jsonify(
            {
                "ok": False,
                "error": "Not Found",
                "path": request.path,
                "type": "NotFound",
            }
        ), 404
    return err, 404


@app.errorhandler(405)
def handle_405(err: Exception) -> Any:
    if request.path.startswith("/api/"):
        return jsonify(
            {
                "ok": False,
                "error": "Method Not Allowed",
                "path": request.path,
                "type": "MethodNotAllowed",
            }
        ), 405
    return err, 405


@app.errorhandler(500)
def handle_500(err: Exception) -> Any:
    if request.path.startswith("/api/"):
        return jsonify(
            {
                "ok": False,
                "error": "Internal Server Error",
                "path": request.path,
                "type": "InternalServerError",
            }
        ), 500
    return err, 500


# =========================================================
# MAIN
# =========================================================

ensure_files()

if __name__ == "__main__":
    print("=== NOVA ARTIFACT SYSTEM PHASE 1 ===")
    print(f"MODEL: {OPENAI_MODEL}")
    print(f"WEB: {WEB_ENABLED}")
    print(f"CLIENT: {'READY' if client is not None else 'DISABLED'}")
    app.run(host="0.0.0.0", port=PORT, debug=True)