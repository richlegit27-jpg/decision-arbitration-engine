from pathlib import Path
import json
import os
import re
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
import uvicorn


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_FILE = TEMPLATES_DIR / "index.html"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
USAGE_FILE = DATA_DIR / "nova_usage.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
APP_HOST = (os.getenv("APP_HOST") or "127.0.0.1").strip()
APP_PORT = int((os.getenv("APP_PORT") or "8743").strip())

# Usage limiter config
DEFAULT_PLAN = (os.getenv("NOVA_DEFAULT_PLAN") or "free").strip().lower()
FREE_DAILY_MESSAGES = int((os.getenv("NOVA_FREE_DAILY_MESSAGES") or "40").strip())
PRO_DAILY_MESSAGES = int((os.getenv("NOVA_PRO_DAILY_MESSAGES") or "300").strip())
ADMIN_BYPASS = (os.getenv("NOVA_ADMIN_BYPASS") or "true").strip().lower() in {"1", "true", "yes", "on"}

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are Nova, an elite AI assistant. "
    "Be clear, direct, intelligent, and efficient. "
    "Give strong structured answers without fluff. "
    "Do not invent facts. If you are unsure, say so plainly. "
    "Use saved memory only when it is relevant to the user's request. "
    "Treat saved memory as user-specific context, not as facts about the outside world."
)

ROUTE_SYSTEM_PROMPTS = {
    "coding": (
        "Mode: coding. "
        "Prioritize implementation, debugging, code correctness, architecture, and exact fixes. "
        "Be direct. Give concrete steps and production-usable code when appropriate."
    ),
    "planning": (
        "Mode: planning. "
        "Prioritize sequencing, roadmap thinking, tradeoffs, milestones, and execution clarity. "
        "Give structured next steps."
    ),
    "writing": (
        "Mode: writing. "
        "Prioritize wording, tone, clarity, editing, rewriting, and polished communication. "
        "Write cleanly and naturally."
    ),
    "analysis": (
        "Mode: analysis. "
        "Prioritize diagnosis, reasoning, evaluation, comparison, and root-cause thinking. "
        "Be precise and explicit about uncertainty."
    ),
    "general": (
        "Mode: general. "
        "Be helpful, concise, practical, and intelligent. "
        "Use the simplest strong answer that solves the request."
    ),
}

MAX_CONTEXT_MESSAGES = 12
MAX_MEMORY_ITEMS = 50
MAX_MEMORY_PROMPT_ITEMS = 12
MAX_MEMORY_SELECTION = 8

MEMORY_KIND_ORDER = ["name", "preference", "goal", "project", "skill", "workflow", "memory"]
MEMORY_KIND_LABELS = {
    "name": "Name",
    "preference": "Preference",
    "goal": "Goal",
    "project": "Project",
    "skill": "Skill",
    "workflow": "Workflow",
    "memory": "Memory",
}

LOW_VALUE_MEMORY_EXACT = {
    "yes",
    "no",
    "maybe",
    "okay",
    "ok",
    "cool",
    "nice",
    "thanks",
    "thank you",
    "hello",
    "hi",
    "hey",
    "test",
}

LOW_VALUE_MEMORY_PHRASES = [
    "right now",
    "today",
    "tomorrow",
    "yesterday",
    "this morning",
    "this afternoon",
    "this evening",
    "good question",
    "that makes sense",
    "i don't know",
    "not sure",
]

PREFERENCE_PREFIX_BLACKLIST = (
    "that ",
    "this ",
    "it ",
    "to ",
    "for now",
)

FILE_LOCK = Lock()


def now() -> int:
    return int(time.time())


