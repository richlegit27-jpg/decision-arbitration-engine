from __future__ import annotations

import os
import re
import shutil
import hashlib
from datetime import datetime
from pathlib import Path


from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from bs4 import BeautifulSoup
import uuid


def update_execution_state_safe(execution, status=None, current_step=None, last_action=None):
    """Safely assign status, current_step, last_action in execution dict."""
    if status is not None:
        execution["status"] = status
    if current_step is not None:
        execution["current_step"] = current_step
    if last_action is not None:
        execution["last_action"] = last_action

from werkzeug.utils import secure_filename
from nova_backend.routes.memory_panel_routes import register_memory_panel_routes
from nova_backend.utils.api_response import ok_response, error_response
from nova_backend.utils.request_utils import get_json_body, get_str, get_list, normalize_attachments
from nova_backend.services.attachment_memory_service import (
    persist_attachments_for_session,
    summarize_attachments_for_session,
)
from nova_backend.utils.route_guard import guarded_json_route
from nova_backend.config import (
    BASE_DIR,
    DATA_DIR,
    UPLOADS_DIR,
    SESSIONS_FILE,
    ARTIFACTS_FILE,
    MEMORY_FILE,
    WEB_TIMEOUT,
    RECON_TIMEOUT,
)

from nova_backend.services.session_service import SessionService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.web_service import WebService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.intent_router_service import IntentRouterService
from nova_backend.utils.file_utils import ensure_dir
from nova_backend.services.chat_service import ChatService
from nova_backend.services.execution_handler import NextMove, default_executor
from nova_backend.services.execution_daemon import ExecutionDaemon
from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)
from nova_backend.services.runtime_bootstrap import (
    RuntimeBootstrap,
)

from nova_backend.services.runtime_response_sanitizer_service import (
    RuntimeResponseSanitizerService,
)

# -----------------------
# APP SETUP
# -----------------------

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

CORS(app)

ensure_dir(DATA_DIR)
ensure_dir(UPLOADS_DIR)

app.config["UPLOAD_FOLDER"] = str(UPLOADS_DIR)

# -----------------------
# SERVICES
# -----------------------

session_service = SessionService(str(SESSIONS_FILE))
artifact_service = ArtifactService(str(ARTIFACTS_FILE))
memory_service = MemoryService(str(MEMORY_FILE))
web_service = WebService(timeout=WEB_TIMEOUT)
recon_service = ReconService(timeout=RECON_TIMEOUT)
intent_router = IntentRouterService()
runtime_brain = SafeUnifiedRuntime()
runtime_response_sanitizer = RuntimeResponseSanitizerService()

restored_runtime = getattr(
    runtime_brain,
    "restored_runtime_state",
    {},
)

print(
    "RESTORED RUNTIME OK",
    {
        "runtime_health": restored_runtime.get(
            "runtime_health"
        ),
        "runtime_signal": restored_runtime.get(
            "runtime_signal"
        ),
        "cycle_count": restored_runtime.get(
            "cycle_count"
        ),
    },
)

last_compressed = getattr(
    runtime_brain,
    "last_compressed_runtime",
    {},
)

print(
    "LAST COMPRESSED OK",
    {
        "runtime_health": last_compressed.get(
            "runtime_health"
        ),
        "runtime_signal": last_compressed.get(
            "runtime_signal"
        ),
        "cycle_count": last_compressed.get(
            "cycle_count"
        ),
    },
)

chat_service = ChatService(
    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service,
    web_service=web_service,
    recon_service=recon_service,
)

# =========================
# RUNTIME BINDING
# =========================

chat_service.runtime = runtime_brain
chat_service.safe_runtime = runtime_brain
chat_service.runtime_brain = runtime_brain

app.runtime_brain = runtime_brain
app.config["runtime_brain"] = runtime_brain

RuntimeBootstrap.save(
    runtime_brain
)

if hasattr(chat_service, "start_execution_daemon"):
    chat_service.start_execution_daemon()

# REMOVE_APP_STARTUP_CHATSERVICE_DEBUG_LOCK

# -----------------------
# HELPERS
# -----------------------

IDENTITY_QUESTION_PATTERNS = [
    re.compile(r"\bwhat(?:'s| is)\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+know\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+know\s+about\s+me\b", re.IGNORECASE),
]

NAME_MEMORY_PATTERNS = [
    re.compile(r"^\s*user\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*my\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
]


def json_ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)



def json_error(message: str, status: int = 400, **kwargs):
    payload = {"ok": False, "error": str(message)}
    payload.update(kwargs)
    return jsonify(payload), status

def request_json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def build_common_state_payload(session_id: str = "") -> dict:
    session = None
    if session_id:
        session = session_service.get_session(session_id)
    if not session:
        session = session_service.get_active()

    return {
        "session": session,
        "sessions": session_service.get_all(),
        "active_session_id": session_service.active_session_id,
        "artifacts": artifact_service.build_list_payload(),
        "memory": memory_service.build_list_payload(),
    }


def _clean_fact_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = re.sub(r"\s+", " ", raw)
    return raw[:1].upper() + raw[1:]


def extract_memory_fact(user_text: str) -> dict | None:
    text = str(user_text or "").strip()
    if not text:
        return None

    patterns = [
        (
            re.compile(r"\bmy name is\s+([A-Za-z][A-Za-z0-9_\-']{0,40})\b", re.IGNORECASE),
            "profile",
            ["identity", "name"],
            5.0,
            lambda m: f"User name is {_clean_fact_value(m.group(1))}",
        ),
        (
            re.compile(r"\bi am\s+([A-Za-z][A-Za-z0-9_\-']{0,40})\b", re.IGNORECASE),
            "profile",
            ["identity"],
            3.5,
            lambda m: f"User says they are {_clean_fact_value(m.group(1))}",
        ),
        (
            re.compile(r"\bi prefer\s+(.+)$", re.IGNORECASE),
            "preference",
            ["preference"],
            2.5,
            lambda m: f"User preference: {m.group(1).strip()}",
        ),
        (
            re.compile(r"\bremember that\s+(.+)$", re.IGNORECASE),
            "note",
            ["memory"],
            2.0,
            lambda m: m.group(1).strip(),
        ),
    ]

    for pattern, kind, tags, weight, builder in patterns:
        match = pattern.search(text)
        if not match:
            continue

        fact_text = str(builder(match) or "").strip()
        if not fact_text:
            continue

        return {
            "text": fact_text,
            "kind": kind,
            "tags": tags,
            "weight": float(weight),
        }

    return None


def memory_exists_for_session(session_id: str, fact_text: str) -> bool:
    target_session = str(session_id or "").strip()
    target_text = str(fact_text or "").strip().lower()
    if not target_text:
        return False

    try:
        for item in memory_service.all():
            item_text = str(item.get("text") or "").strip().lower()
            item_session = str(item.get("session_id") or "").strip()
            if item_text == target_text and item_session == target_session:
                return True
    except Exception:
        return False

    return False