def today_key() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def load_json_file(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    with FILE_LOCK:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_sessions() -> List[Dict[str, Any]]:
    data = load_json_file(SESSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_sessions(data: List[Dict[str, Any]]) -> None:
    save_json_file(SESSIONS_FILE, data)


def load_memory() -> Dict[str, Any]:
    data = load_json_file(MEMORY_FILE, {"items": []})
    if not isinstance(data, dict):
        return {"items": []}
    items = data.get("items", [])
    if not isinstance(items, list):
        items = []
    return {"items": items}


def save_memory(data: Dict[str, Any]) -> None:
    save_json_file(MEMORY_FILE, data)


def load_usage() -> Dict[str, Any]:
    data = load_json_file(USAGE_FILE, {"profiles": {}})
    if not isinstance(data, dict):
        return {"profiles": {}}
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
    data["profiles"] = profiles
    return data


def save_usage(data: Dict[str, Any]) -> None:
    save_json_file(USAGE_FILE, data)


def get_session(sessions: List[Dict[str, Any]], session_id: str):
    for session in sessions:
        if session.get("session_id") == session_id:
            return session
    return None


def move_session_to_top(sessions: List[Dict[str, Any]], session_id: str) -> None:
    idx = None
    for i, session in enumerate(sessions):
        if session.get("session_id") == session_id:
            idx = i
            break
    if idx is None or idx == 0:
        return
    session = sessions.pop(idx)
    sessions.insert(0, session)


def create_session_object(session_id: Optional[str] = None) -> Dict[str, Any]:
    ts = now()
    return {
        "session_id": session_id or str(uuid.uuid4()),
        "title": "New Chat",
        "messages": [],
        "message_count": 0,
        "created_at": ts,
        "updated_at": ts,
    }


def get_or_create_session(sessions: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
    existing = get_session(sessions, session_id)
    if existing:
        return existing

    new_session = create_session_object(session_id=session_id or None)
    sessions.insert(0, new_session)
    return new_session


def get_context(messages: List[Dict[str, Any]], limit: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
    usable: List[Dict[str, Any]] = []
    for msg in messages[-limit:]:
        role = str(msg.get("role") or "").strip().lower()
        content = str(msg.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            usable.append({"role": role, "content": content})
    return usable


def generate_title(text: str) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return "New Chat"
    if len(clean) <= 48:
        return clean
    return clean[:48].rstrip(" .,!?:;-") + "..."


def normalize_memory_text(text: Any) -> str:
    clean = " ".join(str(text or "").split()).strip()
    clean = clean.strip(" .")
    return clean


def canonicalize_for_match(text: str) -> str:
    clean = normalize_memory_text(text).lower()
    clean = re.sub(r"[^\w\s'-]+", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def normalize_memory_kind(kind: str) -> str:
    clean = canonicalize_for_match(kind)
    if clean in MEMORY_KIND_LABELS:
        return clean
    return "memory"


def is_low_value_memory(value: str, kind: str) -> bool:
    clean = normalize_memory_text(value)
    lowered = canonicalize_for_match(clean)

    if not clean:
        return True

    if lowered in LOW_VALUE_MEMORY_EXACT:
        return True

    if len(clean) < 2 or len(clean) > 120:
        return True

    if kind == "name" and len(clean.split()) > 5:
        return True

    if kind == "preference":
        if lowered.startswith(PREFERENCE_PREFIX_BLACKLIST):
            return True

    for phrase in LOW_VALUE_MEMORY_PHRASES:
        if lowered == phrase or lowered.startswith(f"{phrase} "):
            return True

    return False


def upsert_memory_item(kind: str, value: str, source: str = "auto") -> None:
    normalized_kind = normalize_memory_kind(kind)
    clean_value = normalize_memory_text(value)

    if is_low_value_memory(clean_value, normalized_kind):
        return

    data = load_memory()
    items = data.get("items", [])
    normalized_value = canonicalize_for_match(clean_value)

    existing = None
    for item in items:
        item_kind = normalize_memory_kind(str(item.get("kind") or "memory"))
        item_value = canonicalize_for_match(str(item.get("value") or ""))
        if item_kind == normalized_kind and item_value == normalized_value:
            existing = item
            break

    ts = now()

    if existing:
        existing["value"] = clean_value
        existing["kind"] = normalized_kind
        existing["updated_at"] = ts
        existing["source"] = source
    else:
        items.insert(0, {
            "id": str(uuid.uuid4()),
            "kind": normalized_kind,
            "value": clean_value,
            "source": source,
            "created_at": ts,
            "updated_at": ts,
        })

    seen = set()
    deduped = []
    for item in items:
        item_kind = normalize_memory_kind(str(item.get("kind") or "memory"))
        item_value = canonicalize_for_match(str(item.get("value") or ""))
        key = (item_kind, item_value)
        if not item_value or key in seen:
            continue
        seen.add(key)
        item["kind"] = item_kind
        deduped.append(item)

    deduped.sort(key=lambda x: int(x.get("updated_at") or x.get("created_at") or 0), reverse=True)
    data["items"] = deduped[:MAX_MEMORY_ITEMS]
    save_memory(data)


def extract_first_match(content: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return None
    value = normalize_memory_text(match.group(1))
    return value or None


def extract_memory_from_message(text: str) -> None:
    content = normalize_memory_text(text)
    if not content:
        return

    content_lower = content.lower()

    memory_rules = [
        ("name", r"\bmy name is\s+([A-Za-z][A-Za-z0-9' -]{0,40})\b"),
        ("goal", r"\bi want to learn\s+(.+)$"),
        ("goal", r"\bi am learning\s+(.+)$"),
        ("goal", r"\bi'm learning\s+(.+)$"),
        ("goal", r"\bi want to build\s+(.+)$"),
        ("goal", r"\bmy goal is to\s+(.+)$"),
        ("project", r"\bi am working on\s+(.+)$"),
        ("project", r"\bi'm working on\s+(.+)$"),
        ("project", r"\bmy project is\s+(.+)$"),
        ("preference", r"\bi prefer\s+(.+)$"),
        ("preference", r"\bi like\s+(.+)$"),
        ("workflow", r"\bfrom now on\s+(.+)$"),
        ("workflow", r"\bgoing forward\s+(.+)$"),
        ("skill", r"\bi am good at\s+(.+)$"),
        ("skill", r"\bi'm good at\s+(.+)$"),
    ]

    if "?" in content and not any(
        trigger in content_lower for trigger in ["my name is", "i prefer", "from now on", "going forward"]
    ):
        return

    for kind, pattern in memory_rules:
        value = extract_first_match(content, pattern)
        if value:
            upsert_memory_item(kind, value, source="auto")


def score_memory_item_for_request(item: Dict[str, Any], request_text: str) -> int:
    value = canonicalize_for_match(str(item.get("value") or ""))
    kind = normalize_memory_kind(str(item.get("kind") or "memory"))
    request = canonicalize_for_match(request_text)

    if not value:
        return 0

    score = 0

    if kind == "name":
        score += 5
    elif kind in {"preference", "workflow"}:
        score += 4
    elif kind in {"goal", "project"}:
        score += 3
    else:
        score += 2

    request_words = set(request.split())
    value_words = set(value.split())
    overlap = len(request_words.intersection(value_words))
    score += overlap * 4

    if any(word in request for word in value_words if len(word) >= 4):
        score += 2

    updated_at = int(item.get("updated_at") or item.get("created_at") or 0)
    age_bonus = max(0, 3 - min(3, (now() - updated_at) // 86400))
    score += int(age_bonus)

    return score


def classify_intent(user_request: str) -> Dict[str, str]:
    text = canonicalize_for_match(user_request)
    reason = "default"
    intent = "chat"
    mode = "general"

    coding_keywords = {
        "python", "javascript", "js", "typescript", "ts", "html", "css", "sql", "flask", "fastapi",
        "bug", "debug", "fix", "error", "traceback", "exception", "api", "endpoint", "function",
        "code", "script", "app.py", "refactor", "backend", "frontend", "regex", "json"
    }
    planning_keywords = {
        "plan", "roadmap", "next step", "next move", "milestone", "phase", "strategy",
        "organize", "structure", "sequence", "workflow", "priority"
    }
    writing_keywords = {
        "write", "rewrite", "reword", "edit", "polish", "email", "message", "caption",
        "post", "blog", "landing page copy", "wording", "grammar"
    }
    analysis_keywords = {
        "analyze", "analysis", "why", "compare", "difference", "root cause", "investigate",
        "what happened", "evaluate", "tradeoff", "pros and cons"
    }

    if any(token in text for token in coding_keywords):
        mode = "coding"
        intent = "implementation"
        reason = "matched coding keywords"
    elif any(token in text for token in planning_keywords):
        mode = "planning"
        intent = "planning"
        reason = "matched planning keywords"
    elif any(token in text for token in writing_keywords):
        mode = "writing"
        intent = "writing"
        reason = "matched writing keywords"
    elif any(token in text for token in analysis_keywords):
        mode = "analysis"
        intent = "analysis"
        reason = "matched analysis keywords"

    if "?" in user_request and mode == "general":
        intent = "question"
        reason = "question fallback"

    if text.startswith("smff") or "full file" in text or "send full file" in text:
        mode = "coding"
        intent = "full-file"
        reason = "matched full-file workflow"

    return {
        "mode": mode,
        "intent": intent,
        "reason": reason,
    }


def select_relevant_memory_items(user_request: str) -> List[Dict[str, Any]]:
    data = load_memory()
    items = data.get("items", [])
    if not items:
        return []

    ranked: List[Tuple[int, Dict[str, Any]]] = []
    for item in items:
        score = score_memory_item_for_request(item, user_request)
        if score > 0:
            ranked.append((score, item))

    ranked.sort(
        key=lambda pair: (
            pair[0],
            int(pair[1].get("updated_at") or pair[1].get("created_at") or 0),
        ),
        reverse=True,
    )

    selected = [item for score, item in ranked if score >= 4][:MAX_MEMORY_SELECTION]

    if not selected and items:
        # Fallback: keep it intentionally small
        selected = sorted(
            items,
            key=lambda item: int(item.get("updated_at") or item.get("created_at") or 0),
            reverse=True,
        )[:2]

    return selected


def build_memory_prompt_from_items(items: List[Dict[str, Any]]) -> str:
    if not items:
        return ""

    grouped: Dict[str, List[str]] = {}
    for item in items[:MAX_MEMORY_PROMPT_ITEMS]:
        kind = normalize_memory_kind(str(item.get("kind") or "memory"))
        value = normalize_memory_text(str(item.get("value") or ""))
        if not value:
            continue
        grouped.setdefault(kind, []).append(value)

    lines: List[str] = []
    for kind in MEMORY_KIND_ORDER:
        values = grouped.get(kind, [])
        if not values:
            continue
        label = MEMORY_KIND_LABELS.get(kind, kind.title())
        for value in values:
            lines.append(f"- {label}: {value}")

    if not lines:
        return ""

    return (
        "Relevant saved user memory:\n"
        + "\n".join(lines)
        + "\nUse this only when relevant to the current request."
    )


def build_router_metadata(route: Dict[str, str], memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    memory_preview = []
    for item in memory_items[:3]:
        label = MEMORY_KIND_LABELS.get(
            normalize_memory_kind(str(item.get("kind") or "memory")),
            "Memory",
        )
        value = normalize_memory_text(str(item.get("value") or ""))
        if value:
            memory_preview.append(f"{label}: {value}")

    return {
        "mode": route.get("mode", "general"),
        "intent": route.get("intent", "chat"),
        "reason": route.get("reason", "auto"),
        "memory_hits": len(memory_items),
        "memory_preview": memory_preview,
        "timestamp": now(),
    }


def build_openai_messages(
    session_messages: List[Dict[str, Any]],
    user_request: str = "",
) -> Tuple[List[Dict[str, str]], Dict[str, str], List[Dict[str, Any]]]:
    route = classify_intent(user_request)
    relevant_memory = select_relevant_memory_items(user_request)

    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    route_prompt = ROUTE_SYSTEM_PROMPTS.get(route["mode"], ROUTE_SYSTEM_PROMPTS["general"])
    if route_prompt:
        messages.append({"role": "system", "content": route_prompt})

    memory_prompt = build_memory_prompt_from_items(relevant_memory)
    if memory_prompt:
        messages.append({"role": "system", "content": memory_prompt})

    messages.extend(get_context(session_messages))
    return messages, route, relevant_memory


def summarize_sessions_for_state(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for session in sessions:
        messages = session.get("messages", [])
        items.append({
            "session_id": session.get("session_id"),
            "title": session.get("title") or "New Chat",
            "message_count": len(messages) if isinstance(messages, list) else int(session.get("message_count") or 0),
            "updated_at": int(session.get("updated_at") or session.get("created_at") or now()),
        })
    items.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return items


def require_api_key() -> None:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API key")


def validate_chat_input(data: Dict[str, Any]) -> Dict[str, str]:
    session_id = str(data.get("session_id") or "").strip()
    content = normalize_memory_text(data.get("content"))
    model = str(data.get("model") or OPENAI_MODEL).strip() or OPENAI_MODEL

    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    return {
        "session_id": session_id,
        "content": content,
        "model": model,
    }


def get_default_limit_for_plan(plan: str) -> int:
    normalized = (plan or DEFAULT_PLAN).strip().lower()
    if normalized == "pro":
        return PRO_DAILY_MESSAGES
    if normalized == "admin" and ADMIN_BYPASS:
        return 10**9
    return FREE_DAILY_MESSAGES


def ensure_usage_profile(usage_data: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
    profiles = usage_data.setdefault("profiles", {})
    profile = profiles.get(profile_id)

    if not isinstance(profile, dict):
        profile = {
            "profile_id": profile_id,
            "plan": DEFAULT_PLAN,
            "daily": {},
            "created_at": now(),
            "updated_at": now(),
        }
        profiles[profile_id] = profile

    if not isinstance(profile.get("daily"), dict):
        profile["daily"] = {}

    profile["plan"] = str(profile.get("plan") or DEFAULT_PLAN).strip().lower()
    profile["updated_at"] = now()
    return profile


def cleanup_usage_days(profile: Dict[str, Any], keep_days: int = 35) -> None:
    daily = profile.get("daily", {})
    if not isinstance(daily, dict):
        profile["daily"] = {}
        return

    keys = sorted(daily.keys(), reverse=True)
    keep = set(keys[:keep_days])
    profile["daily"] = {k: v for k, v in daily.items() if k in keep}


def build_usage_summary(profile: Dict[str, Any]) -> Dict[str, Any]:
    plan = str(profile.get("plan") or DEFAULT_PLAN).strip().lower()
    limit = get_default_limit_for_plan(plan)
    today = today_key()

    daily = profile.get("daily", {})
    today_count = int((daily.get(today) or {}).get("messages", 0))

    remaining = max(0, limit - today_count) if limit < 10**8 else 999999999
    unlimited = limit >= 10**8

    return {
        "profile_id": str(profile.get("profile_id") or "local"),
        "plan": plan,
        "daily_limit": None if unlimited else limit,
        "messages_used_today": today_count,
        "messages_remaining_today": None if unlimited else remaining,
        "is_limited": not unlimited,
        "today": today,
    }


def get_usage_summary(profile_id: str = "local") -> Dict[str, Any]:
    usage_data = load_usage()
    profile = ensure_usage_profile(usage_data, profile_id)
    cleanup_usage_days(profile)
    save_usage(usage_data)
    return build_usage_summary(profile)


def assert_usage_allowed(profile_id: str = "local") -> Dict[str, Any]:
    summary = get_usage_summary(profile_id)
    if summary["is_limited"] and int(summary["messages_remaining_today"] or 0) <= 0:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily message limit reached for your current plan.",
                "usage": summary,
            },
        )
    return summary


def record_usage_message(profile_id: str = "local") -> Dict[str, Any]:
    usage_data = load_usage()
    profile = ensure_usage_profile(usage_data, profile_id)
    cleanup_usage_days(profile)

    today = today_key()
    daily = profile.setdefault("daily", {})
    day_row = daily.get(today)
    if not isinstance(day_row, dict):
        day_row = {"messages": 0}
        daily[today] = day_row

    day_row["messages"] = int(day_row.get("messages", 0)) + 1
    profile["updated_at"] = now()
    save_usage(usage_data)

    return build_usage_summary(profile)


def update_plan(profile_id: str, plan: str) -> Dict[str, Any]:
    normalized = (plan or "").strip().lower()
    if normalized not in {"free", "pro", "admin"}:
        raise HTTPException(status_code=400, detail="Plan must be free, pro, or admin")

    if normalized == "admin" and not ADMIN_BYPASS:
        raise HTTPException(status_code=400, detail="Admin plan is disabled")

    usage_data = load_usage()
    profile = ensure_usage_profile(usage_data, profile_id)
    profile["plan"] = normalized
    profile["updated_at"] = now()
    cleanup_usage_days(profile)
    save_usage(usage_data)
    return build_usage_summary(profile)


app = FastAPI(title="Nova")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(INDEX_FILE)


@app.get("/blog")
async def blog():
    blog_file = TEMPLATES_DIR / "blog.html"
    if not blog_file.exists():
        raise HTTPException(status_code=404, detail="blog.html not found")
    return FileResponse(blog_file)


@app.get("/landing")
async def landing():
    landing_file = TEMPLATES_DIR / "landing.html"
    if not landing_file.exists():
        raise HTTPException(status_code=404, detail="landing.html not found")
    return FileResponse(landing_file)


@app.get("/app")
async def app_page():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(INDEX_FILE)


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            OPENAI_MODEL,
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-4o-mini",
        ],
        "default": OPENAI_MODEL,
    }


@app.get("/api/state")
async def get_state():
    sessions = load_sessions()
    usage = get_usage_summary("local")
    return {
        "sessions": summarize_sessions_for_state(sessions),
        "usage": usage,
    }


@app.get("/api/usage")
async def api_usage():
    return get_usage_summary("local")


@app.post("/api/usage/plan")
async def api_usage_plan(request: Request):
    data = await request.json()
    plan = str(data.get("plan") or "").strip().lower()
    usage = update_plan("local", plan)
    return {"ok": True, "usage": usage}


@app.get("/api/chat/{session_id}")
async def get_chat(session_id: str):
    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["message_count"] = len(session.get("messages", []))
    return session


@app.get("/api/memory")
async def get_memory():
    return load_memory()


@app.post("/api/memory/add")
async def add_memory(request: Request):
    data = await request.json()
    kind = normalize_memory_kind(str(data.get("kind") or "memory"))
    value = normalize_memory_text(data.get("value"))

    if not value:
        raise HTTPException(status_code=400, detail="Value is required")

    if is_low_value_memory(value, kind):
        raise HTTPException(status_code=400, detail="Memory value is too short, vague, or low quality")

    upsert_memory_item(kind[:40], value[:120], source="manual")
    return {"ok": True, "memory": load_memory()}


@app.post("/api/memory/delete")
async def delete_memory(request: Request):
    data = await request.json()
    memory_id = str(data.get("id") or "").strip()
    if not memory_id:
        raise HTTPException(status_code=400, detail="id is required")

    memory = load_memory()
    before = len(memory["items"])
    memory["items"] = [item for item in memory["items"] if str(item.get("id")) != memory_id]

    if len(memory["items"]) == before:
        raise HTTPException(status_code=404, detail="Memory item not found")

    save_memory(memory)
    return {"ok": True, "memory": memory}


@app.post("/api/session/new")
async def new_session():
    sessions = load_sessions()
    session = create_session_object()
    sessions.insert(0, session)
    save_sessions(sessions)
    return {"session_id": session["session_id"]}


@app.post("/api/session/delete")
async def delete_session(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    sessions = load_sessions()
    new_sessions = [s for s in sessions if s.get("session_id") != session_id]
    if len(new_sessions) == len(sessions):
        raise HTTPException(status_code=404, detail="Session not found")

    save_sessions(new_sessions)
    return {"ok": True}


@app.post("/api/session/rename")
async def rename_session(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()
    title = normalize_memory_text(data.get("title"))

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["title"] = title[:80]
    session["updated_at"] = now()
    move_session_to_top(sessions, session_id)
    save_sessions(sessions)
    return {"ok": True}


@app.post("/api/session/duplicate")
async def duplicate_session(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    ts = now()
    original_messages = session.get("messages", [])
    copied_messages: List[Dict[str, Any]] = []

    if isinstance(original_messages, list):
        for message in original_messages:
            if isinstance(message, dict):
                copied_messages.append(json.loads(json.dumps(message)))

    duplicated = {
        "session_id": str(uuid.uuid4()),
        "title": f"{session.get('title') or 'New Chat'} Copy",
        "messages": copied_messages,
        "message_count": len(copied_messages),
        "created_at": ts,
        "updated_at": ts,
    }

    sessions.insert(0, duplicated)
    save_sessions(sessions)

    return {"ok": True, "session": duplicated}


@app.post("/api/chat")
async def chat_once(request: Request):
    payload = validate_chat_input(await request.json())
    require_api_key()
    assert_usage_allowed("local")

    session_id = payload["session_id"]
    content = payload["content"]
    model = payload["model"]

    sessions = load_sessions()
    session = get_or_create_session(sessions, session_id)

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": content,
        "timestamp": now(),
        "model": model,
    }
    session["messages"].append(user_msg)
    session["updated_at"] = now()
    extract_memory_from_message(content)

    openai_messages, route, relevant_memory = build_openai_messages(
        session["messages"],
        user_request=content,
    )
    router_meta = build_router_metadata(route, relevant_memory)

    response = client.chat.completions.create(
        model=model,
        messages=openai_messages,
        temperature=0.7,
    )

    assistant_text = str(response.choices[0].message.content or "").strip() or "No response returned."

    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": assistant_text,
        "timestamp": now(),
        "model": model,
        "router": router_meta,
    }
    session["messages"].append(assistant_msg)
    session["message_count"] = len(session["messages"])
    session["updated_at"] = now()

    if session["message_count"] == 2:
        session["title"] = generate_title(content)

    move_session_to_top(sessions, session["session_id"])
    save_sessions(sessions)
    usage = record_usage_message("local")

    return {
        "session_id": session["session_id"],
        "title": session["title"],
        "message_count": session["message_count"],
        "message": assistant_msg,
        "messages": session["messages"],
        "usage": usage,
        "router": router_meta,
    }


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    payload = validate_chat_input(await request.json())
    require_api_key()
    assert_usage_allowed("local")

    requested_session_id = payload["session_id"]
    content = payload["content"]
    model = payload["model"]

    sessions = load_sessions()
    session = get_or_create_session(sessions, requested_session_id)

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": content,
        "timestamp": now(),
        "model": model,
    }
    session["messages"].append(user_msg)
    session["updated_at"] = now()
    extract_memory_from_message(content)

    openai_messages, route, relevant_memory = build_openai_messages(
        session["messages"],
        user_request=content,
    )
    router_meta = build_router_metadata(route, relevant_memory)
    session_id = session["session_id"]

    def event_stream():
        assistant_text = ""

        try:
            yield (
                "event: start\n"
                f"data: {json.dumps({'title': session['title'], 'model_used': model, 'session_id': session_id, 'router': router_meta}, ensure_ascii=False)}\n\n"
            )

            stream = client.chat.completions.create(
                model=model,
                messages=openai_messages,
                stream=True,
                temperature=0.7,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    assistant_text += delta
                    yield (
                        "event: delta\n"
                        f"data: {json.dumps({'text': delta, 'model_used': model}, ensure_ascii=False)}\n\n"
                    )

            assistant_msg = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_text.strip() or "No response returned.",
                "timestamp": now(),
                "model": model,
                "router": router_meta,
            }
            session["messages"].append(assistant_msg)
            session["message_count"] = len(session["messages"])
            session["updated_at"] = now()

            if session["message_count"] == 2:
                session["title"] = generate_title(content)

            move_session_to_top(sessions, session_id)
            save_sessions(sessions)
            usage = record_usage_message("local")

            yield (
                "event: done\n"
                f"data: {json.dumps({'message': assistant_msg, 'session_id': session_id, 'title': session['title'], 'usage': usage, 'router': router_meta}, ensure_ascii=False)}\n\n"
            )

        except Exception as e:
            yield (
                "event: error\n"
                f"data: {json.dumps({'message': str(e), 'session_id': session_id}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)