def extract_name_from_memory_text(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    for pattern in NAME_MEMORY_PATTERNS:
        match = pattern.search(raw)
        if match:
            name = str(match.group(1) or "").strip()
            name = re.sub(r"[^\w\s'\-]", "", name).strip()
            if name:
                return _clean_fact_value(name)

    return ""


def find_best_name_memory(session_id: str) -> dict | None:
    target_session = str(session_id or "").strip()
    all_memory = memory_service.all() or []
    candidates = []

    for item in all_memory:
        if not isinstance(item, dict):
            continue

        item_text = str(item.get("text") or "").strip()
        if not item_text:
            continue

        name = extract_name_from_memory_text(item_text)
        if not name:
            continue

        item_session = str(item.get("session_id") or "").strip()
        item_kind = str(item.get("kind") or "").strip().lower()
        item_source = str(item.get("source") or "").strip().lower()
        item_updated = str(item.get("updated_at") or item.get("created_at") or "")
        weight = float(item.get("weight", 1.0) or 1.0)

        score = 0.0
        if item_session and item_session == target_session:
            score += 100.0
        elif not item_session:
            score += 20.0

        if item_kind == "profile":
            score += 25.0

        if item_source in {"router_auto", "manual", "assistant"}:
            score += 5.0

        if item_text.lower().startswith("user name is"):
            score += 15.0
        elif item_text.lower().startswith("name:"):
            score += 10.0
        elif item_text.lower().startswith("my name is"):
            score += 5.0

        score += weight

        candidates.append(
            {
                "score": score,
                "updated_at": item_updated,
                "name": name,
                "item": item,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda c: (
            float(c.get("score", 0.0)),
            str(c.get("updated_at") or ""),
        ),
        reverse=True,
    )
    return candidates[0]

# ==============================
# ==============================

IDENTITY_QUESTION_PATTERNS = [
    re.compile(r"\bwhat(?:'s| is)\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+know\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
]

NAME_VALUE_PATTERNS = [
    re.compile(r"^\s*user\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*my\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
]


def _clean_memory_value(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _normalize_name(value: str) -> str:
    value = _clean_memory_value(value)
    value = re.sub(r"[^\w\s'\-]", "", value).strip()
    if not value:
        return ""
    return value[:1].upper() + value[1:]


    raw = str(text or "").strip()
    if not raw:
        return False
    return any(p.search(raw) for p in IDENTITY_QUESTION_PATTERNS)


def extract_name_from_memory_text(text: str) -> str:
    raw = _clean_memory_value(text)
    if not raw:
        return ""

    for pattern in NAME_VALUE_PATTERNS:
        match = pattern.search(raw)
        if match:
            return _normalize_name(match.group(1))

    return ""


def is_name_memory_item(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    return bool(extract_name_from_memory_text(item.get("text", "")))


def get_memory_items():
    try:
        items = memory_service.all()
        return items if isinstance(items, list) else []
    except Exception:
        return []


def delete_memory_item(memory_id: str) -> bool:
    if not memory_id:
        return False

    for method_name in ("delete_memory", "delete", "remove"):
        method = getattr(memory_service, method_name, None)
        if callable(method):
            try:
                return bool(method(memory_id))
            except Exception:
                return False
    return False


def score_name_memory(item: dict, session_id: str) -> float:
    if not isinstance(item, dict):
        return -9999.0

    score = 0.0
    item_text = str(item.get("text") or "").strip()
    item_session = str(item.get("session_id") or "").strip()
    item_kind = str(item.get("kind") or "").strip().lower()
    item_source = str(item.get("source") or "").strip().lower()
    item_updated = str(item.get("updated_at") or item.get("created_at") or "")

    if not extract_name_from_memory_text(item_text):
        return -9999.0

    if item_session and item_session == str(session_id or "").strip():
        score += 100.0
    elif not item_session:
        score += 15.0

    if item_kind == "profile":
        score += 20.0

    if item_source in {"router_auto", "assistant", "manual", "user"}:
        score += 5.0

    lowered = item_text.lower()
    if lowered.startswith("user name is"):
        score += 15.0
    elif lowered.startswith("name:"):
        score += 10.0
    elif lowered.startswith("my name is"):
        score += 5.0

    if item_updated:
        score += 1.0

    return score


def find_best_name_memory(session_id: str) -> dict | None:
    items = get_memory_items()
    candidates = []

    for item in items:
        score = score_name_memory(item, session_id)
        if score <= -9999.0:
            continue

        candidates.append({
            "item": item,
            "score": score,
            "updated_at": str(item.get("updated_at") or item.get("created_at") or ""),
            "name": extract_name_from_memory_text(item.get("text", "")),
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (x["score"], x["updated_at"]),
        reverse=True,
    )
    return candidates[0]


def cleanup_competing_name_memories(session_id: str, winning_text: str):
    target_session = str(session_id or "").strip()
    winning_text = str(winning_text or "").strip().lower()
    if not winning_text:
        return

    for item in get_memory_items():
        if not isinstance(item, dict):
            continue

        item_id = str(item.get("id") or "").strip()
        item_session = str(item.get("session_id") or "").strip()
        item_text = str(item.get("text") or "").strip().lower()

        if not item_id:
            continue
        if item_session != target_session:
            continue
        if not is_name_memory_item(item):
            continue
        if item_text == winning_text:
            continue

        delete_memory_item(item_id)
# -----------------------
# PAGE ROUTES
# -----------------------

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/preview")
def preview():
    return render_template("preview_index.html")

@app.get("/mobile")
def mobile():
    return render_template("mobile.html")




# -----------------------
# HEALTH
# -----------------------

@app.get("/api/health")
def api_health():
    return json_ok(
        status="ready",
        app="nova",
        cwd=os.getcwd(),
        base_dir=str(BASE_DIR),
        uploads_dir=str(UPLOADS_DIR),
        sessions_file=str(SESSIONS_FILE),
        artifacts_file=str(ARTIFACTS_FILE),
        memory_file=str(MEMORY_FILE),
        route_build="backend-memory-recall-fix-phase-1-001",
    )


# -----------------------
# STATE
# -----------------------

@app.get("/api/state")
def api_state():
    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )


# -----------------------
# CHAT
# -----------------------

@app.route("/api/runtime/summary", methods=["GET"])
def api_runtime_summary():
    return jsonify({"ok": True})

@app.route("/api/runtime/history", methods=["GET"])
def api_runtime_history():
    return jsonify({"ok": True})

@app.route("/api/runtime/decision", methods=["GET"])
def api_runtime_decision():
    return jsonify({"ok": True})

@app.route("/api/runtime/bridge", methods=["POST"])
def api_runtime_bridge():
    return jsonify({"ok": True})

@app.route("/api/runtime/cycle", methods=["POST"])
def api_runtime_cycle():
    try:
        runtime = runtime_brain

        result = runtime.run_cycle(
            execution_state={
                "status": "failed",
                "error": "api_runtime_cycle_test",
                "steps": [
                    {
                        "title": "Runtime API cycle test",
                        "status": "failed",
                    }
                ],
            },
            world_state={},
            scheduler_state={},
            knowledge_graph={},
        )

        runtime.last_compressed_runtime = (
            result.get(
                "compressed_runtime",
                {}
            )
        )

        summary = getattr(
            runtime,
            "last_compressed_runtime",
            {},
        )

        return jsonify(
            {
                "ok": True,
                "result": result,
                "runtime": summary,
            }
        )

    except Exception as e:
        return jsonify(
            {
                "ok": False,
                "error": str(e),
            }
        ), 500

@app.post("/api/fetch")
def api_fetch():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()

    if not url:
        return jsonify({
            "ok": False,
            "error": "Missing url",
            "summary": "",
        }), 400

    result = web_service.fetch(url)

    clean_result = (
        runtime_response_sanitizer.sanitize(
            result
        )
    )

    return jsonify(clean_result)

@app.get("/api/sessions")
def api_sessions():
    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )


# PROJECT_AWARE_MEMORY_CONTEXT_LOCK
def _nova_pa_read_json_file(path):
    try:
        if not path.exists():
            return None

        json_module = __import__("json")
        return json_module.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _nova_pa_compact_text(value, *, limit=500):
    text_value = str(value or "").replace("\r", "\n").strip()

    while "\n\n\n" in text_value:
        text_value = text_value.replace("\n\n\n", "\n\n")

    if len(text_value) > limit:
        return text_value[:limit].rstrip() + "..."

    return text_value


def _nova_pa_memory_text(item):
    if isinstance(item, str):
        return item.strip()

    if not isinstance(item, dict):
        return ""

    for key in (
        "text",
        "content",
        "memory",
        "summary",
        "value",
        "note",
        "description",
    ):
        value = item.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


# MEMORY_HYGIENE_CONTEXT_FILTER_LOCK
def _nova_memory_hygiene_normalize_key(value):
    text_value = str(value or "").strip().lower()
    text_value = re.sub(r"\s+", " ", text_value)
    return text_value[:500]


def _nova_memory_hygiene_is_junk(text_value, kind=""):
    raw = str(text_value or "").strip()
    lowered = raw.lower()
    item_kind = str(kind or "").strip().lower()

    if not lowered:
        return True

    junk_markers = (
        "project-aware context for nova:",
        "relevant persistent memory:",
        "session attachment memory:",
    )

    # If memory accidentally swallowed generated context blocks, stop injecting it again.
    if sum(lowered.count(marker) for marker in junk_markers) >= 2:
        return True

    stale_project_markers = (
        "remote push is still finishing",
        "expanding project-aware memory",
        "project focus recall cleanup committed",
        "backend intelligence context testing",
    )

    if item_kind in {"note", "user_fact", "project_focus"}:
        if any(marker in lowered for marker in stale_project_markers):
            return True

    # Old test instruction that previously overpowered normal answers.
    if lowered.strip() in {
        "say pong only",
        "user preference/correction: say pong only",
    }:
        return True

    if lowered.count("say pong only") >= 2:
        return True

    if lowered.count("what is my current task") >= 2:
        return True

    return False


def _nova_memory_hygiene_score_penalty(text_value, kind=""):
    lowered = str(text_value or "").strip().lower()
    item_kind = str(kind or "").strip().lower()
    penalty = 0

    if item_kind in {"project_focus", "user_fact", "note"}:
        if "current task is" in lowered or "blocker:" in lowered:
            penalty += 200

    if "project-aware context for nova:" in lowered:
        penalty += 500

    if "say pong only" in lowered:
        penalty += 1000

    return penalty


def _nova_pa_memory_kind(item):
    if not isinstance(item, dict):
        return "memory"

    return str(
        item.get("kind")
        or item.get("type")
        or item.get("category")
        or "memory"
    ).strip() or "memory"


def _nova_pa_memory_priority(item):
    if not isinstance(item, dict):
        return 0

    value = item.get("priority", 0)

    try:
        return int(value)
    except Exception:
        return 0


def _nova_pa_extract_memory_items(payload):
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in (
        "items",
        "memories",
        "memory",
        "records",
        "data",
    ):
        value = payload.get(key)

        if isinstance(value, list):
            return value

    return []


def _nova_pa_score_memory_item(item, query_words):
    text_value = _nova_pa_memory_text(item)
    lowered = text_value.lower()

    overlap = sum(
        1
        for word in query_words
        if word and word in lowered
    )

    priority = _nova_pa_memory_priority(item)

    return (overlap * 10) + priority


def _nova_pa_get_memory_context(user_text, *, limit=12, char_limit=3500):
    payload = _nova_pa_read_json_file(DATA_DIR / "nova_memory.json")
    items = _nova_pa_extract_memory_items(payload)

    if not items:
        return []

    query_words = {
        word.strip(".,!?;:()[]{}\"'").lower()
        for word in str(user_text or "").split()
        if len(word.strip(".,!?;:()[]{}\"'")) >= 4
    }

    scored = []

    for item in items:
        text_value = _nova_pa_memory_text(item)

        if not text_value:
            continue

        kind = _nova_pa_memory_kind(item)

        if _nova_memory_hygiene_is_junk(text_value, kind):
            continue

        score = _nova_pa_score_memory_item(item, query_words)
        score = score - _nova_memory_hygiene_score_penalty(text_value, kind)

        scored.append(
            (
                score,
                _nova_pa_memory_priority(item),
                text_value,
                kind,
            )
        )

    scored.sort(
        key=lambda row: (
            row[0],
            row[1],
        ),
        reverse=True,
    )

    lines = []
    seen = set()
    used = 0

    for _score, _priority, text_value, kind in scored:
        compact = _nova_pa_compact_text(text_value, limit=450)
        key = _nova_memory_hygiene_normalize_key(compact)

        if key in seen:
            continue

        seen.add(key)

        line = f"- [{kind}] {compact}"

        if used + len(line) > char_limit:
            break

        lines.append(line)
        used += len(line)

        if len(lines) >= limit:
            break

    return lines


def _nova_pa_message_text(message):
    if isinstance(message, str):
        return message.strip()

    if not isinstance(message, dict):
        return ""

    for key in (
        "text",
        "content",
        "message",
        "body",
    ):
        value = message.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _nova_pa_get_recent_session_context(session_id, *, limit=12, char_limit=3500):
    target_session_id = str(session_id or "").strip()

    if not target_session_id:
        return []

    try:
        session = session_service.get_session(target_session_id)
    except Exception:
        session = None

    if not isinstance(session, dict):
        return []

    messages = session.get("messages") or []

    if not isinstance(messages, list):
        return []

    lines = []
    used = 0

    for message in messages[-limit:]:
        if not isinstance(message, dict):
            continue

        role = str(message.get("role") or "message").strip()
        text_value = _nova_pa_message_text(message)

        if not text_value:
            continue

        compact = _nova_pa_compact_text(text_value, limit=350)
        line = f"- [{role}] {compact}"

        if used + len(line) > char_limit:
            break

        lines.append(line)
        used += len(line)

    return lines


def _nova_build_project_aware_context(
    user_text,
    *,
    session_id="",
    requested_session_id="",
):
    context_lines = []

    try:
        memory_lines = _nova_pa_get_memory_context(user_text)
    except Exception:
        memory_lines = []
        app.logger.exception("[project-aware] failed loading persistent memory context")

    if memory_lines:
        context_lines.append("Relevant persistent memory:")
        context_lines.extend(memory_lines)

    session_context_id = str(session_id or requested_session_id or "").strip()

    try:
        recent_lines = _nova_pa_get_recent_session_context(session_context_id)
    except Exception:
        recent_lines = []
        app.logger.exception("[project-aware] failed loading recent session context")

    if recent_lines:
        if context_lines:
            context_lines.append("")

        context_lines.append("Recent session context:")
        context_lines.extend(recent_lines)

    app.logger.info(
        "[project-aware] built context session_id=%s requested_session_id=%s memory_lines=%s recent_lines=%s total_lines=%s",
        session_id,
        requested_session_id,
        len(memory_lines or []),
        len(recent_lines or []),
        len(context_lines or []),
    )

    if not context_lines:
        return ""

    return "\n".join([
        "",
        "Project-aware context for Nova:",
        *context_lines,
    ]).strip()


# PROJECT_FOCUS_MEMORY_SAVE_RECALL_LOCK
def _nova_project_focus_memory_text(focus):
    focus_value = str(focus or "").strip()

    if not focus_value:
        return ""

    return f"Current project focus: {focus_value}"


def _nova_extract_project_focus_from_text(text_value):
    raw = str(text_value or "").strip()

    if not raw:
        return ""

    patterns = [
        r"\bmy\s+current\s+project\s+focus\s+is\s+(.+?)(?:[.!?\n]|$)",
        r"\bcurrent\s+project\s+focus\s+is\s+(.+?)(?:[.!?\n]|$)",
        r"\bproject\s+focus\s+is\s+(.+?)(?:[.!?\n]|$)",
        r"\bfocus\s+is\s+(.+?)(?:[.!?\n]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)

        if not match:
            continue

        focus = str(match.group(1) or "").strip()
        focus = re.sub(r"\s+", " ", focus).strip(" .!?")

        if focus:
            return focus

    return ""


def _nova_save_project_focus_memory(user_text, session_id):
    focus = _nova_extract_project_focus_from_text(user_text)

    if not focus:
        return None

    memory_text = _nova_project_focus_memory_text(focus)

    if not memory_text:
        return None

    target_session_id = str(session_id or "").strip()

    try:
        for item in memory_service.all() or []:
            if not isinstance(item, dict):
                continue

            item_text = str(item.get("text") or "").strip().lower()
            item_session = str(item.get("session_id") or "").strip()

            if (
                item_text == memory_text.lower()
                and item_session == target_session_id
            ):
                return item
    except Exception:
        app.logger.exception("[project-focus-memory] failed duplicate scan")

    try:
        item = memory_service.add_memory(
            {
                "text": memory_text,
                "kind": "project_focus",
                "source": "project_focus_direct",
                "session_id": target_session_id,
            }
        )

        app.logger.info(
            "[project-focus-memory] saved focus session_id=%s focus=%s",
            target_session_id,
            focus,
        )

        return item

    except Exception:
        app.logger.exception("[project-focus-memory] failed saving focus")
        return None


def _nova_find_project_focus_memory(session_id):
    target_session_id = str(session_id or "").strip()
    candidates = []

    try:
        items = memory_service.all() or []
    except Exception:
        items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        item_text = str(item.get("text") or "").strip()
        item_session = str(item.get("session_id") or "").strip()
        item_kind = str(item.get("kind") or "").strip().lower()
        item_updated = str(item.get("updated_at") or item.get("created_at") or "")

        if not item_text.lower().startswith("current project focus:"):
            continue

        if target_session_id and item_session and item_session != target_session_id:
            continue

        focus = item_text.split(":", 1)[1].strip() if ":" in item_text else ""

        if not focus:
            continue

        score = 0

        if item_session == target_session_id:
            score += 100

        if item_kind == "project_focus":
            score += 25

        candidates.append(
            {
                "score": score,
                "updated_at": item_updated,
                "focus": focus,
                "item": item,
            }
        )

    if not candidates:
        return ""

    candidates.sort(
        key=lambda row: (
            row.get("score", 0),
            str(row.get("updated_at") or ""),
        ),
        reverse=True,
    )

    return str(candidates[0].get("focus") or "").strip()


def _nova_find_recent_project_focus(session_id):
    target_session_id = str(session_id or "").strip()

    if not target_session_id:
        return ""

    try:
        session = session_service.get_session(target_session_id)
    except Exception:
        session = None

    if not isinstance(session, dict):
        return ""

    messages = session.get("messages") or []

    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue

        role = str(message.get("role") or "").strip().lower()

        if role not in {"user", "message"}:
            continue

        message_text = _nova_pa_message_text(message)
        focus = _nova_extract_project_focus_from_text(message_text)

        if focus:
            return focus

    return ""


def _nova_is_project_focus_recall_question(user_text):
    text_value = str(user_text or "").strip().lower()

    if not text_value:
        return False

    project_terms = (
        "project focus",
        "current focus",
        "focus right now",
        "what was my focus",
        "what is my focus",
        "what's my focus",
    )

    personal_terms = (
        "my ",
        "i ",
        "me",
        "our ",
        "nova",
        "current",
    )

    return (
        any(term in text_value for term in project_terms)
        and any(term in text_value for term in personal_terms)
    )


def _nova_try_project_focus_direct_recall(user_text, session_id):
    if not _nova_is_project_focus_recall_question(user_text):
        return None

    focus = _nova_find_recent_project_focus(session_id)

    if not focus:
        focus = _nova_find_project_focus_memory(session_id)

    if not focus:
        return None

    payload = build_common_state_payload(session_id=session_id)

    payload.update(
        {
            "assistant_message": {
                "role": "assistant",
                "text": f"Your current project focus was {focus}.",
            },
            "active_session_id": session_id,
            "debug": {
                "direct_recall": "project_focus",
                "focus": focus,
            },
        }
    )

    return json_ok(**payload)


# PROJECT_STATE_MEMORY_LOCK
# PROJECT_STATE_DEDICATED_STORE_LOCK
PROJECT_STATE_FILE = DATA_DIR / "nova_project_state.json"


def _nova_project_state_now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _nova_read_project_state_store():
    try:
        if not PROJECT_STATE_FILE.exists():
            return {"sessions": {}}

        import json
        # PROJECT_STATE_UTF8_SIG_LOCK
        payload = json.loads(PROJECT_STATE_FILE.read_text(encoding="utf-8-sig"))

        if not isinstance(payload, dict):
            return {"sessions": {}}

        sessions = payload.get("sessions")

        if not isinstance(sessions, dict):
            payload["sessions"] = {}

        return payload

    except Exception:
        app.logger.exception("[project-state-store] failed reading store")
        return {"sessions": {}}


def _nova_write_project_state_store(payload):
    try:
        import json

        if not isinstance(payload, dict):
            payload = {"sessions": {}}

        if not isinstance(payload.get("sessions"), dict):
            payload["sessions"] = {}

        PROJECT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROJECT_STATE_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return True

    except Exception:
        app.logger.exception("[project-state-store] failed writing store")
        return False


def _nova_get_project_state_session(session_id):
    store = _nova_read_project_state_store()
    sessions = store.setdefault("sessions", {})
    target_session_id = str(session_id or "").strip()

    if not target_session_id:
        return {}

    session_state = sessions.get(target_session_id)

    if not isinstance(session_state, dict):
        return {}

    return session_state


def _nova_set_project_state_values(session_id, values):
    target_session_id = str(session_id or "").strip()

    if not target_session_id:
        return {}

    store = _nova_read_project_state_store()
    sessions = store.setdefault("sessions", {})
    session_state = sessions.get(target_session_id)

    if not isinstance(session_state, dict):
        session_state = {}

    for item in values or []:
        if not isinstance(item, dict):
            continue

        kind = str(item.get("kind") or "").strip()
        value = _nova_clean_project_state_value(item.get("value"))

        if not kind or kind not in PROJECT_STATE_MEMORY_KINDS:
            continue

        if not value:
            continue

        session_state[kind] = value

    session_state["updated_at"] = _nova_project_state_now()
    sessions[target_session_id] = session_state
    store["sessions"] = sessions

    _nova_write_project_state_store(store)

    return session_state


PROJECT_STATE_MEMORY_KINDS = {
    "current_task": {
        "label": "Current task",
        "answer": "Your current task was {value}.",
        "save_patterns": [
            r"\bmy\s+current\s+task\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bcurrent\s+task\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\btask\s*:\s*(.+?)(?:[.!?\n]|$)",
            r"\bnext\s+move\s+is\s+(.+?)(?:[.!?\n]|$)",
        ],
        "recall_terms": [
            "what is my current task",
            "what's my current task",
            "what was my current task",
            "what are we doing",
            "what are we working on",
            "what is the next move",
            "what's the next move",
        ],
    },
    "blocker": {
        "label": "Blocker",
        "answer": "Your current blocker was {value}.",
        "save_patterns": [
            r"\bblocker\s*:\s*(.+?)(?:[.!?\n]|$)",
            r"\bmy\s+blocker\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bcurrent\s+blocker\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bblocked\s+by\s+(.+?)(?:[.!?\n]|$)",
        ],
        "recall_terms": [
            "what is blocking me",
            "what's blocking me",
            "what was blocking me",
            "what is the blocker",
            "what's the blocker",
            "current blocker",
        ],
    },
    "active_file": {
        "label": "Active file",
        "answer": "Your active file was {value}.",
        "save_patterns": [
            r"\bactive\s+file\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bcurrent\s+file\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bworking\s+on\s+file\s+(.+?)(?:[.!?\n]|$)",
            r"\bfile\s*:\s*(.+?)(?:[.!?\n]|$)",
        ],
        "recall_terms": [
            "what file am i working on",
            "which file am i working on",
            "what is the active file",
            "what's the active file",
            "current file",
            "active file",
        ],
    },
    "last_checkpoint": {
        "label": "Last checkpoint",
        "answer": "Your last checkpoint was {value}.",
        "save_patterns": [
            r"\blast\s+checkpoint\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bcheckpoint\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bcheckpointed\s+at\s+(.+?)(?:[.!?\n]|$)",
            r"\blockpoint\s+is\s+(.+?)(?:[.!?\n]|$)",
        ],
        "recall_terms": [
            "what was my last checkpoint",
            "what is my last checkpoint",
            "where did we checkpoint",
            "last checkpoint",
            "current checkpoint",
            "lockpoint",
        ],
    },
}


def _nova_clean_project_state_value(value):
    cleaned = str(value or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .!?")

    return cleaned

def _nova_project_state_memory_text(kind: str, value: str) -> str:
    """
    Return a single line text for the project-state kind, avoiding duplicate labels.
    """
    config = PROJECT_STATE_MEMORY_KINDS.get(kind) or {}
    label = str(config.get("label") or kind).strip()

    # remove repeated prefix if value already starts with it
    if value.lower().startswith(label.lower()):
        return f"{label}: {value[len(label)+1:].strip()}"
    return f"{label}: {value.strip()}"

# PROJECT_STATE_LABEL_EXTRACTOR_LOCK
def _nova_extract_project_state_values(user_text):
    raw = str(user_text or "").strip()
    found = []

    if not raw:
        return found

    label_patterns = {
        "current_task": [
            r"current\s+task\s+is\s+",
            r"my\s+current\s+task\s+is\s+",
            r"task\s*:\s*",
            r"next\s+move\s+is\s+",
        ],
        "blocker": [
            r"blocker\s+is\s+",
            r"blocker\s*:\s*",
            r"my\s+blocker\s+is\s+",
            r"current\s+blocker\s+is\s+",
            r"blocked\s+by\s+",
        ],
        "active_file": [
            r"active\s+file\s+is\s+",
            r"current\s+file\s+is\s+",
            r"working\s+on\s+file\s+",
            r"file\s*:\s*",
        ],
        "last_checkpoint": [
            r"last\s+checkpoint\s+is\s+",
            r"checkpoint\s+is\s+",
            r"checkpointed\s+at\s+",
            r"lockpoint\s+is\s+",
        ],
    }

    label_start_parts = []
    for patterns in label_patterns.values():
        label_start_parts.extend(patterns)

    for kind, patterns in label_patterns.items():
        for pattern in patterns:
            combined = (
                r"\b"
                + pattern
                + r"(.+?)(?=\.\s+(?:"
                + "|".join(label_start_parts)
                + r")|\n|$)"
            )

            match = re.search(combined, raw, re.IGNORECASE)

            if not match:
                continue

            value = _nova_clean_project_state_value(match.group(1))

            if value:
                found.append(
                    {
                        "kind": kind,
                        "value": value,
                    }
                )
                break

    return found


def _nova_save_project_state_memories(user_text, session_id):
    extracted = _nova_extract_project_state_values(user_text)

    if not extracted:
        return []

    state = _nova_set_project_state_values(session_id, extracted)

    saved = []

    for item in extracted:
        kind = str(item.get("kind") or "").strip()
        value = _nova_clean_project_state_value(item.get("value"))

        if kind and value:
            saved.append(
                {
                    "kind": kind,
                    "value": value,
                    "session_id": str(session_id or "").strip(),
                    "source": "project_state_dedicated_store",
                    "state": state,
                }
            )

    app.logger.info(
        "[project-state-store] saved kinds=%s session_id=%s",
        ",".join([str(item.get("kind") or "") for item in extracted if isinstance(item, dict)]),
        session_id,
    )

    return saved


# PROJECT_STATE_RECALL_OVERRIDE_LOCK
def _nova_project_state_question_kinds(user_text):
    text_value = str(user_text or "").strip().lower()
    kinds = []

    if not text_value:
        return kinds

    asks_next_or_state = any(
        term in text_value
        for term in (
            "what's next",
            "whats next",
            "what is next",
            "next move",
            "current task",
            "what are we doing",
            "what are we working on",
            "current project state",
            "project state",
            "task and blocker",
            "current task and blocker",
        )
    )

    if asks_next_or_state:
        return list(PROJECT_STATE_MEMORY_KINDS.keys())

    for kind, config in PROJECT_STATE_MEMORY_KINDS.items():
        for term in config.get("recall_terms") or []:
            if term in text_value and kind not in kinds:
                kinds.append(kind)

    if "blocker" in text_value and "blocker" not in kinds:
        kinds.append("blocker")

    if "checkpoint" in text_value and "last_checkpoint" not in kinds:
        kinds.append("last_checkpoint")

    if "active file" in text_value and "active_file" not in kinds:
        kinds.append("active_file")

    return kinds


def _nova_question_project_state_kind(user_text):
    kinds = _nova_project_state_question_kinds(user_text)
    return kinds[0] if kinds else ""


def _nova_find_project_state_memory(session_id: str, kind: str) -> str:
    target_kind = str(kind or "").strip()

    if not target_kind or target_kind not in PROJECT_STATE_MEMORY_KINDS:
        return ""

    state = _nova_get_project_state_session(session_id)
    value = _nova_clean_project_state_value(state.get(target_kind))

    if value:
        return value

    return ""


# PROJECT_STATE_AUTO_INJECT_CONTEXT_LOCK
def _nova_build_project_state_context(session_id):
    state = _nova_get_project_state_session(session_id)

    if not isinstance(state, dict) or not state:
        return ""

    lines = []

    current_task = _nova_clean_project_state_value(state.get("current_task"))
    blocker = _nova_clean_project_state_value(state.get("blocker"))
    active_file = _nova_clean_project_state_value(state.get("active_file"))
    last_checkpoint = _nova_clean_project_state_value(state.get("last_checkpoint"))

    if current_task:
        lines.append(f"Current task: {current_task}")

    if blocker:
        lines.append(f"Blocker: {blocker}")

    if active_file:
        lines.append(f"Active file: {active_file}")

    if last_checkpoint:
        lines.append(f"Last checkpoint: {last_checkpoint}")

    if not lines:
        return ""

    return "\n".join(
        [
            "HIGH PRIORITY SESSION PROJECT STATE:",
            *lines,
            "",
            "Use this session project state as the source of truth for what the user is working on.",
            "Ignore unrelated stale persistent-memory instructions that conflict with this session project state.",
        ]
    )


def _nova_inject_project_state_context(user_text, session_id):
    context = _nova_build_project_state_context(session_id)

    if not context:
        return user_text

    clean_user_text = str(user_text or "").strip()

    if not clean_user_text:
        return context

    return f"{context}\n\nUser message:\n{clean_user_text}"


# SLIM_DIRECT_RECALL_PAYLOAD_LOCK
def _nova_slim_assistant_payload(text, session_id="", **extra):
    payload = {
        "ok": True,
        "assistant_message": {
            "role": "assistant",
            "text": str(text or "").strip(),
        },
        "active_session_id": str(session_id or "").strip(),
    }

    for key, value in extra.items():
        if value is not None:
            payload[key] = value

    return jsonify(payload)


def _nova_prevent_bad_exact_pong_response(assistant_text, user_text):
    clean_answer = str(assistant_text or "").strip()
    clean_user = str(user_text or "").strip().lower()

    if clean_answer.lower() != "pong":
        return clean_answer

    allowed_pong_requests = {
        "pong",
        "say pong",
        "say pong only",
        "reply pong",
        "reply with pong",
    }

    if clean_user in allowed_pong_requests:
        return clean_answer

    return "IÃ¢â‚¬â„¢m ready. What are we working on?"


def _nova_try_project_state_direct_recall(user_text, session_id):
    kinds = _nova_project_state_question_kinds(user_text)

    if not kinds:
        return None

    lines = []

    for kind in kinds:
        value = _nova_find_project_state_memory(session_id, kind)

        if not value:
            continue

        label = str(
            (PROJECT_STATE_MEMORY_KINDS.get(kind) or {}).get("label")
            or kind
        ).strip()

        clean_value = _nova_clean_project_state_value(value)

        if not clean_value:
            continue

        lines.append(f"{label}: {clean_value}")

    if not lines:
        return None

    answer_text = "\n".join(lines)

    app.logger.info(
        "[project-state-recall-override] answered kinds=%s session_id=%s",
        ",".join(kinds),
        session_id,
    )

    return _nova_slim_assistant_payload(
        answer_text,
        session_id=session_id,
        direct_recall="project_state",
        kinds=kinds,
    )


@app.post("/api/chat")
def api_chat():
    data = request_json()

    user_text = str(data.get("user_text") or "").strip()
    requested_session_id = str(data.get("session_id") or "").strip()
    session_id = requested_session_id
    attachments = normalize_attachments(data.get("attachments"))

    # BACKEND_ATTACHMENT_DEBUG_LOG_LOCK
    try:
        app.logger.info(
            "[api_chat] incoming request session_id=%s user_text_len=%s attachments_count=%s attachment_names=%s",
            session_id or "<missing>",
            len(user_text or ""),
            len(attachments or []),
            [
                (
                    item.get("original_filename")
                    or item.get("filename")
                    or item.get("name")
                    or item.get("url")
                    or item.get("file_url")
                    or "<unnamed>"
                )
                for item in (attachments or [])
                if isinstance(item, dict)
            ],
        )
    except Exception:
        app.logger.exception("[api_chat] failed while logging attachment debug info")

    regen_commands = {
        "regen",
        "regenerate",
        "redo image",
        "make another",
        "another image",
    }

    if user_text.lower().strip() in regen_commands:
        last_prompt = chat_service._get_session_meta(
            session_id,
            "last_image_prompt",
        ) or "generate an image"

        result = chat_service._handle_image_generation(
            prompt=last_prompt,
            session_id=session_id,
            parent_artifact_id="",
            source_type="regenerated",
        )

        return jsonify(result)

    if not session_id:
        active = session_service.get_active()
        if active:
            session_id = str(active.get("id") or "").strip()

    if not session_id:
        created = session_service.create("New Chat")
        session_id = created["id"]

    if not user_text and not attachments:
        return json_error("Missing user_text or attachments", 400)

    _nova_save_project_focus_memory(
        user_text,
        session_id,
    )

    _nova_save_project_state_memories(
        user_text,
        session_id,
    )

    direct_project_state_response = _nova_try_project_state_direct_recall(
        user_text,
        session_id,
    )

    if direct_project_state_response is not None:
        app.logger.info(
            "[project-state-direct-recall] answered from project state memory session_id=%s",
            session_id,
        )
        return direct_project_state_response

    direct_project_focus_response = _nova_try_project_focus_direct_recall(
        user_text,
        session_id,
    )

    if direct_project_focus_response is not None:
        app.logger.info(
            "[project-focus-direct-recall] answered from recent session context session_id=%s",
            session_id,
        )
        return direct_project_focus_response

    try:
        # REAL_ATTACHMENT_MEMORY_BACKEND_LOCK
        if attachments:
            try:
                added_attachment_memory = persist_attachments_for_session(
                    attachments,
                    session_id=session_id,
                    client_session_id=requested_session_id,
                )
                app.logger.info(
                    "[api_chat] persisted attachment memory count=%s session_id=%s",
                    added_attachment_memory,
                    session_id,
                )
            except Exception:
                app.logger.exception("[api_chat] failed to persist attachment memory")

        # PROJECT_AWARE_ATTACHMENT_CONTEXT_LOCK
        try:
            remembered_session_attachments = summarize_attachments_for_session(
                session_id,
                limit=25,
                client_session_id=requested_session_id,
            )
        except Exception:
            remembered_session_attachments = []
            app.logger.exception("[api_chat] failed to load remembered session attachments")

        # ATTACHMENT_CONTENT_INJECTION_FINAL_LOCK
        attachment_content_lines = []
        for attachment in remembered_session_attachments or []:
            attachment_filename = str(attachment.get("filename") or "").strip()
            attachment_original_filename = str(attachment.get("original_filename") or "").strip()

            if attachment_filename == "<unknown>":
                attachment_filename = ""

            if attachment_original_filename == "<unknown>":
                attachment_original_filename = ""

            raw_attachment_name = (
                attachment_filename
                or attachment_original_filename
                or Path(str(attachment.get("file_url") or "")).name
                or Path(str(attachment.get("url") or "")).name
                or ""
            )
            file_path = (UPLOADS_DIR / str(raw_attachment_name).strip().lstrip("/\\")).resolve()
            content_snippet = ""
            try:
                if file_path.exists() and file_path.is_file() and str(file_path).startswith(str(UPLOADS_DIR.resolve())):
                    content_snippet = file_path.read_text(encoding="utf-8", errors="replace")[:4000]
                    app.logger.info(
                        "[AttachmentContentFinal] loaded file content path=%s chars=%s",
                        str(file_path),
                        len(content_snippet),
                    )
                else:
                    app.logger.warning("[AttachmentContentFinal] file unavailable path=%s exists=%s", str(file_path), file_path.exists())
            except Exception as e:
                app.logger.warning("[AttachmentContentFinal] failed reading %s: %s", str(file_path), e)
            try:
                uploads_root = UPLOADS_DIR.resolve()

                if (
                    str(file_path).startswith(str(uploads_root))
                    and file_path.exists()
                    and file_path.is_file()
                ):
                    content_snippet = file_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )[:4000]
                    app.logger.info(
                        "[AttachmentContent] loaded file content path=%s chars=%s",
                        str(file_path),
                        len(content_snippet),
                    )
                else:
                    app.logger.warning(
                        "[AttachmentContent] file unavailable path=%s exists=%s",
                        str(file_path),
                        file_path.exists(),
                    )
            except Exception as e:
                app.logger.warning("[AttachmentContent] failed reading %s: %s", file_path, e)

            attachment_content_lines.append(
                f"Attachment {attachment.get('original_filename') or attachment.get('filename') or '<unknown>'} content:\n"
                f"{content_snippet if content_snippet else '[Attachment file was remembered, but readable text content was not available on disk.]'}"
            )

        if attachment_content_lines:
            attachment_content_text = "\n\n".join(attachment_content_lines)
            if user_text:
                user_text = f"{user_text}\n\n{attachment_content_text}"
            else:
                user_text = attachment_content_text

            app.logger.info(
                "[AttachmentContent] injected %s attachments content into user_text session_id=%s",
                len(attachment_content_lines),
                requested_session_id,
            )

        if remembered_session_attachments:
            attachment_context_lines = [
                "",
                "Session attachment memory:",
            ]

            for index, item in enumerate(remembered_session_attachments, start=1):
                attachment_context_lines.append(
                    f"{index}. "
                    f"name={item.get('original_filename') or item.get('filename') or '<unknown>'}; "
                    f"url={item.get('file_url') or ''}; "
                    f"type={item.get('mime_type') or ''}; "
                    f"size={item.get('size') or 0}"
                )

            attachment_context = "\n".join(attachment_context_lines)

            if user_text:
                user_text = f"{user_text}\n\n{attachment_context}"
            else:
                user_text = attachment_context.strip()

            app.logger.info(
                "[api_chat] injected project-aware attachment context count=%s session_id=%s",
                len(remembered_session_attachments),
                session_id,
            )

        user_text = _nova_inject_project_state_context(
            user_text,
            session_id,
        )

        try:
            project_aware_context = _nova_build_project_aware_context(
                user_text,
                session_id=session_id,
                requested_session_id=requested_session_id,
            )
        except Exception:
            project_aware_context = ""
            app.logger.exception("[api_chat] failed to build project-aware memory context")

        if project_aware_context:
            user_text = f"{user_text}\n\n{project_aware_context}" if user_text else project_aware_context

            app.logger.info(
                "[api_chat] injected project-aware memory context chars=%s session_id=%s requested_session_id=%s",
                len(project_aware_context),
                session_id,
                requested_session_id,
            )

        app.logger.info(
            "[api_chat] calling chat_service.handle session_id=%s attachments_count=%s",
            session_id,
            len(attachments or []),
        )

        result = chat_service.handle(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        try:
            app.logger.info(
                "[api_chat] chat_service.handle result ok=%s active_session_id=%s keys=%s",
                result.get("ok") if isinstance(result, dict) else None,
                result.get("active_session_id") if isinstance(result, dict) else None,
                sorted(list(result.keys())) if isinstance(result, dict) else type(result).__name__,
            )

            if isinstance(result, dict):
                active_attachment_session_id = str(
                    result.get("active_session_id")
                    or session_id
                    or ""
                ).strip()

                result["session_attachments"] = summarize_attachments_for_session(
                    active_attachment_session_id,
                    limit=25,
                    client_session_id=requested_session_id,
                )

                app.logger.info(
                    "[api_chat] returned session attachment memory count=%s session_id=%s",
                    len(result.get("session_attachments") or []),
                    active_attachment_session_id,
                )
        except Exception:
            app.logger.exception("[api_chat] failed while logging chat_service result")

        # TEMP DISABLED:
        # runtime_brain.run_cycle is crashing on undefined working_state.
        # Keep disabled until execution mutation is stable.
        # REMOVE_API_CHAT_RAW_RESULT_PRINT_LOCK

        if result is None:
            result = {
                "ok": False,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Nova returned no response from chat_service.handle().",
                },
                "session_id": session_id,
            }

        try:
            if isinstance(result, dict):
                session = result.get("session") or {}
                meta = session.get("meta") or {}

                if meta.get("pending_execution_action"):
                    meta["pending_execution_action"] = ""

                assistant_message = result.get("assistant_message") or {}
                assistant_meta = assistant_message.get("meta") or {}

                if assistant_meta.get("pending_execution_action"):
                    assistant_meta["pending_execution_action"] = ""

        except Exception as cleanup_error:
            print("PENDING EXECUTION CLEANUP FAILED:", cleanup_error)

        assistant_message = result.get("assistant_message") or {
            "role": "assistant",
            "text": "",
        }

        # API_CHAT_RESPONSE_CONTRACT_LOCK
        if not isinstance(assistant_message, dict):
            assistant_message = {
                "role": "assistant",
                "text": str(assistant_message or "").strip(),
            }

        assistant_message.setdefault("role", "assistant")

        assistant_text = str(
            assistant_message.get("text")
            or assistant_message.get("content")
            or assistant_message.get("message")
            or ""
        ).strip()

        if not assistant_text and result.get("ok", True):
            assistant_text = "Nova completed the request but returned an empty assistant response."

        assistant_text = _nova_prevent_bad_exact_pong_response(
            assistant_text,
            user_text,
        )

        assistant_message["text"] = assistant_text

        payload = {
            "ok": result.get("ok", True),
            "assistant_message": assistant_message,
            # ATTACHMENT_CONTEXT_RESPONSE_FIX_LOCK
            "session_attachments": (
                result.get("session_attachments")
                if isinstance(result, dict)
                else []
            ) or [],
            "attachment_debug": {
                "requested_session_id": requested_session_id,
                "active_session_id": (
                    result.get("active_session_id")
                    if isinstance(result, dict)
                    else session_id
                ),
                "session_attachments_count": len(
                    (
                        result.get("session_attachments")
                        if isinstance(result, dict)
                        else []
                    ) or []
                ),
            },
            "active_session_id": (
                result.get("active_session_id")
                or result.get("session_id")
                or session_id
            ),
            "session": (
                result.get("session")
                or session_service.get_session(session_id)
            ),
            "saved_artifact": result.get("saved_artifact"),
            "runtime": {},
            "debug": result.get("debug") or {},
        }

        return json_ok(
            **{
                k: v
                for k, v in payload.items()
                if v is not None
            }
        )

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return json_error(str(exc), 500)

@app.get("/api/chat/<session_id>")
def api_chat_session_compat(session_id: str):
    # MOBILE_MISSING_SESSION_SAFE_FALLBACK_LOCK
    requested_session_id = str(session_id or "").strip()

    session = session_service.get_session(requested_session_id)

    if not session:
        session = {
            "id": requested_session_id,
            "title": "New Chat",
            "messages": [],
            "created_at": "",
            "updated_at": "",
            "pinned": False,
            "working_state": {},
            "execution_state": {},
            "active_execution": None,
            "missing": True,
        }

        return json_ok(
            session=session,
            sessions=session_service.get_all(),
            active_session_id=requested_session_id,
            messages=[],
            missing_session=True,
            mobile_fallback=True,
        )

    return json_ok(
        session=session,
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        messages=session.get("messages") or [],
        missing_session=False,
        mobile_fallback=False,
    )


@app.get("/api/sessions/<session_id>")
def api_session_by_id(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session,
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/new")
def api_sessions_new():
    data = request_json()
    title = str(data.get("title") or "New Chat").strip() or "New Chat"

    session = session_service.create_session(title)
    if not session:
        return json_error("Failed to create session", 500)

    return json_ok(
        session=session_service.get_session(session["id"]),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/switch")
def api_sessions_switch():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.set_active(session_id)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/rename")
def api_sessions_rename():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    title = str(data.get("title") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.rename(session_id, title or "New Chat")
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/pin")
def api_sessions_pin():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    pinned = bool(data.get("pinned"))

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.pin(session_id, pinned)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/delete")
def api_sessions_delete():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    if not session_service.delete(session_id):
        return json_error("Session not found", 404)

    active_id = session_service.active_session_id
    active_session = session_service.get_active()

    return json_ok(
        session=active_session,
        sessions=session_service.get_all(),
        active_session_id=active_id,
    )

# -----------------------
# ARTIFACTS
# -----------------------

@app.get("/api/artifacts")
def api_artifacts():
    return json_ok(
        artifacts=artifact_service.build_list_payload(),
    )


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_view(artifact_id: str):
    payload = artifact_service.build_view_payload(artifact_id)
    if not payload:
        return json_error("Artifact not found", 404)

    return json_ok(
        artifact=payload,
    )

@app.delete("/api/artifacts/<artifact_id>")
def api_delete_artifact(artifact_id: str):
    try:
        ok = artifact_service.delete_artifact(artifact_id)

        return json_ok(
            ok=bool(ok),
            deleted_artifact_id=artifact_id,
            artifacts=artifact_service.build_list_payload(),
        )

    except Exception as e:
        return json_error(f"Failed to delete artifact: {e}", 500)

def delete_artifact(self, artifact_id: str) -> bool:
    try:
        data = self._load()

        artifacts = data.get("artifacts", [])

        new_artifacts = [
            a for a in artifacts
            if str(a.get("id")) != str(artifact_id)
        ]

        if len(new_artifacts) == len(artifacts):
            return False

        data["artifacts"] = new_artifacts
        self._save(data)

        return True

    except Exception as e:
        print("DELETE ARTIFACT ERROR:", e)
        return False

# -----------------------
# MEMORY
# -----------------------

@app.get("/api/memory")
@guarded_json_route
def api_memory():
    memory = memory_service.all()
    return ok_response(
        data={
            "memory": memory,
            "count": len(memory),
        },
        message="Memory loaded.",
    )


@app.post("/api/memory/add")
@guarded_json_route
def api_memory_add():
    data = get_json_body(request)

    text = get_str(data, "text")
    kind = get_str(data, "kind", "note") or "note"
    source = get_str(data, "source", "manual") or "manual"
    session_id = get_str(data, "session_id")

    if not text:
        return error_response(
            error="text is required.",
            code="missing_text",
        ), 400

    item = memory_service.add_memory({
        "text": text,
        "kind": kind,
        "source": source,
        "session_id": session_id,
    })

    memory = memory_service.all()

    memory = memory_service.all()

    return ok_response(
        data={
            "item": item,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory added.",
    )

@app.post("/api/memory/pin")
@guarded_json_route
def api_memory_pin():
    data = get_json_body(request)
    memory_id = get_str(data, "id") or get_str(data, "memory_id")
    pinned = bool(data.get("pinned", True))

    if not memory_id:
        return error_response(
            error="id is required.",
            code="missing_id",
        ), 400

    item = memory_service.pin_memory(memory_id, pinned=pinned)
    memory = memory_service.all()

    return ok_response(
        data={
            "item": item,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory pinned." if pinned else "Memory unpinned.",
    )

@app.post("/api/memory/delete")
@guarded_json_route
def api_memory_delete():
    data = get_json_body(request)
    memory_id = get_str(data, "id") or get_str(data, "memory_id")

    if not memory_id:
        return error_response(
            error="id is required.",
            code="missing_id",
        ), 400

    deleted = memory_service.delete_memory(memory_id)
    memory = memory_service.all()

    return ok_response(
        data={
            "deleted": deleted,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory deleted." if deleted else "Memory not found.",
    )

@app.post("/api/memory/update")
@guarded_json_route
def api_memory_update():
    data = get_json_body(request)

    memory_id = str(data.get("id") or "").strip()
    text = str(data.get("text") or "").strip()
    kind = str(data.get("kind") or "note").strip()

    if not memory_id:
        return error_response("Missing memory id", code="missing_id"), 400

    if not text:
        return error_response("Missing memory text", code="missing_text"), 400

    items = memory_service.all()

    updated = None
    for item in items:
        if str(item.get("id")) == memory_id:
            item["text"] = text
            item["kind"] = kind
            item["updated_at"] = iso_now()
            updated = item
            break

    if not updated:
        return error_response("Memory not found", code="not_found"), 404

    memory_service._write_store({"memory": items})

    return ok_response(
        item=updated,
        message="Memory updated."
    )

@app.post("/api/memory/cleanup")
@guarded_json_route
def api_memory_cleanup():
    result = memory_service.cleanup_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory cleanup complete.",
    )


@app.post("/api/memory/promote")
@guarded_json_route
def api_memory_promote():
    result = memory_service.promote_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory promotion complete.",
    )


@app.post("/api/memory/cleanup-promote")
@guarded_json_route
def api_memory_cleanup_promote():
    result = memory_service.cleanup_and_promote_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory cleanup and promotion complete.",
    )


# -----------------------
# WEB
# -----------------------

@app.post("/api/web/fetch")
def api_web_fetch():
    print("HIT API_WEB_FETCH ROUTE", flush=True)
    try:
        data = request.get_json(silent=True) or {}
        url = str(data.get("url") or "").strip()

        if not url:
            return jsonify({
                "ok": False,
                "error": "Missing url",
            }), 400

        try:
            result = web_service.fetch(url)
        except Exception as exc:
            result = {
                "ok": False,
                "url": url,
                "summary": "Preview unavailable. Open the full article instead.",
                "images": [],
                "error": str(exc),
            }

        if not isinstance(result, dict):
            result = {
                "ok": False,
                "url": url,
                "summary": "Preview unavailable. Open the full article instead.",
                "images": [],
                "error": "web_service.fetch returned non-dict result",
            }

        artifact = None
        if result.get("ok"):
            try:
                artifact = web_service.build_artifact_payload(result)
            except Exception as exc:
                result["artifact_error"] = str(exc)

        return jsonify({
            "ok": True,
            "result": result,
            "artifact": artifact,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "route": "/api/web/fetch",
        }), 200

# -----------------------
# RECON
# -----------------------

@app.post("/api/recon/analyze")
def api_recon_analyze():
    data = request_json()
    url = str(data.get("url") or "").strip()

    if not url:
        return json_error("Missing url", 400)

    result = recon_service.analyze_target(url)
    if not result.get("ok"):
        return json_error(result.get("error") or "Recon failed", 500, result=result)

    return json_ok(
        result=result,
        artifact=recon_service.build_artifact_payload(result),
    )

@app.post("/api/upload")
def api_upload():
    try:
        if "file" not in request.files:
            return jsonify({
                "ok": False,
                "error": "No file provided.",
            }), 400

        file = request.files["file"]
        if not file or not getattr(file, "filename", ""):
            return jsonify({
                "ok": False,
                "error": "Empty file.",
            }), 400

        original_name = os.path.basename(str(file.filename or "upload"))
        safe_name = secure_filename(original_name) or "upload.bin"

        base, ext = os.path.splitext(safe_name)
        ext = ext or ""
        final_name = f"{base}_{uuid.uuid4().hex}{ext}"

        save_path = UPLOADS_DIR / final_name
        file.save(str(save_path))

        mime_type = getattr(file, "mimetype", None) or "application/octet-stream"
        size = save_path.stat().st_size if save_path.exists() else 0

        app.logger.info(
            "[api_upload] saved upload original=%s stored=%s mime_type=%s size=%s url=%s",
            original_name,
            final_name,
            mime_type,
            size,
            f"/api/uploads/{final_name}",
        )

        return jsonify({
            "ok": True,
            "filename": final_name,
            "original_filename": original_name,
            "file_url": f"/api/uploads/{final_name}",
            "url": f"/api/uploads/{final_name}",
            "mime_type": mime_type,
            "size": size,
        })
    except Exception as e:
        app.logger.exception("api_upload failed")
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500

# -----------------------
# UPLOADS
# -----------------------
@app.get("/api/uploads/<path:filename>")
def api_uploads(filename: str):
    try:
        raw_name = str(filename or "").strip().lstrip("/\\")
        full_path = (UPLOADS_DIR / raw_name).resolve()
        uploads_root = UPLOADS_DIR.resolve()

        try:
            full_path.relative_to(uploads_root)
        except ValueError:
            app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")
            return jsonify({
                "ok": False,
                "error": "Invalid upload path",
                "filename": raw_name,
            }), 400

        if not full_path.exists() or not full_path.is_file():
            app.logger.warning(f"UPLOAD MISS: {full_path}")
            return jsonify({
                "ok": False,
                "error": "File not found",
                "filename": raw_name,
                "full_path": str(full_path),
                "uploads_dir": str(uploads_root),
            }), 404

        app.logger.info(f"UPLOAD HIT: {full_path}")
        return send_from_directory(
            directory=str(uploads_root),
            path=raw_name,
            as_attachment=False,
        )

    except TypeError:
        # Older Flask / Werkzeug compatibility
        try:
            raw_name = str(filename or "").strip().lstrip("/\\")
            full_path = (UPLOADS_DIR / raw_name).resolve()
            uploads_root = UPLOADS_DIR.resolve()

            try:
                full_path.relative_to(uploads_root)
            except ValueError:
                app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")
                return jsonify({
                    "ok": False,
                    "error": "Invalid upload path",
                    "filename": raw_name,
                }), 400

            if not full_path.exists() or not full_path.is_file():
                app.logger.warning(f"UPLOAD MISS: {full_path}")
                return jsonify({
                    "ok": False,
                    "error": "File not found",
                    "filename": raw_name,
                    "full_path": str(full_path),
                    "uploads_dir": str(uploads_root),
                }), 404

            app.logger.info(f"UPLOAD HIT: {full_path}")
            return send_from_directory(
                str(uploads_root),
                raw_name,
                as_attachment=False,
            )
        except Exception as e:
            app.logger.exception("api_uploads failed (compat path)")
            return jsonify({
                "ok": False,
                "error": str(e),
                "filename": str(filename or ""),
            }), 500

    except Exception as e:
        app.logger.exception("api_uploads failed")
        return jsonify({
            "ok": False,

            "error": str(e),
            "filename": str(filename or ""),
        }), 500

@app.route("/api/execution/control", methods=["POST"])
def execution_control():
    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id") or "").strip()
    action = str(data.get("action") or "").strip()

    if not session_id:
        return jsonify({
            "ok": False,
            "error": "missing session_id",
            "execution_state": {
                "status": "error",
                "steps": [],
                "history": ["missing session_id"],
            },
        }), 400

    if not action:
        return jsonify({
            "ok": False,
            "error": "missing action",
            "execution_state": {
                "status": "error",
                "steps": [],
                "history": ["missing action"],
            },
        }), 400

    working = chat_service._get_working_state(session_id) or {}
    execution = working.get("execution")

    if not isinstance(execution, dict):
        execution = {}

    steps = execution.get("steps")
    if not isinstance(steps, list):
        steps = []

    history = execution.get("history")
    if not isinstance(history, list):
        history = []

    execution = {
        "status": str(execution.get("status") or "idle"),
        "steps": steps,
        "history": history,
        "last_action": str(execution.get("last_action") or ""),
        "current_step": str(execution.get("current_step") or ""),
    }

    if action == "run_step":
        step_num = len(execution["steps"]) + 1
        step_title = f"Step {step_num}"

        step = {
            "title": step_title,
            "status": "done",
            "output": "Step completed.",
        }

        execution["steps"].append(step)
        execution["history"].append(f"run_step: {step_title}")
        execution["status"] = "complete"
        execution["last_action"] = action
        execution["current_step"] = step_title

    elif action == "run_all":
        start_num = len(execution["steps"]) + 1

        for offset in range(3):
            step_num = start_num + offset
            step_title = f"Step {step_num}"

            step = {
                "title": step_title,
                "status": "done",
                "output": "Step completed.",
            }

            execution["steps"].append(step)

        execution["history"].append("run_all: added 3 completed steps")
        execution["status"] = "complete"
        execution["last_action"] = action
        execution["current_step"] = "Run all complete"

    elif action == "test_fail":
        step_num = len(execution["steps"]) + 1
        step_title = f"Failed Step {step_num}"

        failed_step = {
            "title": step_title,
            "status": "failed",
            "output": "Simulated failure.",
        }

        execution["steps"].append(failed_step)
        execution["history"].append(f"test_fail: {step_title}")
        execution["status"] = "error"
        execution["last_action"] = action
        execution["current_step"] = step_title

    elif action in ("retry", "retry_failed"):
        failed_index = None

        for i in range(len(execution["steps"]) - 1, -1, -1):
            step = execution["steps"][i]
            step_status = str(step.get("status") or "").strip().lower()

            if step_status in ("failed", "error"):
                failed_index = i
                break

        if failed_index is not None:
            failed_step = execution["steps"][failed_index]
            failed_title = str(failed_step.get("title") or f"Step {failed_index + 1}")

            failed_step["status"] = "running"
            failed_step["output"] = "Retrying failed step..."

            execution["status"] = "running"
            execution["last_action"] = "retry_failed"
            execution["current_step"] = failed_title
            execution["history"].append(f"retry_failed: {failed_title}")

            failed_step["status"] = "done"
            failed_step["output"] = "Retry successful."

            execution["status"] = "complete"
            execution["current_step"] = "Retry complete"
        else:
            execution["history"].append("retry_failed: no failed step found")
            execution["status"] = "complete"
            execution["last_action"] = "retry_failed"
            execution["current_step"] = "No failed step found"

    elif action == "stop":
        execution["history"].append("stop")
        execution["status"] = "stopped"
        execution["last_action"] = action
        execution["current_step"] = "Stopped"

    else:
        execution["history"].append(f"unknown action: {action}")
        execution["status"] = "error"
        execution["last_action"] = action
        execution["current_step"] = "Unknown action"

    chat_service._update_working_state(session_id, {
        "execution": execution,
    })

    return jsonify({
        "ok": True,
        "action": action,
        "session_id": session_id,
        "execution_state": execution,
    })


def serialize_move(move):
    if isinstance(move, dict):
        return move

    return {
        "id": str(getattr(move, "id", "")),
        "type": str(getattr(move, "type", "")),
        "payload": getattr(move, "payload", {}) if isinstance(getattr(move, "payload", {}), dict) else {},
    }

@app.route("/api/execution/stream", methods=["POST"])
def execution_stream():
    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id") or "").strip()
    action = str(data.get("action") or "").strip()
    action_text = str(action or "").lower().strip()

    if action_text in {"fix_file", "auto_fix", "apply_fix", "apply fix"}:
        action = "fix_file"

    elif action_text in {"auto", "auto mode", "autopilot"}:
        action = "run_all"

    elif action_text in {
        "next", "nex", "continue", "continue on",
        "keep going", "go", "run next",
        "next step", "what next", "what now"
    }:
        execution_state = {}

        try:
            session = session_service.get_session(session_id) or {}

            execution_state = (
                session.get("working_state", {})
                .get("execution", {})
            )

        except Exception:
            execution_state = {}
            action = "run_step"

    def send_event(name, payload):
        import json
        return f"event: {name}\ndata: {json.dumps(payload)}\n\n"

def save_execution(execution):

    session = session_service.get_session(
        session_id
    )

    if not isinstance(session, dict):
        return

    working_state = session.get(
        "working_state",
        {},
    )

    if not isinstance(working_state, dict):
        working_state = {}

    execution_map = working_state.get(
        "execution",
        {},
    )

    if not isinstance(execution_map, dict):
        execution_map = {}

    execution_map[session_id] = execution

    working_state["execution"] = execution_map

    session["working_state"] = working_state

    session_service.update_session(
        session_id,
        session,
    )

    def replay_existing_step(execution, replay_step, step_title):
        move = replay_step.get("move") if isinstance(replay_step, dict) else None

        if not isinstance(move, dict):
            replay_step["status"] = "failed"
            replay_step["output"] = {
                "error": "Replay failed: no move stored on step.",
            }
            execution["status"] = "error"
            execution["current_step"] = f"Replay failed: {step_title}"
            return replay_step

        replay_result = default_executor(NextMove(
            id=str(move.get("id") or f"replay-{uuid.uuid4().hex}"),
            type=str(move.get("type") or "echo"),
            payload=move.get("payload") if isinstance(move.get("payload"), dict) else {},
        ))

        replay_ok = bool(getattr(replay_result, "success", False))

        replay_step["status"] = "done" if replay_ok else "failed"
        replay_step["output"] = getattr(replay_result, "output", {})

        runtime = getattr(chat_service, "runtime", None)

        if runtime is not None:
            runtime_strategy_memory = getattr(
                runtime,
                "runtime_strategy_memory",
                None,
            )

            if isinstance(runtime_strategy_memory, list):
                runtime_strategy_memory.append(
                    {
                        "action": move.get("type") or action,
                        "success": replay_ok,
                        "failure": not replay_ok,
                        "runtime_signal": (
                            "execution_success"
                            if replay_ok
                            else "execution_failure"
                        ),
                        "score_delta": 1 if replay_ok else -1,
                    }
                )

        update_execution_state_safe(execution, status="complete" if replay_ok else "error")
        execution["current_step"] = "Replay complete" if replay_ok else f"Replay failed: {step_title}"

        return replay_step

    def generate():
        import time

        if not session_id:
            yield send_event("error", {"ok": False, "error": "missing session_id", "done": True})
            return

        if not action:
            yield send_event("error", {"ok": False, "error": "missing action", "done": True})
            return

        session = session_service.get_session(
            session_id
        )

        if not isinstance(
            session,
            dict,
        ):
            session = {}

        execution = (session or {}).get("working_state", {}).get("execution") or {}
        if not isinstance(execution, dict):
            execution = {}

        execution.setdefault("status", "idle")
        execution.setdefault("steps", [])
        execution.setdefault("history", [])
        execution.setdefault("last_action", "")
        execution.setdefault("current_step", "")

        if not isinstance(execution["steps"], list):
            execution["steps"] = []

        if not isinstance(execution["history"], list):
            execution["history"] = []

        yield send_event("start", {
            "ok": True,
            "action": action,
            "session_id": session_id,
            "execution_state": execution,
            "done": False,
        })

        if action == "fix_file":
            execution = (session or {}).get("working_state", {}).get("execution") or {} or {
                "status": "idle",
                "steps": [],
                "history": [],
                "last_action": "",
                "current_step": "",
            }

            pending_file = ""
            pending_code = ""

            try:
                session = session_service.get_session(session_id)
                working_state = session.get("working_state", {}) if isinstance(session, dict) else {}
                meta = session.get("meta", {}) if isinstance(session, dict) else {}

                pending_file = str(
                    working_state.get("pending_fix_file_path")
                    or meta.get("pending_fix_file_path")
                    or ""
                ).strip()

                pending_code = str(
                    working_state.get("pending_fix_code")
                    or meta.get("pending_fix_code")
                    or ""
                )

            except Exception:
                pending_file = ""
                pending_code = ""

            step = {
                "title": "Apply pending file fix",
                "status": "running",
                "move": {
                    "id": f"fix-file-{uuid.uuid4().hex}",
                    "type": "fix_file",
                    "payload": {
                        "file_path": pending_file,
                        "code": pending_code,
                    },
                },
            }

            execution["status"] = "running"
            execution["current_step"] = step["title"]
            execution["last_action"] = action
            execution.setdefault("steps", []).append(step)
            save_execution(execution)

            yield send_event("step_start", {
                "step": step,
                "execution_state": execution,
                "done": False,
            })

            result = default_executor(NextMove(
                id=step["move"]["id"],
                type="fix_file",
                payload=step["move"]["payload"],
            ))

            ok = str(result.status or "").lower() == "success"

            step["status"] = "done" if ok else "failed"
            step["output"] = result.output or {"error": result.error}
            update_execution_state_safe(execution, status="complete" if ok else "error")
            update_execution_state_safe(execution, current_step="Fix applied" if ok else "Fix failed")
            execution.setdefault("history", []).append(
                f"fix_file: {'success' if ok else 'failed'}"
            )
            save_execution(execution)

            yield send_event("step_done", {
                "step": step,
                "execution_state": execution,
                "done": False,
            })

            yield send_event("done", {
                "ok": ok,
                "execution_state": execution,
                "done": True,
            })
            return

        if action == "run_step":
            steps = execution.get("steps", [])

            if not steps:
                execution["status"] = "complete"
                execution["current_step"] = "No steps to run"
                execution["last_action"] = action
                save_execution(execution)

                yield send_event("done", {
                    "ok": True,
                    "execution_state": execution,
                    "done": True,
                })
                return

            current_index = int(execution.get("current_index") or 0)

            if current_index >= len(steps):
                execution["status"] = "complete"
                execution["current_step"] = "All steps completed"
                execution["last_action"] = action
                save_execution(execution)

                yield send_event("done", {
                    "ok": True,
                    "execution_state": execution,
                    "done": True,
                })
                return

            step = steps[current_index]
            step["status"] = "done"

            execution["status"] = "running"
            execution["current_step"] = step.get("title") or f"Step {current_index + 1}"
            execution["current_index"] = current_index + 1
            execution["last_action"] = action
            execution.setdefault("history", []).append(
                f"run_step: {execution['current_step']}"
            )
            save_execution(execution)

            yield send_event("step_done", {
                "ok": True,
                "step": step,
                "execution_state": execution,
                "done": False,
            })

            if execution["current_index"] >= len(steps):
                execution["status"] = "complete"
                save_execution(execution)

            yield send_event("done", {
                "ok": True,
                "execution_state": execution,
                "done": True,
            })
            return

            step = steps[current_index]
            step["status"] = "complete"

            execution_state["status"] = "running"
            execution_state["current_step"] = step.get("title") or f"Step {current_index + 1}"
            execution_state["current_index"] = current_index + 1
            execution_state["last_action"] = action
            execution_state.setdefault("history", []).append(
                f"run_step: {execution_state['current_step']}"
            )

            yield sse("step_done", {
                "ok": True,
                "step": step,
                "execution_state": execution_state,
                "done": False,
            })

            if execution_state["current_index"] >= len(steps):
                execution_state["status"] = "complete"

            yield sse("done", {
                "ok": True,
                "execution_state": execution_state,
                "done": True,
            })
            return

        if action == "run_all":
            start_num = len(execution["steps"]) + 1

            for offset in range(3):
                step_num = start_num + offset
                step_title = f"Step {step_num}"

                move = NextMove(
                    id=f"run-all-{uuid.uuid4().hex}",
                    type="echo",
                    payload={
                        "step": step_num,
                        "message": f"{step_title} executed.",
                    },
                )

                execution["current_step"] = step_title
                execution["status"] = "running"
                execution["last_action"] = action

                yield send_event("step_start", {
                    "step": {
                        "title": step_title,
                        "status": "running",
                        "output": f"{step_title} running...",
                        "move": serialize_move(move),
                    },
                    "execution_state": execution,
                    "done": False,
                })

                time.sleep(0.4)

                result = default_executor(move)
                result_success = bool(getattr(result, "success", False))
                result_output = getattr(result, "output", {})

                step = {
                    "title": step_title,
                    "status": "done" if result_success else "failed",
                    "output": result_output,
                    "move": serialize_move(move),
                }

                execution["steps"].append(step)
                execution["history"].append(f"run_all: {step_title}")

                yield send_event("step_done", {
                    "step": step,
                    "execution_state": execution,
                    "done": False,
                })

            execution["status"] = "complete"
            execution["current_step"] = "Done"

        elif action == "test_fail":
            step_title = f"Failed Step {len(execution['steps']) + 1}"

            failed_step = {
                "title": step_title,
                "status": "failed",
                "output": {
                    "error": "Intentional test failure.",
                },
                "move": {
                    "type": "echo",
                    "payload": {
                        "retry_test": True,
                        "message": "Real retry replay executed.",
                    },
                },
            }

            execution["steps"].append(failed_step)
            execution["history"].append(f"test_fail: {step_title}")
            execution["status"] = "error"
            execution["last_action"] = action
            execution["current_step"] = step_title

            yield send_event("step_done", {
                "step": failed_step,
                "execution_state": execution,
                "done": False,
            })

        elif action == "replay_last":
            if not execution["steps"]:
                execution["history"].append("replay_last: no step found")
                execution["status"] = "complete"
                execution["last_action"] = action
                execution["current_step"] = "No step found"
            else:
                replay_step = execution["steps"][-1]
                step_title = replay_step.get("title", "Last step")

                execution["current_step"] = step_title
                execution["status"] = "running"
                execution["last_action"] = action

                yield send_event("step_start", {
                    "step": {
                        "title": step_title,
                        "status": "running",
                        "output": "Replaying...",
                        "move": replay_step.get("move") if isinstance(replay_step, dict) else None,
                    },
                    "execution_state": execution,
                    "done": False,
                })

                time.sleep(0.3)

                try:
                    replay_existing_step(execution, replay_step, step_title)
                    execution["history"].append(f"replay_last: {step_title}")
                except Exception as exc:
                    replay_step["status"] = "failed"
                    replay_step["output"] = {
                        "error": f"Replay executor crashed: {exc}",
                    }
                    execution["history"].append(f"replay_last_exception: {step_title}")
                    execution["status"] = "error"
                    execution["current_step"] = f"Replay failed: {step_title}"

                yield send_event("step_done", {
                    "step": replay_step,
                    "execution_state": execution,
                    "done": False,
                })

        elif action == "replay_step":
            if step_index is None or step_index < 0 or step_index >= len(execution["steps"]):
                execution["history"].append(f"replay_step: invalid index {step_index}")
                execution["status"] = "error"
                execution["last_action"] = action
                execution["current_step"] = "Invalid step index"
            else:
                replay_step = execution["steps"][step_index]
                step_title = replay_step.get("title", f"Step {step_index + 1}")

                execution["current_step"] = step_title
                execution["status"] = "running"
                execution["last_action"] = action

                yield send_event("step_start", {
                    "step": {
                        "title": step_title,
                        "status": "running",
                        "output": "Replaying selected step...",
                        "move": replay_step.get("move") if isinstance(replay_step, dict) else None,
                    },
                    "execution_state": execution,
                    "done": False,
                })

                time.sleep(0.3)

                try:
                    replay_existing_step(execution, replay_step, step_title)
                    execution["history"].append(f"replay_step: {step_title}")
                except Exception as exc:
                    replay_step["status"] = "failed"
                    replay_step["output"] = {
                        "error": f"Replay executor crashed: {exc}",
                    }
                    execution["history"].append(f"replay_step_exception: {step_title}")
                    execution["status"] = "error"
                    execution["current_step"] = f"Replay failed: {step_title}"

                yield send_event("step_done", {
                    "step": replay_step,
                    "execution_state": execution,
                    "done": False,
                })

        elif action == "retry_failed":
            failed_index = None

            for i in range(len(execution["steps"]) - 1, -1, -1):
                step = execution["steps"][i]
                step_status = str(step.get("status") or "").lower()

                if step_status in ("failed", "error"):
                    failed_index = i
                    break

            if failed_index is not None:
                failed_step = execution["steps"][failed_index]
                step_title = failed_step.get("title", f"Step {failed_index + 1}")

                execution["current_step"] = step_title
                execution["status"] = "running"
                execution["last_action"] = action

                yield send_event("step_start", {
                    "step": {
                        "title": step_title,
                        "status": "running",
                        "output": "Retrying...",
                    },
                    "execution_state": execution,
                    "done": False,
                })

                time.sleep(0.3)

                try:
                    replay_existing_step(execution, failed_step, step_title)
                    execution["history"].append(f"retry_failed: {step_title}")
                except Exception as exc:
                    failed_step["status"] = "failed"
                    failed_step["output"] = {
                        "error": f"Retry executor crashed: {exc}",
                    }
                    execution["history"].append(f"retry_failed_exception: {step_title}")
                    execution["status"] = "error"
                    execution["current_step"] = f"Retry failed: {step_title}"

                yield send_event("step_done", {
                    "step": failed_step,
                    "execution_state": execution,
                    "done": False,
                })
            else:
                execution["history"].append("retry_failed: no failed step found")
                execution["status"] = "complete"
                execution["last_action"] = action
                execution["current_step"] = "No failed step found"

        elif action == "stop":
            execution["history"].append("stop")
            execution["status"] = "stopped"
            execution["last_action"] = action
            execution["current_step"] = "Stopped"

        else:
            execution["history"].append(f"unknown action: {action}")
            execution["status"] = "error"
            execution["last_action"] = action
            execution["current_step"] = "Unknown action"

        save_execution(execution)

        yield send_event("done", {
            "ok": True,
            "execution_state": execution,
            "done": True,
        })

    return Response(generate(), mimetype="text/event-stream")

@app.route("/api/debug/execution", methods=["GET"])
def api_debug_execution():
    try:
        session_id = str(request.args.get("session_id") or "").strip()

        if not session_id:
            return jsonify({
                "ok": False,
                "error": "Missing session_id",
                "active_task": "",
                "next_move": "",
                "last_execution_status": "idle",
                "last_execution_steps": 0,
                "execution_history": [],
            }), 400

        session = session_service.get_session(session_id) or {}
        state = session.get("working_state", {}).get("execution", {})

        if not isinstance(state, dict):
            state = {}

        history = state.get("execution_history")
        if not isinstance(history, list):
            history = []

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "active_task": state.get("active_task") or "",
            "next_move": state.get("next_move") or "",
            "last_execution_status": state.get("last_execution_status") or "idle",
            "last_execution_action": state.get("last_execution_action") or "",
            "last_execution_steps": state.get("last_execution_steps") or len(history),
            "execution_history": history,
            "working_state": state,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "active_task": "",
            "next_move": "",
            "last_execution_status": "error",
            "last_execution_steps": 0,
            "execution_history": [],
        }), 500

@app.route("/api/web/preview", methods=["POST"])
def web_preview():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()

    if not url:
        return jsonify({
            "ok": False,
            "error": "Missing url",
            "title": "Source preview",
            "preview": "",
            "url": "",
        }), 400

    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Resolve Google News RSS redirect links into the real publisher page.
        if "news.google.com/rss/articles/" in url or "news.google.com/articles/" in url:
            try:
                redirect_response = requests.get(
                    url,
                    headers=headers,
                    timeout=10,
                    allow_redirects=True,
                )
                if redirect_response.url:
                    url = redirect_response.url
            except Exception:
                pass

        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=True,
        )

        final_url = response.url or url
        html = response.text or ""

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript",
            "svg",
        ]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        article = soup.find("article")
        if article:
            text = article.get_text("\n", strip=True)
        else:
            text = soup.get_text("\n", strip=True)

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        cleaned_lines = []
        junk_phrases = [
            "sign in",
            "subscribe",
            "advertisement",
            "cookie",
            "privacy policy",
            "terms of use",
            "enable javascript",
            "all rights reserved",
        ]

        for line in lines:
            low = line.lower()
            if any(junk in low for junk in junk_phrases):
                continue
            if len(line) < 20:
                continue
            cleaned_lines.append(line)

        preview = "\n".join(cleaned_lines[:24]).strip()

        if not preview:
            preview = "Preview route is working, but no readable article text was found."

        return jsonify({
            "ok": True,
            "title": title or "Source preview",
            "preview": preview[:4000],
            "url": final_url,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "title": "Source preview",
            "preview": "Preview failed on backend.",
            "url": url,
        }), 500

def create_startup_backup():
    root = Path(r"C:\Users\Owner\nova")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_root = root / "nova_backups"
    backup_dir = backup_root / f"startup_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        root / "app.py",
        root / "nova_backend" / "services" / "chat_service.py",
        root / "static" / "js" / "nova-composer-bundle.js",
        root / "templates" / "index.html",
        root / "static" / "css" / "nova-main.css",
    ]

    for file_path in files_to_backup:
        if file_path.exists():
            relative_path = file_path.relative_to(root)
            destination = backup_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, destination)

    print(f"[NOVA BACKUP] Created: {backup_dir}")

    # ?? AUTO CLEANUP (keep last 10 backups)
    backups = sorted(backup_root.glob("startup_*"), key=lambda p: p.stat().st_mtime, reverse=True)

    for old in backups[10:]:
        try:
            shutil.rmtree(old)
            print(f"[NOVA BACKUP] Removed old: {old}")
        except Exception as e:
            print(f"[NOVA BACKUP] Cleanup error: {e}")

# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    create_startup_backup()
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
        use_reloader=False,
    )

# ATTACHMENT_MEMORY_SESSION_ALIAS_APP_LOCK


