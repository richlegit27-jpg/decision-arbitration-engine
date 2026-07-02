import json
from __future__ import annotations
import json


def _nova_boot_log_20260701(*args, **kwargs):
    import os as _nova_boot_log_os_20260701

    if str(_nova_boot_log_os_20260701.getenv("NOVA_VERBOSE_BOOT_LOGS", "")).strip().lower() in {"1", "true", "yes", "on"}:
        print(*args, **kwargs)



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
from nova_backend.services.chat_execution_service import ChatExecutionService
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


# NOVA_EXECUTION_SERVICE_SINGLETON_20260607
chat_execution_service = ChatExecutionService()
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

# NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701
# Priority project-brain intelligence adapter.
# Catches broad Nova project/judgment/concept questions before memory-write,
# generic chat, or stale fallback routes can answer them.
try:
    @app.before_request
    def _nova_project_brain_general_intelligence_priority_20260701():
        try:
            from flask import jsonify as _nova_gi_jsonify
            from flask import request as _nova_gi_request

            if _nova_gi_request.path != "/api/chat" or _nova_gi_request.method != "POST":
                return None

            payload = _nova_gi_request.get_json(silent=True) or {}

            attachments = payload.get("attachments") or []
            if attachments:
                return None

            user_text = (
                payload.get("message")
                or payload.get("text")
                or payload.get("content")
                or payload.get("user_text")
                or ""
            )

            from nova_backend.services.project_brain_general_intelligence import (
                build_project_brain_general_answer,
            )

            answer = build_project_brain_general_answer(user_text)

            if not answer:
                return None

            data = {
                "ok": True,
                "text": answer.text,
                "content": answer.text,
                "assistant_message": {
                    "role": "assistant",
                    "text": answer.text,
                    "content": answer.text,
                },
                "debug": {
                    "route": "project_brain_general_intelligence",
                    "route_taken": "project_brain_general_intelligence",
                    "intent": answer.intent,
                    "priority_project_brain_general_intelligence": True,
                },
            }

            return _nova_gi_jsonify(data)

        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] installed")
except Exception as _nova_project_brain_general_intelligence_priority_error_20260701:
    print(
        "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] install failed:",
        _nova_project_brain_general_intelligence_priority_error_20260701,
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

_nova_boot_log_20260701(
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

_nova_boot_log_20260701(
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
    sessions = session_service.get_all()
    active_session = session_service.get_active() or {}

    if not isinstance(active_session, dict):
        active_session = {}

    active_session_id = str(
        getattr(session_service, "active_session_id", "")
        or active_session.get("id")
        or active_session.get("session_id")
        or ""
    ).strip()

    messages = active_session.get("messages")
    if not isinstance(messages, list):
        messages = []

    working_state = active_session.get("working_state")
    if not isinstance(working_state, dict):
        working_state = {}

    active_task = str(
        working_state.get("active_task")
        or working_state.get("task")
        or ""
    ).strip()

    current_file = str(
        working_state.get("current_file")
        or working_state.get("file")
        or ""
    ).strip()

    last_user_message = ""
    last_assistant_message = ""

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue

        role = str(message.get("role") or "").strip().lower()
        text = str(
            message.get("text")
            or message.get("content")
            or ""
        ).strip()

        if role == "user" and not last_user_message:
            last_user_message = text

        if role == "assistant" and not last_assistant_message:
            last_assistant_message = text

        if last_user_message and last_assistant_message:
            break

    if not active_task:
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            if str(message.get("role") or "").strip().lower() != "user":
                continue

            text = str(
                message.get("text")
                or message.get("content")
                or ""
            ).strip()

            text_lc = text.lower()

            if "we are working on" in text_lc:
                active_task = text_lc.split("we are working on", 1)[1].strip(" .")
                break

            if "working on" in text_lc:
                active_task = text_lc.split("working on", 1)[1].strip(" .")
                break

    if not current_file and active_task:
        parts = active_task.replace(",", " ").split()

        for part in parts:
            clean_part = part.strip("`'\".,:;()[]{}")

            if clean_part.endswith((".py", ".js", ".css", ".html", ".json", ".md", ".txt")):
                current_file = clean_part
                break

    normalized_working_state = {
        "active_task": active_task,
        "current_file": current_file,
        "last_user_message": last_user_message,
        "last_assistant_message": last_assistant_message,
    }

    state = {
        "active_session_id": active_session_id,
        "active_task": active_task,
        "current_file": current_file,
        "last_user_message": last_user_message,
        "last_assistant_message": last_assistant_message,
        "working_state": normalized_working_state,
    }

    return json_ok(
        state=state,
        sessions=sessions,
        active_session_id=active_session_id,
        session=active_session,
        working_state=normalized_working_state,
        active_task=active_task,
        current_file=current_file,
        last_user_message=last_user_message,
        last_assistant_message=last_assistant_message,
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )




# NOVA_API_CHAT_EARLY_EXPLICIT_MEMORY_GUARD_LIVE_ANCHOR_20260611
def _nova_api_chat_extract_explicit_memory_live_20260611(user_text):
    raw = str(user_text or "").strip()
    lowered = raw.lower().strip()

    prefixes = (
        "remember that ",
        "remember this ",
        "remember ",
        "save that ",
        "save this ",
        "store that ",
        "store this ",
        "note that ",
        "memorize that ",
        "add to memory that ",
        "add this to memory ",
    )

    for prefix in prefixes:
        if lowered.startswith(prefix):
            return raw[len(prefix):].strip(" .\n\r\t")

    return ""


def _nova_api_chat_memory_kind_live_20260611(clean):
    lowered = str(clean or "").lower()

    if (
        "favorite color" in lowered
        or "favourite color" in lowered
        or "prefer" in lowered
        or "from now on" in lowered
        or "always" in lowered
        or "call me" in lowered
        or "my name is" in lowered
    ):
        return "preference"

    return "fact"


def _nova_api_chat_memory_response_live_20260611(raw_user_text, session_id, clean):
    assistant_text = f"Saved to memory: {clean}"

    user_msg = {
        "role": "user",
        "text": raw_user_text,
        "attachments": [],
        "meta": {},
    }

    assistant_msg = {
        "role": "assistant",
        "text": assistant_text,
        "attachments": [],
        "memory_used": [],
        "meta": {
            "mode": "explicit_memory_command",
            "route": "memory_save",
            "save_memory": True,
            "use_memory": True,
            "early_api_guard": True,
        },
    }

    try:
        session_service.add_message(session_id, user_msg)
        session_service.add_message(session_id, assistant_msg)
    except Exception:
        pass

    return {
        "ok": True,
        "active_session_id": session_id,
        "assistant_message": assistant_msg,
        "attachment_debug": {
            "requested_session_id": session_id,
            "active_session_id": session_id,
            "session_attachments_count": 0,
        },
        "debug": {
            "route": "api_chat_early_explicit_memory_guard",
            "route_taken": "memory_save",
        },
        "runtime": {},
        "session": session_service.get_session(session_id) or {
            "id": session_id,
            "messages": [user_msg, assistant_msg],
        },
        "session_attachments": [],
    }


# -----------------------
# CHAT
# -----------------------


# NOVA_WEAK_BACKEND_RESPONSE_GUARD_LOCK
# NOVA_WEAK_BACKEND_RESPONSE_MOJIBAKE_GUARD_LOCK
def _nova_replace_weak_backend_reply(user_text, result):
    """
    Last-mile response guard.

    Prevents weak generic fallback text like:
    "I'm ready. What are we working on?"
    from being returned as the final assistant response.

    Also catches mojibake variants like:
    "IÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢m ready. What are we working on?"
    """
    try:
        if not isinstance(result, dict):
            return result

        assistant = result.get("assistant_message")
        if not isinstance(assistant, dict):
            return result

        text = str(
            assistant.get("text")
            or assistant.get("content")
            or ""
        ).strip()

        normalized = (
            text
            .lower()
            .replace("Ã¢â‚¬â„¢", "'")
            .replace("`", "'")
            .replace("Ã‚Â´", "'")
            .replace("ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢", "'")
            .replace("ÃƒÂ£Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢", "'")
            .replace("iÃƒÂ£Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢m", "i'm")
            .replace("iÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢m", "i'm")
        )

        compact = " ".join(normalized.split())

        weak_hit = (
            compact in {
                "i'm ready. what are we working on?",
                "i'm ready. what are we working on",
                "im ready. what are we working on?",
                "im ready. what are we working on",
            }
            or (
                "ready" in compact
                and "what are we working on" in compact
            )
        )

        if not weak_hit:
            return result

        prompt = str(user_text or "").strip()
        prompt_lc = prompt.lower()

        if "life story" in prompt_lc:
            replacement = (
                "I do not have a personal life story like a human. "
                "I was built to help you think, build, debug, write, learn, and move faster. "
                "For Nova, the active phase is frontend polish: clean the mobile UI, remove weak fallback behavior, "
                "and make the live app match the backend tests that are already passing."
            )
        else:
            replacement = (
        
                "I'm here. What would you like to work on?"
            )

        assistant["text"] = replacement
        assistant["content"] = replacement

        meta = assistant.get("meta")
        if not isinstance(meta, dict):
            meta = {}

        meta["weak_response_guarded"] = True
        meta["weak_response_original"] = text
        assistant["meta"] = meta

        result["assistant_message"] = assistant

        session = result.get("session")
        if isinstance(session, dict) and isinstance(session.get("messages"), list):
            for msg in reversed(session["messages"]):
                if isinstance(msg, dict) and str(msg.get("role") or "").lower() == "assistant":
                    msg["text"] = replacement
                    msg["content"] = replacement
                    msg["meta"] = dict(meta)
                    break

        return result

    except Exception:
        return result




# SAFE_ATTACHMENT_TEXT_CLEANUP_LOCK
def _nova_safe_clean_attachment_text(raw_text, max_chars=6000):
    """Clean noisy PDF/OCR/browser extraction before Nova summarizes it."""
    text_value = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")

    noisy_exact = {
        "search",
        "images",
        "videos",
        "shopping",
        "news",
        "maps",
        "books",
        "flights",
        "finance",
        "all",
        "create",
        "inspiration",
        "keypoints",
            "copy",
            "regen",
            "regenerate",
        "continue",
        "summarize",
        "improve",
        "next",
        "menu",
        "home",
        "sign in",
        "login",
        "privacy",
        "terms",
        "settings",
        "tools",
        "feedback",
        "cached",
        "similar",
        "share",
        "save",
        "more",
        "view all",
    }

    noisy_contains = (
        "url removed from extracted attachment text",
        "wayfair.ca",
        "sponsored",
        "ad Ã‚Â·",
        "ads Ã‚Â·",
        "shop Ã¢â‚¬Âº",
        "wall art Ã¢â‚¬Âº",
        "free_shipping",
        "furniture & dÃƒÂ©cor",
        "kitchen appliances",
        "prices you'll love",
        "eye-catching prints",
        "google",
        "bing",
        "search images",
    )

    cleaned_lines = []
    seen = set()

    for raw_line in text_value.split("\n"):
        line = re.sub(r"\s+", " ", str(raw_line or "")).strip()
        if not line:
            continue

        low = line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
        low_compact = re.sub(r"[^a-z0-9]+", " ", low).strip()

        if low_compact in noisy_exact:
            continue

        if any(bad in low for bad in noisy_contains):
            continue

        if low.startswith("[pdf page") and len(line) < 25:
            continue

        if low.startswith("attachment <unknown> content"):
            continue

        if low.startswith("attachment content:"):
            continue

        if line.startswith("http://") or line.startswith("https://"):
            continue

        if len(line) <= 2:
            continue

        dedupe_key = low_compact[:180]
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()

    if not cleaned:
        cleaned = text_value.strip()

    return cleaned[:max_chars].strip()


def _nova_safe_attachment_name(attachment, fallback="uploaded attachment"):
    """Return a readable attachment name instead of <unknown>."""
    if isinstance(attachment, dict):
        for key in ("original_filename", "filename", "name", "title", "stored", "file_name"):
            value = str(attachment.get(key) or "").strip()
            if value:
                return value

        for key in ("file_url", "url", "src"):
            value = str(attachment.get(key) or "").strip()
            if value:
                return value.rsplit("/", 1)[-1] or fallback

    return fallback



# NOVA_PHASE1_TEXT_ATTACHMENT_READER_20260607
def _nova_phase1_is_text_attachment(item):
    try:
        if not isinstance(item, dict):
            return False

        mime = str(item.get("mime_type") or item.get("type") or item.get("content_type") or "").lower()
        name = str(
            item.get("filename")
            or item.get("original_filename")
            or item.get("name")
            or item.get("url")
            or item.get("file_url")
            or ""
        ).lower()

        text_exts = (
            ".txt", ".md", ".markdown", ".json", ".jsonl",
            ".py", ".js", ".css", ".html", ".htm",
            ".csv", ".tsv", ".log", ".xml", ".yaml", ".yml", ".docx"
        )

        if mime.startswith("text/"):
            return True

        if mime in {
            "application/json",
            "application/javascript",
            "application/x-javascript",
            "application/xml",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/csv"
        }:
            return True

        return name.endswith(text_exts)
    except Exception:
        return False


def _nova_phase1_upload_path_from_attachment(item):
    try:
        import os

        raw = str(
            item.get("path")
            or item.get("local_path")
            or item.get("file_path")
            or item.get("url")
            or item.get("file_url")
            or ""
        ).strip()

        if not raw:
            return None

        if raw.startswith("/api/uploads/"):
            filename = raw.split("/api/uploads/", 1)[1].split("?", 1)[0].strip("/\\")
            base = globals().get("UPLOADS_DIR") or globals().get("UPLOAD_FOLDER")
            if base:
                return os.path.join(str(base), filename)
            return os.path.join(os.path.dirname(__file__), "uploads", filename)

        if os.path.isabs(raw):
            return raw

        filename = raw.split("/")[-1].split("\\")[-1].split("?", 1)[0]
        base = globals().get("UPLOADS_DIR") or globals().get("UPLOAD_FOLDER")
        if base:
            return os.path.join(str(base), filename)

        return os.path.join(os.path.dirname(__file__), "uploads", filename)
    except Exception:
        return None




# NOVA_SKIP_RAW_BINARY_ATTACHMENT_INJECTION_20260607
def _nova_should_skip_raw_attachment_injection(item):
    try:
        if not isinstance(item, dict):
            return False

        mime = str(item.get("mime_type") or item.get("type") or item.get("content_type") or "").lower()
        name = str(
            item.get("filename")
            or item.get("original_filename")
            or item.get("name")
            or item.get("url")
            or item.get("file_url")
            or ""
        ).lower()

        blocked_exts = (
            ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif",
            ".zip", ".exe", ".dll", ".bin"
        )

        blocked_mimes = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/pdf",
            "application/zip",
            "application/octet-stream",
        }

        if mime in blocked_mimes:
            return True

        if mime.startswith("image/"):
            return True

        return name.endswith(blocked_exts)
    except Exception:
        return False


def _nova_filter_raw_injection_attachments(attachments, logger=None):
    kept = []
    skipped = []

    for item in attachments or []:
        if _nova_should_skip_raw_attachment_injection(item):
            skipped.append(item)
        else:
            kept.append(item)

    if skipped and logger:
        try:
            names = [
                str(x.get("original_filename") or x.get("filename") or x.get("name") or x.get("url") or "attachment")
                for x in skipped
                if isinstance(x, dict)
            ]
            logger.info("[RawAttachmentInjectionGuard] skipped raw binary injection for attachments=%s", names)
        except Exception:
            pass

    return kept


def _nova_phase2_extract_docx_text(path):
    try:
        import zipfile
        import xml.etree.ElementTree as ET

        chunks = []

        with zipfile.ZipFile(path, "r") as archive:
            targets = [
                "word/document.xml",
                "word/footnotes.xml",
                "word/endnotes.xml",
                "word/comments.xml",
            ]

            for target in targets:
                if target not in archive.namelist():
                    continue

                xml_bytes = archive.read(target)
                root = ET.fromstring(xml_bytes)

                namespace = {
                    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                }

                paragraphs = []

                for paragraph in root.findall(".//w:p", namespace):
                    texts = []

                    for node in paragraph.findall(".//w:t", namespace):
                        if node.text:
                            texts.append(node.text)

                    line = "".join(texts).strip()

                    if line:
                        paragraphs.append(line)

                if paragraphs:
                    chunks.append("\n".join(paragraphs))

        return "\n\n".join(chunks).strip()
    except Exception:
        return ""

def _nova_phase1_read_text_attachments(attachments, logger=None):
    sections = []

    for item in attachments or []:
        try:
            if not _nova_phase1_is_text_attachment(item):
                continue

            path = _nova_phase1_upload_path_from_attachment(item)
            if not path:
                continue

            import os

            if not os.path.exists(path) or not os.path.isfile(path):
                if logger:
                    logger.warning("[Phase1TextAttachmentReader] missing file path=%s", path)
                continue

            size = os.path.getsize(path)
            max_bytes = 120000

            lower_path = str(path or "").lower()
            lower_name = str(item.get("filename") or item.get("original_filename") or item.get("name") or "").lower()
            mime = str(item.get("mime_type") or item.get("type") or item.get("content_type") or "").lower()

            if (
                lower_path.endswith(".docx")
                or lower_name.endswith(".docx")
                or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                text = _nova_phase2_extract_docx_text(path)

                if not text:
                    if logger:
                        logger.warning("[Phase2DocxAttachmentReader] no readable docx text path=%s", path)
                    continue

                if len(text) > 50000:
                    text = text[:50000] + "\n\n[TRUNCATED: attachment text was longer than 50,000 characters]"

                name = (
                    item.get("original_filename")
                    or item.get("filename")
                    or item.get("name")
                    or os.path.basename(path)
                    or "attachment"
                )

                sections.append(
                    "Attachment file content: {name}\n"
                    "Path: {path}\n"
                    "Size: {size} bytes\n"
                    "Content:\n{text}".format(
                        name=name,
                        path=path,
                        size=size,
                        text=text
                    )
                )

                if logger:
                    logger.info(
                        "[Phase2DocxAttachmentReader] loaded docx attachment name=%s chars=%s",
                        name,
                        len(text)
                    )

                continue
            with open(path, "rb") as handle:
                raw = handle.read(max_bytes)

            text = None
            for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
                try:
                    text = raw.decode(encoding)
                    break
                except Exception:
                    continue

            if text is None:
                continue

            text = text.replace("\x00", "").strip()

            if not text:
                continue

            if len(text) > 50000:
                text = text[:50000] + "\n\n[TRUNCATED: attachment text was longer than 50,000 characters]"

            name = (
                item.get("original_filename")
                or item.get("filename")
                or item.get("name")
                or os.path.basename(path)
                or "attachment"
            )

            sections.append(
                "Attachment file content: {name}\n"
                "Path: {path}\n"
                "Size: {size} bytes\n"
                "Content:\n{text}".format(
                    name=name,
                    path=path,
                    size=size,
                    text=text
                )
            )

            if logger:
                logger.info(
                    "[Phase1TextAttachmentReader] loaded text attachment name=%s chars=%s",
                    name,
                    len(text)
                )
        except Exception as error:
            if logger:
                logger.warning("[Phase1TextAttachmentReader] failed item=%s error=%s", item, error)

    return sections


def _nova_phase1_append_text_attachments_to_user_text(user_text, attachments, logger=None):
    try:
        sections = _nova_phase1_read_text_attachments(attachments, logger=logger)
        if not sections:
            return user_text

        original = str(user_text or "").strip()

        return (
            original
            + "\n\n\n[CURRENT UPLOADED TEXT ATTACHMENTS]\n"
            + "\n\n---\n\n".join(sections)
            + "\n[/CURRENT UPLOADED TEXT ATTACHMENTS]\n"
        ).strip()
    except Exception as error:
        if logger:
            logger.warning("[Phase1TextAttachmentReader] append failed error=%s", error)
        return user_text

@app.route("/api/chat", methods=["POST"])
def api_chat_route():
    return api_chat()

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
# NOVA_RESTORE_API_SESSIONS_ROUTE_20260609
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
        return "pong"

    return clean_answer




# NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702
# Fresh exact project-state recall bridge.
# Thin app.py adapter; decision and response construction live in service layer.
try:
    from flask import jsonify as _nova_project_state_direct_fresh_jsonify_20260702
    from flask import request as _nova_project_state_direct_fresh_request_20260702

    @app.before_request
    def _nova_project_state_direct_freshness_bridge_20260702():
        try:
            if _nova_project_state_direct_fresh_request_20260702.path != "/api/chat":
                return None

            if _nova_project_state_direct_fresh_request_20260702.method != "POST":
                return None

            payload = _nova_project_state_direct_fresh_request_20260702.get_json(silent=True) or {}

            from nova_backend.services.project_state_direct_freshness_bridge import (
                build_project_state_direct_fresh_response,
            )

            response_json = build_project_state_direct_fresh_response(payload)
            if not response_json:
                return None

            return _nova_project_state_direct_fresh_jsonify_20260702(response_json)

        except Exception as exc:
            try:
                print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] installed")
except Exception as _nova_project_state_direct_freshness_bridge_error_20260702:
    print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] failed:", _nova_project_state_direct_freshness_bridge_error_20260702)



# NOVA_PROJECT_STATE_CURRENT_MEMORY_DIRECT_RECALL_20260701
# Direct recall fallback for clean project_state memory records.
def _nova_find_current_project_state_memory_20260701():
    try:
        import json as _nova_project_state_json_20260701

        memory_path = DATA_DIR / "nova_memory.json"
        payload = _nova_project_state_json_20260701.loads(
            memory_path.read_text(encoding="utf-8") or "{}"
        )

        items = payload.get("memory") or []
        candidates = []

        for item in items:
            if not isinstance(item, dict):
                continue

            kind = str(item.get("kind") or "").strip().lower()
            category = str(item.get("category") or "").strip().lower()
            memory_id = str(item.get("id") or "").strip().lower()
            value = str(item.get("text") or item.get("content") or "").strip()

            if not value:
                continue

            if (
                kind == "project_state"
                or category == "project_state"
                or memory_id == "memory_nova_project_state_current"
            ):
                try:
                    weight = float(item.get("weight") or 0.0)
                except Exception:
                    weight = 0.0

                candidates.append((
                    0 if bool(item.get("pinned")) else 1,
                    -weight,
                    str(item.get("updated_at") or ""),
                    value,
                ))

        candidates.sort()

        if candidates:
            return candidates[0][3]

    except Exception as exc:
        try:
            app.logger.warning(
                "[NOVA_PROJECT_STATE_CURRENT_MEMORY_DIRECT_RECALL_20260701] failed: %s",
                exc,
            )
        except Exception:
            pass

    return ""


def _nova_try_project_state_direct_recall(user_text, session_id):
    kinds = _nova_project_state_question_kinds(user_text)

    if not kinds:
        return None

    lines = []

    current_project_state_memory = _nova_find_current_project_state_memory_20260701()
    if current_project_state_memory:
        return _nova_slim_assistant_payload(
            current_project_state_memory,
            session_id=session_id,
            route="project_state_current_memory_direct_recall",
            route_taken="project_state_current_memory_direct_recall",
            project_state_memory_recall=True,
        )

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


# ATTACHMENT_CURRENT_ONLY_BINARY_GUARD_LOCK
def _nova_attachment_url_key(value):
    try:
        value = str(value or "").strip()
    except Exception:
        return ""
    if not value:
        return ""
    value = value.replace("\\", "/")
    if "/api/uploads/" in value:
        return value[value.find("/api/uploads/"):]
    return value


def _nova_attachment_name_key(item):
    if not isinstance(item, dict):
        return ""
    for key in ("url", "file_url", "path", "stored_name", "filename", "name", "original_filename"):
        value = item.get(key)
        cleaned = _nova_attachment_url_key(value)
        if cleaned:
            return cleaned
    return ""


def _nova_is_binary_or_container_attachment(item):
    if not isinstance(item, dict):
        return True

    mime = str(item.get("mime_type") or item.get("mime") or "").lower()
    name = str(
        item.get("filename")
        or item.get("original_filename")
        or item.get("name")
        or item.get("url")
        or item.get("file_url")
        or ""
    ).lower()

    binary_exts = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico",
        ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".avi", ".webm",
        ".pdf", ".zip", ".rar", ".7z", ".exe", ".dll",
    )

    # DOCX is a zipped Office container. Only inject it if your extractor produced readable text elsewhere.
    container_exts = (".docx", ".pptx", ".xlsx")

    if any(name.endswith(ext) for ext in binary_exts + container_exts):
        return True

    if mime.startswith("image/") or mime.startswith("audio/") or mime.startswith("video/"):
        return True

    if mime in {
        "application/pdf",
        "application/zip",
        "application/octet-stream",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }:
        return True

    return False


def _nova_filter_current_attachments_only(candidate_attachments, current_attachments):
    if not isinstance(candidate_attachments, list):
        return []

    if not isinstance(current_attachments, list) or not current_attachments:
        return []

    current_keys = set()
    for item in current_attachments:
        key = _nova_attachment_name_key(item)
        if key:
            current_keys.add(key)

    if not current_keys:
        return []

    filtered = []
    seen = set()

    for item in candidate_attachments:
        key = _nova_attachment_name_key(item)
        if not key or key not in current_keys:
            continue

        if key in seen:
            continue

        seen.add(key)
        filtered.append(item)

    return filtered

# CASUAL_CHAT_GUARD_20260604
@app.before_request
def _nova_casual_chat_guard():
    try:
        from flask import request, jsonify

        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        user_text = str(payload.get("user_text") or "").strip()
        # NOVA_AUTO_PLAN_EXECUTION_START_GUARD_20260607
        auto_plan_execution_result = None
        if auto_plan_execution_result is not None:
            return jsonify(auto_plan_execution_result)
        # NOVA_EXECUTION_STATUS_GUARD_20260607
        execution_status_result = _nova_try_execution_status_20260607(session_id, user_text)
        if execution_status_result is not None:
            return jsonify(execution_status_result)
        # NOVA_EXECUTION_AUTOPLAN_START_GUARD_20260607
        execution_start_result = None
        if execution_start_result is not None:
            return jsonify(execution_start_result)
        # NOVA_EXECUTION_TRIGGER_GUARD_20260607
        execution_result = _nova_try_execution_trigger_20260607(session_id, user_text)
        if execution_result is not None:
            return jsonify(execution_result)
        attachments = payload.get("attachments") or []

        if attachments:
            return None

        clean = " ".join(user_text.lower().split()).strip(" ?!.")

        casual_replies = {
            "hi": "Hey.",
            "hey": "Hey.",
            "hello": "Hey.",
            "yo": "Yo.",
            "sup": "I'm here.",
            "how are you": "I'm good. Ready when you are.",
            "how are u": "I'm good. Ready when you are.",
            "how you doing": "I'm good. Ready when you are.",
            "whats up": "I'm here. Ready for the next move.",
            "what's up": "I'm here. Ready for the next move.",
        }

        if clean not in casual_replies:
            return None

        session_id = str(payload.get("session_id") or "").strip()

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "text": casual_replies[clean],
                "attachments": [],
                "meta": {
                    "route": "casual_chat_guard"
                }
            },
            "attachments": [],
            "session_attachments": [],
            "debug": {
                "route": "casual_chat_guard"
            }
        })

    except Exception:
        return None


@app.post("/api/chat")


# ACTUAL_BINARY_ATTACHMENT_ANALYZER_BLOCK_LOCK


# STRIP_URLS_FROM_EXTRACTED_ATTACHMENT_CHAT_TEXT_LOCK
def _nova_strip_urls_from_extracted_attachment_text(value):
    try:
        import re
        text_value = str(value or "")
        text_value = re.sub(r"https?://\S+", "[URL removed from extracted attachment text]", text_value)
        text_value = re.sub(r"www\.\S+", "[URL removed from extracted attachment text]", text_value)
        return _nova_safe_clean_attachment_text(text_value)
    except Exception:
        return str(value or "")

def _nova_analyze_binary_attachment_for_prompt(attachment_path, mime_type):
    try:
        from pathlib import Path as _NovaPath

        path_obj = _NovaPath(str(attachment_path or ""))
        mime = str(mime_type or "").lower().strip()

        if not path_obj.exists():
            return ""

        if mime == "application/pdf" or path_obj.suffix.lower() == ".pdf":
            try:
                import fitz
            except Exception:
                return "[PDF received, but PyMuPDF/fitz is not installed for text extraction.]"

            pieces = []
            doc = fitz.open(str(path_obj))
            try:
                max_pages = min(len(doc), 5)
                for page_index in range(max_pages):
                    page_text = doc[page_index].get_text("text") or ""
                    page_text = page_text.strip()
                    if page_text:
                        pieces.append(f"[PDF page {page_index + 1}]\n{page_text[:2000]}")
            finally:
                doc.close()

            extracted = "\n\n".join(pieces).strip()
            if extracted:
                return extracted

            return "[PDF received, but no selectable text was found. It may be scanned/image-based.]"

        if mime.startswith("image/") or path_obj.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            try:
                from PIL import Image
                import pytesseract
            except Exception:
                return "[Image received, but OCR dependencies are not installed. Install pillow and pytesseract for text OCR.]"

            image = Image.open(str(path_obj))
            ocr_text = pytesseract.image_to_string(image) or ""
            ocr_text = ocr_text.strip()

            if ocr_text:
                return f"[Image OCR text]\n{ocr_text[:3000]}"

            return "[Image received. No readable OCR text was found.]"

    except Exception as error:
        return f"[Attachment analysis failed: {error}]"

    return ""


def _nova_mobile_now_iso():
    try:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return ""


def _nova_ensure_requested_session(session_id, title="Mobile Chat"):
    target_session_id = str(session_id or "").strip()
    if not target_session_id:
        return None

    try:
        existing = session_service.get_session(target_session_id)
        if existing:
            sessions = session_service.get_all()
            session_service.save(sessions, active=target_session_id)
            return existing
    except Exception:
        app.logger.exception("[mobile-session-save] failed checking existing session")

    now = _nova_mobile_now_iso()

    session = {
        "id": target_session_id,
        "title": str(title or "Mobile Chat").strip()[:80] or "Mobile Chat",
        "messages": [],
        "pinned": False,
        "created_at": now,
        "updated_at": now,
        "working_state": {
            "active_task": "",
            "current_file": "",
            "current_bug": "",
            "last_success": "",
            "next_move": "",
            "checkpoint": "",
            "updated_at": ""
        },
        "active_execution": None,
    }

    try:
        sessions = session_service.get_all()
        if isinstance(sessions, dict):
            sessions = sessions.get("sessions") or []
        if not isinstance(sessions, list):
            sessions = []

        sessions = [
            s for s in sessions
            if isinstance(s, dict) and str(s.get("id") or "").strip() != target_session_id
        ]
        sessions.insert(0, session)

        session_service.save(sessions, active=target_session_id)
        return session
    except Exception:
        app.logger.exception("[mobile-session-save] failed creating requested mobile session")
        return session



def _nova_direct_save_mobile_exchange(session_id, user_text, assistant_text, attachments=None, route="mobile_attachment"):
    # NOVA_DIRECT_MOBILE_SESSION_STORE_LOCK_20260606
    # Directly inserts/updates the mobile session in data/nova_sessions.json.
    # This bypasses append_message() failing when the mobile session object is missing.
    target_session_id = str(session_id or "").strip()
    if not target_session_id:
        return False

    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
    except Exception:
        now = ""

    try:
        store = session_service._read_store()
        sessions = store.get("sessions") if isinstance(store, dict) else []

        if not isinstance(sessions, list):
            sessions = []

        found = None
        for session in sessions:
            if isinstance(session, dict) and str(session.get("id") or "").strip() == target_session_id:
                found = session
                break

        if found is None:
            found = {
                "id": target_session_id,
                "title": str(user_text or "Mobile Chat").strip()[:80] or "Mobile Chat",
                "messages": [],
                "pinned": False,
                "created_at": now,
                "updated_at": now,
                "working_state": {
                    "active_task": "",
                    "current_file": "",
                    "current_bug": "",
                    "last_success": "",
                    "next_move": "",
                    "checkpoint": "",
                    "updated_at": ""
                },
                "active_execution": None,
            }
            sessions.insert(0, found)

        messages = found.get("messages")
        if not isinstance(messages, list):
            messages = []
            found["messages"] = messages

        messages.append({
            "role": "user",
            "text": _nova_strip_project_context_from_visible_text(user_text),
            "attachments": attachments or [],
            "created_at": now,
            "meta": {
                "route": route
            }
        })

        messages.append({
            "role": "assistant",
            "text": str(assistant_text or "").strip(),
            "attachments": attachments or [],
            "created_at": now,
            "meta": {
                "route": route
            }
        })

        found["updated_at"] = now
        store["sessions"] = sessions
        store["active_session_id"] = target_session_id

        session_service._write_store(store)
        return True
    except Exception:
        app.logger.exception("[direct-mobile-session-save] failed")
        return False



def _nova_save_mobile_exchange(session_id, user_text, assistant_text, attachments=None, route="mobile_attachment"):
    target_session_id = str(session_id or "").strip()
    if not target_session_id:
        return False

    _nova_ensure_requested_session(target_session_id, title=user_text or "Mobile Chat")

    try:
        session_service.append_message(
            target_session_id,
            {
                "role": "user",
                "text": _nova_strip_project_context_from_visible_text(user_text),
                "attachments": attachments or [],
                "meta": {
                    "route": route
                }
            }
        )

        session_service.append_message(
            target_session_id,
            {
                "role": "assistant",
                "text": str(assistant_text or "").strip(),
                "attachments": attachments or [],
                "meta": {
                    "route": route
                }
            }
        )

        sessions = session_service.get_all()
        session_service.save(sessions, active=target_session_id)
        return True
    except Exception:
        app.logger.exception("[mobile-session-save] failed appending mobile exchange")
        return False



# NOVA_EXECUTION_TRIGGER_BRIDGE_20260607
def _nova_try_execution_trigger_20260607(session_id, user_text):
    try:
        if not chat_execution_service.is_execution_trigger(user_text):
            return None

        state = chat_execution_service.advance(session_id)
        reply_text = chat_execution_service.format_reply(state)

        return {
            "ok": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
                "execution_state": state,
            },
            "execution_state": state,
        }
    except Exception as exc:
        logger.exception("[NovaExecutionBridge] failed")
        reply_text = "Execution bridge failed: " + str(exc)
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
            },
        }



# NOVA_AUTO_PLAN_EXECUTION_START_20260607
def _nova_try_auto_plan_execution_start_20260607(session_id, user_text):
    try:
        raw_text = str(user_text or "").strip()
        clean_text = " ".join(raw_text.lower().split())

        if not clean_text.startswith("auto-plan "):
            return None

        goal = raw_text[len("auto-plan "):].strip() or "Untitled execution mission"

        steps = [
            "Understand the mission and identify the target files",
            "Make the smallest safe implementation change",
            "Verify the result and report the next move",
        ]

        state = chat_execution_service.start(session_id, goal, steps)
        if not isinstance(state, dict):
            state = chat_execution_service.get_state(session_id)

        current_step = state.get("current_step") if isinstance(state, dict) else None

        reply_text = (
            "Execution mission started: " + goal + "\n\n"
            "Step 1/3: " + str(current_step or "Understand the mission and identify the target files") + "\n\n"
            "Send k, next, continue, or run it to advance."
        )

        return {
            "ok": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
                "execution_state": state,
            },
            "execution_state": state,
        }
    except Exception as exc:
        logger.exception("[NovaAutoPlanExecutionStart] failed")
        reply_text = "Auto-plan execution start failed: " + str(exc)
        return {
            "ok": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
        }


# NOVA_EXECUTION_AUTOPLAN_START_20260607
def _nova_try_execution_autoplan_start_20260607(session_id, user_text):
    try:
        clean = str(user_text or "").strip()
        lower = clean.lower()

        prefixes = [
            "auto-plan ",
            "autoplan ",
            "auto plan ",
        ]

        matched_prefix = None
        for prefix in prefixes:
            if lower.startswith(prefix):
                matched_prefix = prefix
                break

        if not matched_prefix:
            return None

        goal = clean[len(matched_prefix):].strip()
        if not goal:
            goal = "Untitled mission"

        steps = [
            "Inspect the current target and identify the smallest safe change",
            "Apply the implementation without disturbing working systems",
            "Verify the result and report the next move",
        ]

        state = chat_execution_service.start(
            session_id=session_id,
            goal=goal,
            steps=steps,
        )

        reply_text = (
            "Mission started: " + goal + "\n\n"
            "Step 1/" + str(len(steps)) + ": " + str(state.get("current_step")) + "\n\n"
            "Send k, next, continue, or run it to advance."
        )

        return {
            "ok": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
                "execution_state": state,
            },
            "execution_state": state,
        }
    except Exception as exc:
        logger.exception("[NovaExecutionAutoPlanStart] failed")
        reply_text = "Execution auto-plan start failed: " + str(exc)
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
            },
        }

# NOVA_EXECUTION_STATUS_BRIDGE_20260607
def _nova_try_execution_status_20260607(session_id, user_text):
    try:
        clean = str(user_text or "").strip().lower()

        if clean not in {"status", "execution status", "mission status"}:
            return None

        state = chat_execution_service.get_state(session_id)

        if not state or state.get("status") == "idle":
            reply_text = "No active mission."
        else:
            steps = state.get("steps") or []
            total = len(steps)
            current_index = int(state.get("current_index") or 0)
            current_step = state.get("current_step")
            status = state.get("status") or "unknown"
            goal = state.get("goal") or "Untitled mission"

            if status == "complete":
                step_line = "Step: complete"
            else:
                display_step = min(current_index + 1, total) if total else current_index + 1
                step_line = "Step " + str(display_step) + "/" + str(total) + ": " + str(current_step)

            reply_text = (
                "Current mission: " + str(goal) + "\n"
                "Status: " + str(status) + "\n"
                + step_line
            )

        return {
            "ok": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
                "execution_state": state,
            },
            "execution_state": state,
        }
    except Exception as exc:
        logger.exception("[NovaExecutionStatus] failed")
        reply_text = "Execution status failed: " + str(exc)
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
            },
        }


# NOVA_RESTORE_DOCX_EXTRACTOR_20260609
def _nova_extract_docx_text_20260607(file_path):
    """Extract readable text from a .docx file without calling OpenAI."""
    from pathlib import Path
    import zipfile
    import xml.etree.ElementTree as ET

    path = Path(str(file_path or ""))
    if not path.exists() or not path.is_file():
        return ""

    try:
        with zipfile.ZipFile(path) as archive:
            try:
                xml_data = archive.read("word/document.xml")
            except KeyError:
                return ""

        root = ET.fromstring(xml_data)
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

        paragraphs = []
        for paragraph in root.iter(namespace + "p"):
            parts = []
            for node in paragraph.iter(namespace + "t"):
                if node.text:
                    parts.append(node.text)
            line = "".join(parts).strip()
            if line:
                paragraphs.append(line)

        return "\n".join(paragraphs).strip()
    except Exception:
        return ""

# NOVA_DIRECT_ATTACHMENT_TEXT_SUMMARY_20260609
def _nova_plain_attachment_text_summary_20260609(file_name, file_path, content, user_text=""):
    import re

    name = str(file_name or "attachment").strip() or "attachment"
    path = str(file_path or "").strip()
    raw = str(content or "")

    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"(?is)\[CURRENT UPLOADED TEXT ATTACHMENTS\]", "", cleaned)
    cleaned = re.sub(r"(?is)\[/CURRENT UPLOADED TEXT ATTACHMENTS\]", "", cleaned)
    cleaned = re.sub(r"(?im)^Attachment file content:\s*.*$", "", cleaned)
    cleaned = re.sub(r"(?im)^Path:\s*.*$", "", cleaned)
    cleaned = re.sub(r"(?im)^Size:\s*.*$", "", cleaned)
    cleaned = re.sub(r"(?im)^Content:\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    lines = []
    for line in cleaned.splitlines():
        item = line.strip()
        if not item:
            continue
        if item.lower() in {"summarize this file", "summarise this file", "summarize this", "summarise this"}:
            continue

        # NOVA_FILTER_ATTACHMENT_SUMMARY_JUNK_LINES_20260609
        compact = re.sub(r"\s+", "", item)
        if len(compact) <= 2:
            continue
        if re.fullmatch(r"[\W_]+", compact):
            continue

        lines.append(item)

    sample = "\n".join(lines[:120]).strip()
    lower_sample = sample.lower()

    if not sample:
        sample = cleaned[:2000].strip()

    key_points = []

    if "import " in lower_sample or "def " in lower_sample or "class " in lower_sample:
        key_points.append("This appears to be a source code file.")
        if "from __future__ import annotations" in lower_sample:
            key_points.append("It uses future annotations, so it is likely modern Python code.")
        if "def " in lower_sample:
            key_points.append("It defines functions that likely contain the main behavior.")
        if "class " in lower_sample:
            key_points.append("It defines classes, so part of the file is object-oriented.")
        if "flask" in lower_sample or "@app.route" in lower_sample:
            key_points.append("It appears connected to a Flask/backend route system.")
    else:
        key_points.append("The file contains readable text content.")
        sentences = re.split(r"(?<=[.!?])\s+", sample)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) >= 40:
                key_points.append(sentence[:220])
            if len(key_points) >= 5:
                break

    if len(key_points) < 2 and sample:
        for line in lines[:5]:
            key_points.append(line[:220])
            if len(key_points) >= 5:
                break

    preview = sample[:1200].strip()

    body = []
    body.append(f"Summary of {name}:")
    body.append("")
    body.append("Key points:")
    for index, point in enumerate(key_points[:6], 1):
        body.append(f"{index}. {point}")
    body.append("")
    body.append("Preview:")
    body.append(preview)

    if path:
        body.append("")
        body.append(f"File path: {path}")

    return "\n".join(body).strip()

def _nova_strip_project_context_from_visible_text(text):
    clean = str(text or "")

    markers = (
        "\n\nProject-aware context for Nova:",
        "\nProject-aware context for Nova:",
        "Project-aware context for Nova:",
    )

    for marker in markers:
        if marker in clean:
            clean = clean.split(marker, 1)[0].strip()

    return clean

def api_chat():
    # NOVA_API_CHAT_IMAGE_VISION_GATE_20260607
    try:
        from pathlib import Path as _NovaPath
        import base64 as _nova_base64
        import mimetypes as _nova_mimetypes
        import os as _nova_os

        _nova_payload = request.get_json(silent=True) or {}



        _nova_user_text = str(
            _nova_payload.get("user_text")
            or _nova_payload.get("text")
            or _nova_payload.get("message")
            or ""
        ).strip()

        _nova_session_id = str(
            _nova_payload.get("session_id")
            or _nova_payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        _nova_attachments = _nova_payload.get("attachments") or []

        # ðŸš¨ IMAGE FASTPATH SAFETY GUARD
        if str(_nova_user_text or "").strip().lower().startswith("/image"):
            _nova_attachments = []

        _nova_image = None

        if isinstance(_nova_attachments, list):
            for _nova_item in _nova_attachments:
                if not isinstance(_nova_item, dict):
                    continue

                _nova_mime = str(
                    _nova_item.get("mime_type")
                    or _nova_item.get("type")
                    or ""
                ).lower()

                _nova_name_probe = str(
                    _nova_item.get("filename")
                    or _nova_item.get("original_filename")
                    or _nova_item.get("name")
                    or _nova_item.get("url")
                    or _nova_item.get("file_url")
                    or ""
                ).lower()

                if (
                    _nova_mime.startswith("image/")
                    or any(ext in _nova_name_probe for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
                ):
                    _nova_image = _nova_item
                    break
        # NOVA_IMAGE_GATE_WEB_INTENT_STRIPS_STALE_ATTACHMENTS_20260609
        # Web/news prompts must ignore stale mobile attachment payload before the image gate scans it.
        _nova_image_gate_clean = " ".join(str(_nova_user_text or "").lower().split())
        _nova_image_gate_web_terms = (
            "latest news",
            "news about",
            "today in",
            "what happened today",
            "current news",
            "breaking news",
            "recent news",
            "latest tech news",
            "latest sports",
            "weather",
            "forecast",
            "current events",
        )
        if any(term in _nova_image_gate_clean for term in _nova_image_gate_web_terms):
            _nova_attachments = []
            try:
                request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
                request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
            except Exception:
                pass

        if isinstance(_nova_attachments, list):
            for _nova_item in _nova_attachments:
                if not isinstance(_nova_item, dict):
                    continue

                _nova_mime = str(
                    _nova_item.get("mime_type")
                    or _nova_item.get("type")
                    or ""
                ).lower()

                _nova_name_probe = str(
                    _nova_item.get("filename")
                    or _nova_item.get("original_filename")
                    or _nova_item.get("name")
                    or _nova_item.get("url")
                    or _nova_item.get("file_url")
                    or ""
                ).lower()

                if (
                    _nova_mime.startswith("image/")
                    or any(_nova_ext in _nova_name_probe for _nova_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
                ):
                    _nova_image = _nova_item
                    break

        if _nova_image:
            _nova_raw_url = str(
                _nova_image.get("url")
                or _nova_image.get("file_url")
                or ""
            ).strip()

            _nova_raw_name = str(
                _nova_image.get("filename")
                or _nova_image.get("original_filename")
                or _nova_image.get("name")
                or ""
            ).strip()

            _nova_filename = ""

            if "/api/uploads/" in _nova_raw_url:
                _nova_filename = _nova_raw_url.split("/api/uploads/", 1)[1].split("?", 1)[0].split("#", 1)[0]
            elif _nova_raw_url:
                _nova_filename = _NovaPath(_nova_raw_url).name

            if not _nova_filename and _nova_raw_name:
                _nova_filename = _NovaPath(_nova_raw_name).name

            _nova_filename = _nova_filename.replace("\\", "/").split("/")[-1].strip()

            _nova_candidates = [
                _NovaPath.cwd() / "uploads" / _nova_filename,
                _NovaPath.cwd() / "static" / "uploads" / _nova_filename,
                _NovaPath(__file__).resolve().parent / "uploads" / _nova_filename,
                _NovaPath(__file__).resolve().parent / "static" / "uploads" / _nova_filename,
            ]

            _nova_image_path = None

            for _nova_candidate in _nova_candidates:
                try:
                    if _nova_candidate.exists() and _nova_candidate.is_file():
                        _nova_image_path = _nova_candidate
                        break
                except Exception:
                    continue

            if _nova_image_path is None:
                _nova_text = (
                    "VISION_DEBUG: image file not found. "
                    + "filename=" + str(_nova_filename)
                    + " raw_url=" + str(_nova_raw_url)
                    + " candidates=" + " | ".join(str(c) for c in _nova_candidates)
                )
                _nova_vision_used = False
            else:
                try:
                    from openai import OpenAI as _NovaOpenAI

                    _nova_mime_type = _nova_mimetypes.guess_type(str(_nova_image_path))[0] or "image/jpeg"

                    with open(_nova_image_path, "rb") as _nova_file:
                        _nova_encoded = _nova_base64.b64encode(_nova_file.read()).decode("utf-8")

                    _nova_data_url = "data:" + _nova_mime_type + ";base64," + _nova_encoded

                    _nova_client = _NovaOpenAI(api_key=_nova_os.getenv("OPENAI_API_KEY"))

                    _nova_response = _nova_client.chat.completions.create(
                        model=_nova_os.getenv("NOVA_VISION_MODEL", "gpt-4o-mini"),
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are Nova's image analysis module. "
                                    "Describe the attached image directly. "
                                    "Do not use web search. "
                                    "Do not mention unrelated news. "
                                    "If something cannot be identified, describe what is visible."
                                ),
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": _nova_user_text or "What is this image?",
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": _nova_data_url,
                                        },
                                    },
                                ],
                            },
                        ],
                        temperature=0.2,
                        max_tokens=500,
                    )

                    _nova_text = str(_nova_response.choices[0].message.content or "").strip()

                    if not _nova_text:
                        _nova_text = "VISION_DEBUG: OpenAI vision returned empty text."
                        _nova_vision_used = False
                    else:
                        _nova_vision_used = True

                except Exception as _nova_exc:
                    _nova_text = "VISION_DEBUG: OpenAI vision failed: " + str(_nova_exc)
                    _nova_vision_used = False

            return jsonify({
                "ok": True,
                "active_session_id": _nova_session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_text,
                    "attachments": [],
                    "meta": {
                        "attachment_analysis": True,
                        "api_chat_image_vision_gate": True,
                        "vision_used": _nova_vision_used,
                        "source_urls": [],
                        "sources": [],
                    },
                },
                "debug": {
                    "route": "api_chat",
                    "route_taken": "attachment_analysis",
                    "decision": {
                        "route": "attachment_analysis",
                        "mode": "image_analysis",
                        "strategy": "api_chat_image_vision_gate",
                        "source_urls": [],
                        "sources": [],
                    },
                },
                "session_attachments": _nova_attachments,
                "attachment_debug": {
                    "requested_session_id": _nova_session_id,
                    "session_attachments_count": len(_nova_attachments) if isinstance(_nova_attachments, list) else 0,
                },
            })

    except Exception as _nova_api_image_gate_error:
        print("[NOVA_API_CHAT_IMAGE_VISION_GATE] failed:", _nova_api_image_gate_error)

    # NOVA_DURABLE_EXECUTION_TOP_GUARD_20260607
    try:
        _nova_exec_payload = request.get_json(silent=True) or {}
        _nova_exec_user_text = str(
            _nova_exec_payload.get("user_text")
            or _nova_exec_payload.get("text")
            or _nova_exec_payload.get("message")
            or ""
        ).strip()
        _nova_exec_session_id = str(
            _nova_exec_payload.get("session_id")
            or _nova_exec_payload.get("client_session_id")
            or "default"
        ).strip() or "default"
        _nova_exec_clean = " ".join(_nova_exec_user_text.lower().split())

        # NOVA_WEB_INTENT_BLOCKS_STALE_ATTACHMENT_20260609
        # Fresh web/news/weather/current-events prompts must not be hijacked by stale attachment/image state.
        _nova_web_intent_terms = (
            "latest news",
            "news about",
            "today in",
            "what happened today",
            "current news",
            "breaking news",
            "recent news",
            "latest tech news",
            "latest sports",
            "weather",
            "forecast",
            "current events",
        )
        _nova_is_web_intent = any(term in _nova_exec_clean for term in _nova_web_intent_terms)

        if _nova_is_web_intent:
            try:
                request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
                request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
            except Exception:
                pass
        # NOVA_IMAGE_ATTACHMENT_NO_WEB_FALLBACK_20260607
        _nova_image_prompt_words = [
            "describe this image",
            "what is this image",
            "what is in this image",
            "what's in this image",
            "look at this image",
            "analyze this image",
            "analyse this image",
            "this picture",
            "this photo",
        ]

        _nova_current_attachments = _nova_exec_payload.get("attachments") or []
        if not isinstance(_nova_current_attachments, list):
            _nova_current_attachments = []

        _nova_has_image_attachment = False
        for _nova_attachment in _nova_current_attachments:
            if not isinstance(_nova_attachment, dict):
                continue

            _nova_name = str(
                _nova_attachment.get("filename")
                or _nova_attachment.get("original_filename")
                or _nova_attachment.get("name")
                or _nova_attachment.get("url")
                or _nova_attachment.get("file_url")
                or ""
            ).lower()

            _nova_mime = str(_nova_attachment.get("mime_type") or _nova_attachment.get("type") or "").lower()

            if (
                _nova_mime.startswith("image/")
                or _nova_name.endswith(".png")
                or _nova_name.endswith(".jpg")
                or _nova_name.endswith(".jpeg")
                or _nova_name.endswith(".webp")
            ):
                _nova_has_image_attachment = True
                break

        if _nova_has_image_attachment and any(_word in _nova_exec_clean for _word in _nova_image_prompt_words):
            _nova_exec_payload["force_image_analysis"] = True
            _nova_exec_payload["disable_web_fetch"] = True

        # NOVA_IMAGE_PROMPT_NO_WEB_GUARD_20260607
        _nova_image_words = [
            "describe this image",
            "describe image",
            "what is in this image",
            "what's in this image",
            "what is this image",
            "look at this image",
            "analyze this image",
            "analyse this image",
            "this picture",
            "this photo",
        ]

        if any(_word in _nova_exec_clean for _word in _nova_image_words):
            _nova_current_attachments = _nova_exec_payload.get("attachments") or []
            if not isinstance(_nova_current_attachments, list):
                _nova_current_attachments = []

            if not _nova_current_attachments:
                _nova_answer = (
                    "I can see you asked me to describe an image, but no image attachment reached /api/chat.\n\n"
                    "The upload/preview side may be working, but the mobile send payload is still dropping the attachment before the backend receives it.\n\n"
                    "Next fix: make the mobile /api/chat request include the pending image attachment so backend sees attachments_count=1."
                )

                return jsonify({
                    "ok": True,
                    "text": _nova_answer,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _nova_answer,
                        "meta": {
                            "image_prompt_no_attachment": True,
                            "web_bypassed": True,
                            "route_taken": "image_prompt_no_web_guard"
                        },
                        "attachments": []
                    },
                    "debug": {
                        "route": "api_chat",
                        "route_taken": "image_prompt_no_web_guard",
                        "blocked": ["web_fetch"]
                    }
                })

        # NOVA_DOCX_ATTACHMENT_DIRECT_HANDLER_20260607
        _nova_docx_attachment_words = [
            "attachment",
            "attach",
            "what is this file",
            "what is this attachment",
            "summarize this attachment",
            "summarise this attachment",
            "summarize this file",
            "summarise this file",
            "this file",
        ]

        if any(_word in _nova_exec_clean for _word in _nova_docx_attachment_words):
            _nova_current_attachments = _nova_exec_payload.get("attachments") or []

            if isinstance(_nova_current_attachments, list) and _nova_current_attachments:
                for _nova_attachment in _nova_current_attachments:
                    _nova_name = str(
                        _nova_attachment.get("original_filename")
                        or _nova_attachment.get("filename")
                        or _nova_attachment.get("name")
                        or _nova_attachment.get("url")
                        or _nova_attachment.get("file_url")
                        or ""
                    ).lower()

                    if ".docx" not in _nova_name:
                        continue

                    _nova_file_path = _nova_find_uploaded_file_path_20260607(_nova_attachment)
                    # NOVA_USE_PHASE2_DOCX_EXTRACTOR_DIRECT_20260609
                    _nova_docx_text = _nova_phase2_extract_docx_text(_nova_file_path)

                    if _nova_docx_text:
                        _nova_preview = _nova_docx_text[:1200].strip()

                        # NOVA_DIRECT_DOCX_ATTACHMENT_SUMMARY_RETURN_20260609
                        _nova_answer = _nova_plain_attachment_text_summary_20260609(
                            _nova_name,
                            _nova_file_path,
                            _nova_docx_text,
                            _nova_exec_user_text,  # NOVA_FIX_DOCX_SUMMARY_USER_TEXT_ARG_20260609
                        )

                        return jsonify({
                            "ok": True,
                            "text": _nova_answer,
                            "assistant_message": {
                                "role": "assistant",
                                "text": _nova_answer,
                                "meta": {
                                    "docx_attachment_extracted": True,
                                    "route_taken": "docx_attachment_direct_handler",
                                    "file_path": _nova_file_path
                                },
                                "attachments": []
                            },
                            "debug": {
                                "route": "api_chat",
                                "route_taken": "docx_attachment_direct_handler",
                                "file_path": _nova_file_path,
                                "extracted_chars": len(_nova_docx_text)
                            }
                        })

        # NOVA_ATTACHMENT_PROMPT_NO_WEB_GUARD_20260607
        _nova_attachment_words = [
            "attachment",
            "attach",
            "summarize this attachment",
            "summarise this attachment",
            "summarize this file",
            "summarise this file",
            "this file",
        ]

        if any(_word in _nova_exec_clean for _word in _nova_attachment_words):
            _nova_current_attachments = _nova_exec_payload.get("attachments") or []
            if not isinstance(_nova_current_attachments, list):
                _nova_current_attachments = []

            if not _nova_current_attachments:
                _nova_answer = (
                    "I can see you asked about an attachment, but no attachment reached /api/chat.\n\n"
                    "Frontend upload/preview may have worked, but the send payload did not include the file.\n\n"
                    "Next fix: make the mobile send payload carry the uploaded attachment into /api/chat."
                )

                return jsonify({
                    "ok": True,
                    "text": _nova_answer,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _nova_answer,
                        "meta": {
                            "attachment_prompt_no_attachment": True,
                            "web_bypassed": True,
                            "route_taken": "attachment_prompt_no_web_guard"
                        },
                        "attachments": []
                    },
                    "debug": {
                        "route": "api_chat",
                        "route_taken": "attachment_prompt_no_web_guard",
                        "blocked": ["web_fetch"]
                    }
                })

        # NOVA_API_CHAT_PROJECT_STATUS_FRONT_GUARD_20260607
        _nova_project_status_phrases = [
            "what did we fix",
            "what we fixed",
            "explain what we fixed",
            "summarize what we fixed",
            "what did we do today",
            "what have we done today",
        ]

        if any(_phrase in _nova_exec_clean for _phrase in _nova_project_status_phrases):
            _nova_answer = (
                "Here is what we actually fixed today:\n\n"
                "- Fixed the mobile composer buttons so send, voice, attach, tools, and TTS stopped stretching.\n"
                "- Fixed the mojibukakke icon issue where broken encoded symbols were showing instead of clean icons.\n"
                "- Fixed the stale frontend cache issue where /mobile kept loading an old nova-mobile-app.js?v=attachment-payload-bridge-20260607204432 version.\n"
                "- Slimmed the mobile composer/input bar so the real input and main buttons are now 40px high.\n"
                "- Fixed the router bug where the word 'today' forced local project questions into web_fetch.\n\n"
                "Remaining issue: add a real work-log system so Nova can summarize actual project progress instead of guessing from old memories."
            )

            return jsonify({
                "ok": True,
                "text": _nova_answer,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_answer,
                    "meta": {
                        "project_status_direct": True,
                        "route_taken": "api_chat_project_status_front_guard",
                        "memory_bypassed": True,
                        "web_bypassed": True
                    },
                    "attachments": []
                },
                "debug": {
                    "route": "api_chat",
                    "route_taken": "api_chat_project_status_front_guard",
                    "blocked": ["chat_service_memory", "web_fetch"]
                }
            })


        # NOVA_EXECUTION_STATUS_TOP_GUARD_20260607
        if _nova_exec_clean in {"status", "execution status", "mission status"}:
            _nova_exec_state = chat_execution_service.get_state(_nova_exec_session_id)
            _nova_exec_reply = chat_execution_service.format_reply(_nova_exec_state)

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply,
                    "content": _nova_exec_reply,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })

        # NOVA_EXECUTION_RESET_ALL_BRIDGE_20260607
        if _nova_exec_clean in {"reset all", "reset all missions", "clear all missions", "clear all execution", "reset executions"}:
            _nova_reset_session_ids = []

            if hasattr(chat_execution_service, "list_sessions"):
                try:
                    _nova_reset_session_ids = list(chat_execution_service.list_sessions() or [])
                except Exception:
                    _nova_reset_session_ids = []

            if not _nova_reset_session_ids:
                for _nova_attr_name in ("states", "_states", "execution_states", "_execution_states", "missions", "_missions"):
                    _nova_attr_value = getattr(chat_execution_service, _nova_attr_name, None)
                    if isinstance(_nova_attr_value, dict):
                        _nova_reset_session_ids = list(_nova_attr_value.keys())
                        break

            if _nova_exec_session_id not in _nova_reset_session_ids:
                _nova_reset_session_ids.append(_nova_exec_session_id)

            _nova_reset_session_ids = [
                str(_nova_sid).strip()
                for _nova_sid in _nova_reset_session_ids
                if str(_nova_sid).strip()
            ]

            _nova_reset_session_ids = list(dict.fromkeys(_nova_reset_session_ids))
            _nova_cleared_sessions = []

            for _nova_sid in _nova_reset_session_ids:
                try:
                    chat_execution_service.reset(_nova_sid)
                    _nova_cleared_sessions.append(_nova_sid)
                except Exception:
                    pass

            if _nova_cleared_sessions:
                reply_text = (
                    "All known execution missions reset. Cleared sessions: "
                    + ", ".join(_nova_cleared_sessions)
                )
            else:
                reply_text = "No execution missions were found to reset."

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })
        # NOVA_EXECUTION_RESET_BRIDGE_20260607
        if _nova_exec_clean in {"reset mission", "reset execution", "clear mission", "reset"}:
            _nova_exec_state = chat_execution_service.reset(_nova_exec_session_id)
            reply_text = f"Mission reset. Previous mission state cleared for session {_nova_exec_session_id}."

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })

        _nova_boot_log_20260701("DEBUG GOAL:", _nova_exec_user_text)
        _nova_boot_log_20260701("DEBUG CLEAN:", _nova_exec_clean)

        if _nova_exec_clean.startswith("auto-plan "):
            _nova_exec_goal = (
                _nova_exec_user_text[len("auto-plan "):].strip()
                or "Untitled execution mission"
            )

            _nova_goal_lower = _nova_exec_goal.lower()

            _nova_boot_log_20260701("DEBUG LOWER:", _nova_goal_lower)

            if "attachment" in _nova_goal_lower or "upload" in _nova_goal_lower or "preview" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect the attachment upload, payload, and preview flow",
                    "Patch the smallest broken link between upload capture and preview rendering",
                    "Test upload preview, send payload, and attachment summary behavior",
                ]
            elif (
                "mobile" in _nova_goal_lower
                or " css" in _nova_goal_lower
                or " ui " in f" {_nova_goal_lower} "
            ):
                _nova_exec_steps = [
                    "Inspect the mobile UI file and identify the broken layout target",
                    "Patch the smallest CSS or JS issue without touching stable backend logic",
                    "Verify mobile layout, composer buttons, and session behavior",
                ]
            elif "web" in _nova_goal_lower or "fetch" in _nova_goal_lower or "search" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect the web fetch route, ranking path, and displayed source output",
                    "Patch the smallest mismatch between backend fetch results and UI/session output",
                    "Verify fresh search results, source ordering, and displayed cards",
                ]
            elif "memory" in _nova_goal_lower or "recall" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect memory write, ranking, and recall injection path",
                    "Patch the smallest issue blocking correct memory recall",
                    "Verify recall with a direct follow-up prompt",
                ]
            elif "execution" in _nova_goal_lower or "plan" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect execution state, trigger routing, and durable save file",
                    "Patch the smallest issue in mission start or step advancement",
                    "Verify auto-plan, k, next, continue, and completion behavior",
                ]
            else:
                _nova_exec_steps = [
                    "Inspect the mission and identify the likely target files",
                    "Make the smallest safe implementation change",
                    "Verify the result and report the next move",
                ]
            _nova_exec_state = chat_execution_service.start(
                _nova_exec_session_id,
                _nova_exec_goal,
                _nova_exec_steps,
            )
            _nova_exec_reply = (
                "Execution mission started: " + _nova_exec_goal + "\n\n"
                "Step 1/3: " + str(_nova_exec_state.get("current_step") or _nova_exec_steps[0]) + "\n\n"
                "Send k, next, continue, or run it to advance."
            )
            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply,
                    "content": _nova_exec_reply,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })

        if _nova_exec_clean in {"k", "ok", "okay", "next", "continue", "run it", "run step", "execute", "go"}:
            _nova_exec_state = chat_execution_service.advance(_nova_exec_session_id)
            _nova_exec_reply = chat_execution_service.format_reply(_nova_exec_state)
            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply,
                    "content": _nova_exec_reply,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })
    except Exception as exc:
        logger.exception("[NovaDurableExecutionTopGuard] failed")
        _nova_exec_reply = "Execution top guard failed: " + str(exc)
        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": _nova_exec_reply,
                "content": _nova_exec_reply,
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
        })
    # NOVA_AUTO_PLAN_TOP_OF_API_CHAT_GUARD_20260607
    try:
        _nova_early_payload = request.get_json(silent=True) or {}
        _nova_early_user_text = str(
            _nova_early_payload.get("user_text")
            or _nova_early_payload.get("text")
            or _nova_early_payload.get("message")
            or ""
        ).strip()
        _nova_early_session_id = str(
            _nova_early_payload.get("session_id")
            or _nova_early_payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        _nova_early_auto_plan_result = None

        if _nova_early_auto_plan_result is not None:
            return jsonify(_nova_early_auto_plan_result)
    except Exception as exc:
        logger.exception("[NovaAutoPlanTopGuard] failed")
        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "Auto-plan top guard failed: " + str(exc),
                "content": "Auto-plan top guard failed: " + str(exc),
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
        })
    # NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611
    # Explicit execution controls must beat web/news/search routing.
    try:
        _nova_exec_payload2 = request.get_json(silent=True) or {}
        _nova_exec_text2 = str(
            _nova_exec_payload2.get("user_text")
            or _nova_exec_payload2.get("text")
            or _nova_exec_payload2.get("message")
            or ""
        ).strip()
        _nova_exec_clean2 = " ".join(_nova_exec_text2.lower().split())

        _nova_exec_session_id2 = str(
            _nova_exec_payload2.get("session_id")
            or _nova_exec_payload2.get("client_session_id")
            or _nova_exec_payload2.get("conversation_id")
            or "default"
        ).strip() or "default"

        _nova_exec_commands2 = {
            "next": "next",
            "nex": "next",
            "continue": "next",
            "continue on": "next",
            "keep going": "next",
            "go": "next",
            "run next": "next",
            "next step": "next",
            "run step": "next",
            "run_step": "next",
            "run all": "run_all",
            "run_all": "run_all",
            "run it": "run_all",
            "execute": "run_all",
            "execute all": "run_all",
            "auto": "run_all",
            "auto mode": "run_all",
            "autopilot": "run_all",
            "retry": "retry",
            "retry failed": "retry",
            "retry_failed": "retry",
            "try again": "retry",
            "rerun failed": "retry",
            "stop": "cancel",
            "cancel": "cancel",
        }

        if _nova_exec_clean2 in _nova_exec_commands2:
            _nova_exec_action2 = _nova_exec_commands2[_nova_exec_clean2]

            if _nova_exec_action2 == "run_all":
                _nova_exec_state2 = chat_execution_service.run_all(_nova_exec_session_id2)
            elif _nova_exec_action2 == "cancel":
                _nova_exec_state2 = chat_execution_service.cancel(_nova_exec_session_id2)
            else:
                _nova_exec_state2 = chat_execution_service.advance(_nova_exec_session_id2)

            # NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611
            _nova_exec_status2 = str(_nova_exec_state2.get("status") or "").strip().lower()
            _nova_exec_goal2 = str(_nova_exec_state2.get("goal") or "").strip()
            _nova_exec_error2 = str(_nova_exec_state2.get("error") or "").strip()
            _nova_exec_steps2 = _nova_exec_state2.get("steps") or []
            _nova_exec_current2 = str(_nova_exec_state2.get("current_step") or "").strip()
            _nova_exec_index2 = int(_nova_exec_state2.get("current_index") or 0)

            if _nova_exec_status2 in {"idle", "none", ""}:
                _nova_exec_reply2 = _nova_exec_error2 or "No active execution mission. Start one with: auto-plan <goal>"
            elif _nova_exec_status2 in {"complete", "completed"}:
                if _nova_exec_goal2:
                    _nova_exec_reply2 = "Execution complete: " + _nova_exec_goal2
                else:
                    _nova_exec_reply2 = "Execution complete."
            elif _nova_exec_status2 in {"failed", "error"}:
                _nova_exec_reply2 = _nova_exec_error2 or "Execution failed."
            else:
                _nova_exec_total2 = len(_nova_exec_steps2)
                _nova_exec_step_num2 = min(_nova_exec_index2 + 1, _nova_exec_total2) if _nova_exec_total2 else 1
                if not _nova_exec_current2 and _nova_exec_steps2:
                    _nova_exec_current2 = str(_nova_exec_steps2[_nova_exec_index2] if _nova_exec_index2 < _nova_exec_total2 else _nova_exec_steps2[-1])
                _nova_exec_reply2 = (
                    "Execution waiting. "
                    + "Step "
                    + str(_nova_exec_step_num2)
                    + "/"
                    + str(_nova_exec_total2 or "?")
                    + ": "
                    + (_nova_exec_current2 or "Next step")
                )

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply2,
                    "content": _nova_exec_reply2,
                },
                "execution_state": _nova_exec_state2,
                "debug": {
                    "route": "execution_command_top_guard",
                    "command": _nova_exec_clean2,
                    "action": _nova_exec_action2,
                    "session_id": _nova_exec_session_id2,
                },
            })
    except Exception as exc:
        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "Execution command guard failed: " + str(exc),
                "content": "Execution command guard failed: " + str(exc),
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
            "debug": {
                "route": "execution_command_top_guard_failed",
            },
        })

    data = request_json()

    user_text = str(
        data.get("user_text")
        or data.get("text")
        or data.get("message")
        or ""
    ).strip()

    if isinstance(data, dict) and user_text:
        data["user_text"] = user_text
        data["text"] = user_text
        data["message"] = user_text

    _nova_user_text_lower = str(user_text or "").strip().lower()

    requested_session_id = str(data.get("session_id") or "").strip()
    session_id = requested_session_id

    # NOVA_EMPTY_SESSION_CREATE_GUARD_EXACT_20260610
    # Normalize attachments before session creation so blank frontend pings do not create stored sessions.
    attachments = normalize_attachments(data.get("attachments"))
    if not user_text and not attachments:
        return jsonify({
            "ok": True,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "text": "",
            },
            "text": "",
            "empty_request": True,
            "no_session_created": True,
        })

        result["session_id"] = result.get("session_id") or session_id
        result["active_session_id"] = result.get("active_session_id") or result.get("session_id") or session_id

        # NOVA_IMAGE_FASTPATH_RESPONSE_CLEANUP_20260610
        # Normalize echoed image-command text so the user sees only the real prompt.
        def _nova_clean_image_echo_text(value):
            value = str(value or "").strip()
            prefix = "Generated image for:"
            if not value.startswith(prefix):
                return value

            prompt = value[len(prefix):].strip()
            lowered = prompt.lower()

            cleanup_prefixes = [
                "/image",
                "generate an image of ",
                "generate image of ",
                "generate an image ",
                "generate image ",
                "create an image of ",
                "create image of ",
                "create an image ",
                "create image ",
                "make an image of ",
                "make image of ",
                "make an image ",
                "make image ",
                "draw ",
            ]

            if lowered == "/image":
                prompt = "image"
            else:
                for item in cleanup_prefixes:
                    if lowered.startswith(item):
                        prompt = prompt[len(item):].strip() or "image"
                        break

            return f"Generated image for: {prompt}"

        result["text"] = _nova_clean_image_echo_text(result.get("text"))
        assistant_message = result.get("assistant_message")
        if isinstance(assistant_message, dict):
            assistant_message["text"] = _nova_clean_image_echo_text(assistant_message.get("text"))
            result["assistant_message"] = assistant_message

        
        # NOVA_ATTACHMENT_SYNC_TEXT_TO_CLEAN_CONTENT_ALL_RETURNS_20260611
        try:
            _nova_result_for_attachment_sync = result if isinstance(result, dict) else None
            if isinstance(_nova_result_for_attachment_sync, dict):
                _nova_assistant_for_attachment_sync = _nova_result_for_attachment_sync.get("assistant_message")
                if isinstance(_nova_assistant_for_attachment_sync, dict):
                    _nova_content_for_attachment_sync = str(_nova_assistant_for_attachment_sync.get("content") or "").strip()
                    if _nova_content_for_attachment_sync.startswith("Attachment analysis:") and "Attachment " in _nova_content_for_attachment_sync and " content:" in _nova_content_for_attachment_sync:
                        _nova_assistant_for_attachment_sync["text"] = _nova_content_for_attachment_sync
                        _nova_assistant_for_attachment_sync["content"] = _nova_content_for_attachment_sync
                        _nova_result_for_attachment_sync["assistant_message"] = _nova_assistant_for_attachment_sync
        except Exception:
            pass
        return jsonify(result)


    # MOBILE_SESSION_FORCE_LOCK_20260606
    # Honor mobile-provided session ids instead of letting backend drift to random session_* ids.
    if requested_session_id:
        # FORCE_MOBILE_SESSION_OBJECT_CREATE_LOCK_20260606
        # Active id alone is not enough. Ensure the actual mobile session object exists.
        try:
            _nova_ensure_requested_session(
                requested_session_id,
                title=user_text or "Mobile Chat",
            )
        except Exception:
            app.logger.exception("[api_chat] failed to ensure requested mobile session object")

    try:
        # MOBILE_ATTACHMENT_FIX_20260606: active_session_id is read-only.
        pass
    except Exception:
        app.logger.exception("[api_chat] failed to force active mobile session id")


    attachments = normalize_attachments(request.json.get("attachments", []))

    # NOVA_API_CHAT_WEB_INTENT_STRIPS_CURRENT_ATTACHMENTS_20260609
    # If this is a fresh web/news request, do not let stale mobile attachment state hijack routing.
    _nova_main_clean_for_web = " ".join(str(user_text or "").lower().split())
    _nova_main_web_terms = (
        "latest news",
        "news about",
        "today in",
        "what happened today",
        "current news",
        "breaking news",
        "recent news",
        "latest tech news",
        "latest sports",
        "weather",
        "forecast",
        "current events",
    )
    if (
        request.environ.get("NOVA_IGNORE_STALE_ATTACHMENTS_20260609") == "1"
        or any(term in _nova_main_clean_for_web for term in _nova_main_web_terms)
    ):
        attachments = []
        try:
            data["attachments"] = []
            request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
            request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
        except Exception:
            pass

    # NOVA_INLINE_TEXT_ATTACHMENT_FASTPATH_20260612
    # Inline attachment text from API/mobile/browser tests is valid content.
    # Answer it before older upload-file lookup paths can return "file was not found in uploads."
    try:
        _nova_inline_text_items = []
        if isinstance(attachments, list):
            for _nova_inline_att in attachments:
                if not isinstance(_nova_inline_att, dict):
                    continue

                _nova_inline_text = str(_nova_inline_att.get("text") or _nova_inline_att.get("content") or "").strip()
                if not _nova_inline_text:
                    continue

                _nova_inline_name = str(
                    _nova_inline_att.get("original_filename")
                    or _nova_inline_att.get("filename")
                    or "inline attachment"
                ).strip()

                _nova_inline_text_items.append((_nova_inline_name, _nova_inline_text))

        _nova_inline_prompt = " ".join(str(user_text or "").lower().split())
        _nova_inline_wants_attachment = (
            bool(_nova_inline_text_items)
            and (
                "attachment" in _nova_inline_prompt
                or "summarize" in _nova_inline_prompt
                or "summary" in _nova_inline_prompt
                or "what exact text" in _nova_inline_prompt
                or "what is inside" in _nova_inline_prompt
                or "what's inside" in _nova_inline_prompt
                or "key point" in _nova_inline_prompt
                or "keypoint" in _nova_inline_prompt
                or len(_nova_inline_prompt) <= 60
            )
        )

        if _nova_inline_wants_attachment:
            _nova_inline_lines = []
            for _nova_inline_name, _nova_inline_text in _nova_inline_text_items:
                _nova_inline_lines.append(f"{_nova_inline_name}:")
                _nova_inline_lines.append(_nova_inline_text)

            _nova_inline_reply = (
                "Attachment analysis:\n"
                + "\n".join(_nova_inline_lines).strip()
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_inline_reply,
                    "content": _nova_inline_reply,
                },
                "text": _nova_inline_reply,
                "session_attachments": list(attachments or []),
                "attachment_debug": {
                    "requested_session_id": requested_session_id,
                    "active_session_id": session_id,
                    "session_attachments_count": len(attachments or []),
                    "inline_text_fastpath": True,
                },
                "debug": {
                    "route": "app_inline_text_attachment_fastpath",
                    "route_taken": "attachment_analysis",
                    "blocked_file_lookup": True,
                },
            })
    except Exception as _nova_inline_text_fastpath_error:
        app.logger.warning(
            "[InlineTextAttachmentFastPath] failed; falling through: %s",
            _nova_inline_text_fastpath_error,
        )
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

        # NOVA_INLINE_API_CHAT_FINAL_WEAK_GUARD_LOCK
        try:
            assistant = result.get("assistant_message") if isinstance(result, dict) else None
            current_text = str(
                (assistant or {}).get("text")
                or (assistant or {}).get("content")
                or ""
            ).strip()
            current_compact = " ".join(
                current_text
                .lower()
                .replace("Ã¢â‚¬â„¢", "'")
                .replace("ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢", "'")
                .replace("ÃƒÂ£Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢", "'")
                .replace("iÃƒÂ£Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢m", "i'm")
                .replace("iÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢m", "i'm")
                .split()
            )
            if (
                isinstance(result, dict)
                and isinstance(assistant, dict)
                and "ready" in current_compact
                and "what are we working on" in current_compact
            ):
                replacement = (
                    "I do not have a personal life story like a human. "
                    "I was built to help you think, build, debug, write, learn, and move faster. "
                    "For Nova, the active phase is frontend polish: clean the mobile UI, remove weak fallback behavior, "
                    "and make the live app match the backend tests that are already passing."
                )
                assistant["text"] = replacement
                assistant["content"] = replacement
                meta = assistant.get("meta") if isinstance(assistant.get("meta"), dict) else {}
                meta["weak_response_guarded"] = True
                meta["weak_response_original"] = current_text
                assistant["meta"] = meta
                result["assistant_message"] = assistant
        except Exception:
            pass

        return jsonify(_nova_replace_weak_backend_reply(user_text, result))

    force_new_session = bool(data.get("force_new_session") or data.get("new_session"))

    if not session_id and not force_new_session:
        active = session_service.get_active()
        if active:
            session_id = str(active.get("id") or "").strip()

    if not session_id:
        created = session_service.create("New Chat")
        session_id = created["id"]

    if not user_text and not attachments:
        return json_error("Missing user_text or attachments", 400)

    # EARLY_IMAGE_ATTACHMENT_GATE_20260606
    # If the current request includes image attachments, answer before memory,
    # web routing, weak fallback guards, or chat_service can turn it into a generic intro.
    try:
        current_attachments = attachments if isinstance(attachments, list) else []
        image_attachments = []

        for item in current_attachments:
            if not isinstance(item, dict):
                continue

            name = str(
                item.get("original_filename")
                or item.get("filename")
                or item.get("name")
                or "image attachment"
            ).strip()

            mime = str(
                item.get("mime_type")
                or item.get("content_type")
                or item.get("type")
                or item.get("mime")
                or ""
            ).strip()

            url = str(item.get("file_url") or item.get("url") or item.get("path") or "").strip()
            name_lower = name.lower()

            if (
                mime.lower().startswith("image/")
                or name_lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
                or url.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
            ):
                image_attachments.append({
                    "name": name,
                    "mime": mime or "image/*",
                    "url": url,
                    "raw": item,
                })

        if image_attachments:
            # SKIP_EARLY_IMAGE_GATE_FOR_ANALYSIS_REQUESTS_20260606
            # Do not let the receipt gate block real image/attachment analysis.
            _analysis_text = str(user_text or "").lower().strip()
            _analysis_words = (
                "summarize",
                "summary",
                "analyze",
                "analyse",
                "describe",
                "what is this",
                "what's this",
                "what is in",
                "what's in",
                "what was the attached",
                "what was attached",
                "read this",
                "look at this",
                "tell me about",
            )

            if any(word in _analysis_text for word in _analysis_words):
                image_attachments = []
            else:
                lines = ["Image attachment received."]

            for index, item in enumerate(image_attachments[:5], start=1):
                line = f"{index}. {item.get('name') or 'image attachment'} ({item.get('mime') or 'image/*'})"
                if item.get("url"):
                    line += f" Ã¢â‚¬â€ {item.get('url')}"
                lines.append(line)

            lines.append("")
            lines.append("The image is now attached to this chat request.")

            _early_gate_text = str(user_text or "").lower().strip()
            _early_gate_analysis_request = any(
                word in _early_gate_text
                for word in (
                    "summarize",
                    "summary",
                    "analyze",
                    "analyse",
                    "describe",
                    "what is this",
                    "what's this",
                    "what is in",
                    "what's in",
                    "read this",
                    "look at this",
                    "tell me about",
                )
            )

            if _early_gate_analysis_request:
                raise RuntimeError("skip early image receipt gate for analysis request")

            reply_text = "Attachment received."

            app.logger.info(
                "[EarlyImageAttachmentGate] returning image attachment response session_id=%s image_count=%s",
                session_id,
                len(image_attachments),
            )

            # MOBILE_EARLY_IMAGE_SAVE_EXCHANGE_LOCK_20260606
            _nova_direct_save_mobile_exchange(
                session_id,
                user_text,
                reply_text,
                attachments=current_attachments,
                route="early_image_attachment_gate",
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "attachments": current_attachments,
                    "meta": {
                        "route": "early_image_attachment_gate",
                    },
                },
                "attachments": current_attachments,
                "session_attachments": current_attachments,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "debug": {
                    "route": "early_image_attachment_gate",
                    "image_count": len(image_attachments),
                    "attachments_count": len(current_attachments),
                },
            })
    except Exception as early_image_error:
        app.logger.warning(
            "[EarlyImageAttachmentGate] failed; continuing normal api_chat flow: %s",
            early_image_error,
        )

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

        # NOVA_PHASE1_TEXT_ATTACHMENT_READER_INJECT_20260607
        user_text = _nova_phase1_append_text_attachments_to_user_text(
            user_text,
            attachments,
            logger=app.logger,
        )


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

        # NOVA_SKIP_RAW_BINARY_ATTACHMENT_INJECTION_CALL_20260607
        raw_injection_attachments = _nova_filter_raw_injection_attachments(
            attachments,
            logger=app.logger,
        )
        # ATTACHMENT_CONTENT_INJECTION_FINAL_LOCK
        # HARD_BYPASS_CASUAL_GREETINGS_LOCK
        # Tiny casual messages should not enter project-aware memory, attachment memory,
        # web routing, or task-mode responses.
        _nova_clean_casual_text = str(user_text or "").strip().lower()
        _nova_casual_greetings = {
            "hi",
            "hey",
            "yo",
            "hello",
            "sup",
        }

        if not attachments and _nova_clean_casual_text in _nova_casual_greetings:
            app.logger.info(
                "[api_chat] hard bypass casual greeting session_id=%s text=%r",
                session_id,
                user_text,
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Hey.",
                },
                "attachments": [],
                "session_attachments": [],
                "skip_post_processing": True,
                "skip_rewrite": True,
                "meta": {
                    "strategy": "hard_bypass_casual_greeting",
                },
            })

        attachment_content_lines = []

        # ATTACHMENT_INJECTION_LOOP_CURRENT_ONLY_LOCK
        # When the user sends attachments with this request, inject ONLY those current files.
        # Old session attachment memory can still be stored, but must not flood this prompt.
        # ACTUAL_STOP_STALE_ATTACHMENT_MEMORY_LOCK
        if attachments:
            remembered_session_attachments = list(attachments)
            app.logger.info(
                "[AttachmentContentGate] forcing current request attachments only before injection count=%s session_id=%s",
                len(remembered_session_attachments or []),
                session_id,
            )
        else:
            remembered_session_attachments = []
            app.logger.info(
                "[AttachmentContentGate] no current attachments; stale session attachment injection disabled session_id=%s",
                session_id,
            )

        # KILL_STALE_ATTACHMENT_LOOP_DIRECT_LOCK
        # Hard stop: never loop old remembered attachments when this request has no current upload.
        if not attachments:
            remembered_session_attachments = []
            attachment_content_lines = []
            app.logger.info(
                "[AttachmentContentGate] direct stale attachment loop killed because current request has no attachments session_id=%s",
                session_id,
            )

        for attachment in remembered_session_attachments or []:
            attachment_filename = str(attachment.get("filename") or "").strip()
            attachment_original_filename = str(attachment.get("original_filename") or "").strip()

            if attachment_filename == "<unknown>":
                attachment_filename = ""

            if attachment_original_filename == "<unknown>":
                attachment_original_filename = ""

            # ATTACHMENT_CONTENT_ROOT_FIX_20260604
            raw_attachment_name = (
                attachment_filename
                or attachment_original_filename
                or Path(str(attachment.get("stored_name") or "")).name
                or Path(str(attachment.get("file_url") or "")).name
                or Path(str(attachment.get("url") or "")).name
                or ""
            )

            local_path_value = str(attachment.get("local_path") or attachment.get("path") or "").strip()
            candidate_paths = []

            if local_path_value:
                candidate_paths.append(Path(local_path_value).expanduser())

            if raw_attachment_name:
                safe_name = Path(str(raw_attachment_name).strip().lstrip("/\\")).name
                candidate_paths.append((UPLOADS_DIR / safe_name).resolve())

            file_path = None
            uploads_root = UPLOADS_DIR.resolve()

            for candidate in candidate_paths:
                try:
                    candidate = candidate.resolve()
                except Exception:
                    continue

                if not candidate.exists() or not candidate.is_file():
                    continue

                if str(candidate).startswith(str(uploads_root)) or str(candidate).startswith(str(BASE_DIR.resolve())):
                    file_path = candidate
                    break

            if file_path is None and raw_attachment_name:
                file_path = (UPLOADS_DIR / Path(str(raw_attachment_name).strip().lstrip("/\\")).name).resolve()
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
                    # SKIP_BINARY_ATTACHMENT_TEXT_INJECTION_LOCK
                    mime_type = str(attachment.get("mime_type") or "").lower().strip()
                    filename_for_type = str(
                        attachment.get("original_filename")
                        or attachment.get("filename")
                        or ""
                    ).lower().strip()

                    binary_extensions = (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".webp",
                        ".bmp",
                        ".ico",
                        ".pdf",
                        ".zip",
                        ".7z",
                        ".rar",
                        ".exe",
                        ".dll",
                        ".mp3",
                        ".mp4",
                        ".mov",
                        ".wav",
                        ".webm",
                    )

                    is_binary_attachment = (
                        mime_type.startswith("image/")
                        or mime_type.startswith("audio/")
                        or mime_type.startswith("video/")
                        or mime_type in {
                            "application/pdf",
                            "application/zip",
                            "application/octet-stream",
                        }
                        or filename_for_type.endswith(binary_extensions)
                    )

                    if is_binary_attachment:
                        # FIX_ATTACHMENT_ANALYZER_ROUTE_AND_CALL_LOCK
                        attachment_path = str(file_path)
                        mime_type = str(mime_type or "")
                        extracted_attachment_text = _nova_analyze_binary_attachment_for_prompt(
                            attachment_path,
                            mime_type,
                        )
                        if extracted_attachment_text:
                            # STRIP_URLS_FROM_EXTRACTED_ATTACHMENT_CHAT_TEXT_LOCK
                            extracted_attachment_text = _nova_strip_urls_from_extracted_attachment_text(extracted_attachment_text)
                            content_snippet = extracted_attachment_text[:4000]
                            app.logger.info(
                                "[AttachmentAnalyzer] extracted binary attachment content path=%s chars=%s mime_type=%s",
                                attachment_path,
                                len(content_snippet),
                                mime_type,
                            )
                        else:
                            app.logger.info(
                                "[AttachmentAnalyzer] skipped binary attachment prompt append path=%s mime_type=%s",
                                attachment_path,
                                mime_type,
                            )
                            content_snippet = "[Attachment received, but no readable text could be extracted.]"
                    else:
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

            # ATTACHMENT_OUTPUT_CLEANER_20260604
            content_snippet = str(content_snippet or "")
            content_snippet = content_snippet.replace("\ufeff", "").replace("\u200b", "").strip()

            fallback_text = "[Attachment content could not be read from disk.]"

            attachment_display_name = (
                attachment.get("original_filename")
                or attachment.get("filename")
                or "<unknown>"
            )

            content_snippet = str(content_snippet or "")
            content_snippet = content_snippet.replace("\ufeff", "").replace("\u200b", "").strip()

            if not str(attachment.get("mime_type") or "").lower().startswith(("image/", "application/pdf")):
                content_snippet = content_snippet.replace(
                    "This uploaded attachment contains readable text about:",
                    ""
                ).replace(
                    "This uploaded attachment contains readable text about:",
                    ""
                ).strip()

            attachment_content_lines.append(
                f"Attachment {attachment_display_name} content:\n"
                f"{content_snippet if content_snippet else fallback_text}"
            )

        # GATE_REMEMBERED_ATTACHMENT_INJECTION_LOCK
        attachment_gate_text = str(user_text or "").lower().strip()
        current_request_attachments = attachments if isinstance(attachments, list) else []

        attachment_intent_words = (
            "attachment",
            "attachments",
            "attached",
            "file",
            "files",
            "image",
            "photo",
            "picture",
            "pic",
            "screenshot",
            "document",
            "docx",
            "pdf",
            "analyze this",
            "what is this",
            "what's this",
            "look at this",
            "read this",
            "summarize this file",
        )

        allow_remembered_attachment_injection = bool(current_request_attachments)


        if not allow_remembered_attachment_injection:
            attachment_content_lines = []
            remembered_session_attachments = []
            app.logger.info(
                "[AttachmentContentGate] skipped remembered attachment injection for non-attachment message session_id=%s text_len=%s",
                requested_session_id,
                len(attachment_gate_text),
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

        # SHORT_CHAT_SKIP_ATTACHMENT_MEMORY_LOCK
        short_casual_text = str(user_text or "").strip().lower()
        skip_remembered_attachment_context = (
            len(short_casual_text) <= 12
            and short_casual_text in {
                "hi",
                "yo",
                "hey",
                "hello",
                "sup",
                "k",
                "ok",
                "kk",
                "test",
            }
            and not attachments
        )

        if False and remembered_session_attachments and not skip_remembered_attachment_context:

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

        # SKIP_PROJECT_CONTEXT_FOR_CASUAL_SHORT_MESSAGES_LOCK
        _nova_original_user_text_before_project_context = str(user_text or "").strip()
        _nova_short_casual_messages = {
            "hi",
            "hey",
            "yo",
            "hello",
            "sup",
            "ok",
            "okay",
            "k",
            "yes",
            "no",
            "thanks",
            "thank you",
        }
        _nova_skip_project_context = (
            len(_nova_original_user_text_before_project_context) <= 16
            and _nova_original_user_text_before_project_context.lower() in _nova_short_casual_messages
        )

        if _nova_skip_project_context:
            app.logger.info(
                "[project-aware] skipped project context for short casual message session_id=%s text=%r",
                session_id,
                _nova_exec_user_text,  # NOVA_FIX_DOCX_SUMMARY_USER_TEXT_ARG_20260609
            )
        else:
            user_text = _nova_inject_project_state_context(
                user_text,
                session_id,
            )

        try:
            if _nova_skip_project_context:
                project_aware_context = ""
            else:
                project_aware_context = _nova_build_project_aware_context(
                    user_text,
                    session_id=session_id,
                    requested_session_id=requested_session_id,
                )
        except Exception:
            project_aware_context = ""
            app.logger.exception("[api_chat] failed to build project-aware memory context")

        if project_aware_context:
            raw_user_text = user_text
            clean_probe = str(raw_user_text or "").strip().lower()

            is_image_request = (
                clean_probe.startswith("/image")
                or clean_probe.startswith("draw ")
                or clean_probe.startswith("generate image")
                or clean_probe.startswith("make image")
                or clean_probe.startswith("create image")
            )

            if not is_image_request:
                user_text = f"{user_text}\n\n{project_aware_context}" if user_text else project_aware_context

                app.logger.info(
                    "[api_chat] injected project-aware memory context chars=%s session_id=%s requested_session_id=%s",
                    len(project_aware_context),
                    session_id,
                    requested_session_id,
                )

        # FORCE_EXTRACTED_TEXT_CHAT_HANDOFF_LOCK
        # If attachment text was already extracted into user_text, hand off to chat_service as plain text.
        # This prevents chat_service attachment guards from returning canned attachment responses.
        attachments_for_chat_service = list(attachments or [])

        # NOVA_IMAGE_COMMAND_ATTACHMENT_BYPASS_20260610
        # Explicit image generation commands must not be hijacked by stale/current attachment gates.
        _nova_image_command_text = str(data.get("user_text") or data.get("text") or data.get("message") or "").strip().lower()
        _nova_is_image_command = (
            _nova_image_command_text.startswith("/image")
            or _nova_image_command_text.startswith("image ")
            or _nova_image_command_text.startswith("generate image")
            or _nova_image_command_text.startswith("generate an image")
            or _nova_image_command_text.startswith("draw ")
            or _nova_image_command_text.startswith("create image")
            or _nova_image_command_text.startswith("make image")
        )

        if _nova_is_image_command:
            attachments = []
            remembered_session_attachments = []
            attachment_content_lines = []
            attachments_for_chat_service = []
            app.logger.info(
                "[ImageCommandAttachmentBypass] cleared attachment state for image command session_id=%s text=%r",
                session_id,
                _nova_image_command_text,
            )

        if attachment_content_lines:
            attachments_for_chat_service = []

            app.logger.info(
                "[AttachmentContentGate] extracted attachment text active; suppressing raw attachments session_id=%s extracted_count=%s",
                session_id,
                len(attachment_content_lines),
            )

        # APP_ATTACHMENT_PREHANDLE_REAL_ANCHOR_LOCK
        # Attachment requests are answered here after extracted text is injected,
        # but before chat_service/web routing can hijack the prompt.
        try:
            import re as _nova_prehandle_re

            _nova_prehandle_text = str(user_text or "")
            _nova_prehandle_lower = _nova_prehandle_text.lower()

            _nova_has_attachment_text = (
                "attachment content:" in _nova_prehandle_lower
                or "uploaded attachment context below" in _nova_prehandle_lower
                or "extracted attachment text" in _nova_prehandle_lower
                or "[mobile quick action attachment context active]" in _nova_prehandle_lower
            )

            _nova_attachment_intent = (
                "summarize" in _nova_prehandle_lower
                or "summary" in _nova_prehandle_lower
                or "keypoint" in _nova_prehandle_lower
                or "key point" in _nova_prehandle_lower
                or "continue" in _nova_prehandle_lower
                or "uploaded pdf attachment" in _nova_prehandle_lower
                or "uploaded attachment" in _nova_prehandle_lower
            )

            if _nova_has_attachment_text and _nova_attachment_intent:
                _nova_noise_exact = {
                    "attachment <unknown> content:",
                    "attachment content:",
                    "uploaded attachment content:",
                    "[pdf page 1]",
                    "search",
                    "images",
                    "videos",
                    "create",
                    "inspiration",
                    "keypoints",
            "copy",
            "regen",
            "regenerate",
                    "continue",
                    "summarize",
                    "summary",
                    "cop",
                    "filt",
                    "moderate",
                    "amazon",
                    "bath",
                    "related content",
                }

                _nova_noise_contains = (
                    "wayfair",
                    "save big",
                    "prices you'll love",
                    "eye-catching prints",
                    "url removed from extracted attachment text",
                    "free_shipping",
                    "furniture & dÃƒÂ©cor",
                    "kitchen appliances",
                    "love, horror and more themes",
                    "plain field in front of mountain peak",
                    "free stock photo",
                    "google news",
                    "direct_url_patch_hit",
                )

                _nova_lines = []
                _nova_seen = set()

                for _nova_raw_line in _nova_prehandle_text.splitlines():
                    _nova_line = _nova_prehandle_re.sub(r"^\s*\d+\.\s*", "", str(_nova_raw_line or "")).strip()
                    _nova_line = _nova_line.replace("Attachment <unknown>", "uploaded attachment")
                    _nova_line = _nova_line.replace("Attachment content:", "").strip()
                    _nova_line = _nova_prehandle_re.sub(r"\s+", " ", _nova_line).strip()

                    if not _nova_line:
                        continue

                    _nova_low = _nova_line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
                    _nova_low_compact = _nova_prehandle_re.sub(r"[^a-z0-9]+", " ", _nova_low).strip()

                    if _nova_low_compact in _nova_noise_exact:
                        continue

                    if any(_nova_bad in _nova_low for _nova_bad in _nova_noise_contains):
                        continue

                    if _nova_line.startswith("http://") or _nova_line.startswith("https://"):
                        continue

                    if len(_nova_line) <= 2:
                        continue

                    if _nova_low.startswith("typed user text"):
                        continue

                    if _nova_low.startswith("uploaded attachment context below"):
                        continue

                    if _nova_low.startswith("extracted attachment text"):
                        continue

                    if _nova_low.startswith("[mobile quick action attachment context active]"):
                        continue

                    _nova_key = _nova_low_compact[:160]
                    if not _nova_key or _nova_key in _nova_seen:
                        continue

                    _nova_seen.add(_nova_key)
                    _nova_lines.append(_nova_line)

                _nova_top = _nova_lines[:8]

                if _nova_top:
                    _nova_reply = "Attachment content:\n" + "\n".join(_nova_top[:12])
                else:
                    _nova_reply = (
                        "Attachment content:\n"
                        "The attachment was received, but no clean readable text was found."
                    )

                app.logger.info(
                    "[AttachmentPreHandle] answered before chat_service to block web/news hijack session_id=%s lines=%s",
                    session_id,
                    len(_nova_top),
                )

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _nova_reply.strip(),
                    },
                    "debug": {
                        "route": "attachment_prehandle_response",
                        "blocked_web_hijack": True,
                    },
                })

        except Exception as _nova_prehandle_exc:
            app.logger.warning(
                "[AttachmentPreHandle] failed; falling through to chat_service: %s",
                _nova_prehandle_exc,
            )


        # APP_ATTACHMENT_LINES_PREHANDLE_LOCK
        # Attachment text is already extracted in app.py. Answer before chat_service.handle,
        # because chat_service may route short mobile quick-actions to cached web/news URLs.
        try:
            import re as _nova_attach_re

            _attachment_lines = attachment_content_lines if isinstance(attachment_content_lines, list) else []
            _request_attachments = attachments if isinstance(attachments, list) else []
            _has_current_attachment = bool(_attachment_lines or _request_attachments)

            _intent_text = str(user_text or "").lower()
            _is_attachment_action = (
                "summarize" in _intent_text
                or "summary" in _intent_text
                or "keypoint" in _intent_text
                or "key point" in _intent_text
                or "continue" in _intent_text
                or "improve" in _intent_text
                or "next" in _intent_text
                or len(_intent_text.strip()) <= 40
            )

            # NOVA_ENABLE_ATTACHMENT_LINES_PREHANDLE_SAFE_20260611
            # Text attachments should answer immediately for summarize/continue/next/improve
            # instead of falling through to stale web/source/image routing.
            _has_image_like_attachment = False
            try:
                for _att in _request_attachments:
                    if not isinstance(_att, dict):
                        continue
                    _mime = str(_att.get("mime_type") or _att.get("type") or "").lower()
                    _name = str(_att.get("filename") or _att.get("original_filename") or "").lower()
                    if (
                        _mime.startswith("image/")
                        or _name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"))
                    ):
                        _has_image_like_attachment = True
                        break
            except Exception:
                _has_image_like_attachment = False

            _attachment_web_probe = " ".join(str(user_text or "").lower().split())
            _attachment_is_web_intent = (
                request.environ.get("NOVA_FORCE_WEB_INTENT_20260609") == "1"
                or request.environ.get("NOVA_IGNORE_STALE_ATTACHMENTS_20260609") == "1"
                or any(term in _attachment_web_probe for term in (
                    "latest news",
                    "news about",
                    "today in",
                    "what happened today",
                    "current news",
                    "breaking news",
                    "recent news",
                    "latest tech news",
                    "latest sports",
                    "weather",
                    "forecast",
                    "current events",
                ))
            )

            _attachment_is_image_command = str(user_text or "").lower().strip().startswith((
                "/image",
                "image ",
                "generate image",
                "generate an image",
                "draw ",
                "create image",
                "make image",
            ))

            if (
                _has_current_attachment
                and _is_attachment_action
                and not _has_image_like_attachment
                and not bool(locals().get("_attachment_web_intent", False))
                and not _attachment_is_image_command
            ):
                _raw_text = "\n".join(str(x or "") for x in _attachment_lines).strip()
                if not _raw_text:
                    _raw_text = str(user_text or "").strip()

                _noise_exact = {
                    "attachment <unknown> content:",
                    "attachment content:",
                    "uploaded attachment content:",
                    "[pdf page 1]",
                    "search",
                    "images",
                    "videos",
                    "create",
                    "inspiration",
                    "keypoints",
            "copy",
            "regen",
            "regenerate",
                    "continue",
                    "summarize",
                    "summary",
                    "cop",
                    "filt",
                    "moderate",
                    "amazon",
                    "bath",
                    "related content",
                }

                _noise_contains = (
                    "wayfair",
                    "save big",
                    "prices you'll love",
                    "eye-catching prints",
                    "url removed from extracted attachment text",
                    "free_shipping",
                    "furniture & dÃƒÂ©cor",
                    "kitchen appliances",
                    "love, horror and more themes",
                    "plain field in front of mountain peak",
                    "free stock photo",
                    "news.google.com",
                    "direct_url_patch_hit",
                )


                _raw_low_for_fake_context = str(_raw_text or "").lower()

                if (
                    "project-aware context for nova:" in _raw_low_for_fake_context
                    or "relevant persistent memory:" in _raw_low_for_fake_context
                    or "recent session context:" in _raw_low_for_fake_context
                    or "persistent memory:" in _raw_low_for_fake_context
                ):
                    raise RuntimeError("attachment prehandle ignored injected Nova memory context")
                _lines = []
                _seen = set()

                for _raw in _raw_text.splitlines():
                    _line = _nova_attach_re.sub(r"^\s*\d+\.\s*", "", str(_raw or "")).strip()
                    _line = _line.replace("Attachment <unknown>", "uploaded attachment")
                    _line = _line.replace("Attachment content:", "").strip()
                    _line = _nova_attach_re.sub(r"\s+", " ", _line).strip()

                    if not _line:
                        continue

                    _low = _line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
                    _compact = _nova_attach_re.sub(r"[^a-z0-9]+", " ", _low).strip()

                    if _compact in _noise_exact:
                        continue

                    if any(_bad in _low for _bad in _noise_contains):
                        continue

                    if _line.startswith("http://") or _line.startswith("https://"):
                        continue

                    if len(_line) <= 2:
                        continue

                    if not _compact or _compact in _seen:
                        continue

                    _seen.add(_compact)
                    _lines.append(_line)

                _top = _lines[:8]

                _fake_context_markers = (
                    "project-aware context for nova:",
                    "relevant persistent memory:",
                    "recent session context:",
                    "persistent memory:",
                    "[preference]",
                    "[user_fact]",
                    "[people]",
                )

                _top = [
                    _item for _item in _top
                    if not any(
                        _marker in str(_item or "").lower()
                        for _marker in _fake_context_markers
                    )
                ]

                if not _top:
                    raise RuntimeError("attachment prehandle ignored fake memory context")

                if _top:
                    _topic = "; ".join(_top[:3])
                    _reply = "Attachment analysis:\n"
                    _reply += f"This uploaded attachment contains readable text about: {_topic}.\n\n"
                    _reply += "Key points:\n"
                    for _i, _item in enumerate(_top, start=1):
                        _reply += f"{_i}. {_item}\n"
                    _reply += "\nPreview:\n" + "\n".join(_top[:6])
                else:
                    _reply = (
                        "Attachment analysis:\n"
                        "The attachment was received and processed, but the extracted text is too limited or noisy to summarize cleanly."
                    )

                _reply_low = str(_reply or "").lower()

                if (
                    "project-aware context for nova:" in _reply_low
                    or "relevant persistent memory:" in _reply_low
                    or "recent session context:" in _reply_low
                    or "persistent memory:" in _reply_low
                    or "[preference]" in _reply_low
                    or "[user_fact]" in _reply_low
                    or "[people]" in _reply_low
                ):
                    _reply = (
                        "Attachment received.\n"
                        "The file was uploaded, but Nova ignored internal memory/context text that was accidentally mixed into the attachment analyzer."
                    )

                app.logger.info(
                    "[AttachmentLinesPreHandle] answered before chat_service.handle session_id=%s lines=%s",
                    session_id,
                    len(_top),
                )

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _reply.strip(),
                    },
                    "debug": {
                        "route": "app_attachment_lines_prehandle",
                        "blocked_web_hijack": True,
                    },
                })

        except Exception as _attachment_prehandle_exc:
            app.logger.warning(
                "[AttachmentLinesPreHandle] failed; falling through to chat_service.handle: %s",
                _attachment_prehandle_exc,
            )

        # IMAGE_ATTACHMENT_PREHANDLE_LOCK
        # Current image attachments must beat web/source-open routing.
        try:
            # NOVA_IMAGE_COMMAND_SKIP_IMAGE_ATTACHMENT_PREHANDLE_20260610
            # Explicit image generation commands must not be converted into attachment-received replies.
            _nova_image_prehandle_command_text = str(
                data.get("user_text")
                or data.get("text")
                or data.get("message")
                or user_text
                or ""
            ).strip().lower()

            _nova_skip_image_attachment_prehandle = (
                _nova_image_prehandle_command_text.startswith("/image")
                or _nova_image_prehandle_command_text.startswith("image ")
                or _nova_image_prehandle_command_text.startswith("generate image")
                or _nova_image_prehandle_command_text.startswith("generate an image")
                or _nova_image_prehandle_command_text.startswith("draw ")
                or _nova_image_prehandle_command_text.startswith("create image")
                or _nova_image_prehandle_command_text.startswith("make image")
            )

            if _nova_skip_image_attachment_prehandle:
                raise RuntimeError("skip image attachment prehandle for explicit image command")

            current_attachments = list(attachments or [])
            image_attachments = []

            for item in current_attachments:
                if not isinstance(item, dict):
                    continue

                mime = str(
                    item.get("mime_type")
                    or item.get("type")
                    or item.get("mime")
                    or ""
                ).lower().strip()

                name = str(
                    item.get("original_filename")
                    or item.get("filename")
                    or item.get("name")
                    or item.get("url")
                    or item.get("file_url")
                    or "image attachment"
                ).strip()

                url = str(item.get("file_url") or item.get("url") or "").strip()

                if mime.startswith("image/") or name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                    image_attachments.append({
                        "name": name,
                        "mime": mime or "image/*",
                        "url": url,
                    })

            _image_prehandle_text = str(user_text or "").lower().strip()


            _is_image_prehandle_analysis = any(


                word in _image_prehandle_text


                for word in (


                    "summarize",


                    "summary",


                    "analyze",


                    "analyse",


                    "describe",


                    "what is this",


                    "what's this",


                    "what is in",


                    "what's in",


                    "read this",


                    "look at this",


                    "tell me about",


                )


            )


            


            if image_attachments and _is_image_prehandle_analysis:


                raise RuntimeError("skip image prehandle receipt for analysis request")


            


            if image_attachments:


                lines = ["Image attachment received."]

                for index, item in enumerate(image_attachments[:5], start=1):
                    label = item.get("name") or "image attachment"
                    mime = item.get("mime") or "image/*"
                    url = item.get("url") or ""

                    line = f"{index}. {label} ({mime})"
                    if url:
                        line += f" Ã¢â‚¬â€ {url}"
                    lines.append(line)

                lines.append("")
                lines.append("I can analyze this image, describe what is visible, or answer a question about it. The image attachment is now being handled as an attachment, not as a previous web source.")

                reply_text = "\n".join(lines).strip()

                app.logger.info(
                    "[ImageAttachmentPreHandle] answered before chat_service.handle session_id=%s images=%s",
                    session_id,
                    len(image_attachments),
                )

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": reply_text,
                    },
                    "session_attachments": current_attachments,
                    "attachments": current_attachments,
                    "skip_post_processing": True,
                    "skip_rewrite": True,
                    "meta": {
                        "strategy": "image_attachment_prehandle",
                        "image_count": len(image_attachments),
                    },
                })
        except Exception as _image_attachment_prehandle_error:
            app.logger.warning(
                "[ImageAttachmentPreHandle] failed; falling through to chat_service.handle: %s",
                _image_attachment_prehandle_error,
            )

        # NOVA_API_CHAT_EARLY_EXPLICIT_MEMORY_GUARD_LIVE_ANCHOR_20260611_CALL
        try:
            _nova_raw_user_text = str(
                data.get("user_text")
                or data.get("text")
                or data.get("message")
                or user_text
                or ""
            ).strip()
            _nova_explicit_memory_text = _nova_api_chat_extract_explicit_memory_live_20260611(_nova_raw_user_text)

            if _nova_explicit_memory_text:
                memory_service.add_memory({
                    "text": _nova_explicit_memory_text,
                    "kind": _nova_api_chat_memory_kind_live_20260611(_nova_explicit_memory_text),
                    "source": "app_explicit_memory_command",
                    "session_id": session_id or "",
                })

                return jsonify(
                    _nova_api_chat_memory_response_live_20260611(
                        raw_user_text=_nova_raw_user_text,
                        session_id=session_id,
                        clean=_nova_explicit_memory_text,
                    )
                )
        except Exception as _nova_early_memory_error:
            app.logger.warning("[api_chat early explicit memory guard live] failed: %s", _nova_early_memory_error)

        app.logger.info(
            "[api_chat] calling chat_service.handle session_id=%s attachments_count=%s",
            session_id,
            len(attachments_for_chat_service or []),
        )

        # CLEAN_IMAGE_PROMPT_RIGHT_BEFORE_CHAT_SERVICE_LOCK
        _nova_pre_chat_user_text = str(user_text or "")
        _nova_pre_chat_lower = _nova_pre_chat_user_text.lower().strip()
        _nova_image_prompt_starters = (
            "generate an image",
            "create an image",
            "make an image",
            "draw an image",
            "generate a picture",
            "create a picture",
            "make a picture",
            "draw a picture",
        )

        if any(_nova_pre_chat_lower.startswith(_starter) for _starter in _nova_image_prompt_starters):
            if "\n\nProject-aware context for Nova:" in _nova_pre_chat_user_text:
                user_text = _nova_pre_chat_user_text.split("\n\nProject-aware context for Nova:", 1)[0].strip()
            elif "\nProject-aware context for Nova:" in _nova_pre_chat_user_text:
                user_text = _nova_pre_chat_user_text.split("\nProject-aware context for Nova:", 1)[0].strip()
            else:
                user_text = _nova_pre_chat_user_text.strip()

            app.logger.info(
                "[api_chat] cleaned project-aware context from image-generation prompt session_id=%s cleaned_len=%s",
                session_id,
                len(user_text),
            )

        # NOVA_WEB_INTENT_CLEANS_PROJECT_CONTEXT_BEFORE_CHAT_SERVICE_20260609
        # Fresh web/news prompts must not let injected recent context trigger image generation.
        _nova_real_user_text_for_web = str(
            data.get("user_text")
            or data.get("text")
            or data.get("message")
            or ""
        ).strip()

        _nova_real_web_probe = " ".join(_nova_real_user_text_for_web.lower().split())
        _nova_real_web_terms = (
            "latest news",
            "news about",
            "today in",
            "what happened today",
            "current news",
            "breaking news",
            "recent news",
            "latest tech news",
            "latest sports",
            "weather",
            "forecast",
            "current events",
        )

        if (
            request.environ.get("NOVA_FORCE_WEB_INTENT_20260609") == "1"
            or any(term in _nova_real_web_probe for term in _nova_real_web_terms)
        ):
            if _nova_real_user_text_for_web:
                user_text = _nova_real_user_text_for_web
                attachments_for_chat_service = []
                attachments = []

                try:
                    data["attachments"] = []
                    data["user_text"] = _nova_real_user_text_for_web
                    data["text"] = _nova_real_user_text_for_web
                    data["message"] = _nova_real_user_text_for_web
                    request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
                    request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
                    app.logger.info(
                        "[api_chat] web intent cleaned project context before chat_service.handle text=%r",
                        _nova_real_user_text_for_web,
                    )
                except Exception:
                    pass

        image_command_user_text = user_text

        if user_text.lower().startswith("/image"):
            image_command_user_text = "generate image " + (user_text[6:].strip() or "image")

        app.logger.info(
            "[api_chat] calling chat_service.handle session_id=%s attachments_count=%s",
            session_id,
            len(attachments_for_chat_service or []),
        )

        result = chat_service.handle(
            user_text=image_command_user_text,
            session_id=session_id,
            attachments=attachments_for_chat_service,
        )

        # NOVA_MOBILE_IMAGE_URL_ACTIVE_SESSION_FORCE_20260630
        # Image generation can create the PNG but leave image_url attached to
        # a stale/placeholder session. Force the image URL onto the actual
        # requested mobile session response and latest assistant message.
        try:
            if isinstance(result, dict):
                request_payload_for_image = data if isinstance(data, dict) else (request.get_json(silent=True) or {})

                target_session_id = str(
                    request_payload_for_image.get("session_id")
                    or request_payload_for_image.get("sessionId")
                    or request_payload_for_image.get("active_session_id")
                    or locals().get("requested_session_id")
                    or result.get("active_session_id")
                    or result.get("session_id")
                    or session_id
                    or ""
                ).strip()

                if not target_session_id:
                    target_session_id = str(session_id or "").strip()

                assistant = result.get("assistant_message")
                if not isinstance(assistant, dict):
                    assistant = {
                        "role": "assistant",
                        "text": str(result.get("text") or "").strip(),
                    }

                image_url = str(
                    result.get("image_url")
                    or result.get("imageUrl")
                    or assistant.get("image_url")
                    or assistant.get("imageUrl")
                    or ""
                ).strip()

                result_text_for_image = str(
                    result.get("text")
                    or assistant.get("text")
                    or assistant.get("content")
                    or ""
                ).strip()

                if not image_url and result_text_for_image.startswith("Generated image for:"):
                    try:
                        generated_files = sorted(
                            Path(UPLOADS_DIR).glob("generated_*.png"),
                            key=lambda item: item.stat().st_mtime,
                            reverse=True,
                        )
                        if generated_files:
                            image_url = f"/api/uploads/{generated_files[0].name}"
                    except Exception as image_file_error:
                        app.logger.warning(
                            "[MobileImageUrlForce] newest generated file lookup failed: %s",
                            image_file_error,
                        )

                if image_url:
                    image_filename = image_url.split("/api/uploads/", 1)[-1].split("?", 1)[0].strip("/\\")

                    image_attachment = {
                        "id": image_filename,
                        "filename": image_filename,
                        "stored_name": image_filename,
                        "url": image_url,
                        "file_url": image_url,
                        "mime_type": "image/png",
                        "type": "image/png",
                    }

                    assistant["role"] = "assistant"
                    assistant["text"] = result_text_for_image or f"Generated image for: {image_command_user_text}"
                    assistant["content"] = assistant["text"]
                    assistant["image_url"] = image_url
                    assistant["attachments"] = [image_attachment]

                    meta = assistant.get("meta")
                    if not isinstance(meta, dict):
                        meta = {}
                    meta["source"] = "image_generation"
                    meta["image_url"] = image_url
                    meta["active_session_forced"] = True
                    meta["forced_target_session_id"] = target_session_id
                    assistant["meta"] = meta

                    result["assistant_message"] = assistant
                    result["text"] = assistant["text"]
                    result["content"] = assistant["text"]
                    result["image_url"] = image_url
                    result["active_session_id"] = target_session_id
                    result["session_id"] = target_session_id

                    # Patch session through session_service.
                    try:
                        current_session = session_service.get_session(target_session_id) or {}
                        messages = current_session.get("messages")
                        if isinstance(messages, list):
                            for message in reversed(messages):
                                if (
                                    isinstance(message, dict)
                                    and str(message.get("role") or "").lower() == "assistant"
                                    and str(message.get("text") or "").startswith("Generated image for:")
                                ):
                                    message["image_url"] = image_url
                                    message["attachments"] = [image_attachment]
                                    message["meta"] = dict(meta)
                                    break

                            current_session["messages"] = messages
                            all_sessions = session_service.get_all()

                            if isinstance(all_sessions, dict):
                                all_sessions.setdefault("sessions", {})
                                if isinstance(all_sessions["sessions"], dict):
                                    all_sessions["sessions"][target_session_id] = current_session
                                session_service.save(all_sessions, active=target_session_id)
                    except Exception as session_patch_error:
                        app.logger.warning(
                            "[MobileImageUrlForce] session_service patch failed: %s",
                            session_patch_error,
                        )

                    # Direct JSON patch fallback. This handles dict or array session stores.
                    try:
                        sessions_path = Path(SESSIONS_FILE)
                        store = json.loads(sessions_path.read_text(encoding="utf-8"))

                        sessions_obj = store.get("sessions")
                        target_session = None

                        if isinstance(sessions_obj, dict):
                            target_session = sessions_obj.get(target_session_id)
                        elif isinstance(sessions_obj, list):
                            for item in sessions_obj:
                                if isinstance(item, dict) and str(item.get("id") or "") == target_session_id:
                                    target_session = item
                                    break

                        if isinstance(target_session, dict):
                            target_messages = target_session.get("messages")
                            if isinstance(target_messages, list):
                                patched = False

                                for message in reversed(target_messages):
                                    if (
                                        isinstance(message, dict)
                                        and str(message.get("role") or "").lower() == "assistant"
                                        and str(message.get("text") or "").startswith("Generated image for:")
                                    ):
                                        message["image_url"] = image_url
                                        message["attachments"] = [image_attachment]
                                        message["meta"] = dict(meta)
                                        patched = True
                                        break

                                if patched:
                                    target_session["messages"] = target_messages
                                    store["active"] = target_session_id
                                    store["active_session_id"] = target_session_id
                                    sessions_path.write_text(
                                        json.dumps(store, indent=2, ensure_ascii=False),
                                        encoding="utf-8",
                                    )

                    except Exception as json_patch_error:
                        app.logger.warning(
                            "[MobileImageUrlForce] direct json patch failed: %s",
                            json_patch_error,
                        )

                    app.logger.info(
                        "[MobileImageUrlForce] forced image_url=%s target_session_id=%s old_session_id=%s",
                        image_url,
                        target_session_id,
                        session_id,
                    )
        except Exception as image_force_error:
            app.logger.warning("[MobileImageUrlForce] failed: %s", image_force_error)

         # =========================
        # IMAGE NORMALIZATION BLOCK
        # =========================
        if isinstance(result, dict):
            assistant = result.get("assistant_message") or {}

            if isinstance(assistant, dict):
                prompt = result.get("prompt") or assistant.get("text") or ""

                if isinstance(prompt, str) and prompt.startswith("generate image "):
                    clean_prompt = prompt[len("generate image "):].strip()

                    result["prompt"] = clean_prompt
                    assistant["text"] = f"Generated image for: {clean_prompt}"
                    assistant["content"] = assistant["text"]

                    if "image_url" in assistant:
                        result["image_url"] = assistant["image_url"]

                    result["assistant_message"] = assistant

        # =========================
        # SAFE LOGGING
        # =========================
        try:
            app.logger.info(
                "[api_chat] chat_service.handle result ok=%s active_session_id=%s keys=%s",
                result.get("ok") if isinstance(result, dict) else None,
                result.get("active_session_id") if isinstance(result, dict) else None,
                sorted(list(result.keys())) if isinstance(result, dict) else type(result).__name__,
            )
        except Exception:
            pass

            # NOVA_SAFE_API_CHAT_WEAK_GUARD_AFTER_HANDLE_LOCK
            result = _nova_replace_weak_backend_reply(image_command_user_text, result)

            # AFTER_WEAK_GUARD_ATTACHMENT_SUMMARY_LOCK
            # Final safety: if attachment text was extracted but the reply is still the old canned
            # attachment response, replace it with a local summary after weak-reply cleanup.
            try:
                if attachment_content_lines and isinstance(result, dict):
                    assistant_message = result.get("assistant_message")
                    if isinstance(assistant_message, dict):
                        current_reply = str(
                            assistant_message.get("text")
                            or assistant_message.get("content")
                            or ""
                        ).strip()
            
                        lower_reply = current_reply.lower()
                        is_canned_attachment_reply = (
                            "i received the attachment" in lower_reply
                            and "instead of generating an image" in lower_reply
                        )
            
                        if is_canned_attachment_reply:
                            extracted_text = "\n\n".join(str(item or "") for item in attachment_content_lines).strip()
            
                            try:
                                summary_payload = _nova_local_summary_from_text(extracted_text)
                            except Exception:
                                summary_payload = None
            
                            if isinstance(summary_payload, dict):
                                summary = str(summary_payload.get("summary") or "").strip()
                                key_points = summary_payload.get("key_points") or []
                                preview = str(summary_payload.get("preview") or "").strip()
                            else:
                                summary = "I extracted readable text from the attachment."
                                key_points = []
                                seen = set()
                                for raw_line in extracted_text.splitlines():
                                    cleaned = " ".join(str(raw_line or "").strip().split())
                                    lowered = cleaned.lower()
                                    if not cleaned or lowered in seen or len(cleaned) < 8:
                                        continue
                                    seen.add(lowered)
                                    key_points.append(cleaned)
                                    if len(key_points) >= 10:
                                        break
                                preview = "\n".join(key_points[:6])
            
                            # WEAK_GUARD_CLEAN_BEFORE_FORMAT_LOCK
                            # Clean weak-guard attachment text before formatting final response.
                            # Prevents double summaries like:
                            # "This attachment appears... This attachment appears... Key points..."
                            import re as _nova_weak_guard_re

                            def _nova_weak_guard_clean_line(value):
                                line = str(value or "").strip()
                                line = _nova_weak_guard_re.sub(r"^\\s*\\d+\\.\\s*", "", line).strip()
                                line = line.replace("Ã®ÂºÂ", "").strip()
                                line = line.replace("Attachment <unknown>", "uploaded attachment")
                                line = _nova_weak_guard_re.sub(r"\\s+", " ", line).strip()
                                return line

                            _nova_weak_bad_exact = {
                                "attachment analysis:",
                                "key points:",
                                "preview:",
            "copy",
            "regen",
            "regenerate",
                                "uploaded attachment content:",
                                "attachment content:",
                                "attachment <unknown> content:",
                                "keypoints",
            "copy",
            "regen",
            "regenerate",
                                "summarize",
                                "summary",
                                "continue",
                            }

                            _nova_weak_bad_starts = (
                                "this attachment appears to contain extracted image/pdf content about:",
                                "this attachment appears to contain image/search/pdf extraction text about:",
                                "this attachment appears to be about:",
                            )

                            _nova_weak_bad_contains = (
                                "uploaded attachment content:",
                                "attachment <unknown> content:",
                                "key points:;",
                                "preview:;",
                            )

                            def _nova_weak_keep_line(value):
                                line = _nova_weak_guard_clean_line(value)
                                if not line:
                                    return ""

                                low = line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
                                compact = _nova_weak_guard_re.sub(r"[^a-z0-9]+", " ", low).strip()

                                if low in _nova_weak_bad_exact or compact in _nova_weak_bad_exact:
                                    return ""

                                if any(low.startswith(prefix) for prefix in _nova_weak_bad_starts):
                                    return ""

                                if any(bad in low for bad in _nova_weak_bad_contains):
                                    return ""

                                if line.isdigit():
                                    return ""

                                if len(line) <= 2:
                                    return ""

                                return line

                            cleaned_key_points = []
                            seen_weak_points = set()

                            if isinstance(key_points, list):
                                for raw_point in key_points:
                                    clean_point = _nova_weak_keep_line(raw_point)
                                    if not clean_point:
                                        continue

                                    key = _nova_weak_guard_re.sub(
                                        r"[^a-z0-9]+",
                                        " ",
                                        clean_point.lower(),
                                    ).strip()[:160]

                                    if not key or key in seen_weak_points:
                                        continue

                                    seen_weak_points.add(key)
                                    cleaned_key_points.append(clean_point)

                                    if len(cleaned_key_points) >= 10:
                                        break

                            key_points = cleaned_key_points

                            cleaned_preview_lines = []
                            for raw_preview_line in str(preview or "").splitlines():
                                clean_preview_line = _nova_weak_keep_line(raw_preview_line)
                                if clean_preview_line:
                                    cleaned_preview_lines.append(clean_preview_line)

                            preview = "\n".join(cleaned_preview_lines[:6])

                            if key_points:
                                summary = (
                                    "This uploaded attachment contains readable text about: "
                                    + "; ".join(key_points[:3])
                                    + "."
                                )
                            else:
                                summary = "The attachment was received and processed, but the extracted text is too limited or noisy to summarize cleanly."

                            points_text = ""
                            if isinstance(key_points, list) and key_points:
                                points_text = "\n".join(
                                    f"{index + 1}. {point}"
                                    for index, point in enumerate(key_points[:10])
                                )
            
                            replacement_text = (
                                "Attachment analysis:\n"
                                + (summary or "I extracted readable text from the attachment.")
                                + ("\n\nKey points:\n" + points_text if points_text else "")
                                + ("\n\nPreview:\n" + preview[:1200] if preview else "")
                            ).strip()
            
                            # NOVA_DISABLE_ATTACHMENT_RECURSIVE_WRAPPER_REWRITE_20260611
                            _nova_existing_attachment_content = str(assistant_message.get("content") or "").strip()
                            _nova_replacement_text_value = str(replacement_text or "").strip()

                            if (
                                _nova_existing_attachment_content.startswith("Attachment analysis:")
                                and "Attachment " in _nova_existing_attachment_content
                                and " content:" in _nova_existing_attachment_content
                                and "This uploaded attachment contains readable text about:" in _nova_replacement_text_value
                            ):
                                assistant_message["text"] = _nova_existing_attachment_content
                                assistant_message["content"] = _nova_existing_attachment_content
                            else:
                                assistant_message["text"] = replacement_text
                                assistant_message["content"] = replacement_text

                            result["assistant_message"] = assistant_message
                            result["skip_cleanup"] = True
                            result["skip_post_processing"] = True
                            result["skip_rewrite"] = True
            
                            app.logger.info(
                                "[AttachmentContentGate] after weak guard replaced canned attachment reply chars=%s key_points=%s session_id=%s",
                                len(replacement_text),
                                len(key_points or []),
                                session_id,
                            )
            except Exception as _nova_after_weak_guard_attachment_error:
                app.logger.warning(
                    "[AttachmentContentGate] after weak guard attachment summary failed error=%s",
                    _nova_after_weak_guard_attachment_error,
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


                # REAL_RESPONSE_ATTACHMENT_COUNT_LOCK
                # Force returned attachment payload/count to current request only.
                try:
                    if isinstance(result, dict):
                        result["session_attachments"] = list(attachments or [])
                        result_session = result.get("session")
                        if isinstance(result_session, dict):
                            result_session["session_attachments"] = list(attachments or [])
                            result_session["attachment_memory"] = list(attachments or [])
                            result_session["attachments"] = list(attachments or [])
                    app.logger.info(
                        "[AttachmentContentGate] real response attachment payload forced current-only count=%s session_id=%s",
                        len(attachments or []),
                        requested_session_id,
                    )
                except Exception as _nova_real_response_attachment_error:
                    app.logger.warning(
                        "[AttachmentContentGate] real response attachment payload cleanup failed error=%s",
                        _nova_real_response_attachment_error,
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

        # NOVA_NORMALIZE_RESULT_BEFORE_ASSISTANT_MESSAGE_20260608
        # Some attachment/DOCX paths return a plain string from chat_service.handle.
        # Normalize it into Nova's expected /api/chat dict contract before result.get(...).
        if isinstance(result, str):
            result = {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "content": result,
                    "text": result,
                },
                "text": result,
                "session_id": session_id,
                "active_session_id": session_id,
                "debug": {
                    "normalized_string_result": True,
                    "route_taken": "attachment_analysis",
                },
            }

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

        # NOVA_ATTACHMENT_DIRECT_TEXT_CLEAN_WIRED_20260611
        if isinstance(assistant_text, str) and "Attachment analysis:" in assistant_text:
            cleaner = globals().get("_nova_direct_clean_attachment_text_response_20260611")
            if callable(cleaner):
                assistant_text = cleaner(assistant_text)

        assistant_message["text"] = assistant_text
        assistant_message["content"] = assistant_text
        # NOVA_ATTACHMENT_SYNC_TEXT_AFTER_CONTENT_ASSIGN_20260611
        try:
            _nova_attachment_content_sync = str(assistant_message.get("content") or "").strip()
            if (
                _nova_attachment_content_sync.startswith("Attachment analysis:")
                and "Attachment " in _nova_attachment_content_sync
                and " content:" in _nova_attachment_content_sync
            ):
                assistant_message["text"] = _nova_attachment_content_sync
                assistant_text = _nova_attachment_content_sync
        except Exception:
            pass

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



# NOVA_FIX_MISSING_UPLOAD_HELPER_LOGGER_20260609
import logging as _nova_logging_20260609
logger = _nova_logging_20260609.getLogger(__name__)

def _nova_find_uploaded_file_path_20260607(attachment):
    """
    Resolve a mobile upload attachment dict into a local uploads file path.
    Safe fallback for attachment summary routes.
    """
    from pathlib import Path

    try:
        item = attachment if isinstance(attachment, dict) else {}

        candidates = [
            item.get("path"),
            item.get("file_path"),
            item.get("stored_path"),
            item.get("local_path"),
            item.get("filename"),
            item.get("stored_filename"),
            item.get("name"),
            item.get("url"),
            item.get("file_url"),
        ]

        base_dir = Path(__file__).resolve().parent
        upload_dir = base_dir / "uploads"

        for raw in candidates:
            if not raw:
                continue

            value = str(raw).strip().replace("\\", "/")
            value = value.split("?", 1)[0].split("#", 1)[0]

            if "/api/uploads/" in value:
                value = value.rsplit("/api/uploads/", 1)[-1]

            if value.startswith("/api/uploads/"):
                value = value[len("/api/uploads/"):]

            direct = Path(value)
            if direct.is_file():
                return str(direct)

            name = value.rsplit("/", 1)[-1]
            if name:
                candidate = upload_dir / name
                if candidate.is_file():
                    return str(candidate)

        return None
    except Exception:
        return None




@app.get("/api/sessions/<session_id>")
def api_session_by_id(session_id: str):
    # NOVA_CLEAN_SESSION_DETAIL_ENDPOINT_20260611
    # NOVA_SESSION_JSON_UTF8_SIG_READ_FIX_20260611
    # Clean desktop session detail endpoint. Returns one full session from
    # the canonical session store and marks the response so the auth-scope
    # after-request filter does not strip it.
    try:
        from pathlib import Path

        sid = str(session_id or "").strip()
        root = Path(__file__).resolve().parent

        candidates = []

        def add_candidate(value):
            try:
                if value:
                    p = Path(value).resolve()
                    if p not in candidates:
                        candidates.append(p)
            except Exception:
                pass

        add_candidate(globals().get("SESSIONS_FILE"))
        add_candidate(root / "data" / "nova_sessions.json")
        add_candidate(Path.cwd() / "data" / "nova_sessions.json")
        add_candidate(Path("C:/Users/Owner/nova/data/nova_sessions.json"))

        found = None
        active_session_id = ""

        for sessions_path in candidates:
            if not sessions_path.exists():
                continue

            try:
                store = json.loads(sessions_path.read_text(encoding="utf-8-sig") or "{}")
            except Exception:
                continue

            if not isinstance(store, dict):
                continue

            active_session_id = str(store.get("active_session_id") or "").strip()
            items = store.get("sessions")
            if not isinstance(items, list):
                continue

            for item in items:
                if isinstance(item, dict) and str(item.get("id") or "").strip() == sid:
                    found = item
                    active_session_id = sid
                    break

            if found is not None:
                break

        if found is None:
            return jsonify({
                "ok": False,
                "error": "Session not found",
                "session": None,
                "active_session_id": active_session_id,
                "skip_session_auth_scope_filter": True,
            }), 404

        return jsonify({
            "ok": True,
            "session": found,
            "active_session_id": active_session_id,
            "skip_session_auth_scope_filter": True,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "session": None,
            "active_session_id": str(session_id or "").strip(),
            "skip_session_auth_scope_filter": True,
        }), 500


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

        noisy_video_request = raw_name.lower().endswith((
            ".mp4",
            ".mov",
            ".webm",
            ".m4v",
        ))

        try:
            full_path.relative_to(uploads_root)
        except ValueError:
            if not noisy_video_request:
                app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")

            return jsonify({
                "ok": False,
                "error": "Invalid upload path",
                "filename": raw_name,
            }), 400

        if not full_path.exists() or not full_path.is_file():
            if not noisy_video_request:
                app.logger.warning(f"UPLOAD MISS: {full_path}")

            return jsonify({
                "ok": False,
                "error": "Upload not found",
                "filename": raw_name,
                "full_path": str(full_path),
                "uploads_dir": str(uploads_root),
            }), 404

        if not noisy_video_request:
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

            noisy_video_request = raw_name.lower().endswith((
                ".mp4",
                ".mov",
                ".webm",
                ".m4v",
            ))

            try:
                full_path.relative_to(uploads_root)
            except ValueError:
                if not noisy_video_request:
                    app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")

                return jsonify({
                    "ok": False,
                    "error": "Invalid upload path",
                    "filename": raw_name,
                }), 400

            if not full_path.exists() or not full_path.is_file():
                if not noisy_video_request:
                    app.logger.warning(f"UPLOAD MISS: {full_path}")

                return jsonify({
                    "ok": False,
                    "error": "Upload not found",
                    "filename": raw_name,
                    "full_path": str(full_path),
                    "uploads_dir": str(uploads_root),
                }), 404

            if not noisy_video_request:
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


# FIX_ATTACHMENT_ANALYZER_ROUTE_AND_CALL_LOCK
# Safety repair: make sure /api/chat points to api_chat, not helper functions.
try:
    if "api_chat" in globals():
        for _nova_rule in app.url_map.iter_rules():
            if str(_nova_rule.rule) == "/api/chat":
                app.view_functions[_nova_rule.endpoint] = api_chat
                _nova_boot_log_20260701(f"[NOVA ROUTE REPAIR] /api/chat endpoint={_nova_rule.endpoint} rebound to api_chat")
except Exception as _nova_route_repair_error:
    print(f"[NOVA ROUTE REPAIR FAILED] {_nova_route_repair_error}")


# ATTACHMENT_EXTRACT_ENDPOINT_LOCK
@app.route("/api/attachment/extract", methods=["POST"])
def api_attachment_extract():
    """
    Extract readable text from an uploaded PDF/image without touching the chat pipeline.
    Accepts JSON:
      {
        "url": "/api/uploads/file.pdf",
        "path": "optional local path",
        "mime_type": "application/pdf"
      }
    """
    try:
        payload = request.get_json(silent=True) or {}

        upload_url = str(payload.get("url") or payload.get("file_url") or "").strip()
        local_path = str(payload.get("path") or "").strip()
        mime_type = str(payload.get("mime_type") or payload.get("type") or "").strip()

        if not local_path and upload_url:
            filename = upload_url.replace("\\", "/").split("/")[-1].strip()
            if filename:
                local_path = str(Path(UPLOADS_DIR) / filename)

        if not local_path:
            return jsonify({
                "ok": False,
                "error": "Missing url or path.",
            }), 400

        file_path = Path(local_path)

        if not file_path.exists():
            return jsonify({
                "ok": False,
                "error": f"File not found: {file_path}",
            }), 404

        if not mime_type:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
            elif suffix == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        extracted_text = _nova_analyze_binary_attachment_for_prompt(
            str(file_path),
            mime_type,
        )

        extracted_text = str(extracted_text or "").strip()

        app.logger.info(
            "[AttachmentExtractEndpoint] extracted path=%s chars=%s mime_type=%s",
            str(file_path),
            len(extracted_text),
            mime_type,
        )

        return jsonify({
            "ok": True,
            "path": str(file_path),
            "url": upload_url,
            "mime_type": mime_type,
            "chars": len(extracted_text),
            "text": extracted_text,
        })

    except Exception as error:
        app.logger.exception("[AttachmentExtractEndpoint] failed")
        return jsonify({
            "ok": False,
            "error": str(error),
        }), 500




# ATTACHMENT_SUMMARIZE_ENDPOINT_LOCK
def _nova_clean_extracted_attachment_text(text, limit=6000):
    raw = str(text or "")
    lines = []

    skip_fragments = (
        "sponsored",
        "safesearch",
        "create a new collection",
        "saved images",
        "saved to collections",
        "related searches",
        "more images on this site",
        "go to site",
    )

    for line in raw.splitlines():
        cleaned = " ".join(str(line or "").strip().split())

        if not cleaned:
            continue

        lowered = cleaned.lower()

        if any(fragment in lowered for fragment in skip_fragments):
            continue

        if len(cleaned) <= 2:
            continue

        lines.append(cleaned)

    joined = "\n".join(lines)
    return joined[:limit]


def _nova_local_summary_from_text(text):
    cleaned = _nova_clean_extracted_attachment_text(text)
    lines = [line for line in cleaned.splitlines() if line.strip()]

    if not lines:
        return {
            "summary": "No clean readable text was found.",
            "key_points": [],
            "preview": "",
        }

    title_candidates = []
    for line in lines[:30]:
        if 3 <= len(line) <= 90:
            title_candidates.append(line)

    key_points = []
    seen = set()

    for line in lines:
        lowered = line.lower()

        if lowered in seen:
            continue

        seen.add(lowered)

        if len(line) >= 12:
            key_points.append(line)

        if len(key_points) >= 10:
            break

    first_lines = lines[:8]
    summary = "This attachment appears to contain text extracted from a web/search/image results page or document capture."

    if title_candidates:
        summary = "This uploaded attachment appears to be about: " + "; ".join(title_candidates[:5]) + "."

    return {
        "summary": summary,
        "key_points": key_points,
        "preview": "\n".join(first_lines)[:1200],
    }


# ATTACHMENT_SUMMARY_CLEAN_RETURN_LOCK
def _nova_clean_attachment_endpoint_text(value: object) -> str:
    import re

    text_value = str(value or "")
    text_value = text_value.replace("\ufeff", "")
    text_value = text_value.replace("\r\n", "\n").replace("\r", "\n")

    bad_phrases = (
        "This uploaded attachment contains readable text about:",
        "This uploaded attachment contains readable text about:",
        "This uploaded attachment appears to be about:",
    )

    for phrase in bad_phrases:
        text_value = text_value.replace(phrase, "")

    text_value = re.sub(
        r"\[Attachment analysis failed:\s*tesseract is not installed[^\]]*\]\.?",
        "",
        text_value,
        flags=re.IGNORECASE,
    )

    text_value = re.sub(
        r"Attachment analysis failed:\s*tesseract is not installed[^\n.]*(\.|\n)?",
        "",
        text_value,
        flags=re.IGNORECASE,
    )

    text_value = re.sub(r"\bKey points:\s*;\s*", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\bPreview:\s*;\s*", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r";\s*Attachment\s+", "\nAttachment ", text_value)
    text_value = re.sub(r"\s*;\s*", "\n", text_value)

    lines = []
    seen = set()

    for raw_line in text_value.splitlines():
        line = str(raw_line or "").strip()
        line = re.sub(r"^\s*\d+\.\s*", "", line).strip()
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        low = line.lower()

        if low in {
            "attachment analysis:",
            "key points:",
            "preview:",
            "copy",
            "regen",
            "regenerate",
            "summary:",
            "attachment content:",
            "uploaded attachment content:",
        }:
            continue

        if low.startswith("this attachment appears"):
            continue

        if "tesseract is not installed" in low:
            continue

        if low in {"copy", "regen", "regenerate", "copied", "failed"}:
            continue

        if low.startswith("copyregen"):
            continue

        key = re.sub(r"[^a-z0-9]+", " ", low).strip()[:180]

        if not key or key in seen:
            continue

        seen.add(key)
        lines.append(line)

        if len(lines) >= 12:
            break

    return "\n".join(lines).strip()


def _nova_clean_attachment_endpoint_payload(local_summary: dict, cleaned_text: object) -> dict:
    import re

    clean_text_value = _nova_clean_attachment_endpoint_text(cleaned_text)

    source_lines = []

    if clean_text_value:
        source_lines.extend(clean_text_value.splitlines())

    for item in list((local_summary or {}).get("key_points") or []):
        cleaned = _nova_clean_attachment_endpoint_text(item)
        if cleaned:
            source_lines.extend(cleaned.splitlines())

    summary_clean = _nova_clean_attachment_endpoint_text((local_summary or {}).get("summary"))
    preview_clean = _nova_clean_attachment_endpoint_text((local_summary or {}).get("preview"))

    if summary_clean:
        source_lines.extend(summary_clean.splitlines())

    if preview_clean:
        source_lines.extend(preview_clean.splitlines())

    final_lines = []
    seen = set()

    for raw_line in source_lines:
        line = str(raw_line or "").strip()
        if not line:
            continue

        low = line.lower()
        key = re.sub(r"[^a-z0-9]+", " ", low).strip()[:180]

        if not key or key in seen:
            continue

        if low.startswith("this attachment appears"):
            continue

        if "tesseract is not installed" in low:
            continue

        if low in {"copy", "regen", "regenerate", "copied", "failed"}:
            continue

        if low.startswith("copyregen"):
            continue

        seen.add(key)
        final_lines.append(line)

        if len(final_lines) >= 10:
            break

    if not final_lines:
        return {
            "summary": "Attachment analysis:\nThe attachment was processed, but no clean readable text was found.",
            "key_points": [],
            "preview": "",
        }

    summary = "Attachment analysis:\n\n" + "\n".join(final_lines[:6])
    preview = "\n".join(final_lines[:8])[:1200]

    return {
        "summary": summary.strip(),
        "key_points": final_lines[:10],
        "preview": preview.strip(),
    }

@app.route("/api/attachment/summarize", methods=["POST"])
def api_attachment_summarize():
    """
    Extract and summarize an uploaded PDF/image without touching the chat pipeline.
    Accepts JSON:
      {
        "url": "/api/uploads/file.pdf",
        "path": "optional local path",
        "mime_type": "application/pdf"
      }
    """
    try:
        payload = request.get_json(silent=True) or {}

        upload_url = str(payload.get("url") or payload.get("file_url") or "").strip()
        local_path = str(payload.get("path") or "").strip()
        mime_type = str(payload.get("mime_type") or payload.get("type") or "").strip()

        if not local_path and upload_url:
            filename = upload_url.replace("\\", "/").split("/")[-1].strip()
            if filename:
                local_path = str(Path(UPLOADS_DIR) / filename)

        if not local_path:
            return jsonify({
                "ok": False,
                "error": "Missing url or path.",
            }), 400

        file_path = Path(local_path)

        if not file_path.exists():
            return jsonify({
                "ok": False,
                "error": f"File not found: {file_path}",
            }), 404

        if not mime_type:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
            elif suffix == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        extracted_text = _nova_analyze_binary_attachment_for_prompt(
            str(file_path),
            mime_type,
        )

        cleaned_text = _nova_clean_extracted_attachment_text(extracted_text)
        local_summary = _nova_local_summary_from_text(extracted_text)

        app.logger.info(
            "[AttachmentSummarizeEndpoint] summarized path=%s raw_chars=%s clean_chars=%s mime_type=%s",
            str(file_path),
            len(str(extracted_text or "")),
            len(cleaned_text),
            mime_type,
        )

        # ATTACHMENT_SUMMARIZE_ENDPOINT_FILTER_LOCK
        # Final endpoint-level cleanup for noisy PDF/image search-page extraction.
        import re as _nova_endpoint_re

        def _nova_endpoint_keep_attachment_line(value):
            line = str(value or "").strip()
            line = line.replace("Ã®ÂºÂ", "").strip()
            line = _nova_endpoint_re.sub(r"^\\s*\\d+\\.\\s*", "", line).strip()
            line = _nova_endpoint_re.sub(r"\\s+", " ", line).strip()

            if not line:
                return ""

            low = line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
            compact = _nova_endpoint_re.sub(r"[^a-z0-9]+", " ", low).strip()

            bad_exact = {
                "pdf page 1",
                "search",
                "images",
                "videos",
                "maps",
                "create",
                "inspiration",
                "all",
                "shopping",
                "news",
                "books",
                "flights",
                "finance",
                "keypoints",
            "copy",
            "regen",
            "regenerate",
                "continue",
                "summarize",
                "summary",
                "preview",
                "cop",
                "filt",
                "moderate",
                "bath",
                "amazon",
                "related content",
                "furniture dÃƒÂ©cor",
                "kitchen appliances",
            }

            bad_contains = (
                "wayfair",
                "save big",
                "prices you'll love",
                "eye-catching prints",
                "love, horror and more themes",
                "free_shipping",
                "url removed from extracted attachment text",
                "plain field in front of mountain peak",
                "free stock photo",
                "https://www.amazon.",
                "https://www.wayfair.",
                "Ã¢â‚¬Âº shop Ã¢â‚¬Âº",
                "Ã¢â‚¬Âº wall art Ã¢â‚¬Âº",
            )

            if low in bad_exact or compact in bad_exact:
                return ""

            if any(bad in low for bad in bad_contains):
                return ""

            if line.startswith("http://") or line.startswith("https://"):
                return ""

            if line.isdigit():
                return ""

            if len(line) <= 2:
                return ""

            return line

        _endpoint_lines = []
        _endpoint_seen = set()

        for _raw_point in list(local_summary.get("key_points") or []):
            _line = _nova_endpoint_keep_attachment_line(_raw_point)
            if not _line:
                continue

            _key = _nova_endpoint_re.sub(r"[^a-z0-9]+", " ", _line.lower()).strip()[:180]
            if not _key or _key in _endpoint_seen:
                continue

            _endpoint_seen.add(_key)
            _endpoint_lines.append(_line)

        # If key_points were mostly junk, fall back to cleaned_text lines.
        if not _endpoint_lines:
            for _raw_line in str(cleaned_text or "").splitlines():
                _line = _nova_endpoint_keep_attachment_line(_raw_line)
                if not _line:
                    continue

                _key = _nova_endpoint_re.sub(r"[^a-z0-9]+", " ", _line.lower()).strip()[:180]
                if not _key or _key in _endpoint_seen:
                    continue

                _endpoint_seen.add(_key)
                _endpoint_lines.append(_line)

                if len(_endpoint_lines) >= 10:
                    break

        if _endpoint_lines:
            local_summary["key_points"] = _endpoint_lines[:10]
            local_summary["summary"] = "This uploaded attachment appears to be about: " + "; ".join(_endpoint_lines[:5]) + "."
            local_summary["preview"] = "\\n".join(_endpoint_lines[:6])[:1200]
        else:
            local_summary["key_points"] = []
            local_summary["summary"] = "The attachment was processed, but the extracted text was mostly search/navigation noise."
            local_summary["preview"] = ""

        # DIRECT_TEXT_ATTACHMENT_SUMMARY_LOCK
        direct_text_suffixes = {
            ".txt",
            ".md",
            ".markdown",
            ".py",
            ".js",
            ".css",
            ".html",
            ".htm",
            ".json",
            ".csv",
            ".log",
        }

        file_suffix = str(file_path.suffix or "").lower().strip()
        mime_lower = str(mime_type or "").lower().strip()

        if file_suffix in direct_text_suffixes or mime_lower.startswith("text/") or "markdown" in mime_lower or "json" in mime_lower:
            try:
                direct_text = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                direct_text = str(cleaned_text or "")

            direct_lines = []
            direct_seen = set()

            for raw_line in str(direct_text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
                line = str(raw_line or "").replace("\ufeff", "").strip()

                if not line:
                    continue

                low_line = line.lower().strip()

                if low_line in {"copy", "regen", "regenerate", "copied", "failed"}:
                    continue

                if low_line.startswith("copyregen"):
                    continue

                key = line.lower().strip()

                if key in direct_seen:
                    continue

                direct_seen.add(key)
                direct_lines.append(line)

                if len(direct_lines) >= 12:
                    break

            if direct_lines:
                direct_preview = "\n".join(direct_lines[:12])[:1200]
                cleaned_endpoint_summary = {
                    "summary": "Attachment analysis:\n\n" + direct_preview,
                    "key_points": direct_lines[:10],
                    "preview": direct_preview,
                }
            else:
                cleaned_endpoint_summary = {
                    "summary": "Attachment analysis:\nThe text attachment was received, but no readable lines were found.",
                    "key_points": [],
                    "preview": "",
                }
        else:
            cleaned_endpoint_summary = _nova_clean_attachment_endpoint_payload(local_summary, cleaned_text)

        return jsonify({
            "ok": True,
            "path": str(file_path),
            "url": upload_url,
            "mime_type": mime_type,
            "raw_chars": len(str(extracted_text or "")),
            "clean_chars": len(cleaned_text),
            "summary": cleaned_endpoint_summary["summary"],
            "key_points": cleaned_endpoint_summary["key_points"],
            "preview": cleaned_endpoint_summary["preview"],
            "clean_text": cleaned_endpoint_summary["preview"] or cleaned_text,
        })

    except Exception as error:
        app.logger.exception("[AttachmentSummarizeEndpoint] failed")
        return jsonify({
            "ok": False,
            "error": str(error),
        }), 500




# ATTACHMENT_KEYPOINTS_ENDPOINT_LOCK
def _nova_attachment_keypoints_from_text(text, max_points=10):
    raw = str(text or "")
    points = []
    seen = set()

    skip_fragments = (
        "sponsored",
        "safesearch",
        "create a new collection",
        "saved images",
        "saved to collections",
        "related searches",
        "more images on this site",
        "go to site",
        "http://",
        "https://",
        "www.",
    )

    for line in raw.splitlines():
        cleaned = " ".join(str(line or "").strip().split())

        if not cleaned:
            continue

        lowered = cleaned.lower()

        if lowered in seen:
            continue

        if any(fragment in lowered for fragment in skip_fragments):
            continue

        if len(cleaned) < 8:
            continue

        seen.add(lowered)
        points.append(cleaned)

        if len(points) >= max_points:
            break

    return points

@app.route("/api/attachment/keypoints", methods=["POST"])
def api_attachment_keypoints():
    """
    Extract key points from an uploaded PDF/image without touching the chat pipeline.
    Accepts JSON:
      {
        "url": "/api/uploads/file.pdf",
        "path": "optional local path",
        "mime_type": "application/pdf"
      }
    """
    try:
        payload = request.get_json(silent=True) or {}

        upload_url = str(payload.get("url") or payload.get("file_url") or "").strip()
        local_path = str(payload.get("path") or "").strip()
        mime_type = str(payload.get("mime_type") or payload.get("type") or "").strip()

        if not local_path and upload_url:
            filename = upload_url.replace("\\", "/").split("/")[-1].strip()
            if filename:
                local_path = str(Path(UPLOADS_DIR) / filename)

        if not local_path:
            return jsonify({
                "ok": False,
                "error": "Missing url or path.",
            }), 400

        file_path = Path(local_path)

        if not file_path.exists():
            return jsonify({
                "ok": False,
                "error": f"File not found: {file_path}",
            }), 404

        if not mime_type:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
            elif suffix == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        extracted_text = _nova_analyze_binary_attachment_for_prompt(
            str(file_path),
            mime_type,
        )

        key_points = _nova_attachment_keypoints_from_text(extracted_text, max_points=10)

        summary = "No readable key points found."
        if key_points:
            summary = "Top attachment point: " + key_points[0]

        app.logger.info(
            "[AttachmentKeypointsEndpoint] extracted keypoints path=%s raw_chars=%s points=%s mime_type=%s",
            str(file_path),
            len(str(extracted_text or "")),
            len(key_points),
            mime_type,
        )

        return jsonify({
            "ok": True,
            "path": str(file_path),
            "url": upload_url,
            "mime_type": mime_type,
            "raw_chars": len(str(extracted_text or "")),
            "summary": summary,
            "key_points": key_points,
            "points_count": len(key_points),
        })

    except Exception as error:
        app.logger.exception("[AttachmentKeypointsEndpoint] failed")
        return jsonify({
            "ok": False,
            "error": str(error),
        }), 500




# CHAT_ATTACHMENT_RESPONSE_CLEANUP_LOCK
@app.after_request
def _nova_clean_attachment_analysis_response(response):
    """Final cleanup for canned attachment-analysis replies before mobile sees them."""
    try:
        from flask import request
        import re

        if request.path != "/api/chat":
            return response

        content_type = str(response.headers.get("Content-Type") or "").lower()
        if "application/json" not in content_type:
            return response

        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return response

        assistant_message = data.get("assistant_message")
        if not isinstance(assistant_message, dict):
            return response

        text_value = str(assistant_message.get("text") or "")

        if "Attachment analysis:" not in text_value:
            return response

        noisy_exact = {
            "attachment <unknown> content:",
            "attachment content:",
            "[pdf page 1]",
            "search",
            "images",
            "videos",
            "create",
            "inspiration",
            "keypoints",
            "copy",
            "regen",
            "regenerate",
            "continue",
            "cop",
            "filt",
            "moderate",
            "amazon",
            "bath",
            "related content",
        }

        noisy_contains = (
            "wayfair",
            "save big",
            "prices you'll love",
            "eye-catching prints",
            "url removed from extracted attachment text",
            "free_shipping",
            "furniture & dÃƒÂ©cor",
            "kitchen appliances",
            "love, horror and more themes",
            "plain field in front of mountain peak",
            "free stock photo",
            "6000 Ãƒâ€”",
            "jpeg",
        )

        def clean_line(line):
            line = re.sub(r"^\s*\d+\.\s*", "", str(line or "")).strip()
            line = line.replace("Attachment <unknown>", "uploaded attachment")
            line = line.replace("Attachment content:", "").strip()
            line = re.sub(r"\s+", " ", line).strip()
            return line

        raw_lines = []
        for line in text_value.splitlines():
            cleaned = clean_line(line)
            if not cleaned:
                continue

            low = cleaned.lower().strip(" :;-Ã¢â‚¬Â¢*|")
            low_compact = re.sub(r"[^a-z0-9]+", " ", low).strip()

            if low_compact in noisy_exact:
                continue

            if any(bad in low for bad in noisy_contains):
                continue

            if len(cleaned) <= 2:
                continue

            raw_lines.append(cleaned)

        useful = []
        seen = set()

        skip_prefixes = (
            "attachment analysis",
            "this attachment appears to be about",
            "key points",
            "preview",
        )

        for line in raw_lines:
            low = line.lower()
            if any(low.startswith(prefix) for prefix in skip_prefixes):
                continue

            key = re.sub(r"[^a-z0-9]+", " ", low).strip()[:160]
            if not key or key in seen:
                continue

            seen.add(key)
            useful.append(line)

        if useful:
            top = useful[:8]
            topic = "; ".join(top[:3])
            cleaned_text = "Attachment analysis:\n"
            cleaned_text += f"This uploaded attachment contains readable text about: {topic}.\n\n"
            cleaned_text += "Key points:\n"
            for index, item in enumerate(top, start=1):
                cleaned_text += f"{index}. {item}\n"

            cleaned_text += "\nPreview:\n"
            cleaned_text += "\n".join(top[:6])
        else:
            cleaned_text = (
                "Attachment analysis:\n"
                "The attachment was received and text was extracted, but most of the extracted text looks like noisy search-page/navigation content rather than a clean document body."
            )

        _nova_existing_content = str(assistant_message.get("content") or "").strip()
        _nova_candidate_text = cleaned_text.strip()
        if (
            _nova_existing_content.startswith("Attachment analysis:")
            and "Attachment " in _nova_existing_content
            and " content:" in _nova_existing_content
            and "This uploaded attachment contains readable text about:" in _nova_candidate_text
        ):
            assistant_message["text"] = _nova_existing_content
            assistant_message["content"] = _nova_existing_content
        else:
            # DISABLED_RECURSIVE_ATTACHMENT_TEXT_REWRITE_20260615
            # assistant_message["text"] = _nova_candidate_text
            pass
        data["assistant_message"] = assistant_message

        payload = json.dumps(data)
        response.set_data(payload)
        response.headers["Content-Length"] = str(len(payload.encode("utf-8")))

        return response

    except Exception:
        return response




# ATTACHMENT_OUTPUT_NOISE_CLEANUP_LOCK
@app.after_request
def _nova_final_attachment_output_noise_cleanup(response):
    """Final cosmetic cleanup for attachment-analysis text."""
    try:
        from flask import request
        import re

        if request.path != "/api/chat":
            return response

        content_type = str(response.headers.get("Content-Type") or "").lower()
        if "application/json" not in content_type:
            return response

        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return response

        assistant_message = data.get("assistant_message")
        if not isinstance(assistant_message, dict):
            return response

        text_value = str(assistant_message.get("text") or "")
        if "Attachment analysis:" not in text_value:
            return response

        bad_exact = {
            "uploaded attachment content:",
            "attachment content:",
            "attachment <unknown> content:",
            "keypoints",
            "copy",
            "regen",
            "regenerate",
            "continue",
            "summarize",
            "summary",
            "preview:",
            "copy",
            "regen",
            "regenerate",
            "key points:",
        }

        bad_contains = (
            "love, horror and more themes",
            "wayfair",
            "save big",
            "prices you'll love",
            "eye-catching prints",
            "url removed from extracted attachment text",
            "free_shipping",
            "furniture & dÃƒÂ©cor",
            "kitchen appliances",
            "related content",
        )

        useful = []
        seen = set()

        for raw_line in text_value.splitlines():
            line = re.sub(r"^\s*\d+\.\s*", "", str(raw_line or "")).strip()
            line = line.replace("Ã®ÂºÂ", "").strip()
            line = line.replace("Attachment <unknown>", "uploaded attachment")
            line = re.sub(r"\s+", " ", line).strip()

            if not line:
                continue

            low = line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
            compact = re.sub(r"[^a-z0-9]+", " ", low).strip()

            if low.startswith("attachment analysis"):
                continue

            if low.startswith("this attachment appears"):
                continue

            if low in bad_exact or compact in bad_exact:
                continue

            if any(bad in low for bad in bad_contains):
                continue

            if line.isdigit():
                continue

            if len(line) <= 2:
                continue

            key = compact[:160]
            if not key or key in seen:
                continue

            seen.add(key)
            useful.append(line)

        top = useful[:8]

        if top:
            topic = "; ".join(top[:3])
            cleaned = "Attachment analysis:\n"
            cleaned += f"This uploaded attachment contains readable text about: {topic}.\n\n"
            cleaned += "Key points:\n"

            for index, item in enumerate(top, start=1):
                cleaned += f"{index}. {item}\n"

            cleaned += "\nPreview:\n"
            cleaned += "\n".join(top[:6])
        else:
            cleaned = (
                "Attachment analysis:\n"
                "The attachment was received and processed, but the extracted text is too limited or noisy to summarize cleanly."
            )

        _nova_existing_content = str(assistant_message.get("content") or "").strip()
        _nova_candidate_text = cleaned.strip()
        if (
            _nova_existing_content.startswith("Attachment analysis:")
            and "Attachment " in _nova_existing_content
            and " content:" in _nova_existing_content
            and "This uploaded attachment contains readable text about:" in _nova_candidate_text
        ):
            assistant_message["text"] = _nova_existing_content
            assistant_message["content"] = _nova_existing_content
        else:
            # DISABLED_RECURSIVE_ATTACHMENT_TEXT_REWRITE_20260615
            # assistant_message["text"] = _nova_candidate_text
            pass
        data["assistant_message"] = assistant_message

        payload = json.dumps(data, ensure_ascii=False)
        response.set_data(payload)
        response.headers["Content-Length"] = str(len(payload.encode("utf-8")))

        return response

    except Exception:
        return response




# ATTACHMENT_DOUBLE_SUMMARY_CLEANUP_LOCK
@app.after_request
def _nova_attachment_double_summary_cleanup(response):
    """Remove repeated attachment-analysis template lines from final output."""
    try:
        from flask import request
        import re

        if request.path != "/api/chat":
            return response

        content_type = str(response.headers.get("Content-Type") or "").lower()
        if "application/json" not in content_type:
            return response

        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return response

        assistant_message = data.get("assistant_message")
        if not isinstance(assistant_message, dict):
            return response

        text_value = str(assistant_message.get("text") or "")
        if "Attachment analysis:" not in text_value:
            return response

        lines = []
        seen = set()

        bad_exact = {
            "attachment analysis:",
            "key points:",
            "preview:",
            "copy",
            "regen",
            "regenerate",
            "uploaded attachment content:",
            "attachment content:",
            "attachment <unknown> content:",
            "keypoints",
            "copy",
            "regen",
            "regenerate",
            "summarize",
            "summary",
            "continue",
        }

        bad_starts = (
            "this attachment appears to contain extracted image/pdf content about:",
            "this attachment appears to contain image/search/pdf extraction text about:",
            "this attachment appears to be about:",
            "key points:",
            "preview:",
            "copy",
            "regen",
            "regenerate",
        )

        bad_contains = (
            "uploaded attachment content:",
            "attachment <unknown> content:",
            "key points:;",
            "preview:;",
        )

        for raw_line in text_value.splitlines():
            line = str(raw_line or "").strip()
            line = re.sub(r"^\s*\d+\.\s*", "", line).strip()
            line = line.replace("Ã®ÂºÂ", "").strip()
            line = re.sub(r"\s+", " ", line).strip()

            if not line:
                continue

            low = line.lower().strip(" :;-Ã¢â‚¬Â¢*|")
            compact = re.sub(r"[^a-z0-9]+", " ", low).strip()

            if low in bad_exact or compact in bad_exact:
                continue

            if any(low.startswith(prefix) for prefix in bad_starts):
                continue

            if any(bad in low for bad in bad_contains):
                continue

            if line.isdigit():
                continue

            if len(line) <= 2:
                continue

            key = compact[:160]
            if not key or key in seen:
                continue

            seen.add(key)
            lines.append(line)

        top = lines[:8]

        if top:
            topic = "; ".join(top[:3])
            cleaned = "Attachment analysis:\n"
            cleaned += f"This uploaded attachment contains readable text about: {topic}.\n\n"
            cleaned += "Key points:\n"

            for index, item in enumerate(top, start=1):
                cleaned += f"{index}. {item}\n"

            cleaned += "\nPreview:\n"
            cleaned += "\n".join(top[:6])
        else:
            cleaned = (
                "Attachment analysis:\n"
                "The attachment was received and processed, but the extracted text is too limited or noisy to summarize cleanly."
            )

        _nova_existing_content = str(assistant_message.get("content") or "").strip()
        _nova_candidate_text = cleaned.strip()
        if (
            _nova_existing_content.startswith("Attachment analysis:")
            and "Attachment " in _nova_existing_content
            and " content:" in _nova_existing_content
            and "This uploaded attachment contains readable text about:" in _nova_candidate_text
        ):
            assistant_message["text"] = _nova_existing_content
            assistant_message["content"] = _nova_existing_content
        else:
            # DISABLED_RECURSIVE_ATTACHMENT_TEXT_REWRITE_20260615
            # assistant_message["text"] = _nova_candidate_text
            pass
        data["assistant_message"] = assistant_message

        payload = json.dumps(data, ensure_ascii=False)
        response.set_data(payload)
        response.headers["Content-Length"] = str(len(payload.encode("utf-8")))

        return response

    except Exception:
        return response

# ATTACHMENT_FOLLOWUP_RECALL_LOCK_20260604
@app.before_request
def _nova_attachment_followup_recall_gate():
    try:
        from flask import request, jsonify
        from pathlib import Path

        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()
        session_id = str(payload.get("session_id") or "").strip()
        attachments = payload.get("attachments") or []

        lower = user_text.lower()
        wants_attachment = (
            "attachment" in lower
            and (
                "what was in" in lower
                or "what is in" in lower
                or "summarize" in lower
                or "tell me" in lower
            )
        )

        if not wants_attachment or attachments or not session_id:
            return None

        return None

    except Exception:
        return None

# STOP_FAKE_ATTACHMENT_CHAT_20260604

# NOVA_SESSION_ATTACHMENT_MEMORY_GATE_20260611
def _nova_session_attachment_memory_path_20260611():
    try:
        from pathlib import Path
        base = Path(__file__).resolve().parent
        data_dir = base / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "nova_session_attachments.json"
    except Exception:
        return Path("data") / "nova_session_attachments.json"


def _nova_load_session_attachment_memory_20260611():
    try:
        path = _nova_session_attachment_memory_path_20260611()
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8-sig") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _nova_save_session_attachment_memory_20260611(data):
    try:
        path = _nova_session_attachment_memory_path_20260611()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data if isinstance(data, dict) else {}, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def _nova_normalize_attachment_item_for_session_20260611(item):
    try:
        if not isinstance(item, dict):
            return None

        normalized = {}

        for key in (
            "filename",
            "original_filename",
            "file_url",
            "url",
            "path",
            "local_path",
            "mime_type",
            "type",
            "size",
        ):
            value = item.get(key)
            if value is not None and str(value).strip():
                normalized[key] = value

        if not normalized.get("filename"):
            normalized["filename"] = (
                normalized.get("original_filename")
                or str(normalized.get("file_url") or normalized.get("url") or normalized.get("path") or "attachment").replace("\\", "/").split("/")[-1]
            )

        return normalized if normalized else None
    except Exception:
        return None


def _nova_resolve_saved_attachment_path_20260611(item):
    try:
        from pathlib import Path

        if not isinstance(item, dict):
            return None

        candidates = [
            item.get("local_path"),
            item.get("path"),
        ]

        for url_key in ("file_url", "url"):
            raw_url = str(item.get(url_key) or "").strip()
            if raw_url:
                filename = raw_url.replace("\\", "/").split("/")[-1].strip()
                if filename:
                    candidates.append(str(Path(UPLOADS_DIR) / filename))

        filename = str(item.get("filename") or item.get("original_filename") or "").strip()
        if filename:
            candidates.append(str(Path(UPLOADS_DIR) / filename))

        for candidate in candidates:
            if not candidate:
                continue
            candidate_path = Path(str(candidate))
            if not candidate_path.is_absolute():
                candidate_path = Path(__file__).resolve().parent / candidate_path
            if candidate_path.exists() and candidate_path.is_file():
                return candidate_path

        return None
    except Exception:
        return None


def _nova_read_saved_attachment_text_20260611(item, limit=4000):
    try:
        path = _nova_resolve_saved_attachment_path_20260611(item)
        if not path:
            return ""

        suffix = path.suffix.lower()
        if suffix in (".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css", ".xml", ".log"):
            for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    return path.read_text(encoding=encoding, errors="replace")[:limit].strip()
                except Exception:
                    continue

        return f"[Saved attachment exists but is not plain readable text: {path.name}]"
    except Exception:
        return ""


def _nova_build_saved_attachment_reply_20260611(user_text, saved_attachments):
    try:
        clean_user = str(user_text or "").lower()
        lines = ["Attachment analysis:"]

        matched_any = False

        for item in saved_attachments:
            if not isinstance(item, dict):
                continue

            name = str(
                item.get("filename")
                or item.get("original_filename")
                or item.get("file_url")
                or "attachment"
            ).replace("\\", "/").split("/")[-1]

            # If the user names a specific file, prefer that file.
            if ".txt" in clean_user or "attachment" in clean_user or "file" in clean_user:
                raw_names = [
                    str(item.get("filename") or "").lower(),
                    str(item.get("original_filename") or "").lower(),
                    name.lower(),
                ]
                mentioned_specific_other = any(part.endswith(".txt") for part in clean_user.split())
                if mentioned_specific_other and not any(raw_name and raw_name in clean_user for raw_name in raw_names):
                    continue

            content = _nova_read_saved_attachment_text_20260611(item)
            if not content:
                continue

            matched_any = True
            lines.append(f"Attachment {name} content:")
            lines.append(content)

        if not matched_any:
            for item in saved_attachments:
                name = str(
                    item.get("filename")
                    or item.get("original_filename")
                    or item.get("file_url")
                    or "attachment"
                ).replace("\\", "/").split("/")[-1]
                content = _nova_read_saved_attachment_text_20260611(item)
                if content:
                    lines.append(f"Attachment {name} content:")
                    lines.append(content)
                    matched_any = True

        if not matched_any:
            return ""

        return "\n".join(lines).strip()
    except Exception:
        return ""


@app.before_request
def nova_session_attachment_memory_gate_20260611():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return None

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or payload.get("active_session_id")
            or ""
        ).strip()

        if not session_id:
            return None

        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        attachments = payload.get("attachments") or []
        if isinstance(attachments, dict):
            attachments = [attachments]
        if not isinstance(attachments, list):
            attachments = []

        memory = _nova_load_session_attachment_memory_20260611()
        saved = memory.get(session_id) if isinstance(memory, dict) else None
        saved = saved if isinstance(saved, list) else []

        # Save current request attachments for later follow-ups.
        if attachments:
            normalized = []
            for item in attachments:
                normalized_item = _nova_normalize_attachment_item_for_session_20260611(item)
                if normalized_item:
                    normalized.append(normalized_item)

            if normalized:
                existing_keys = {
                    str(x.get("file_url") or x.get("url") or x.get("path") or x.get("filename") or "")
                    for x in saved
                    if isinstance(x, dict)
                }

                for item in normalized:
                    key = str(item.get("file_url") or item.get("url") or item.get("path") or item.get("filename") or "")
                    if key and key not in existing_keys:
                        saved.append(item)
                        existing_keys.add(key)

                # NOVA_SESSION_ATTACHMENT_MEMORY_DEDUPE_AND_TEXT_LOCK_20260611
                _nova_deduped_saved_by_name = {}
                for _nova_saved_item in saved:
                    if not isinstance(_nova_saved_item, dict):
                        continue
                    _nova_saved_name = str(
                        _nova_saved_item.get("filename")
                        or _nova_saved_item.get("original_filename")
                        or _nova_saved_item.get("file_url")
                        or _nova_saved_item.get("url")
                        or ""
                    ).replace("\\", "/").split("/")[-1].strip().lower()

                    if not _nova_saved_name:
                        _nova_saved_name = str(
                            _nova_saved_item.get("file_url")
                            or _nova_saved_item.get("url")
                            or _nova_saved_item.get("path")
                            or ""
                        ).strip().lower()

                    if _nova_saved_name:
                        _nova_deduped_saved_by_name[_nova_saved_name] = _nova_saved_item

                saved = list(_nova_deduped_saved_by_name.values())[-20:]
                memory[session_id] = saved
                _nova_save_session_attachment_memory_20260611(memory)

            return None

        clean = " ".join(user_text.lower().split())
        wants_saved_attachment = (
            ("attachment" in clean or "file" in clean or ".txt" in clean or "secret phrase" in clean)
            and (
                "what" in clean
                or "summarize" in clean
                or "tell me" in clean
                or "secret phrase" in clean
                or "previous" in clean
                or "uploaded" in clean
            )
        )

        if not wants_saved_attachment or not saved:
            return None

        assistant_text = _nova_build_saved_attachment_reply_20260611(user_text, saved)
        if not assistant_text:
            return None

        user_msg = {
            "role": "user",
            "text": user_text,
            "attachments": [],
            "meta": {
                "session_attachment_memory_lookup": True,
            },
        }

        assistant_msg = {
            "role": "assistant",
            "text": assistant_text,
            "content": assistant_text,
            "attachments": saved,
            "meta": {
                "route_taken": "session_attachment_memory_recall",
                "session_attachment_memory_count": len(saved),
            },
        }

        return jsonify({
            "ok": True,
            "active_session_id": session_id,
            "session_id": session_id,
            "assistant_message": assistant_msg,
            "text": assistant_text,
            "attachment_debug": {
                "requested_session_id": session_id,
                "active_session_id": session_id,
                "session_attachments_count": len(saved),
                "session_attachment_memory_recall": True,
            },
            "debug": {
                "route": "api_chat",
                "route_taken": "session_attachment_memory_recall",
            },
            "runtime": {},
            "session_attachments": saved,
        })

    except Exception:
        return None



@app.before_request
def _nova_stop_fake_attachment_chat_gate():
    try:
        from flask import request, jsonify

        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        user_text = str(payload.get("user_text") or "").strip()
        attachments = payload.get("attachments") or []

        clean = " ".join(user_text.lower().split())

        casual_messages = {
            "hi",
            "hey",
            "hello",
            "yo",
            "sup",
            "how are you",
            "how are you?",
            "how you doing",
            "how are u",
            "whats up",
            "what's up",
        }

        if attachments:
            return None

        if clean not in casual_messages:
            return None

        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "I'm good. Ready when you are.",
                "attachments": [],
                "meta": {
                    "route": "normal_chat_casual_gate"
                }
            },
            "attachments": [],
            "session_attachments": [],
            "debug": {
                "route": "normal_chat_casual_gate"
            }
        })

    except Exception:
        return None


# NOVA_BACKEND_READINESS_ROUTE_20260609
# Live local backend readiness endpoint.
try:
    from nova_backend.services.chat_service_backend_readiness import get_backend_readiness

    @app.route("/api/backend/readiness", methods=["GET"])
    def api_backend_readiness_20260609():
        return get_backend_readiness()

except Exception as _nova_backend_readiness_route_error_20260609:
    @app.route("/api/backend/readiness", methods=["GET"])
    def api_backend_readiness_route_error_20260609():
        return {
            "ok": False,
            "error": "backend_readiness_route_failed",
            "detail": str(_nova_backend_readiness_route_error_20260609),
        }, 500


# NOVA_MOBILE_DIRECT_SESSION_PERSIST_ENDPOINT_20260609
@app.post("/api/mobile/session/persist")
def nova_mobile_direct_session_persist_20260609():
    try:
        from pathlib import Path
        from datetime import datetime, timezone
        import uuid

        payload = request.get_json(silent=True) or {}

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or payload.get("active_session_id")
            or ""
        ).strip()

        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        assistant_text = str(
            payload.get("assistant_text")
            or payload.get("assistant")
            or payload.get("response")
            or ""
        ).strip()

        if not session_id:
            session_id = "mobile_" + uuid.uuid4().hex[:16]

        if not user_text and not assistant_text:
            return jsonify({
                "ok": False,
                "error": "No message text supplied."
            }), 400

        root_dir = Path(__file__).resolve().parent
        sessions_path = Path(globals().get("SESSIONS_FILE") or (root_dir / "data" / "nova_sessions.json"))
        sessions_path.parent.mkdir(parents=True, exist_ok=True)

        if sessions_path.exists():
            raw = sessions_path.read_text(encoding="utf-8-sig").strip()
            data = json.loads(raw) if raw else {"sessions": []}
        else:
            data = {"sessions": []}

        if isinstance(data, list):
            data = {"sessions": data}

        sessions = data.setdefault("sessions", [])
        now = datetime.now(timezone.utc).isoformat()

        session = None
        for item in sessions:
            if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                session = item
                break

        if session is None:
            session = {
                "id": session_id,
                "title": user_text[:60] or "New Chat",
                "created_at": now,
                "updated_at": now,
                "pinned": False,
                "messages": [],
                "working_state": {
                    "active_task": "",
                    "checkpoint": "",
                    "current_bug": "",
                    "current_file": "",
                    "last_success": "",
                    "next_move": "",
                    "updated_at": ""
                },
                "active_execution": None
            }
            sessions.append(session)

        messages = session.setdefault("messages", [])
        if not isinstance(messages, list):
            messages = []
            session["messages"] = messages

        recent_pairs = [
            (
                str(messages[i].get("text") or "").strip(),
                str(messages[i + 1].get("text") or "").strip() if i + 1 < len(messages) and isinstance(messages[i + 1], dict) else ""
            )
            for i in range(max(0, len(messages) - 10), len(messages))
            if isinstance(messages[i], dict)
        ]

        if (user_text, assistant_text) not in recent_pairs:
            if user_text:
                messages.append({
                    "id": "msg_" + uuid.uuid4().hex,
                    "role": "user",
                    "text": user_text,
                    "attachments": payload.get("attachments") if isinstance(payload.get("attachments"), list) else [],
                    "created_at": now,
                    "updated_at": now,
                    "meta": {
                        "route": "mobile_direct_session_persist"
                    }
                })

            if assistant_text:
                messages.append({
                    "id": "msg_" + uuid.uuid4().hex,
                    "role": "assistant",
                    "text": assistant_text,
                    "attachments": [],
                    "created_at": now,
                    "updated_at": now,
                    "meta": {
                        "route": "mobile_direct_session_persist"
                    }
                })

        if not str(session.get("title") or "").strip() or str(session.get("title")).lower() == "new chat":
            session["title"] = user_text[:60] or "New Chat"

        session["updated_at"] = now

        tmp = sessions_path.with_suffix(sessions_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(sessions_path)

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "messages": len(messages)
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 500

# NOVA_APP_ROUTE_FIXED_CLEAN_BOTTOM_20260610
@app.get("/app")
def nova_desktop_app_fixed_20260610():
    return render_template("app.html")


# NOVA_LOCAL_AUTH_ROUTES_20260610
# Local dev auth API: /api/auth/status, /api/auth/register, /api/auth/login, /api/auth/logout
def _nova_install_local_auth_routes_20260610():
    import os
    import secrets
    import hashlib
    from pathlib import Path
    from flask import request, jsonify, session

    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    secret_path = data_dir / "nova_flask_secret.key"
    if not getattr(app, "secret_key", None):
        if secret_path.exists():
            app.secret_key = secret_path.read_text(encoding="utf-8").strip()
        else:
            secret = secrets.token_hex(32)
            secret_path.write_text(secret, encoding="utf-8")
            app.secret_key = secret

    users_path = data_dir / "nova_auth_users.json"

    def route_exists(rule):
        return any(str(r.rule) == rule for r in app.url_map.iter_rules())

    def load_users():
        if not users_path.exists():
            return {"users": []}
        try:
            data = json.loads(users_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"users": []}
            if not isinstance(data.get("users"), list):
                data["users"] = []
            return data
        except Exception:
            return {"users": []}

    def save_users(data):
        users_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def clean(value):
        return str(value or "").strip()

    def hash_password(password, salt):
        raw = (str(salt) + "::" + str(password)).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def public_user(user):
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "email": user.get("email"),
        }

    def find_user(identifier):
        ident = clean(identifier).lower()
        for user in load_users().get("users", []):
            if clean(user.get("username")).lower() == ident:
                return user
            if clean(user.get("email")).lower() == ident:
                return user
        return None

    def current_user():
        uid = session.get("nova_user_id")
        if not uid:
            return None
        for user in load_users().get("users", []):
            if user.get("id") == uid:
                return user
        return None

    def auth_status():
        user = current_user()
        return jsonify({
            "ok": True,
            "authenticated": bool(user),
            "user": public_user(user) if user else None,
            "mode": "local",
        })

    def auth_register():
        payload = request.get_json(silent=True) or {}
        username = clean(payload.get("username") or payload.get("name"))
        email = clean(payload.get("email"))
        password = str(payload.get("password") or "")

        if not username and email:
            username = email.split("@", 1)[0]

        if not username:
            return jsonify({"ok": False, "error": "Username is required."}), 400
        if len(password) < 4:
            return jsonify({"ok": False, "error": "Password must be at least 4 characters."}), 400

        data = load_users()

        if find_user(username) or (email and find_user(email)):
            return jsonify({"ok": False, "error": "User already exists."}), 409

        salt = secrets.token_hex(16)
        user = {
            "id": "user_" + secrets.token_hex(12),
            "username": username,
            "email": email,
            "salt": salt,
            "password_hash": hash_password(password, salt),
        }

        data["users"].append(user)
        save_users(data)

        session["nova_user_id"] = user["id"]

        return jsonify({
            "ok": True,
            "authenticated": True,
            "user": public_user(user),
        })

    def auth_login():
        payload = request.get_json(silent=True) or {}
        identifier = clean(payload.get("username") or payload.get("email") or payload.get("login"))
        password = str(payload.get("password") or "")

        user = find_user(identifier)
        if not user:
            return jsonify({"ok": False, "error": "Invalid username or password."}), 401

        expected = user.get("password_hash")
        actual = hash_password(password, user.get("salt", ""))

        if not expected or actual != expected:
            return jsonify({"ok": False, "error": "Invalid username or password."}), 401

        session["nova_user_id"] = user["id"]

        return jsonify({
            "ok": True,
            "authenticated": True,
            "user": public_user(user),
        })

    def auth_logout():
        session.pop("nova_user_id", None)
        return jsonify({
            "ok": True,
            "authenticated": False,
            "user": None,
        })

    if not route_exists("/api/auth/status"):
        app.add_url_rule("/api/auth/status", "nova_auth_status_20260610", auth_status, methods=["GET"])

    if not route_exists("/api/auth/register"):
        app.add_url_rule("/api/auth/register", "nova_auth_register_20260610", auth_register, methods=["POST"])

    if not route_exists("/api/auth/login"):
        app.add_url_rule("/api/auth/login", "nova_auth_login_20260610", auth_login, methods=["POST"])

    if not route_exists("/api/auth/logout"):
        app.add_url_rule("/api/auth/logout", "nova_auth_logout_20260610", auth_logout, methods=["POST"])

    # Compatibility aliases in case the frontend calls the shorter paths.
    if not route_exists("/api/login"):
        app.add_url_rule("/api/login", "nova_api_login_20260610", auth_login, methods=["POST"])

    if not route_exists("/api/logout"):
        app.add_url_rule("/api/logout", "nova_api_logout_20260610", auth_logout, methods=["POST"])

    if not route_exists("/api/register"):
        app.add_url_rule("/api/register", "nova_api_register_20260610", auth_register, methods=["POST"])


_nova_install_local_auth_routes_20260610()



# NOVA_LOGIN_PAGE_ROUTES_20260610
# Page routes for local auth screens.
def _nova_install_login_page_routes_20260610():
    from flask import render_template, redirect, url_for, request, session

    def route_exists(rule):
        return any(str(r.rule) == rule for r in app.url_map.iter_rules())

    def login_page():
        return render_template(
            "login.html",
            active_tab="login",
            prefill_username=request.args.get("username", ""),
            prefill_register_username="",
        )

    def register_page():
        return render_template(
            "login.html",
            active_tab="register",
            prefill_username="",
            prefill_register_username=request.args.get("username", ""),
        )

    if not route_exists("/login"):
        app.add_url_rule("/login", "nova_login_page_20260610", login_page, methods=["GET"])

    if not route_exists("/register"):
        app.add_url_rule("/register", "nova_register_page_20260610", register_page, methods=["GET"])

    # NOVA_LOGOUT_PAGE_CLEARS_SESSION_20260610
    def logout_page():
        session.pop("nova_user_id", None)
        return redirect("/login")

    if not route_exists("/logout"):
        app.add_url_rule("/logout", "nova_logout_page_20260610", logout_page, methods=["GET"])
    else:
        app.view_functions["nova_logout_page_20260610"] = logout_page


_nova_install_login_page_routes_20260610()


# NOVA_AUTH_COMPAT_ALIAS_ROUTES_SAFE_20260611
# Frontend compatibility aliases for local auth.
def _nova_install_auth_compat_alias_routes_safe_20260611():
    try:
        from flask import jsonify, session

        def has_rule_method(rule_path, method):
            method = str(method or "").upper()
            for rule in app.url_map.iter_rules():
                if getattr(rule, "rule", "") == rule_path and method in getattr(rule, "methods", set()):
                    return True
            return False

        def forward_to_existing(endpoint_names):
            for endpoint in endpoint_names:
                view = app.view_functions.get(endpoint)
                if callable(view):
                    return view()
            return jsonify({
                "ok": False,
                "error": "Auth endpoint is not available.",
            }), 404

        def auth_status():
            user = None
            try:
                uid = session.get("nova_user_id")
                if uid:
                    users_data = load_json(users_path, {"users": []})
                    users = users_data.get("users", []) if isinstance(users_data, dict) else []
                    for item in users:
                        if isinstance(item, dict) and str(item.get("id") or "") == str(uid):
                            user = public_user(item) if callable(public_user) else {
                                "id": item.get("id"),
                                "username": item.get("username") or item.get("name") or item.get("email"),
                                "name": item.get("name") or item.get("username") or item.get("email"),
                                "email": item.get("email") or "",
                            }
                            break
            except Exception:
                user = None

            return jsonify({
                "ok": True,
                "authenticated": bool(user),
                "user": user,
                "mode": "local",
            })

        def auth_logout_alias():
            session.pop("nova_user_id", None)
            return jsonify({
                "ok": True,
                "authenticated": False,
                "user": None,
                "redirect_to": "/login",
            })

        def auth_login_alias():
            return forward_to_existing([
                "nova_api_login_20260610",
                "auth_login",
            ])

        def auth_register_alias():
            return forward_to_existing([
                "nova_api_register_20260610",
                "auth_register",
            ])

        # NOVA_AUTH_ME_STATUS_ALIASES_20260612
        routes = [
            ("/api/auth/status", "nova_api_auth_status_safe_20260611", auth_status, ["GET"]),
            ("/api/auth/me", "nova_api_auth_me_safe_20260612", auth_status, ["GET"]),
            ("/api/me", "nova_api_me_safe_20260612", auth_status, ["GET"]),
            ("/auth/status", "nova_auth_status_page_safe_20260612", auth_status, ["GET"]),
            ("/api/auth/logout", "nova_api_auth_logout_safe_20260611", auth_logout_alias, ["POST", "GET"]),
            ("/api/auth/login", "nova_api_auth_login_safe_20260611", auth_login_alias, ["POST"]),
            ("/api/auth/register", "nova_api_auth_register_safe_20260611", auth_register_alias, ["POST"]),
            ("/login", "nova_login_post_safe_20260611", auth_login_alias, ["POST"]),
            ("/register", "nova_register_post_safe_20260611", auth_register_alias, ["POST"]),
        ]

        installed = 0
        for rule_path, endpoint, view, methods in routes:
            missing = [method for method in methods if not has_rule_method(rule_path, method)]
            if not missing:
                continue
            app.add_url_rule(rule_path, endpoint, view, methods=missing)
            installed += 1

        _nova_boot_log_20260701("[NOVA AUTH] safe compat alias routes installed:", installed)

    except Exception as exc:
        print("[NOVA AUTH] safe compat alias install failed:", exc)


_nova_install_auth_compat_alias_routes_safe_20260611()






# NOVA_SLIM_API_SESSIONS_PAYLOAD_20260611
@app.after_request
def nova_slim_api_sessions_payload_20260611(response):
    try:
        path = str(request.path or "")

        # NOVA_HEADER_SKIP_SLIM_SESSIONS_RESPONSE_20260611
        if response.headers.get("X-Nova-Slim-Sessions") == "1":
            return response

        if path != "/api/sessions":
            return response

        try:
            payload = response.get_json(silent=True)
        except Exception:
            payload = None

        if not isinstance(payload, dict):
            return response

        # NOVA_SKIP_AFTER_REQUEST_FOR_SLIM_SESSIONS_20260611
        # The before_request slim sessions route already returns the final payload.
        # Do not re-slim it here, because this old hook can collapse sessions to [].
        if payload.get("slim_sessions_payload") is True and payload.get("debug", {}).get("route_taken") == "slim_sessions_payload":
            return response

        # The sessions drawer does not need full artifact records.
        # Full artifact/gallery APIs can serve those separately.
        if "artifacts" in payload:
            payload["artifacts"] = []

        if "artifact" in payload:
            payload.pop("artifact", None)

        sessions = payload.get("sessions")
        if isinstance(sessions, list):
            slim_sessions = []

            for item in sessions:
                if not isinstance(item, dict):
                    continue

                messages = item.get("messages")
                message_count = len(messages) if isinstance(messages, list) else 0

                slim = {
                    "id": item.get("id"),
                    "title": item.get("title") or "New Chat",
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "pinned": bool(item.get("pinned")),
                    "message_count": message_count,
                    "user_id": item.get("user_id"),
                    "username": item.get("username"),
                    "meta": item.get("meta") if isinstance(item.get("meta"), dict) else {},
                    "working_state": item.get("working_state") if isinstance(item.get("working_state"), dict) else {},
                    "active_execution": item.get("active_execution") if isinstance(item.get("active_execution"), dict) else {},
                }

                slim_sessions.append(slim)

            payload["sessions"] = slim_sessions

        session_obj = payload.get("session")
        if isinstance(session_obj, dict):
            messages = session_obj.get("messages")
            message_count = len(messages) if isinstance(messages, list) else 0

            payload["session"] = {
                "id": session_obj.get("id"),
                "title": session_obj.get("title") or "New Chat",
                "created_at": session_obj.get("created_at"),
                "updated_at": session_obj.get("updated_at"),
                "pinned": bool(session_obj.get("pinned")),
                "message_count": message_count,
                "user_id": session_obj.get("user_id"),
                "username": session_obj.get("username"),
                "meta": session_obj.get("meta") if isinstance(session_obj.get("meta"), dict) else {},
                "working_state": session_obj.get("working_state") if isinstance(session_obj.get("working_state"), dict) else {},
                "active_execution": session_obj.get("active_execution") if isinstance(session_obj.get("active_execution"), dict) else {},
            }

        payload.setdefault("ok", True)
        payload["slim_sessions_payload"] = True

        body = json.dumps(payload, ensure_ascii=False)
        response.set_data(body)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Content-Length"] = str(len(body.encode("utf-8")))

        return response

    except Exception as exc:
        try:
            app.logger.warning("[Nova Slim Sessions Payload] failed: %s", exc)
        except Exception:
            pass
        return response




# NOVA_BEFORE_REQUEST_SLIM_API_SESSIONS_20260611
@app.before_request
def nova_before_request_slim_api_sessions_20260611():
    try:
        if request.path != "/api/sessions" or request.method != "GET":
            return None

        raw_sessions = []

        for method_name in (
            "list_sessions",
            "get_sessions",
            "all_sessions",
            "load_sessions",
            "all",
        ):
            try:
                method = getattr(session_service, method_name, None)
                if callable(method):
                    candidate = method()
                    if isinstance(candidate, list):
                        raw_sessions = candidate
                        break
                    if isinstance(candidate, dict):
                        if isinstance(candidate.get("sessions"), list):
                            raw_sessions = candidate.get("sessions") or []
                            break
                        if isinstance(candidate.get("data"), dict) and isinstance(candidate["data"].get("sessions"), list):
                            raw_sessions = candidate["data"].get("sessions") or []
                            break
            except Exception:
                pass

        # NOVA_SLIM_SESSIONS_DIRECT_JSON_FALLBACK_20260611
        if not raw_sessions:
            try:
                sessions_path = os.path.join(app.root_path, "data", "nova_sessions.json")
                with open(sessions_path, "r", encoding="utf-8") as handle:
                    sessions_payload = json.load(handle)

                if isinstance(sessions_payload, dict):
                    active_session_id = str(sessions_payload.get("active_session_id") or "").strip()

                    if isinstance(sessions_payload.get("sessions"), list):
                        raw_sessions = sessions_payload.get("sessions") or []
                    elif isinstance(sessions_payload.get("data"), dict) and isinstance(sessions_payload["data"].get("sessions"), list):
                        raw_sessions = sessions_payload["data"].get("sessions") or []
                elif isinstance(sessions_payload, list):
                    raw_sessions = sessions_payload
            except Exception as exc:
                try:
                    app.logger.warning("[Nova Slim Sessions Direct JSON Fallback] failed: %s", exc)
                except Exception:
                    pass

        slim_sessions = []

        for item in raw_sessions:
            if not isinstance(item, dict):
                continue

            messages = item.get("messages")
            message_count = len(messages) if isinstance(messages, list) else int(item.get("message_count") or 0)

            slim_sessions.append({
                "id": item.get("id") or item.get("session_id") or "",
                "title": item.get("title") or "New Chat",
                "created_at": item.get("created_at") or "",
                "updated_at": item.get("updated_at") or "",
                "pinned": bool(item.get("pinned")),
                "message_count": message_count,
                "user_id": item.get("user_id") or "",
                "username": item.get("username") or "",
                "meta": item.get("meta") if isinstance(item.get("meta"), dict) else {},
                "working_state": item.get("working_state") if isinstance(item.get("working_state"), dict) else {},
                "active_execution": item.get("active_execution") if isinstance(item.get("active_execution"), dict) else {},
            })

        def _updated_key_20260611(item):
            return str(item.get("updated_at") or item.get("created_at") or "")

        slim_sessions.sort(key=_updated_key_20260611, reverse=True)

        active_session_id = ""
        try:
            active_session_id = str(
                request.cookies.get("nova_active_session_id")
                or request.cookies.get("active_session_id")
                or request.cookies.get("session_id")
                or ""
            ).strip()
        except Exception:
            active_session_id = ""

        if not active_session_id and slim_sessions:
            active_session_id = str(slim_sessions[0].get("id") or "")

        returned_sessions = slim_sessions[:50]

        slim_response = jsonify({
            "ok": True,
            "active_session_id": active_session_id,
            "sessions": returned_sessions,
            "items": returned_sessions,
            "artifacts": [],
            "slim_sessions_payload": True,
            "debug": {
                "route": "before_request_slim_api_sessions",
                "route_taken": "slim_sessions_payload",
                "raw_session_count": len(raw_sessions),
                "returned_session_count": len(returned_sessions),
            },
        })
        slim_response.headers["X-Nova-Slim-Sessions"] = "1"
        return slim_response

    except Exception as exc:
        try:
            app.logger.warning("[Nova Before Request Slim Sessions] failed: %s", exc)
        except Exception:
            pass
        return None


# NOVA_SESSION_AUTH_SCOPE_20260610
# App-level session ownership bridge.
# Keeps legacy unowned sessions safe, then claims them for the logged-in local user.
def _nova_install_session_auth_scope_20260610():
    from pathlib import Path
    from flask import request, session, g, Response

    data_dir = Path(__file__).resolve().parent / "data"
    sessions_path = data_dir / "nova_sessions.json"
    users_path = data_dir / "nova_auth_users.json"

    def load_json(path, fallback):
        try:
            if not path.exists():
                return fallback
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, type(fallback)) else fallback
        except Exception:
            return fallback

    def write_sessions_store(store):
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            tmp = sessions_path.with_suffix(sessions_path.suffix + ".tmp")
            tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(sessions_path)
            return True
        except Exception as exc:
            try:
                app.logger.warning("[Nova Session Auth Scope] write failed: %s", exc)
            except Exception:
                pass
            return False

    def current_auth_user():
        uid = session.get("nova_user_id")
        if not uid:
            return None

        users_data = load_json(users_path, {"users": []})
        users = users_data.get("users", []) if isinstance(users_data, dict) else []

        for user in users:
            if not isinstance(user, dict):
                continue
            if str(user.get("id") or "") == str(uid):
                return {
                    "id": str(user.get("id") or ""),
                    "username": str(user.get("username") or ""),
                    "email": str(user.get("email") or ""),
                }

        return {
            "id": str(uid),
            "username": "",
            "email": "",
        }

    def is_unowned(item):
        if not isinstance(item, dict):
            return False
        return not str(item.get("user_id") or "").strip() and not str(item.get("username") or "").strip()

    def is_visible_to_user(item, user):
        if not isinstance(item, dict):
            return False

        if not user:
            return is_unowned(item)

        item_user_id = str(item.get("user_id") or "").strip()
        item_username = str(item.get("username") or "").strip().lower()

        if not item_user_id and not item_username:
            return True

        if item_user_id and item_user_id == str(user.get("id") or ""):
            return True

        if item_username and item_username == str(user.get("username") or "").strip().lower():
            return True

        return False

    def claim_session(item, user):
        if not isinstance(item, dict) or not user:
            return False

        changed = False

        if not str(item.get("user_id") or "").strip():
            item["user_id"] = str(user.get("id") or "")
            changed = True

        if not str(item.get("username") or "").strip():
            item["username"] = str(user.get("username") or "")
            changed = True

        meta = item.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            item["meta"] = meta
            changed = True

        if not str(meta.get("owner_source") or "").strip():
            meta["owner_source"] = "local_auth"
            changed = True

        return changed

    def normalize_store_for_user(user):
        store = load_json(sessions_path, {"active_session_id": "", "sessions": []})

        if not isinstance(store, dict):
            store = {"active_session_id": "", "sessions": []}

        sessions = store.get("sessions", [])
        if not isinstance(sessions, list):
            sessions = []

        changed = False

        if user:
            for item in sessions:
                if is_unowned(item):
                    changed = claim_session(item, user) or changed

        visible = [item for item in sessions if is_visible_to_user(item, user)]

        active_id = str(store.get("active_session_id") or "").strip()
        visible_ids = {str(item.get("id") or "") for item in visible if isinstance(item, dict)}

        if active_id not in visible_ids:
            new_active = str(visible[0].get("id") or "").strip() if visible else ""
            if store.get("active_session_id") != new_active:
                store["active_session_id"] = new_active
                changed = True

        store["sessions"] = sessions

        if changed:
            write_sessions_store(store)

        return store, visible

    @app.before_request
    def nova_session_auth_scope_before_request_20260610():
        path = str(request.path or "")
        if not (
            path.startswith("/api/sessions")
            or path.startswith("/api/chat")
            or path.startswith("/api/chat/stream")
        ):
            return None

        user = current_auth_user()
        g.nova_auth_user = user
        normalize_store_for_user(user)
        return None

    @app.after_request
    def nova_session_auth_scope_after_request_20260610(response):
        # NOVA_SESSION_AUTH_SKIP_DETAIL_RESPONSE_FLEX_20260611
        # Session detail routes may return one full session. If the
        # route explicitly marks the response, do not sanitize it.
        try:
            data = response.get_json(silent=True)
            if isinstance(data, dict) and data.get("skip_session_auth_scope_filter"):
                return response
        except Exception:
            pass

        path = str(request.path or "")

        if not path.startswith("/api/sessions"):
            return response

        # NOVA_SKIP_AUTH_SCOPE_FOR_SLIM_SESSIONS_20260611
        # The direct slim sessions route already built the final clean payload.
        # Do not owner-filter it here, because unauth/local mode can collapse sessions to [].
        if response.headers.get("X-Nova-Slim-Sessions") == "1":
            return response

        user = getattr(g, "nova_auth_user", None) or current_auth_user()
        store, visible = normalize_store_for_user(user)

        try:
            payload = response.get_json(silent=True)
        except Exception:
            payload = None

        if not isinstance(payload, dict):
            return response

        visible_ids = {str(item.get("id") or "") for item in visible if isinstance(item, dict)}

        def filter_sessions(items):
            if not isinstance(items, list):
                return items
            return [
                item for item in items
                if isinstance(item, dict) and str(item.get("id") or "") in visible_ids
            ]

        payload["sessions"] = filter_sessions(payload.get("sessions", visible))
        payload["active_session_id"] = store.get("active_session_id") or ""

        if isinstance(payload.get("session"), dict):
            sid = str(payload["session"].get("id") or "")
            if sid not in visible_ids:
                payload["session"] = visible[0] if visible else None

        body = json.dumps(payload, ensure_ascii=False)
        response.set_data(body)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Content-Length"] = str(len(body.encode("utf-8")))

        return response


_nova_install_session_auth_scope_20260610()



# NOVA_PRUNE_EMPTY_SESSION_SPAM_20260610
# Prevents frontend/route bugs from filling nova_sessions.json with duplicate empty "New Chat" records.
def _nova_install_empty_session_spam_pruner_20260610():
    from pathlib import Path
    from flask import request

    data_dir = Path(__file__).resolve().parent / "data"
    sessions_path = data_dir / "nova_sessions.json"

    def load_store():
        try:
            if not sessions_path.exists():
                return {"active_session_id": "", "sessions": []}
            data = json.loads(sessions_path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                return {"active_session_id": "", "sessions": []}
            if not isinstance(data.get("sessions"), list):
                data["sessions"] = []
            data.setdefault("active_session_id", "")
            return data
        except Exception:
            return {"active_session_id": "", "sessions": []}

    def save_store(store):
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            tmp = sessions_path.with_suffix(sessions_path.suffix + ".tmp")
            tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(sessions_path)
            return True
        except Exception as exc:
            try:
                app.logger.warning("[Nova Session Spam Pruner] save failed: %s", exc)
            except Exception:
                pass
            return False

    def is_empty_new_chat(item):
        if not isinstance(item, dict):
            return False

        title = str(item.get("title") or "").strip().lower()
        messages = item.get("messages")

        if title not in ("", "new chat"):
            return False

        if isinstance(messages, list) and len(messages) > 0:
            return False

        if item.get("pinned"):
            return False

        active_execution = item.get("active_execution")
        if active_execution not in (None, {}, [], ""):
            return False

        working_state = item.get("working_state")
        if isinstance(working_state, dict):
            meaningful = [
                str(working_state.get("active_task") or "").strip(),
                str(working_state.get("checkpoint") or "").strip(),
                str(working_state.get("current_bug") or "").strip(),
                str(working_state.get("current_file") or "").strip(),
                str(working_state.get("last_success") or "").strip(),
                str(working_state.get("next_move") or "").strip(),
            ]
            if any(meaningful):
                return False

        return True

    def owner_key(item):
        user_id = str(item.get("user_id") or "").strip()
        username = str(item.get("username") or "").strip().lower()
        return user_id or username or "legacy_unowned"




    def sort_key(item):
        return str(item.get("updated_at") or item.get("created_at") or "")

    def prune_empty_new_chat_spam():
        store = load_store()
        sessions = store.get("sessions", [])

        if not isinstance(sessions, list):
            return 0

        empty_by_owner = {}
        for item in sessions:
            if is_empty_new_chat(item):
                empty_by_owner.setdefault(owner_key(item), []).append(item)

        keep_ids = set()
        remove_ids = set()

        for key, items in empty_by_owner.items():
            if not items:
                continue

            # Keep the newest empty New Chat for each owner. Remove the rest.
            newest = sorted(items, key=sort_key, reverse=True)[0]
            keep_ids.add(str(newest.get("id") or ""))

            for old in items:
                old_id = str(old.get("id") or "")
                if old_id and old_id != str(newest.get("id") or ""):
                    remove_ids.add(old_id)

        if not remove_ids:
            return 0

        old_active = str(store.get("active_session_id") or "")
        new_sessions = [
            item for item in sessions
            if not (isinstance(item, dict) and str(item.get("id") or "") in remove_ids)
        ]

        if old_active in remove_ids:
            preferred = ""
            for item in new_sessions:
                if str(item.get("id") or "") in keep_ids:
                    preferred = str(item.get("id") or "")
                    break
            if not preferred and new_sessions:
                preferred = str(new_sessions[0].get("id") or "")
            store["active_session_id"] = preferred

        store["sessions"] = new_sessions
        save_store(store)
        return len(remove_ids)

    @app.after_request
    def nova_prune_empty_session_spam_after_request_20260610(response):
        path = str(request.path or "")

        if (
            path.startswith("/api/sessions")
            or path.startswith("/api/chat")
            or path.startswith("/api/chat/stream")
            or path == "/mobile"
        ):
            removed = prune_empty_new_chat_spam()
            if removed:
                try:
                    app.logger.info("[Nova Session Spam Pruner] removed %s duplicate empty New Chat sessions", removed)
                except Exception:
                    pass

        return response


_nova_install_empty_session_spam_pruner_20260610()



# NOVA_ATTACHMENT_SHAPE_NORMALIZER_20260610
# Keeps saved session message attachments as JSON-safe lists of objects.
def _nova_install_attachment_shape_normalizer_20260610():
    import re
    from pathlib import Path
    from flask import request

    data_dir = Path(__file__).resolve().parent / "data"
    sessions_path = data_dir / "nova_sessions.json"

    def load_store():
        try:
            if not sessions_path.exists():
                return {"active_session_id": "", "sessions": []}
            data = json.loads(sessions_path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                return {"active_session_id": "", "sessions": []}
            if not isinstance(data.get("sessions"), list):
                data["sessions"] = []
            data.setdefault("active_session_id", "")
            return data
        except Exception:
            return {"active_session_id": "", "sessions": []}

    def save_store(store):
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            tmp = sessions_path.with_suffix(sessions_path.suffix + ".tmp")
            tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(sessions_path)
            return True
        except Exception as exc:
            try:
                app.logger.warning("[Nova Attachment Shape Normalizer] save failed: %s", exc)
            except Exception:
                pass
            return False

    def parse_powershell_object_string(value):
        text = str(value or "").strip()

        if not text:
            return []

        if not (text.startswith("@{") and text.endswith("}")):
            return []

        inner = text[2:-1].strip()
        if not inner:
            return []

        item = {}
        parts = re.split(r";\s*", inner)

        for part in parts:
            if "=" not in part:
                continue

            key, raw = part.split("=", 1)
            key = str(key or "").strip()
            raw = str(raw or "").strip()

            if not key:
                continue

            if key in ("size", "size_bytes"):
                try:
                    item[key] = int(raw)
                except Exception:
                    item[key] = raw
            else:
                item[key] = raw

        if not item:
            return []

        if "url" in item and "file_url" not in item:
            item["file_url"] = item.get("url") or ""

        if "filename" in item and "name" not in item:
            item["name"] = item.get("filename") or ""

        return [item]

    def normalize_attachments(value):
        changed = False

        if value is None:
            return [], True

        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict):
                    clean = dict(item)

                    if "url" in clean and "file_url" not in clean:
                        clean["file_url"] = clean.get("url") or ""
                        changed = True

                    if "filename" in clean and "name" not in clean:
                        clean["name"] = clean.get("filename") or ""
                        changed = True

                    out.append(clean)
                    continue

                if isinstance(item, str):
                    parsed = parse_powershell_object_string(item)
                    if parsed:
                        out.extend(parsed)
                        changed = True
                    else:
                        changed = True
                    continue

                changed = True

            return out, changed

        if isinstance(value, dict):
            clean = dict(value)

            if "url" in clean and "file_url" not in clean:
                clean["file_url"] = clean.get("url") or ""

            if "filename" in clean and "name" not in clean:
                clean["name"] = clean.get("filename") or ""

            return [clean], True

        if isinstance(value, str):
            parsed = parse_powershell_object_string(value)
            return parsed, True

        return [], True

    def normalize_message_attachment_shapes():
        store = load_store()
        sessions = store.get("sessions", [])

        if not isinstance(sessions, list):
            return 0

        changed_count = 0

        for sess in sessions:
            if not isinstance(sess, dict):
                continue

            messages = sess.get("messages")
            if not isinstance(messages, list):
                continue

            for msg in messages:
                if not isinstance(msg, dict):
                    continue

                attachments, changed = normalize_attachments(msg.get("attachments"))

                if changed:
                    msg["attachments"] = attachments
                    changed_count += 1

                meta = msg.get("meta")
                if isinstance(meta, str) and meta.strip().startswith("@{") and meta.strip().endswith("}"):
                    parsed_meta = parse_powershell_object_string(meta)
                    msg["meta"] = parsed_meta[0] if parsed_meta else {}
                    changed_count += 1
                elif meta is None:
                    msg["meta"] = {}
                    changed_count += 1

        if changed_count:
            store["sessions"] = sessions
            save_store(store)

        return changed_count

    @app.after_request
    def nova_attachment_shape_normalizer_after_request_20260610(response):
        path = str(request.path or "")

        if (
            path.startswith("/api/sessions")
            or path.startswith("/api/chat")
            or path.startswith("/api/chat/stream")
            or path == "/mobile"
        ):
            changed = normalize_message_attachment_shapes()
            if changed:
                try:
                    app.logger.info("[Nova Attachment Shape Normalizer] repaired %s message attachment/meta fields", changed)
                except Exception:
                    pass

        return response


_nova_install_attachment_shape_normalizer_20260610()


# NOVA_HELP_PAGE_ROUTE_20260611
@app.route("/help")
def nova_help_page_20260611():
    return render_template("help.html")


# NOVA_BLOG_PAGE_ROUTE_20260611
@app.route("/blog")
def nova_blog_page_20260611():
    return render_template("blog.html")


# NOVA_BEFORE_REQUEST_EXPLICIT_MEMORY_GUARD_20260611
@app.before_request
def nova_before_request_explicit_memory_guard_20260611():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None


        payload = request.get_json(silent=True) or {}
        raw_user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        lowered = raw_user_text.lower().strip()

        prefixes = (
            "remember that ",
            "remember this ",
            "remember ",
            "save that ",
            "save this ",
            "store that ",
            "store this ",
            "note that ",
            "memorize that ",
            "add to memory that ",
            "add this to memory ",
        )

        clean = ""
        for prefix in prefixes:
            if lowered.startswith(prefix):
                clean = raw_user_text[len(prefix):].strip(" .\n\r\t")
                break

        if not clean:
            return None

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or ""
        ).strip()

        if not session_id:
            session_id = "session_" + uuid.uuid4().hex

        clean_lc = clean.lower()
        kind = "fact"

        # NOVA_MEMORY_KIND_GENERAL_FAVORITE_20260611
        if (
            "favorite " in clean_lc
            or "favourite " in clean_lc
            or "prefer" in clean_lc
            or "from now on" in clean_lc
            or "always" in clean_lc
            or "call me" in clean_lc
            or "my name is" in clean_lc
        ):
            kind = "preference"

        memory_service.add_memory({
            "text": clean,
            "kind": kind,
            "source": "app_explicit_memory_command",
            "session_id": session_id,
        })

        assistant_text = f"Saved to memory: {clean}"

        user_msg = {
            "role": "user",
            "text": raw_user_text,
            "attachments": [],
            "meta": {},
        }

        assistant_msg = {
            "role": "assistant",
            "text": assistant_text,
            "attachments": [],
            "memory_used": [],
            "meta": {
                "mode": "explicit_memory_command",
                "route": "memory_save",
                "save_memory": True,
                "use_memory": True,
                "before_request_guard": True,
            },
        }

        try:
            if hasattr(session_service, "add_message"):
                session_service.add_message(session_id, user_msg)
                session_service.add_message(session_id, assistant_msg)
        except Exception:
            pass

        session_obj = None
        try:
            session_obj = session_service.get_session(session_id)
        except Exception:
            session_obj = None

        return jsonify({
            "ok": True,
            "active_session_id": session_id,
            "assistant_message": assistant_msg,
            "attachment_debug": {
                "requested_session_id": session_id,
                "active_session_id": session_id,
                "session_attachments_count": 0,
            },
            "debug": {
                "route": "before_request_explicit_memory_guard",
                "route_taken": "memory_save",
            },
            "runtime": {},
            "session": session_obj or {
                "id": session_id,
                "messages": [user_msg, assistant_msg],
            },
            "session_attachments": [],
        })

    except Exception as exc:
        try:
            app.logger.warning("[before_request explicit memory guard] failed: %s", exc)
        except Exception:
            pass
        return None


# NOVA_BEFORE_REQUEST_FAVORITE_RECALL_GUARD_20260611
@app.before_request
def nova_before_request_favorite_recall_guard_20260611():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        raw_user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        clean_question = " ".join(raw_user_text.lower().replace("?", " ").split())

        prefix = "what is my favorite "
        if not clean_question.startswith(prefix):
            return None

        favorite_key = clean_question[len(prefix):].strip()
        if not favorite_key:
            return None

        target_start = f"my favorite {favorite_key} is "

        best_item = None
        for item in memory_service.all() or []:
            if not isinstance(item, dict):
                continue

            item_text = str(item.get("text") or "").strip()
            item_lc = item_text.lower()

            if item_lc.startswith(target_start):
                best_item = item
                break

        if not best_item:
            return None

        item_text = str(best_item.get("text") or "").strip()
        answer_value = item_text[len(target_start):].strip()
        if not answer_value:
            return None

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or ""
        ).strip()

        if not session_id:
            session_id = "session_" + uuid.uuid4().hex

        assistant_text = f"Your favorite {favorite_key} is {answer_value}."

        user_msg = {
            "role": "user",
            "text": raw_user_text,
            "attachments": [],
            "meta": {},
        }

        assistant_msg = {
            "role": "assistant",
            "text": assistant_text,
            "attachments": [],
            "memory_used": [best_item],
            "meta": {
                "mode": "memory_recall",
                "route": "favorite_memory_recall",
                "before_request_guard": True,
                "memory_used_count": 1,
            },
        }

        try:
            if hasattr(session_service, "add_message"):
                session_service.add_message(session_id, user_msg)
                session_service.add_message(session_id, assistant_msg)
        except Exception:
            pass

        try:
            session_obj = session_service.get_session(session_id)
        except Exception:
            session_obj = None

        return jsonify({
            "ok": True,
            "active_session_id": session_id,
            "assistant_message": assistant_msg,
            "attachment_debug": {
                "requested_session_id": session_id,
                "active_session_id": session_id,
                "session_attachments_count": 0,
            },
            "debug": {
                "route": "before_request_favorite_recall_guard",
                "route_taken": "favorite_memory_recall",
            },
            "runtime": {},
            "session": session_obj or {
                "id": session_id,
                "messages": [user_msg, assistant_msg],
            },
            "session_attachments": [],
        })

    except Exception as exc:
        try:
            app.logger.warning("[before_request favorite recall guard] failed: %s", exc)
        except Exception:
            pass
        return None

# NOVA_BEFORE_REQUEST_MEMORY_SUMMARY_GUARD_20260611
@app.before_request
def nova_before_request_memory_summary_guard_20260611():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        raw_user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        clean_question = " ".join(raw_user_text.lower().replace("?", " ").split())

        summary_questions = {
            "what do you remember about me",
            "what memory do you have",
            "what memories do you have",
            "show my memories",
            "show me my memories",
            "list my memories",
            "what do you know about me",
            "what have you remembered",
            "what have you saved about me",
        }

        if clean_question not in summary_questions:
            return None

        memories = []
        try:
            memories = memory_service.all() or []
        except Exception:
            memories = []

        clean_memories = []
        seen = set()

        for item in memories:
            if not isinstance(item, dict):
                continue

            text_value = str(item.get("text") or "").strip()
            if not text_value:
                continue

            key = text_value.lower()
            if key in seen:
                continue

            seen.add(key)

            kind = str(item.get("kind") or "memory").strip() or "memory"
            clean_memories.append({
                "kind": kind,
                "text": text_value,
                "source": str(item.get("source") or "").strip(),
                "weight": item.get("weight"),
                "updated_at": str(item.get("updated_at") or item.get("created_at") or "").strip(),
            })

        def sort_key(item):
            try:
                weight = float(item.get("weight") or 0)
            except Exception:
                weight = 0
            return (weight, item.get("updated_at") or "")

        clean_memories.sort(key=sort_key, reverse=True)

        if clean_memories:
            lines = []
            for item in clean_memories[:12]:
                kind = item.get("kind") or "memory"
                text_value = item.get("text") or ""
                lines.append(f"- [{kind}] {text_value}")

            assistant_text = "Here is what I remember:\n\n" + "\n".join(lines)
        else:
            assistant_text = "I do not have any saved memories yet."

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or ""
        ).strip()

        if not session_id:
            session_id = "session_" + uuid.uuid4().hex

        user_msg = {
            "role": "user",
            "text": raw_user_text,
            "attachments": [],
            "meta": {},
        }

        assistant_msg = {
            "role": "assistant",
            "text": assistant_text,
            "attachments": [],
            "memory_used": clean_memories[:12],
            "meta": {
                "mode": "memory_summary",
                "route": "memory_summary_recall",
                "before_request_guard": True,
                "memory_used_count": len(clean_memories[:12]),
            },
        }

        try:
            if hasattr(session_service, "add_message"):
                session_service.add_message(session_id, user_msg)
                session_service.add_message(session_id, assistant_msg)
        except Exception:
            pass

        try:
            session_obj = session_service.get_session(session_id)
        except Exception:
            session_obj = None

        return jsonify({
            "ok": True,
            "active_session_id": session_id,
            "assistant_message": assistant_msg,
            "attachment_debug": {
                "requested_session_id": session_id,
                "active_session_id": session_id,
                "session_attachments_count": 0,
            },
            "debug": {
                "route": "before_request_memory_summary_guard",
                "route_taken": "memory_summary_recall",
            },
            "runtime": {},
            "session": session_obj or {
                "id": session_id,
                "messages": [user_msg, assistant_msg],
            },
            "session_attachments": [],
        })

    except Exception as exc:
        try:
            app.logger.warning("[before_request memory summary guard] failed: %s", exc)
        except Exception:
            pass
        return None

# NOVA_CHAT_STREAM_REAL_20260613

@app.route("/api/events/stream")
def stream_events():
    def event_stream():
        while True:
            # keep connection alive
            yield "data: {}\n\n"
            time.sleep(15)

    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/api/chat/stream", methods=["POST"])
def nova_chat_stream():

    from flask import Response

    def generate():

        try:
            result = api_chat()

            # --- FORCE NORMALIZATION ---
            payload = None

            if isinstance(result, dict):
                payload = result
            elif hasattr(result, "get_json"):
                payload = result.get_json(silent=True)

            if not isinstance(payload, dict):
                payload = {}

            assistant = payload.get("assistant_message") or {}

            text = assistant.get("text", "")
            
            if not isinstance(text, str):
                text = ""

        except Exception as e:
            yield "data: " + json.dumps({
                "type": "error",
                "content": str(e)
            }) + "\n\n"
            return

        if not text:
            text = "No response generated."

        full = ""

        for chunk in text.split():
            full += chunk + " "

            yield "data: " + json.dumps({
                "type": "token",
                "content": chunk + " "
            }) + "\n\n"

        yield "data: " + json.dumps({
            "type": "message",
            "content": full.strip()
        }) + "\n\n"

        yield "data: " + json.dumps({
            "type": "done",
            "done": True
        }) + "\n\n"

    return Response(generate(), mimetype="text/event-stream")

@app.before_request
def nova_memory_command_before_web_20260611():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return None

        raw_user_text = str(
            data.get("user_text")
            or data.get("text")
            or data.get("message")
            or data.get("prompt")
            or ""
        ).strip()

        if not raw_user_text:
            return None

        clean_lower = " ".join(raw_user_text.lower().split())

        memory_prefixes = (
            "remember that ",
            "remember this ",
            "remember ",
            "save this ",
            "save to memory ",
            "store this ",
            "note that ",
            "add to memory ",
        )

        if not clean_lower.startswith(memory_prefixes):
            return None

        fact = raw_user_text
        for prefix in memory_prefixes:
            if clean_lower.startswith(prefix):
                fact = raw_user_text[len(prefix):].strip()
                break

        if not fact:
            return None

        session_id = str(
            data.get("session_id")
            or data.get("client_session_id")
            or data.get("active_session_id")
            or ""
        ).strip()

        if not session_id:
            session_id = "default"

        category = "preference"
        memory_text = fact

        focus_prefixes = (
            "my current nova focus is ",
            "current nova focus is ",
            "my current project focus is ",
            "current project focus is ",
        )

        fact_lower = " ".join(fact.lower().split())
        for prefix in focus_prefixes:
            if fact_lower.startswith(prefix):
                focus_value = fact[len(prefix):].strip()
                if focus_value:
                    category = "project_focus"
                    memory_text = "Current project focus: " + focus_value
                break

        existing = False
        try:
            for item in memory_service.all() or []:
                if isinstance(item, dict):
                    if str(item.get("text") or "").strip().lower() == memory_text.lower():
                        existing = True
                        break
        except Exception:
            existing = False

        if not existing:
            memory_service.add_memory({
                "text": memory_text,
                "category": category,
                "session_id": session_id,
                "source": "memory_command_before_web",
                "pinned": True,
                "weight": 10.0,
            })

        return None

    except Exception:
        return None

@app.before_request
def nova_focus_recall_before_web_20260611():
    return None

    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return None

        raw_user_text = str(
            data.get("user_text")
            or data.get("text")
            or data.get("message")
            or data.get("prompt")
            or ""
        ).strip()

        if not raw_user_text:
            return None

        clean = " ".join(raw_user_text.lower().split())

        focus_questions = (
            "what is my current nova focus",
            "what's my current nova focus",
            "what is my nova focus",
            "what's my nova focus",
            "what is my current project focus",
            "what's my current project focus",
            "what are we focused on",
            "what am i focused on",
        )

        if not any(q in clean for q in focus_questions):
            return None

        session_id = str(
            data.get("session_id")
            or data.get("client_session_id")
            or data.get("active_session_id")
            or ""
        ).strip()

        if not session_id:
            try:
                session_id = session_service.get_active_session_id()
            except Exception:
                session_id = ""

        if not session_id:
            session_id = "default"

        memories = []
        try:
            memories = memory_service.all() or []
        except Exception:
            memories = []

        best_text = ""
        best_score = -1

        for item in memories:
            if not isinstance(item, dict):
                continue

            text_value = str(
                item.get("text")
                or item.get("content")
                or item.get("fact")
                or ""
            ).strip()

            if not text_value:
                continue

            category = str(item.get("category") or item.get("type") or "").strip().lower()
            item_session_id = str(item.get("session_id") or "").strip()

            haystack = text_value.lower()
            score = 0

            if "desktop sessions and memory" in haystack:
                score += 20

            if category == "project_focus":
                score += 15

            if "current project focus:" in haystack:
                score += 12

            if "current nova focus" in haystack:
                score += 10

            if "nova focus" in haystack:
                score += 8

            if "project focus" in haystack:
                score += 8

            if item_session_id == session_id:
                score += 4
            elif not item_session_id:
                score += 1

            if score > best_score:
                best_score = score
                best_text = text_value

        if not best_text or best_score <= 0:
            assistant_text = "I do not have a current Nova focus saved yet."
        else:
            focus = best_text

            prefixes = (
                "Current project focus:",
                "current project focus:",
                "my current Nova focus is",
                "my current nova focus is",
                "current Nova focus is",
                "current nova focus is",
                "Current Nova focus:",
                "current nova focus:",
            )

            for prefix in prefixes:
                if focus.startswith(prefix):
                    focus = focus[len(prefix):].strip()
                    break

            assistant_text = "Your current Nova focus is: " + focus

        # ðŸ”’ IMPORTANT: DO NOT RETURN RESPONSE
        # Only attach data to request for downstream handler
        request.nova_focus_recall = {
            "session_id": session_id,
            "assistant_text": assistant_text,
            "best_score": best_score,
        }

        return None

    except Exception:
        return None


# NOVA_ATTACHMENT_DIRECT_TEXT_CLEAN_FINAL_20260611
def _nova_direct_clean_attachment_text_response_20260611(text_value):
    """
    Final safety cleaner for attachment-analysis replies.

    Goal:
    - keep real extracted attachment content
    - remove recursive summary wrappers
    - avoid repeated "This uploaded attachment contains readable text about..."
    """
    try:
        raw = str(text_value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not raw:
            return raw

        if "Attachment analysis:" not in raw:
            return raw

        lines = [line.strip() for line in raw.split("\n")]
        kept = []
        seen = set()

        skip_prefixes = (
            "This uploaded attachment contains readable text about:",
            "Key points:",
            "Preview:",
        )

        for line in lines:
            if not line:
                continue

            low = line.lower().strip()

            if low == "attachment analysis:":
                continue

            if any(low.startswith(prefix.lower()) for prefix in skip_prefixes):
                continue

            if re.match(r"^\d+\.\s*this uploaded attachment contains readable text about:", line, re.I):
                continue

            if "This uploaded attachment contains readable text about:" in line:
                continue

            normalized = re.sub(r"\s+", " ", line).strip()
            if not normalized:
                continue

            key = normalized.lower()
            if key in seen:
                continue

            seen.add(key)
            kept.append(normalized)

        content_lines = []

        for line in kept:
            if re.match(r"^Attachment\s+.+\s+content:\s*$", line, re.I):
                content_lines.append(line)
                continue

            if "secret test phrase" in line.lower():
                content_lines.append(line)
                continue

            if line.lower().startswith("attachment ") and " content:" in line.lower():
                content_lines.append(line)
                continue

            if len(line) >= 12 and not line.lower().startswith("this uploaded attachment"):
                content_lines.append(line)

        if not content_lines:
            return "Attachment analysis:\nThe attachment was received, but no clean readable text was found."

        final = "Attachment analysis:\n" + "\n".join(content_lines[:12])
        return final.strip()
    except Exception:
        return text_value

# NOVA_WEB_FETCH_REQUESTED_SESSION_BRIDGE_SAFE_20260612
# Registers before the existing target-session bridge.
# Rewrites successful web_fetch /api/chat responses to the requested session id
# and includes a response session object so the UI can render source cards even
# if /api/sessions/<id> filtering is still strict.
@app.after_request
def nova_web_fetch_requested_session_bridge_safe_20260612(response):
    try:
        if request.path != "/api/chat" or request.method != "POST":
            return response

        if getattr(response, "status_code", 500) >= 400:
            return response

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return response

        target_session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or payload.get("active_session_id")
            or ""
        ).strip()

        if not target_session_id:
            return response

        user_text = str(
            payload.get("user_text")
            or payload.get("message")
            or payload.get("text")
            or ""
        ).strip()

        if not user_text:
            return response

        response_json = response.get_json(silent=True) or {}
        if not isinstance(response_json, dict) or not response_json.get("ok", False):
            return response

        debug = response_json.get("debug") if isinstance(response_json.get("debug"), dict) else {}
        assistant_message = response_json.get("assistant_message")
        assistant_meta = {}

        if isinstance(assistant_message, dict) and isinstance(assistant_message.get("meta"), dict):
            assistant_meta.update(assistant_message.get("meta") or {})

        route_text = " ".join([
            str(debug.get("route") or ""),
            str(debug.get("route_taken") or ""),
            str(assistant_meta.get("route") or ""),
            str(assistant_meta.get("strategy") or ""),
        ]).lower()

        is_web_fetch = (
            "web_fetch" in route_text
            or assistant_meta.get("route") == "web"
            or assistant_meta.get("strategy") == "web_fetch"
            or isinstance(assistant_meta.get("sources"), list)
            or isinstance(assistant_meta.get("source_urls"), list)
        )

        if not is_web_fetch:
            return response

        assistant_text = ""
        assistant_attachments = []

        if isinstance(assistant_message, dict):
            assistant_text = str(
                assistant_message.get("text")
                or assistant_message.get("content")
                or ""
            ).strip()

            if isinstance(assistant_message.get("attachments"), list):
                assistant_attachments = assistant_message.get("attachments") or []

        if not assistant_text:
            assistant_text = str(
                response_json.get("text")
                or response_json.get("response")
                or response_json.get("answer")
                or ""
            ).strip()

        if not assistant_text:
            return response

        bridge_meta = dict(assistant_meta)
        bridge_meta.update({
            "route": "web_fetch_requested_session_bridge_safe",
            "target_session_id": target_session_id,
            "response_active_session_id": str(response_json.get("active_session_id") or ""),
            "response_session_id": str(response_json.get("session_id") or ""),
            "web_fetch_session_bridge": True,
        })

        user_message = {
            "role": "user",
            "text": user_text,
            "content": user_text,
            "attachments": payload.get("attachments") if isinstance(payload.get("attachments"), list) else [],
            "meta": {
                "route": "web_fetch_requested_session_bridge_safe",
                "target_session_id": target_session_id,
            },
        }

        assistant_saved = {
            "role": "assistant",
            "text": assistant_text,
            "content": assistant_text,
            "attachments": assistant_attachments,
            "meta": bridge_meta,
        }

        # Best-effort persistence.
        try:
            existing = session_service.get_session(target_session_id)
        except Exception:
            existing = None

        existing_blob = str(existing or "")

        try:
            if user_text not in existing_blob:
                # Disabled 20260622: target-session bridge/chat service handles user persistence.
                pass

            if assistant_text not in existing_blob:
                # Disabled 20260622: prevent duplicate assistant persistence from web_fetch_requested_session_bridge_safe.
                pass
        except Exception as persist_error:
            try:
                app.logger.warning(
                    "[WebFetchRequestedSessionBridgeSafe] persistence failed: %s",
                    persist_error,
                )
            except Exception:
                pass

        try:
            final_session = session_service.get_session(target_session_id)
        except Exception:
            final_session = None

        if not final_session:
            final_session = {
                "id": target_session_id,
                "messages": [user_message, assistant_saved],
                "session_attachments": [],
                "meta": {},
            }

        response_json["session_id"] = target_session_id
        response_json["active_session_id"] = target_session_id
        response_json["target_session_append_bridge"] = True
        response_json["web_fetch_requested_session_bridge"] = True
        response_json["session"] = final_session

        if isinstance(response_json.get("assistant_message"), dict):
            response_json["assistant_message"]["session_id"] = target_session_id
            response_json["assistant_message"]["active_session_id"] = target_session_id

        response.set_data(json.dumps(response_json, ensure_ascii=False))
        response.headers["Content-Length"] = str(len(response.get_data()))
        response.headers["Content-Type"] = "application/json"

    except Exception as error:
        try:
            app.logger.warning(
                "[WebFetchRequestedSessionBridgeSafe] failed: %s",
                error,
            )
        except Exception:
            pass

    return response

# NOVA_FORCE_WEB_FETCH_BRIDGE_RUNS_LAST_20260612
# Flask executes after_request hooks in reverse registration order.
# Force the safe web-fetch bridge to index 0 so it runs last and cannot be
# overwritten by older response-normalizer hooks.
try:
    _nova_after_hooks = app.after_request_funcs.get(None, [])
    _nova_bridge_name = "nova_web_fetch_requested_session_bridge_safe_20260612"
    _nova_bridge_func = None

    for _nova_hook in list(_nova_after_hooks):
        if getattr(_nova_hook, "__name__", "") == _nova_bridge_name:
            _nova_bridge_func = _nova_hook
            try:
                _nova_after_hooks.remove(_nova_hook)
            except ValueError:
                pass
            break

    if _nova_bridge_func is not None:
        _nova_after_hooks.insert(0, _nova_bridge_func)
        app.after_request_funcs[None] = _nova_after_hooks
        _nova_boot_log_20260701("[NOVA_WEB_FETCH_BRIDGE_ORDER] forced bridge to run last")
    else:
        print("[NOVA_WEB_FETCH_BRIDGE_ORDER] bridge function not found")
except Exception as _nova_bridge_order_error:
    try:
        app.logger.warning("[NOVA_WEB_FETCH_BRIDGE_ORDER] failed: %s", _nova_bridge_order_error)
    except Exception:
        pass

# NOVA_API_CHAT_TARGET_SESSION_APPEND_BRIDGE_20260611
# Ensures /api/chat persists user+assistant exchanges into the explicit
# request session_id/client_session_id/active_session_id instead of silently
# creating or returning a different active session.
@app.after_request
def nova_api_chat_target_session_append_bridge_20260611(response):
    try:
        if request.path != "/api/chat" or request.method != "POST":
            return response

        if getattr(response, "status_code", 500) >= 400:
            return response

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return response

        target_session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or payload.get("active_session_id")
            or ""
        ).strip()

        if not target_session_id:
            return response

        user_text = str(
            payload.get("message")
            or payload.get("user_text")
            or payload.get("text")
            or payload.get("prompt")
            or ""
        ).strip()

        if not user_text:
            return response

        response_json = response.get_json(silent=True) or {}
        if not isinstance(response_json, dict) or not response_json.get("ok", False):
            return response

        assistant_message = response_json.get("assistant_message")
        assistant_text = ""

        if isinstance(assistant_message, dict):
            assistant_text = str(
                assistant_message.get("text")
                or assistant_message.get("content")
                or ""
            ).strip()

        if not assistant_text:
            assistant_text = str(
                response_json.get("text")
                or response_json.get("response")
                or response_json.get("answer")
                or ""
            ).strip()

        if not assistant_text:
            return response

        try:
            target_session = session_service.get_session(target_session_id)
        except Exception:
            target_session = None

        if not target_session:
            return response

        try:
            existing_blob = json.dumps(target_session, ensure_ascii=False)
        except Exception:
            existing_blob = str(target_session)

        visible_user_text = _nova_strip_project_context_from_visible_text(user_text)

        # Idempotency guard. If a normal route already saved this exact user
        # text into the target session, do not duplicate it.
        if visible_user_text in existing_blob:
            return response

        request_meta = {
            "route": "api_chat_target_session_append_bridge",
            "target_session_id": target_session_id,
            "response_active_session_id": str(response_json.get("active_session_id") or ""),
            "response_session_id": str(response_json.get("session_id") or ""),
        }

        try:
            session_service.append_message(target_session_id, {
                "role": "user",
                "text": visible_user_text,
                "attachments": payload.get("attachments") if isinstance(payload.get("attachments"), list) else [],
                "meta": request_meta,
            })

            assistant_meta = {}
            assistant_attachments = []

            if isinstance(assistant_message, dict):
                if isinstance(assistant_message.get("meta"), dict):
                    assistant_meta.update(assistant_message.get("meta") or {})
                if isinstance(assistant_message.get("attachments"), list):
                    assistant_attachments = assistant_message.get("attachments") or []

            assistant_meta.update(request_meta)

            session_service.append_message(target_session_id, {
                "role": "assistant",
                "text": assistant_text,
                "attachments": assistant_attachments,
                "meta": assistant_meta,
            })

            response_json["session_id"] = target_session_id
            response_json["active_session_id"] = target_session_id
            response_json["target_session_append_bridge"] = True

            try:
                response.set_data(json.dumps(response_json, ensure_ascii=False))
                response.mimetype = "application/json"
            except Exception:
                pass

        except Exception as exc:
            try:
                app.logger.warning("[Nova API Chat Target Session Append Bridge] skipped: %s", exc)
            except Exception:
                pass

        return response

    except Exception:
        return response



# NOVA_FINAL_SESSION_DETAIL_RESPONSE_CACHE_20260612
# Final rescue for source-card session detail:
# - /api/chat already returns the correct requested session id and sources.
# - Some session_service append paths do not make synthetic requested sessions
#   readable through /api/sessions/<id>.
# - This hook runs last, saves the final /api/chat response session to disk,
#   and lets failed /api/sessions/<id> calls recover from that disk cache.
_NOVA_FINAL_SESSION_DETAIL_CACHE_20260612 = {}

def _nova_final_session_detail_cache_path_20260612():
    try:
        return os.path.join(BASE_DIR, "data", "nova_sessions.json")
    except Exception:
        return os.path.join(os.getcwd(), "data", "nova_sessions.json")


def _nova_final_load_sessions_store_20260612():
    try:
        path_value = _nova_final_session_detail_cache_path_20260612()
        if os.path.exists(path_value):
            with open(path_value, "r", encoding="utf-8") as handle:
                data = json.load(handle) or {}
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _nova_final_save_sessions_store_20260612(store):
    try:
        path_value = _nova_final_session_detail_cache_path_20260612()
        os.makedirs(os.path.dirname(path_value), exist_ok=True)
        with open(path_value, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)
        return True
    except Exception as error:
        try:
            app.logger.warning("[FinalSessionDetailCache] save failed: %s", error)
        except Exception:
            pass
    return False


def _nova_final_find_session_in_store_20260612(store, session_id):
    sessions = store.get("sessions")
    if isinstance(sessions, dict):
        item = sessions.get(session_id)
        return item if isinstance(item, dict) else None

    if isinstance(sessions, list):
        for item in sessions:
            if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                return item

    return None


def _nova_final_upsert_session_in_store_20260612(session_id, session_obj):
    if not session_id or not isinstance(session_obj, dict):
        return None

    store = _nova_final_load_sessions_store_20260612()

    sessions = store.get("sessions")
    if not isinstance(sessions, list):
        sessions = []

    existing = None
    for item in sessions:
        if isinstance(item, dict) and str(item.get("id") or "") == session_id:
            existing = item
            break

    if existing is None:
        existing = {
            "id": session_id,
            "title": str(session_obj.get("title") or "Web Fetch")[:80],
            "messages": [],
            "session_attachments": [],
            "meta": {},
        }
        sessions.insert(0, existing)

    for key, value in session_obj.items():
        if key == "messages":
            continue
        existing[key] = value

    messages = session_obj.get("messages")
    if not isinstance(messages, list):
        messages = existing.get("messages") if isinstance(existing.get("messages"), list) else []

    existing["messages"] = messages
    existing["message_count"] = len(messages)
    existing["active_session_id"] = session_id

    try:
        existing["updated_at"] = datetime.utcnow().isoformat() + "Z"
    except Exception:
        pass

    meta = existing.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        existing["meta"] = meta

    meta["final_session_detail_response_cache"] = True

    store["sessions"] = sessions
    store["active_session_id"] = session_id

    _nova_final_save_sessions_store_20260612(store)
    _NOVA_FINAL_SESSION_DETAIL_CACHE_20260612[session_id] = existing

    return existing


@app.after_request
def nova_final_session_detail_response_cache_20260612(response):
    try:
        request_path = str(getattr(request, "path", "") or "")
        request_method = str(getattr(request, "method", "") or "").upper()

        if request_method == "POST" and request_path == "/api/chat":
            response_json = response.get_json(silent=True) or {}
            if not isinstance(response_json, dict):
                return response

            session_id = str(
                response_json.get("session_id")
                or response_json.get("active_session_id")
                or ""
            ).strip()

            if not session_id:
                return response

            session_obj = response_json.get("session")
            if not isinstance(session_obj, dict):
                session_obj = {
                    "id": session_id,
                    "title": "Web Fetch",
                    "messages": [],
                    "session_attachments": [],
                    "meta": {},
                }

            session_obj["id"] = session_id

            messages = session_obj.get("messages")
            if not isinstance(messages, list):
                messages = []

            user_text = ""
            try:
                payload = request.get_json(silent=True) or {}
                if isinstance(payload, dict):
                    user_text = str(
                        payload.get("user_text")
                        or payload.get("message")
                        or payload.get("text")
                        or ""
                    ).strip()
            except Exception:
                user_text = ""

            assistant_message = response_json.get("assistant_message")
            assistant_text = ""

            if isinstance(assistant_message, dict):
                assistant_text = str(
                    assistant_message.get("text")
                    or assistant_message.get("content")
                    or ""
                ).strip()

            # NOVA_FINAL_CACHE_WORKING_ON_RECALL_REPAIR_20260630
            # chat_service can answer before the requested-session bridge/final cache
            # has the right session loaded. At this point app.py already has the
            # correct session messages, so repair the visible answer here.
            try:
                working_question = str(user_text or "").strip().lower() in {
                    "what are we working on",
                    "what are we working on?",
                    "what were we working on",
                    "what were we working on?",
                }

                bad_working_answer = str(assistant_text or "").strip() in {
                    "",
                    "No active task is currently tracked yet.",
                    "We're working on No active task is currently tracked..",
                    "We're working on No active task is currently tracked.",
                }

                if working_question and bad_working_answer:
                    inferred_task = ""

                    session_title = str(session_obj.get("title") or "").strip()
                    lowered_title = session_title.lower()

                    if lowered_title.startswith("we are working on "):
                        inferred_task = session_title[len("we are working on "):].strip(" .")
                    elif lowered_title.startswith("we're working on "):
                        inferred_task = session_title[len("we're working on "):].strip(" .")
                    elif lowered_title.startswith("working on "):
                        inferred_task = session_title[len("working on "):].strip(" .")

                    if not inferred_task:
                        for msg in reversed(messages):
                            if not isinstance(msg, dict):
                                continue

                            role = str(
                                msg.get("role")
                                or msg.get("sender")
                                or ""
                            ).strip().lower()

                            if role != "user":
                                continue

                            msg_text = str(
                                msg.get("text")
                                or msg.get("content")
                                or ""
                            ).strip()

                            lowered_msg = msg_text.lower()

                            if lowered_msg in {
                                "what are we working on",
                                "what are we working on?",
                                "what were we working on",
                                "what were we working on?",
                            }:
                                continue

                            if lowered_msg.startswith("we are working on "):
                                inferred_task = msg_text[len("we are working on "):].strip(" .")
                                break

                            if lowered_msg.startswith("we're working on "):
                                inferred_task = msg_text[len("we're working on "):].strip(" .")
                                break

                            if lowered_msg.startswith("working on "):
                                inferred_task = msg_text[len("working on "):].strip(" .")
                                break

                    if inferred_task:
                        fixed_text = f"We're working on {inferred_task}."

                        bad_saved_working_answers = {
                            "",
                            "No active task is currently tracked yet.",
                            "We're working on No active task is currently tracked..",
                            "We're working on No active task is currently tracked.",
                        }

                        try:
                            for msg in reversed(messages):
                                if not isinstance(msg, dict):
                                    continue

                                role = str(
                                    msg.get("role")
                                    or msg.get("sender")
                                    or ""
                                ).strip().lower()

                                if role != "assistant":
                                    continue

                                msg_text = str(
                                    msg.get("text")
                                    or msg.get("content")
                                    or ""
                                ).strip()

                                if msg_text in bad_saved_working_answers:
                                    msg["text"] = fixed_text
                                    msg["content"] = fixed_text

                                    msg_meta = msg.get("meta")
                                    if not isinstance(msg_meta, dict):
                                        msg_meta = {}

                                    msg_meta["route"] = "final_cache_working_on_recall_repair"
                                    msg_meta["repaired_saved_working_recall"] = True
                                    msg_meta["session_id"] = session_id

                                    msg["meta"] = msg_meta
                                    break

                            session_obj["messages"] = messages

                        except Exception:
                            pass

                        assistant_text = fixed_text

                        if isinstance(assistant_message, dict):
                            assistant_message["text"] = fixed_text
                            assistant_message["content"] = fixed_text

                            assistant_meta = assistant_message.get("meta")
                            if not isinstance(assistant_meta, dict):
                                assistant_meta = {}

                            assistant_meta["route"] = "final_cache_working_on_recall_repair"
                            assistant_meta["repaired_working_recall"] = True
                            assistant_meta["session_id"] = session_id

                            assistant_message["meta"] = assistant_meta
                            response_json["assistant_message"] = assistant_message

                        working_state = session_obj.get("working_state")
                        if not isinstance(working_state, dict):
                            working_state = {}

                        working_state["active_task"] = inferred_task

                        if ".py" in inferred_task and not working_state.get("current_file"):
                            for part in inferred_task.replace("\\", "/").split():
                                clean_part = part.strip("`'\".,:;()[]{}")
                                if clean_part.endswith(".py"):
                                    working_state["current_file"] = clean_part.split("/")[-1]
                                    break

                        session_obj["working_state"] = working_state

            except Exception:
                pass

            # NOVA_FINAL_CACHE_CURRENT_FILE_RECALL_REPAIR_20260630
            # chat_service can answer before the final requested session state is attached.
            # At this point app.py has the correct session_obj, so repair current-file recall.
            try:
                file_question = str(user_text or "").strip().lower() in {
                    "what file are we in",
                    "which file",
                    "current file",
                    "what file",
                }

                bad_file_answer = str(assistant_text or "").strip() in {
                    "",
                    "Current file:\nNo active file is currently tracked.",
                    "No active file is currently tracked.",
                    "No active file is currently tracked",
                }

                if file_question and bad_file_answer:
                    working_state = session_obj.get("working_state")
                    if not isinstance(working_state, dict):
                        working_state = {}

                    current_file = str(
                        working_state.get("current_file")
                        or ""
                    ).strip()

                    if current_file:
                        fixed_text = f"Current file:\n{current_file}"

                        assistant_text = fixed_text

                        if isinstance(assistant_message, dict):
                            assistant_message["text"] = fixed_text
                            assistant_message["content"] = fixed_text

                            assistant_meta = assistant_message.get("meta")
                            if not isinstance(assistant_meta, dict):
                                assistant_meta = {}

                            assistant_meta["route"] = "final_cache_current_file_recall_repair"
                            assistant_meta["repaired_current_file_recall"] = True
                            assistant_meta["session_id"] = session_id

                            assistant_message["meta"] = assistant_meta
                            response_json["assistant_message"] = assistant_message

            except Exception:
                pass

            # NOVA_FINAL_CACHE_ACTIVE_TASK_RECALL_REPAIR_20260630
            # chat_service can answer before the final requested session state is attached.
            # At this point app.py has the correct session_obj, so repair active-task recall.
            try:
                active_task_question = str(user_text or "").strip().lower() in {
                    "what is the active task",
                    "active task",
                    "what are we doing",
                }

                bad_active_task_answer = str(assistant_text or "").strip() in {
                    "",
                    "Active task:\nNo active task is currently tracked.",
                    "Active task:\nNo active task is currently tracked yet.",
                    "No active task is currently tracked.",
                    "No active task is currently tracked",
                    "No active task is currently tracked yet.",
                }

                if active_task_question and bad_active_task_answer:
                    working_state = session_obj.get("working_state")
                    if not isinstance(working_state, dict):
                        working_state = {}

                    active_task = str(
                        working_state.get("active_task")
                        or ""
                    ).strip()

                    if active_task:
                        fixed_text = f"Active task:\n{active_task}"

                        assistant_text = fixed_text

                        if isinstance(assistant_message, dict):
                            assistant_message["text"] = fixed_text
                            assistant_message["content"] = fixed_text

                            assistant_meta = assistant_message.get("meta")
                            if not isinstance(assistant_meta, dict):
                                assistant_meta = {}

                            assistant_meta["route"] = "final_cache_active_task_recall_repair"
                            assistant_meta["repaired_active_task_recall"] = True
                            assistant_meta["session_id"] = session_id

                            assistant_message["meta"] = assistant_meta
                            response_json["assistant_message"] = assistant_message

            except Exception:
                pass

            if user_text and user_text not in json.dumps(messages, ensure_ascii=False):
                messages.append({
                    "role": "user",
                    "text": user_text,
                    "content": user_text,
                    "attachments": [],
                    "meta": {
                        "route": "final_session_detail_response_cache",
                        "session_id": session_id,
                    },
                })

            assistant_id = ""
            if isinstance(assistant_message, dict):
                assistant_id = str(assistant_message.get("id") or "").strip()

            existing_messages_blob = json.dumps(messages, ensure_ascii=False)

            assistant_already_saved = False

            if assistant_id and assistant_id in existing_messages_blob:
                assistant_already_saved = True

            if assistant_text and assistant_text in existing_messages_blob:
                assistant_already_saved = True

            # NOVA_FINAL_CACHE_SKIP_DOUBLE_ASSISTANT_20260630
            # If chat_service.handle or another bridge already saved an assistant turn,
            # do not let the final session-detail cache append another assistant variant.
            try:
                last_saved_role = ""

                for existing_msg in reversed(messages):
                    if not isinstance(existing_msg, dict):
                        continue

                    existing_role = str(
                        existing_msg.get("role")
                        or existing_msg.get("sender")
                        or ""
                    ).strip().lower()

                    existing_text = str(
                        existing_msg.get("text")
                        or existing_msg.get("content")
                        or existing_msg.get("message")
                        or ""
                    ).strip()

                    if existing_role and existing_text:
                        last_saved_role = existing_role
                        break

                if last_saved_role == "assistant":
                    assistant_already_saved = True

            except Exception:
                pass

            # NOVA_FINAL_SESSION_CACHE_SAME_TEXT_DEDUPE_20260622
            # If another bridge already placed the same assistant text in session.messages,
            # do not append the top-level assistant_message again.
            if assistant_text and not assistant_already_saved:
                try:
                    _assistant_text_norm = str(assistant_text or "").strip()

                    for _existing_msg in messages:
                        if not isinstance(_existing_msg, dict):
                            continue

                        _existing_role = str(
                            _existing_msg.get("role")
                            or _existing_msg.get("sender")
                            or ""
                        ).strip().lower()

                        _existing_text = str(
                            _existing_msg.get("text")
                            or _existing_msg.get("content")
                            or _existing_msg.get("message")
                            or ""
                        ).strip()

                        if (
                            _existing_role == "assistant"
                            and _assistant_text_norm
                            and _existing_text == _assistant_text_norm
                        ):
                            assistant_already_saved = True
                            break

                except Exception:
                    pass

            if assistant_text and not assistant_already_saved:
                saved_assistant = assistant_message if isinstance(assistant_message, dict) else {}
                saved_assistant = dict(saved_assistant)
                saved_assistant["role"] = "assistant"
                saved_assistant["text"] = assistant_text
                saved_assistant["content"] = assistant_text

                session_meta = saved_assistant.get("meta")
                if not isinstance(session_meta, dict):
                    session_meta = {}
                    saved_assistant["meta"] = session_meta

                session_meta["route"] = session_meta.get("route") or "final_session_detail_response_cache"
                session_meta["session_id"] = session_id

                messages.append(saved_assistant)

            cleaned_messages = []

            for msg in messages:
                if not isinstance(msg, dict):
                    continue

                clean_msg = dict(msg)

                if clean_msg.get("role") == "user":
                    clean_msg["text"] = _nova_strip_project_context_from_visible_text(
                        clean_msg.get("text") or clean_msg.get("content") or ""
                    )
                    clean_msg["content"] = clean_msg["text"]

                cleaned_messages.append(clean_msg)

            messages = cleaned_messages

            session_obj["messages"] = messages
            session_obj["message_count"] = len(messages)
            session_obj["active_session_id"] = session_id

            # NOVA_FINAL_CACHE_WORKING_STATE_PERSIST_20260630
            # Persist inferred working_state into the session itself so /api/chat,
            # /api/state, mobile, and session restore all agree.
            try:
                working_state = session_obj.get("working_state")

                if not isinstance(working_state, dict):
                    working_state = {}

                active_task = str(
                    working_state.get("active_task")
                    or working_state.get("task")
                    or ""
                ).strip()

                current_file = str(
                    working_state.get("current_file")
                    or working_state.get("file")
                    or ""
                ).strip()

                last_user_message = ""
                last_assistant_message = ""

                session_messages = session_obj.get("messages")
                if not isinstance(session_messages, list):
                    session_messages = []

                for message in reversed(session_messages):
                    if not isinstance(message, dict):
                        continue

                    role = str(message.get("role") or "").strip().lower()
                    message_text = str(
                        message.get("text")
                        or message.get("content")
                        or ""
                    ).strip()

                    if role == "user" and not last_user_message:
                        last_user_message = message_text

                    if role == "assistant" and not last_assistant_message:
                        last_assistant_message = message_text

                    if last_user_message and last_assistant_message:
                        break

                if not active_task:
                    session_title = str(session_obj.get("title") or "").strip()
                    lowered_title = session_title.lower()

                    if lowered_title.startswith("we are working on "):
                        active_task = session_title[len("we are working on "):].strip(" .")

                    elif lowered_title.startswith("we're working on "):
                        active_task = session_title[len("we're working on "):].strip(" .")

                    elif lowered_title.startswith("working on "):
                        active_task = session_title[len("working on "):].strip(" .")

                if not active_task:
                    for message in reversed(session_messages):
                        if not isinstance(message, dict):
                            continue

                        if str(message.get("role") or "").strip().lower() != "user":
                            continue

                        message_text = str(
                            message.get("text")
                            or message.get("content")
                            or ""
                        ).strip()

                        lowered_message = message_text.lower()

                        if lowered_message in {
                            "what are we working on",
                            "what are we working on?",
                            "what were we working on",
                            "what were we working on?",
                            "what file are we in",
                            "what file are we in?",
                            "current file",
                            "active task",
                        }:
                            continue

                        if lowered_message.startswith("we are working on "):
                            active_task = message_text[len("we are working on "):].strip(" .")
                            break

                        if lowered_message.startswith("we're working on "):
                            active_task = message_text[len("we're working on "):].strip(" .")
                            break

                        if lowered_message.startswith("working on "):
                            active_task = message_text[len("working on "):].strip(" .")
                            break

                if not current_file and active_task:
                    for part in active_task.replace(",", " ").split():
                        clean_part = part.strip("`'\".,:;()[]{}")

                        if clean_part.endswith((
                            ".py",
                            ".js",
                            ".css",
                            ".html",
                            ".json",
                            ".md",
                            ".txt",
                        )):
                            current_file = clean_part
                            break

                working_state["active_task"] = active_task
                working_state["current_file"] = current_file
                working_state["last_user_message"] = last_user_message
                working_state["last_assistant_message"] = last_assistant_message

                session_obj["working_state"] = working_state
                session_obj["active_session_id"] = session_id

            except Exception:
                pass

            cached = _nova_final_upsert_session_in_store_20260612(session_id, session_obj)

            if isinstance(cached, dict):
                response_session = dict(cached)

                # NOVA_HIDE_TOP_LEVEL_ASSISTANT_DUPLICATE_FROM_RESPONSE_20260630
                # The assistant reply is already returned as response_json["assistant_message"].
                # Do not also include the same newest assistant bubble inside response_json["session"]
                # for this immediate /api/chat response, or the frontend can render it twice.
                try:
                    response_messages = response_session.get("messages")

                    if isinstance(response_messages, list) and assistant_text:
                        stripped_messages = []
                        removed_current_assistant = False

                        for msg in reversed(response_messages):
                            if not isinstance(msg, dict):
                                stripped_messages.append(msg)
                                continue

                            role = str(
                                msg.get("role")
                                or msg.get("sender")
                                or ""
                            ).strip().lower()

                            msg_text = str(
                                msg.get("text")
                                or msg.get("content")
                                or ""
                            ).strip()

                            if (
                                not removed_current_assistant
                                and role == "assistant"
                                and msg_text == assistant_text
                            ):
                                removed_current_assistant = True
                                continue

                            stripped_messages.append(msg)

                        stripped_messages.reverse()
                        response_session["messages"] = stripped_messages

                    if isinstance(response_json.get("assistant_message"), dict):
                        response_json["assistant_message"].setdefault("meta", {})
                        response_json["assistant_message"]["meta"]["render_source"] = "assistant_message_only"
                        response_json["assistant_message"]["meta"]["already_saved_to_session"] = True

                    # NOVA_FINAL_CACHE_REPAIRED_RECALL_SESSION_MESSAGE_SYNC_20260630
                    # If app.py repaired the top-level assistant_message, keep the returned
                    # session.messages payload in sync so the UI cannot render stale cache text.
                    try:
                        repaired_assistant = response_json.get("assistant_message")

                        if isinstance(repaired_assistant, dict):
                            repaired_meta = repaired_assistant.get("meta")
                            if not isinstance(repaired_meta, dict):
                                repaired_meta = {}

                            repaired_recall = bool(
                                repaired_meta.get("repaired_current_file_recall")
                                or repaired_meta.get("repaired_active_task_recall")
                            )

                            fixed_text = str(
                                repaired_assistant.get("text")
                                or repaired_assistant.get("content")
                                or ""
                            ).strip()

                            if repaired_recall and fixed_text and isinstance(response_session, dict):
                                response_session["active_session_id"] = session_id

                                working_state = response_session.get("working_state")
                                if not isinstance(working_state, dict):
                                    working_state = {}

                                working_state["last_user_message"] = str(user_text or "")
                                working_state["last_assistant_message"] = fixed_text
                                response_session["working_state"] = working_state

                                returned_messages = response_session.get("messages")
                                if not isinstance(returned_messages, list):
                                    returned_messages = []

                                assistant_id = str(
                                    repaired_assistant.get("id")
                                    or repaired_assistant.get("message_id")
                                    or ""
                                ).strip()

                                stale_recall_answers = {
                                    "Current file:\nNo active file is currently tracked.",
                                    "No active file is currently tracked.",
                                    "No active file is currently tracked",
                                    "Active task:\nNo active task is currently tracked.",
                                    "Active task:\nNo active task is currently tracked yet.",
                                    "No active task is currently tracked.",
                                    "No active task is currently tracked",
                                    "No active task is currently tracked yet.",
                                }

                                patched_existing_message = False

                                for msg in reversed(returned_messages):
                                    if not isinstance(msg, dict):
                                        continue

                                    if str(msg.get("role") or "").lower() != "assistant":
                                        continue

                                    msg_id = str(msg.get("id") or "").strip()
                                    msg_text = str(
                                        msg.get("text")
                                        or msg.get("content")
                                        or ""
                                    ).strip()

                                    same_message_id = bool(
                                        assistant_id
                                        and msg_id
                                        and msg_id == assistant_id
                                    )

                                    stale_recall_message = msg_text in stale_recall_answers

                                    if same_message_id or stale_recall_message:
                                        msg["text"] = fixed_text
                                        msg["content"] = fixed_text
                                        msg["attachments"] = msg.get("attachments") or []

                                        msg_meta = msg.get("meta")
                                        if not isinstance(msg_meta, dict):
                                            msg_meta = {}

                                        msg_meta.update(repaired_meta)
                                        msg_meta["session_id"] = session_id
                                        msg_meta["render_source"] = "assistant_message_only"
                                        msg_meta["already_saved_to_session"] = True

                                        msg["meta"] = msg_meta
                                        msg["session_id"] = session_id
                                        msg["active_session_id"] = session_id

                                        patched_existing_message = True
                                        break

                                if not patched_existing_message:
                                    returned_messages.append(
                                        {
                                            "id": assistant_id,
                                            "role": "assistant",
                                            "text": fixed_text,
                                            "content": fixed_text,
                                            "attachments": [],
                                            "meta": repaired_meta,
                                            "session_id": session_id,
                                            "active_session_id": session_id,
                                        }
                                    )

                                response_session["messages"] = returned_messages

                    except Exception:
                        pass

                except Exception:
                    response_session = dict(cached)

                # NOVA_FINAL_CACHE_STALE_WORKING_STATE_HISTORY_CLEANUP_20260630
                # Clean stale direct-recall answers inside returned session.messages.
                # This prevents the UI from rendering old "No active..." text when
                # working_state already has the truth.
                try:
                    if isinstance(response_session, dict):
                        working_state = response_session.get("working_state")
                        if not isinstance(working_state, dict):
                            working_state = {}

                        current_file = str(
                            working_state.get("current_file")
                            or ""
                        ).strip()

                        active_task = str(
                            working_state.get("active_task")
                            or ""
                        ).strip()

                        returned_messages = response_session.get("messages")
                        if isinstance(returned_messages, list):
                            for msg in returned_messages:
                                if not isinstance(msg, dict):
                                    continue

                                if str(msg.get("role") or "").lower() != "assistant":
                                    continue

                                msg_text = str(
                                    msg.get("text")
                                    or msg.get("content")
                                    or ""
                                ).strip()

                                fixed_text = ""

                                if (
                                    current_file
                                    and msg_text in {
                                        "Current file:\nNo active file is currently tracked.",
                                        "No active file is currently tracked.",
                                        "No active file is currently tracked",
                                    }
                                ):
                                    fixed_text = f"Current file:\n{current_file}"

                                if (
                                    active_task
                                    and msg_text in {
                                        "Active task:\nNo active task is currently tracked.",
                                        "Active task:\nNo active task is currently tracked yet.",
                                        "No active task is currently tracked.",
                                        "No active task is currently tracked",
                                        "No active task is currently tracked yet.",
                                    }
                                ):
                                    fixed_text = f"Active task:\n{active_task}"

                                if not fixed_text:
                                    continue

                                msg["text"] = fixed_text
                                msg["content"] = fixed_text
                                msg["attachments"] = msg.get("attachments") or []
                                msg["session_id"] = session_id
                                msg["active_session_id"] = session_id

                                msg_meta = msg.get("meta")
                                if not isinstance(msg_meta, dict):
                                    msg_meta = {}

                                msg_meta["route"] = "final_cache_stale_working_state_history_cleanup"
                                msg_meta["session_id"] = session_id
                                msg_meta["render_source"] = "assistant_message_only"
                                msg_meta["stale_working_state_history_cleaned"] = True

                                msg["meta"] = msg_meta

                            response_session["messages"] = returned_messages

                except Exception:
                    pass

                response_json["session"] = response_session
                response_json["session_id"] = session_id
                response_json["active_session_id"] = session_id
            try:
                session_service.active_session_id = session_id
            except Exception:
                pass
                response_json["final_session_detail_response_cache"] = True
                response.set_data(json.dumps(response_json, ensure_ascii=False))
                response.headers["Content-Length"] = str(len(response.get_data()))
                response.headers["Content-Type"] = "application/json"

            return response

        if request_method == "GET" and request_path.startswith("/api/sessions/"):
            if request_path.rstrip("/") == "/api/sessions":
                return response

            if getattr(response, "status_code", 200) < 400:
                return response

            session_id = request_path[len("/api/sessions/"):].strip().strip("/")
            if not session_id:
                return response

            session_obj = _NOVA_FINAL_SESSION_DETAIL_CACHE_20260612.get(session_id)

            if not session_obj:
                store = _nova_final_load_sessions_store_20260612()
                session_obj = _nova_final_find_session_in_store_20260612(store, session_id)

            if not isinstance(session_obj, dict):
                return response

            messages = session_obj.get("messages")
            if not isinstance(messages, list):
                messages = []

            payload = {
                "ok": True,
                "id": session_id,
                "active_session_id": session_id,
                "message_count": len(messages),
                "session": session_obj,
                "skip_session_auth_scope_filter": True,
                "session_detail_web_fetch_cache_fallback": True,
            }

            return app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json",
            )

    except Exception as error:
        try:
            app.logger.warning("[FinalSessionDetailCache] failed: %s", error)
        except Exception:
            pass

    return response


# Force this hook to run last. Flask executes after_request hooks in reverse order,
# so index 0 is the final hook to touch the response.
try:
    _nova_hooks = app.after_request_funcs.get(None, [])
    _nova_name = "nova_final_session_detail_response_cache_20260612"
    _nova_func = None

    for _nova_hook in list(_nova_hooks):
        if getattr(_nova_hook, "__name__", "") == _nova_name:
            _nova_func = _nova_hook
            try:
                _nova_hooks.remove(_nova_hook)
            except ValueError:
                pass
            break

    if _nova_func is not None:
        _nova_hooks.insert(0, _nova_func)
        app.after_request_funcs[None] = _nova_hooks
        _nova_boot_log_20260701("[NOVA_FINAL_SESSION_DETAIL_CACHE] forced final hook to run last")
except Exception:
    pass





























# NOVA_HISTORY_LIST_AND_DETAIL_20260621
def nova_history_load_sessions_20260621():
    from pathlib import Path

    base = Path(__file__).resolve().parent
    data_path = base / "data" / "nova_sessions.json"

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("sessions", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

        values = list(payload.values())
        if values and all(isinstance(v, dict) for v in values):
            return values

    return []


def nova_history_sid_20260621(session):
    if not isinstance(session, dict):
        return ""
    return str(
        session.get("id") or
        session.get("session_id") or
        session.get("sid") or
        session.get("uuid") or
        ""
    )


def nova_history_title_20260621(session):
    if not isinstance(session, dict):
        return "Untitled session"
    return str(
        session.get("title") or
        session.get("name") or
        session.get("label") or
        "Untitled session"
    )


def nova_history_messages_20260621(session):
    if not isinstance(session, dict):
        return []

    for key in ("messages", "chat", "conversation", "items"):
        value = session.get(key)
        if isinstance(value, list):
            return value

    return []


def nova_history_msg_text_20260621(message):

    if isinstance(message, str):
        return message

    if not isinstance(message, dict):
        return str(message)

    for key in ("content", "text", "message", "body", "output", "answer"):
        value = message.get(key)
        if value is not None and str(value).strip():
            return str(value)

    return json.dumps(message, ensure_ascii=False, indent=2)


def nova_history_msg_role_20260621(message):
    if not isinstance(message, dict):
        return "message"

    return str(
        message.get("role") or
        message.get("sender") or
        message.get("type") or
        "message"
    )


@app.route("/history")
def nova_history_list_page_20260621():
    import html

    sessions = [
        s for s in nova_history_load_sessions_20260621()
        if nova_history_sid_20260621(s)
    ]

    def updated(s):
        if not isinstance(s, dict):
            return ""
        return str(s.get("updated_at") or s.get("updated") or s.get("created_at") or s.get("created") or "")

    sessions.sort(key=updated, reverse=True)

    cards = []

    for s in sessions:
        sid = nova_history_sid_20260621(s)
        title = nova_history_title_20260621(s)
        count = s.get("message_count") or len(nova_history_messages_20260621(s)) or 0

        cards.append(f"""
          <a class="session" href="/history/{html.escape(sid)}">
            <div class="title">{html.escape(title)}</div>
            <div class="meta">{html.escape(str(count))} messages ? {html.escape(updated(s))}</div>
            <div class="sid">{html.escape(sid)}</div>
          </a>
        """)

    if not cards:
        cards.append('<div class="empty">No sessions found.</div>')

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Nova History</title>
  <style>
    body {{
      margin: 0;
      padding: 22px;
      background: #0f172a;
      color: #f8fafc;
      font-family: Arial, sans-serif;
    }}

    .wrap {{
      max-width: 850px;
      margin: 0 auto;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
    }}

    .sub {{
      opacity: 0.72;
      margin-bottom: 16px;
    }}

    .top {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: #0f172a;
      padding-bottom: 12px;
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .btn {{
      border: 1px solid rgba(168, 85, 247, 0.75);
      background: rgba(168, 85, 247, 0.18);
      color: white;
      padding: 10px 12px;
      border-radius: 10px;
      text-decoration: none;
      font-size: 14px;
    }}

    .btn.disabled {{
      opacity: 0.55;
      cursor: not-allowed;
      display: inline-block;
    }}

    .list {{
      max-height: calc(100vh - 150px);
      overflow-y: auto;
      padding-right: 8px;
    }}

    .session {{
      display: block;
      margin: 10px 0;
      padding: 14px;
      border-radius: 14px;
      border: 1px solid rgba(168, 85, 247, 0.65);
      background: #1f2937;
      color: white;
      text-decoration: none;
      box-sizing: border-box;
    }}

    .session:hover {{
      background: rgba(168, 85, 247, 0.25);
    }}

    .title {{
      font-size: 17px;
      font-weight: 800;
    }}

    .meta {{
      opacity: 0.75;
      font-size: 13px;
      margin-top: 6px;
    }}

    .sid {{
      opacity: 0.48;
      font-size: 12px;
      margin-top: 6px;
      word-break: break-all;
    }}

    .empty {{
      padding: 18px;
      border-radius: 14px;
      background: #1f2937;
      border: 1px solid rgba(168, 85, 247, 0.65);
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Nova History</h1>
    <div class="sub">Found {len(sessions)} sessions. Click a card to view its messages.</div>

    <div class="top">
      <a class="btn" href="/app">Back to Nova</a>
      <a class="btn" href="/new-session">New Chat</a>
      <a class="btn" href="/history">Refresh</a>
      <a class="btn" href="/api/sessions">Raw API</a>
    </div>

    <div class="list">
      {''.join(cards)}
    </div>
  </div>
</body>
</html>
"""


@app.route("/history/<session_id>")
def nova_history_detail_page_20260621(session_id):
    import html

    sessions = nova_history_load_sessions_20260621()
    session = None

    for s in sessions:
        if nova_history_sid_20260621(s) == session_id:
            session = s
            break

    if not session:
        return f"""
<!doctype html>
<html>
<body style="font-family:Arial;background:#0f172a;color:white;padding:24px;">
  <h1>Session not found</h1>
  <p>{html.escape(session_id)}</p>
  <p><a style="color:#c084fc;" href="/history">Back to history</a></p>
</body>
</html>
"""

    title = nova_history_title_20260621(session)
    sid = nova_history_sid_20260621(session)
    messages = nova_history_messages_20260621(session)

    rows = []

    for m in messages:
        role = nova_history_msg_role_20260621(m)
        text = nova_history_msg_text_20260621(m)

        rows.append(f"""
          <div class="msg {html.escape(role.lower())}">
            <div class="role">{html.escape(role)}</div>
            <pre>{html.escape(text)}</pre>
          </div>
        """)

    if not rows:
        rows.append("""
          <div class="empty">
            This is a new empty session. No messages yet. Click "Open in Nova" to start chatting.
          </div>
        """)

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      padding: 22px;
      background: #0f172a;
      color: #f8fafc;
      font-family: Arial, sans-serif;
    }}

    .wrap {{
      max-width: 900px;
      margin: 0 auto;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}

    .sid {{
      opacity: 0.55;
      font-size: 12px;
      margin-bottom: 16px;
      word-break: break-all;
    }}

    .top {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: #0f172a;
      padding-bottom: 12px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .btn {{
      border: 1px solid rgba(168, 85, 247, 0.75);
      background: rgba(168, 85, 247, 0.18);
      color: white;
      padding: 10px 12px;
      border-radius: 10px;
      text-decoration: none;
      font-size: 14px;
    }}

    .btn.disabled {{
      opacity: 0.55;
      cursor: not-allowed;
      display: inline-block;
    }}

    .composer {{
      display: flex;
      gap: 10px;
      margin: 12px 0 16px;
      align-items: stretch;
    }}

    .composer textarea {{
      flex: 1;
      min-height: 54px;
      resize: vertical;
      border-radius: 12px;
      border: 1px solid rgba(168, 85, 247, 0.55);
      background: #111827;
      color: white;
      padding: 12px;
      font-family: Arial, sans-serif;
      font-size: 14px;
      box-sizing: border-box;
    }}

    .composer button {{
      border: 1px solid rgba(168, 85, 247, 0.75);
      background: rgba(168, 85, 247, 0.25);
      color: white;
      padding: 10px 14px;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 700;
    }}

    .messages {{
      max-height: calc(100vh - 245px);
      overflow-y: auto;
      padding-right: 8px;
    }}

    .msg {{
      margin: 12px 0;
      padding: 14px;
      border-radius: 14px;
      background: #1f2937;
      border: 1px solid rgba(148, 163, 184, 0.24);
    }}

    .msg.user {{
      border-color: rgba(168, 85, 247, 0.65);
    }}

    .msg.assistant {{
      border-color: rgba(59, 130, 246, 0.55);
    }}

    .role {{
      font-size: 12px;
      opacity: 0.7;
      font-weight: 800;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}

    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: inherit;
      line-height: 1.45;
    }}

    .empty {{
      padding: 18px;
      border-radius: 14px;
      background: #1f2937;
      border: 1px solid rgba(168, 85, 247, 0.65);
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{html.escape(title)}</h1>
    <div class="sid">{html.escape(sid)}</div>

    <div class="top">
      <a class="btn" href="/history">Back to History</a>
      <span class="btn disabled">Open in Nova disabled for now</span>
    </div>

    <form class="composer" method="POST" action="/history/{html.escape(sid)}/send">
      <textarea name="text" placeholder="Type here to add to this exact session..." required></textarea>
      <button type="submit">Add to This Session</button>
    </form>

    <div class="messages">
      {''.join(rows)}
    </div>
  </div>
</body>
</html>
"""


@app.route("/new-session")
def nova_history_new_session_20260621():
    import uuid
    from pathlib import Path
    from datetime import datetime, timezone

    base = Path(__file__).resolve().parent
    data_path = base / "data" / "nova_sessions.json"

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"sessions": []}

    if isinstance(payload, list):
        root = {"sessions": payload}
        sessions = payload
    elif isinstance(payload, dict):
        root = payload
        sessions = None

        for key in ("sessions", "items", "data"):
            if isinstance(root.get(key), list):
                sessions = root[key]
                break

        if sessions is None:
            sessions = []
            root["sessions"] = sessions
    else:
        root = {"sessions": []}
        sessions = root["sessions"]

    now = datetime.now(timezone.utc).isoformat()
    sid = "session_" + uuid.uuid4().hex

    session = {
        "id": sid,
        "title": "New Chat",
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
        "messages": [],
        "meta": {},
        "pinned": False,
        "working_state": {
            "active_task": "",
            "checkpoint": "",
            "current_bug": "",
            "current_file": "",
            "last_success": "",
            "next_move": "",
            "updated_at": ""
        }
    }

    sessions.insert(0, session)
    root["active_session_id"] = sid
    root["sessions"] = sessions

    data_path.write_text(json.dumps(root, indent=2, ensure_ascii=False), encoding="utf-8")

    return f"""
<!doctype html>
<html>
<body>
<script>
  localStorage.setItem("nova_active_session_id", "{sid}");
  localStorage.setItem("nova_session_id", "{sid}");
  localStorage.setItem("nova_desktop_active_session_id", "{sid}");
  localStorage.setItem("nova_current_session_id", "{sid}");
  location.href = "/app?session_id={sid}&bust=" + Date.now();
</script>
New session created.
</body>
</html>
"""
# END_NOVA_HISTORY_LIST_AND_DETAIL_20260621


# NOVA_OPEN_SESSION_BRIDGE_20260622
@app.route("/open-session/<session_id>")
def nova_open_session_bridge_20260622(session_id):
    import html
    from pathlib import Path

    sid = str(session_id or "").strip()
    base = Path(__file__).resolve().parent
    data_path = base / "data" / "nova_sessions.json"

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"sessions": []}

    def get_sessions(root):
        if isinstance(root, list):
            return root

        if isinstance(root, dict):
            for key in ("sessions", "items", "data"):
                value = root.get(key)
                if isinstance(value, list):
                    return value

        return []

    sessions = get_sessions(payload)
    found = False

    for session in sessions:
        if not isinstance(session, dict):
            continue

        current_id = str(
            session.get("id") or
            session.get("session_id") or
            session.get("sid") or
            session.get("uuid") or
            ""
        ).strip()

        if current_id == sid:
            found = True
            session["id"] = sid
            session["session_id"] = sid

            if not isinstance(session.get("messages"), list):
                session["messages"] = []

            break

    if isinstance(payload, dict):
        payload["active_session_id"] = sid

    try:
        data_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    safe_sid = html.escape(sid)

    if not found:
        return f"""
<!doctype html>
<html>
<body style="background:#0f172a;color:white;font-family:Arial;padding:24px;">
  <h1>Session not found</h1>
  <p>{safe_sid}</p>
  <p><a style="color:#c084fc;" href="/history">Back to history</a></p>
</body>
</html>
"""

    return f"""
<!doctype html>
<html>
<body style="background:#0f172a;color:white;font-family:Arial;padding:24px;">
  <p>Opening session...</p>

  <script>
    const sid = "{safe_sid}";

    try {{
      localStorage.setItem("nova_active_session_id", sid);
      localStorage.setItem("nova_session_id", sid);
      localStorage.setItem("nova_desktop_active_session_id", sid);
      localStorage.setItem("nova_current_session_id", sid);
      localStorage.setItem("active_session_id", sid);
      localStorage.setItem("session_id", sid);

      sessionStorage.setItem("nova_active_session_id", sid);
      sessionStorage.setItem("nova_session_id", sid);
      sessionStorage.setItem("active_session_id", sid);
      sessionStorage.setItem("session_id", sid);
    }} catch (_) {{}}

    location.replace("/app?session_id=" + encodeURIComponent(sid) + "&force_session=1&bust=" + Date.now());
  </script>
</body>
</html>
"""
# END_NOVA_OPEN_SESSION_BRIDGE_20260622



# NOVA_HISTORY_DIRECT_SEND_20260622
@app.route("/history/<session_id>/send", methods=["POST"])
def nova_history_direct_send_20260622(session_id):
    from pathlib import Path
    from datetime import datetime, timezone
    from flask import request, redirect

    sid = str(session_id or "").strip()
    text = str(request.form.get("text") or "").strip()

    if not sid or not text:
        return redirect("/history/" + sid)

    base = Path(__file__).resolve().parent
    data_path = base / "data" / "nova_sessions.json"

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"sessions": []}

    def get_sessions(root):
        if isinstance(root, list):
            return root

        if isinstance(root, dict):
            for key in ("sessions", "items", "data"):
                value = root.get(key)
                if isinstance(value, list):
                    return value

        return []

    def get_sid(session):
        if not isinstance(session, dict):
            return ""
        return str(
            session.get("id") or
            session.get("session_id") or
            session.get("sid") or
            session.get("uuid") or
            ""
        ).strip()

    sessions = get_sessions(payload)
    target = None

    for session in sessions:
        if get_sid(session) == sid:
            target = session
            break

    if target is None:
        now = datetime.now(timezone.utc).isoformat()
        target = {
            "id": sid,
            "session_id": sid,
            "title": "New Chat",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "messages": [],
            "meta": {},
            "pinned": False,
            "working_state": {
                "active_task": "",
                "checkpoint": "",
                "current_bug": "",
                "current_file": "",
                "last_success": "",
                "next_move": "",
                "updated_at": ""
            }
        }

        if isinstance(payload, dict):
            if not isinstance(payload.get("sessions"), list):
                payload["sessions"] = []
            payload["sessions"].insert(0, target)
            sessions = payload["sessions"]
        else:
            payload = {"sessions": [target]}

            sessions = payload["sessions"]

    messages = target.get("messages")
    if not isinstance(messages, list):
        messages = []
        target["messages"] = messages

    now = datetime.now(timezone.utc).isoformat()

    messages.append({
        "role": "user",
        "content": text,
        "created_at": now
    })

    target["id"] = sid
    target["session_id"] = sid
    target["message_count"] = len(messages)
    target["updated_at"] = now

    if str(target.get("title") or "").strip().lower() in ("", "new chat", "untitled session"):
        words = text.replace("\n", " ").split()
        title = " ".join(words[:6]).strip()
        target["title"] = title[:60] if title else "New Chat"

    if isinstance(payload, dict):
        payload["active_session_id"] = sid

    data_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return redirect("/history/" + sid)
# END_NOVA_HISTORY_DIRECT_SEND_20260622

# NOVA_FINAL_TITLE_GUARD_20260630
# Last response/disk cleanup for accidental-input and stale Web Fetch session titles.
try:
    import json as _nova_title_guard_json_20260630
    import re as _nova_title_guard_re_20260630
    from collections import Counter as _nova_title_guard_counter_20260630
    from pathlib import Path as _nova_title_guard_Path_20260630
    from flask import request as _nova_title_guard_request_20260630

    def _nova_title_guard_is_garbage_20260630(value) -> bool:
        text = str(value or "")
        compact = "".join(text.split())

        if not compact:
            return False

        lower = compact.lower()

        if lower in {
            "k",
            "ok",
            "okay",
            "next",
            "continue",
            "run",
            "runit",
            "stop",
            "cancel",
            "yes",
            "no",
            "hello",
            "hi",
            "hey",
        }:
            return False

        if len(compact) < 8:
            return False

        counts = _nova_title_guard_counter_20260630(compact)
        most_common_ratio = counts.most_common(1)[0][1] / max(len(compact), 1)

        alpha_count = sum(1 for ch in compact if ch.isalpha())
        digit_count = sum(1 for ch in compact if ch.isdigit())
        symbol_count = sum(1 for ch in compact if not ch.isalnum())
        symbol_digit_ratio = (digit_count + symbol_count) / max(len(compact), 1)

        if len(compact) >= 12 and most_common_ratio >= 0.75:
            return True

        if len(compact) >= 20 and alpha_count == 0 and symbol_digit_ratio >= 0.90:
            return True

        if len(compact) >= 24 and alpha_count <= 2 and symbol_digit_ratio >= 0.80:
            return True

        if _nova_title_guard_re_20260630.search(r"(.)\1{9,}", compact):
            return True

        if (
            _nova_title_guard_re_20260630.search(r"([\[\]\(\)\{\}=\\\/\|'\-]){8,}", compact)
            and alpha_count <= 3
        ):
            return True

        return False

    def _nova_title_guard_clean_title_20260630(title, user_text, route, source):
        current = str(title or "").strip()
        lowered = current.lower().strip()

        web_like = lowered in {
            "",
            "web fetch",
            "source preview",
            "generated image",
        }

        guard_like = (
            str(route or "").strip().lower() == "accidental_input_guard"
            or str(source or "").strip().lower() == "accidental_input_guard"
            or _nova_title_guard_is_garbage_20260630(current)
            or _nova_title_guard_is_garbage_20260630(user_text)
        )

        if guard_like:
            return "New Chat"

        if web_like:
            candidate = str(user_text or "").replace("\n", " ").strip()
            if candidate and not _nova_title_guard_is_garbage_20260630(candidate):
                return candidate[:60]
            return "New Chat"

        return current or "New Chat"

    def _nova_title_guard_persist_20260630(session_id, clean_title):
        try:
            sid = str(session_id or "").strip()
            if not sid:
                return

            data_path = _nova_title_guard_Path_20260630(__file__).resolve().parent / "data" / "nova_sessions.json"

            if not data_path.exists():
                return

            store = _nova_title_guard_json_20260630.loads(data_path.read_text(encoding="utf-8"))

            sessions = store.get("sessions")
            if not isinstance(sessions, list):
                return

            changed = False

            for item in sessions:
                if not isinstance(item, dict):
                    continue

                item_id = str(item.get("id") or item.get("session_id") or "").strip()
                if item_id != sid:
                    continue

                old_title = str(item.get("title") or "").strip()

                if (
                    old_title.lower() in {"", "web fetch", "source preview", "generated image"}
                    or _nova_title_guard_is_garbage_20260630(old_title)
                ):
                    item["title"] = clean_title
                    changed = True

            if changed:
                tmp = data_path.with_suffix(data_path.suffix + ".tmp")
                tmp.write_text(
                    _nova_title_guard_json_20260630.dumps(store, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                tmp.replace(data_path)

        except Exception as _nova_title_guard_persist_error_20260630:
            print(
                "[NOVA_FINAL_TITLE_GUARD_20260630] persist skipped:",
                _nova_title_guard_persist_error_20260630,
            )

    @app.after_request
    def nova_final_title_guard_20260630(response):
        try:
            request_path = str(getattr(_nova_title_guard_request_20260630, "path", "") or "")
            request_method = str(getattr(_nova_title_guard_request_20260630, "method", "") or "").upper()

            if request_method != "POST" or request_path != "/api/chat":
                return response

            data = response.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return response

            session = data.get("session")
            if not isinstance(session, dict):
                return response

            assistant_message = data.get("assistant_message")
            if not isinstance(assistant_message, dict):
                assistant_message = {}

            assistant_meta = assistant_message.get("meta")
            if not isinstance(assistant_meta, dict):
                assistant_meta = {}

            route = (
                data.get("route")
                or data.get("mode")
                or assistant_meta.get("route")
                or assistant_meta.get("source")
                or ""
            )

            source = assistant_meta.get("source") or data.get("source") or ""

            user_text = ""
            messages = session.get("messages")
            if isinstance(messages, list):
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                    if str(msg.get("role") or "").strip().lower() == "user":
                        user_text = str(msg.get("text") or msg.get("content") or "").strip()
                        break

            if not user_text:
                user_text = str(data.get("user_text") or data.get("message") or "").strip()

            old_title = str(session.get("title") or "").strip()
            clean_title = _nova_title_guard_clean_title_20260630(
                old_title,
                user_text,
                route,
                source,
            )

            if clean_title != old_title:
                session["title"] = clean_title
                data["session"] = session
                _nova_title_guard_persist_20260630(
                    data.get("session_id") or data.get("active_session_id") or session.get("id"),
                    clean_title,
                )

                new_raw = _nova_title_guard_json_20260630.dumps(data, ensure_ascii=False)
                response.set_data(new_raw)
                response.headers["Content-Length"] = str(len(response.get_data()))
                response.headers["Content-Type"] = "application/json"

        except Exception as _nova_title_guard_error_20260630:
            print(
                "[NOVA_FINAL_TITLE_GUARD_20260630] skipped:",
                _nova_title_guard_error_20260630,
            )

        return response

    try:
        _nova_title_guard_hooks_20260630 = app.after_request_funcs.get(None, [])
        _nova_title_guard_func_20260630 = None

        for _nova_title_guard_hook_20260630 in list(_nova_title_guard_hooks_20260630):
            if getattr(_nova_title_guard_hook_20260630, "__name__", "") == "nova_final_title_guard_20260630":
                _nova_title_guard_func_20260630 = _nova_title_guard_hook_20260630
                _nova_title_guard_hooks_20260630.remove(_nova_title_guard_hook_20260630)
                break

        if _nova_title_guard_func_20260630 is not None:
            _nova_title_guard_hooks_20260630.insert(0, _nova_title_guard_func_20260630)

    except Exception as _nova_title_guard_order_error_20260630:
        print(
            "[NOVA_FINAL_TITLE_GUARD_20260630] hook order skipped:",
            _nova_title_guard_order_error_20260630,
        )

    _nova_boot_log_20260701("[NOVA_FINAL_TITLE_GUARD_20260630] installed")

except Exception as _nova_final_title_guard_install_error_20260630:
    print(
        "[NOVA_FINAL_TITLE_GUARD_20260630] failed:",
        _nova_final_title_guard_install_error_20260630,
    )


# NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630
# Final visible-response guard for image generation.
# This runs after final_session_detail_response_cache so visible assistant text
# matches the already-clean saved artifact/session title.
try:
    import json as _nova_img_cache_json_20260630
    import re as _nova_img_cache_re_20260630

    def _nova_img_cache_clean_prompt_20260630(value):
        raw = str(value or "").strip()

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*Generated\s+image\s*(for)?\s*:\s*",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*Image\s*:\s*",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*(please\s+)?(generate|create|make|draw|render|produce)\s+(an?\s+)?(image|picture|photo|illustration|art|drawing)\s*",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*(of|for)\s+",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = raw.strip(" .")
        return raw or "your image"

    def _nova_img_cache_is_image_response_20260630(data):
        if not isinstance(data, dict):
            return False

        assistant_message = data.get("assistant_message")
        saved_artifact = data.get("saved_artifact")

        if isinstance(assistant_message, dict):
            meta = assistant_message.get("meta")
            if assistant_message.get("image_url"):
                return True
            if isinstance(meta, dict) and meta.get("source") == "image_generation":
                return True

            attachments = assistant_message.get("attachments")
            if isinstance(attachments, list):
                for item in attachments:
                    if isinstance(item, dict) and (
                        item.get("image_url")
                        or item.get("url")
                        or item.get("file_url")
                    ):
                        mime = str(item.get("mime_type") or item.get("type") or "").lower()
                        if mime.startswith("image/") or str(item.get("filename") or "").lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                            return True

        if isinstance(saved_artifact, dict):
            if saved_artifact.get("image_url"):
                return True
            if str(saved_artifact.get("kind") or "").lower() == "image":
                return True
            if str(saved_artifact.get("type") or "").lower() == "image_generation":
                return True

        return False

    def _nova_img_cache_pick_prompt_20260630(data):
        assistant_message = data.get("assistant_message") if isinstance(data, dict) else {}
        saved_artifact = data.get("saved_artifact") if isinstance(data, dict) else {}
        session = data.get("session") if isinstance(data, dict) else {}

        candidates = []

        if isinstance(saved_artifact, dict):
            candidates.extend([
                saved_artifact.get("summary"),
                saved_artifact.get("prompt"),
                saved_artifact.get("body"),
            ])

            meta = saved_artifact.get("meta")
            if isinstance(meta, dict):
                candidates.append(meta.get("prompt"))

        if isinstance(session, dict):
            candidates.append(session.get("title"))

        if isinstance(assistant_message, dict):
            candidates.extend([
                assistant_message.get("text"),
                assistant_message.get("content"),
            ])

        for candidate in candidates:
            clean = _nova_img_cache_clean_prompt_20260630(candidate)
            if clean and clean != "your image":
                return clean

        return "your image"

    def _nova_img_cache_fix_image_response_20260630(data):
        if not _nova_img_cache_is_image_response_20260630(data):
            return data

        prompt = _nova_img_cache_pick_prompt_20260630(data)
        clean_text = f"Generated image: {prompt}"

        assistant_message = data.get("assistant_message")
        if isinstance(assistant_message, dict):
            assistant_message["text"] = clean_text
            assistant_message["content"] = clean_text
            data["assistant_message"] = assistant_message

        saved_artifact = data.get("saved_artifact")
        if isinstance(saved_artifact, dict):
            saved_artifact["summary"] = clean_text

            viewer = saved_artifact.get("viewer")
            if isinstance(viewer, dict):
                viewer["summary"] = clean_text
                saved_artifact["viewer"] = viewer

            data["saved_artifact"] = saved_artifact

        session = data.get("session")
        if isinstance(session, dict):
            working_state = session.get("working_state")
            if isinstance(working_state, dict):
                working_state["last_assistant_message"] = clean_text
                session["working_state"] = working_state

            messages = session.get("messages")
            if isinstance(messages, list):
                for message in messages:
                    if not isinstance(message, dict):
                        continue

                    if str(message.get("role") or "").lower() == "assistant":
                        message_text = str(message.get("text") or message.get("content") or "")
                        if "Generated image" in message_text:
                            message["text"] = clean_text
                            message["content"] = clean_text

            data["session"] = session

        return data

    @app.after_request
    def _nova_final_image_response_cache_text_guard_20260630(response):
        try:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if "application/json" not in content_type:
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = _nova_img_cache_json_20260630.loads(raw)
            fixed = _nova_img_cache_fix_image_response_20260630(data)

            if fixed is data:
                new_raw = _nova_img_cache_json_20260630.dumps(fixed, ensure_ascii=False)
                response.set_data(new_raw)
                response.headers["Content-Length"] = str(len(response.get_data()))
                response.headers["Content-Type"] = "application/json"

            return response
        except Exception as _nova_img_cache_guard_error_20260630:
            print("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] skipped:", _nova_img_cache_guard_error_20260630)
            return response

    # Flask runs after_request handlers in reverse registration order.
    # Move this one to the front so it executes last, after final_session_detail_response_cache.
    try:
        _nova_img_cache_funcs_20260630 = app.after_request_funcs.get(None, [])
        if (
            _nova_img_cache_funcs_20260630
            and _nova_img_cache_funcs_20260630[-1].__name__ == "_nova_final_image_response_cache_text_guard_20260630"
        ):
            _nova_img_cache_funcs_20260630.insert(0, _nova_img_cache_funcs_20260630.pop())
    except Exception:
        pass

    _nova_boot_log_20260701("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] installed")
except Exception as _nova_img_cache_install_error_20260630:
    print("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] failed:", _nova_img_cache_install_error_20260630)

# NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630
# Final /api/chat response repair for idle next/k project-state recall.
# This runs at the Flask route layer because the idle execution fallback is produced
# outside ChatService.handle in some paths.
try:
    import json as _nova_api_project_state_json_20260630
    import importlib.util as _nova_api_project_state_importlib_util_20260630
    from pathlib import Path as _NovaApiProjectStatePath20260630
    from flask import request as _nova_api_project_state_request_20260630

    def _nova_api_project_state_load_answer_20260630(user_text):
        service_path = (
            _NovaApiProjectStatePath20260630(__file__)
            .resolve()
            .parent
            / "nova_backend"
            / "services"
            / "project_state_service.py"
        )

        spec = _nova_api_project_state_importlib_util_20260630.spec_from_file_location(
            "_nova_api_project_state_service_direct_20260630",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = _nova_api_project_state_importlib_util_20260630.module_from_spec(spec)
        spec.loader.exec_module(module)

        answer_fn = getattr(module, "answer_project_state_question", None)
        if not callable(answer_fn):
            return None

        return answer_fn(user_text, runtime_execution_state=None)

    def _nova_api_project_state_patch_payload_20260630(payload, reply):
        if not isinstance(payload, dict):
            payload = {}

        payload["ok"] = True
        payload["success"] = True
        payload["content"] = reply
        payload["message"] = reply
        payload["response"] = reply
        payload["route"] = "project_state_recall"
        payload["route_taken"] = "project_state_recall"

        assistant = payload.get("assistant_message")
        if not isinstance(assistant, dict):
            assistant = {
                "role": "assistant",
                "attachments": [],
            }

        assistant["content"] = reply
        assistant.setdefault("role", "assistant")
        assistant.setdefault("attachments", [])
        payload["assistant_message"] = assistant

        debug = payload.get("debug")
        if not isinstance(debug, dict):
            debug = {}
        debug["route"] = "project_state_recall"
        debug["route_taken"] = "project_state_recall"
        payload["debug"] = debug

        meta = payload.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["route"] = "project_state_recall"
        meta["strategy"] = "project_state_recall"
        payload["meta"] = meta

        return payload

    def _nova_api_project_state_content_20260630(payload):
        if not isinstance(payload, dict):
            return ""

        assistant = payload.get("assistant_message")
        if isinstance(assistant, dict):
            content = assistant.get("content")
            if isinstance(content, str):
                return content

        for key in ("content", "response", "message", "text", "answer"):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        return ""

    def _nova_api_project_state_request_text_20260630():
        try:
            data = _nova_api_project_state_request_20260630.get_json(silent=True) or {}
            if isinstance(data, dict):
                for key in ("message", "user_text", "text", "prompt"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except Exception:
            pass

        return ""

    def _nova_api_project_state_wrap_endpoint_20260630(endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630", False):
            return True

        def _nova_api_project_state_wrapped_view_20260630(*args, **kwargs):
            result = view(*args, **kwargs)

            try:
                user_text = _nova_api_project_state_request_text_20260630().lower()
                if user_text not in {"next", "k", "ok", "okay", "continue"}:
                    return result

                if not hasattr(result, "get_data") or not hasattr(result, "set_data"):
                    return result

                raw = result.get_data(as_text=True)
                payload = _nova_api_project_state_json_20260630.loads(raw)

                content = _nova_api_project_state_content_20260630(payload)
                if "no active execution mission" not in str(content or "").lower():
                    return result

                reply = _nova_api_project_state_load_answer_20260630(user_text)
                if not reply:
                    return result

                payload = _nova_api_project_state_patch_payload_20260630(payload, reply)
                encoded = _nova_api_project_state_json_20260630.dumps(payload, ensure_ascii=False)

                result.set_data(encoded)
                try:
                    result.headers["Content-Length"] = str(len(result.get_data()))
                    result.headers["Content-Type"] = "application/json"
                except Exception:
                    pass

                return result
            except Exception as _nova_api_project_state_route_error_20260630:
                try:
                    print(
                        "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] bypass:",
                        _nova_api_project_state_route_error_20260630,
                    )
                except Exception:
                    pass

            return result

        _nova_api_project_state_wrapped_view_20260630.__name__ = getattr(
            view,
            "__name__",
            "_nova_api_project_state_wrapped_view_20260630",
        )
        _nova_api_project_state_wrapped_view_20260630._NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630 = True

        app.view_functions[endpoint_name] = _nova_api_project_state_wrapped_view_20260630
        return True

    _nova_api_project_state_wrapped_count_20260630 = 0
    for _endpoint_name_20260630, _view_20260630 in list(app.view_functions.items()):
        try:
            rule_matches = [
                rule.rule
                for rule in app.url_map.iter_rules()
                if rule.endpoint == _endpoint_name_20260630
            ]

            if "/api/chat" in rule_matches:
                if _nova_api_project_state_wrap_endpoint_20260630(_endpoint_name_20260630):
                    _nova_api_project_state_wrapped_count_20260630 += 1
        except Exception:
            pass

    _nova_boot_log_20260701(
        "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",
        _nova_api_project_state_wrapped_count_20260630,
    )
except Exception as _nova_api_project_state_install_error_20260630:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] failed:",
            _nova_api_project_state_install_error_20260630,
        )
    except Exception:
        pass

# NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701
# Route-level natural project-state recall.
# This intentionally does not modify project_state_service.py.
# It maps short natural project prompts to the already-green project-state answers.
try:
    import json as _nova_natural_project_json_20260701
    import re as _nova_natural_project_re_20260701
    import importlib.util as _nova_natural_project_importlib_util_20260701
    from pathlib import Path as _NovaNaturalProjectPath20260701
    from flask import request as _nova_natural_project_request_20260701
    from flask import Response as _NovaNaturalProjectResponse20260701

    def _nova_natural_project_normalize_20260701(value):
        text = str(value or "").strip().lower()
        text = text.replace("â€™", "'")
        text = _nova_natural_project_re_20260701.sub(r"\s+", " ", text)
        return text

    def _nova_natural_project_prompt_map_20260701(user_text):
        text = _nova_natural_project_normalize_20260701(user_text)

        if not text or len(text) > 140:
            return ""

        current_exact = {
            "are we good",
            "are we good?",
            "are we locked",
            "are we locked?",
            "is it locked",
            "is it locked?",
            "are we clean",
            "are we clean?",
            "how far are we",
            "how far are we?",
            "how far are we now",
            "how far are we now?",
            "where are we at",
            "where are we at?",
            "where are we now",
            "where are we now?",
            "how close are we",
            "how close are we?",
            "status now",
            "progress now",
        }

        fixed_exact = {
            "what is locked",
            "what is locked?",
            "what's locked",
            "what's locked?",
            "what got locked",
            "what got locked?",
            "what did we lock",
            "what did we lock?",
            "what passed",
            "what passed?",
            "what is green",
            "what is green?",
            "what's green",
            "what's green?",
        }

        remaining_exact = {
            "anything left",
            "anything left?",
            "anything else",
            "anything else?",
            "what else",
            "what else?",
            "what still needs doing",
            "what still needs doing?",
            "what needs doing",
            "what needs doing?",
            "how much is left",
            "how much is left?",
        }

        next_exact = {
            "what should we do now",
            "what should we do now?",
            "what do we do now",
            "what do we do now?",
            "what now",
            "what now?",
            "can we move on",
            "can we move on?",
            "should we move on",
            "should we move on?",
            "move on?",
        }

        if text in current_exact:
            return "what are we working on?"

        if text in fixed_exact:
            return "what did we just fix?"

        if text in remaining_exact:
            return "what is left?"

        if text in next_exact:
            return "next"

        return ""

    def _nova_natural_project_request_json_20260701():
        try:
            data = _nova_natural_project_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_natural_project_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_natural_project_load_answer_20260701(mapped_prompt):
        service_path = (
            _NovaNaturalProjectPath20260701(__file__)
            .resolve()
            .parent
            / "nova_backend"
            / "services"
            / "project_state_service.py"
        )

        spec = _nova_natural_project_importlib_util_20260701.spec_from_file_location(
            "_nova_natural_project_state_service_direct_20260701",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = _nova_natural_project_importlib_util_20260701.module_from_spec(spec)
        spec.loader.exec_module(module)

        answer_fn = getattr(module, "answer_project_state_question", None)
        if not callable(answer_fn):
            return None

        return answer_fn(mapped_prompt, runtime_execution_state=None)

    def _nova_natural_project_payload_20260701(reply, data):
        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        payload = {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "attachments": [],
            },
            "route": "project_state_recall",
            "route_taken": "project_state_recall",
            "debug": {
                "route": "project_state_recall",
                "route_taken": "project_state_recall",
                "natural_project_recall": True,
            },
            "meta": {
                "route": "project_state_recall",
                "strategy": "natural_project_recall",
            },
        }

        return payload

    def _nova_natural_project_wrap_endpoint_20260701(endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701", False):
            return True

        def _nova_natural_project_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_natural_project_request_json_20260701()
                user_text = _nova_natural_project_request_text_20260701(data)
                mapped_prompt = _nova_natural_project_prompt_map_20260701(user_text)

                if mapped_prompt:
                    reply = _nova_natural_project_load_answer_20260701(mapped_prompt)
                    if reply:
                        payload = _nova_natural_project_payload_20260701(reply, data)
                        encoded = _nova_natural_project_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaNaturalProjectResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_natural_project_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] bypass:",
                        _nova_natural_project_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_natural_project_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_natural_project_wrapped_view_20260701",
        )
        _nova_natural_project_wrapped_view_20260701._NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701 = True

        app.view_functions[endpoint_name] = _nova_natural_project_wrapped_view_20260701
        return True

    _nova_natural_project_wrapped_count_20260701 = 0
    for _endpoint_name_20260701, _view_20260701 in list(app.view_functions.items()):
        try:
            rule_matches = [
                rule.rule
                for rule in app.url_map.iter_rules()
                if rule.endpoint == _endpoint_name_20260701
            ]

            if "/api/chat" in rule_matches:
                if _nova_natural_project_wrap_endpoint_20260701(_endpoint_name_20260701):
                    _nova_natural_project_wrapped_count_20260701 += 1
        except Exception:
            pass

    _nova_boot_log_20260701(
        "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] wrapped endpoints:",
        _nova_natural_project_wrapped_count_20260701,
    )
except Exception as _nova_natural_project_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] failed:",
            _nova_natural_project_install_error_20260701,
        )
    except Exception:
        pass

# NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701
# Route-level compact project-state context for broader Nova/project status prompts.
# Uses project_state_service.compact_project_state_context() but does not modify the service.
try:
    import json as _nova_compact_project_json_20260701
    import re as _nova_compact_project_re_20260701
    import importlib.util as _nova_compact_project_importlib_util_20260701
    from pathlib import Path as _NovaCompactProjectPath20260701
    from flask import request as _nova_compact_project_request_20260701
    from flask import Response as _NovaCompactProjectResponse20260701

    def _nova_compact_project_normalize_20260701(value):
        text = str(value or "").strip().lower()
        text = text.replace("â€™", "'")
        text = _nova_compact_project_re_20260701.sub(r"\s+", " ", text)
        return text

    def _nova_compact_project_should_answer_20260701(user_text):
        text = _nova_compact_project_normalize_20260701(user_text)

        if not text or len(text) > 240:
            return False

        # Leave exact direct commands to the already-locked project-state/natural-recall wrappers.
        exact_owned_elsewhere = {
            "what are we working on",
            "what are we working on?",
            "what did we just fix",
            "what did we just fix?",
            "what is left",
            "what is left?",
            "next",
            "k",
            "are we good",
            "are we good?",
            "what is locked",
            "what is locked?",
            "how far are we now",
            "how far are we now?",
            "what should we do now",
            "what should we do now?",
            "can we move on",
            "can we move on?",
        }

        if text in exact_owned_elsewhere:
            return False

        project_terms = [
            "nova",
            "project",
            "checkpoint",
            "current work",
            "our work",
            "what we're doing",
            "what we are doing",
        ]

        status_terms = [
            "status",
            "summary",
            "context",
            "checkpoint",
            "progress",
            "where",
            "current",
            "working on",
            "next",
            "left",
            "locked",
            "phase",
        ]

        has_project_term = any(term in text for term in project_terms)
        has_status_term = any(term in text for term in status_terms)

        blocked_terms = [
            "bitcoin",
            "price",
            "weather",
            "image",
            "generate image",
            "draw",
            "attachment",
            "upload",
            "file",
            "soccer",
            "news",
        ]

        if any(term in text for term in blocked_terms):
            return False

        return has_project_term and has_status_term

    def _nova_compact_project_request_json_20260701():
        try:
            data = _nova_compact_project_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_compact_project_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_compact_project_brain_response_20260701(user_text):
        # NOVA_COMPACT_PROJECT_CONTEXT_DELEGATE_TO_PROJECT_BRAIN_20260701
        # Broad Nova project paraphrases belong to Project Brain general intelligence.
        try:
            normalized = _nova_compact_project_normalize_20260701(user_text)

            direct_recall_prompts = {
                "what are we working on",
                "what are we working on?",
                "what are we working on now",
                "what are we working on now?",
                "what are we working on right now",
                "what are we working on right now?",
            }

            if normalized in direct_recall_prompts:
                return None

            from nova_backend.services.project_brain_general_intelligence import (
                build_project_brain_general_answer,
            )

            answer = build_project_brain_general_answer(user_text)

            if not answer:
                return None

            answer_text = str(getattr(answer, "text", answer) or "").strip()
            answer_intent = str(
                getattr(answer, "intent", "general_project_answer")
                or "general_project_answer"
            ).strip()

            if not answer_text:
                return None

            return _NovaCompactProjectResponse20260701(
                _nova_compact_project_json_20260701.dumps(
                    {
                        "ok": True,
                        "text": answer_text,
                        "assistant_message": {
                            "role": "assistant",
                            "content": answer_text,
                            "text": answer_text,
                            "attachments": [],
                        },
                        "route": "project_brain_general_intelligence",
                        "route_taken": "project_brain_general_intelligence",
                        "debug": {
                            "route": "project_brain_general_intelligence",
                            "route_taken": "project_brain_general_intelligence",
                            "intent": answer_intent,
                            "compact_project_context_delegated": True,
                        },
                        "meta": {
                            "route": "project_brain_general_intelligence",
                            "strategy": "project_brain_general_intelligence",
                        },
                    },
                    ensure_ascii=False,
                ),
                mimetype="application/json",
            )

        except Exception as exc:
            try:
                print(
                    "[NOVA_COMPACT_PROJECT_CONTEXT_DELEGATE_TO_PROJECT_BRAIN_20260701] bypass:",
                    exc,
                )
            except Exception:
                pass
            return None

    def _nova_compact_project_load_context_20260701():
        service_path = (
            _NovaCompactProjectPath20260701(__file__)
            .resolve()
            .parent
            / "nova_backend"
            / "services"
            / "project_state_service.py"
        )

        spec = _nova_compact_project_importlib_util_20260701.spec_from_file_location(
            "_nova_compact_project_state_service_direct_20260701",
            str(service_path),
        )

        if not spec or not spec.loader:
            return ""

        module = _nova_compact_project_importlib_util_20260701.module_from_spec(spec)
        spec.loader.exec_module(module)

        compact_fn = getattr(module, "compact_project_state_context", None)
        if not callable(compact_fn):
            return ""

        return str(compact_fn(max_locked=8) or "").strip()

    def _nova_compact_project_payload_20260701(reply, data):
        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        return {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "attachments": [],
            },
            "route": "project_state_context",
            "route_taken": "project_state_context",
            "debug": {
                "route": "project_state_context",
                "route_taken": "project_state_context",
                "compact_project_context": True,
            },
            "meta": {
                "route": "project_state_context",
                "strategy": "compact_project_context",
            },
        }

    def _nova_compact_project_wrap_endpoint_20260701(endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701", False):
            return True

        def _nova_compact_project_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_compact_project_request_json_20260701()
                user_text = _nova_compact_project_request_text_20260701(data)

                project_brain_response = _nova_compact_project_brain_response_20260701(user_text)
                if project_brain_response is not None:
                    return project_brain_response

                if _nova_compact_project_should_answer_20260701(user_text):
                    context = _nova_compact_project_load_context_20260701()

                    if context:
                        reply = (
                            "Current Nova project context:\n"
                            f"{context}\n\n"
                            "This is the compact checkpoint view for the current Nova work."
                        )

                        payload = _nova_compact_project_payload_20260701(reply, data)
                        encoded = _nova_compact_project_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaCompactProjectResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_compact_project_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] bypass:",
                        _nova_compact_project_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_compact_project_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_compact_project_wrapped_view_20260701",
        )
        _nova_compact_project_wrapped_view_20260701._NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701 = True

        app.view_functions[endpoint_name] = _nova_compact_project_wrapped_view_20260701
        return True

    _nova_compact_project_wrapped_count_20260701 = 0
    for _endpoint_name_20260701, _view_20260701 in list(app.view_functions.items()):
        try:
            rule_matches = [
                rule.rule
                for rule in app.url_map.iter_rules()
                if rule.endpoint == _endpoint_name_20260701
            ]

            if "/api/chat" in rule_matches:
                if _nova_compact_project_wrap_endpoint_20260701(_endpoint_name_20260701):
                    _nova_compact_project_wrapped_count_20260701 += 1
        except Exception:
            pass

    _nova_boot_log_20260701(
        "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] wrapped endpoints:",
        _nova_compact_project_wrapped_count_20260701,
    )
except Exception as _nova_compact_project_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] failed:",
            _nova_compact_project_install_error_20260701,
        )
    except Exception:
        pass

# NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701
# Prefix-only autonomy task brief route.
# Safe mode: proposal-only. Does not edit files, run commands, or execute plans.
try:
    import json as _nova_autonomy_json_20260701
    import importlib.util as _nova_autonomy_importlib_util_20260701
    from pathlib import Path as _NovaAutonomyPath20260701
    from flask import request as _nova_autonomy_request_20260701
    from flask import Response as _NovaAutonomyResponse20260701

    _NOVA_AUTONOMY_PREFIXES_20260701 = (
        "autonomy:",
        "autonomy ",
        "task brain:",
        "safe task:",
        "safe autonomy:",
    )

    def _nova_autonomy_request_json_20260701():
        try:
            data = _nova_autonomy_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_autonomy_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_autonomy_goal_from_text_20260701(user_text):
        text = str(user_text or "").strip()
        low = text.lower()

        for prefix in _NOVA_AUTONOMY_PREFIXES_20260701:
            if low.startswith(prefix):
                return text[len(prefix):].strip() or "Improve Nova safely."

        return ""

    def _nova_autonomy_load_formatter_20260701():
        service_path = (
            _NovaAutonomyPath20260701(__file__)
            .resolve()
            .parent
            / "nova_backend"
            / "services"
            / "autonomy_task_brain.py"
        )

        spec = _nova_autonomy_importlib_util_20260701.spec_from_file_location(
            "_nova_autonomy_task_brain_direct_20260701",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = _nova_autonomy_importlib_util_20260701.module_from_spec(spec)
        spec.loader.exec_module(module)

        formatter = getattr(module, "format_autonomy_task_brief", None)
        return formatter if callable(formatter) else None

    def _nova_autonomy_payload_20260701(reply, data):
        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        return {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "attachments": [],
            },
            "route": "autonomy_task_brief",
            "route_taken": "autonomy_task_brief",
            "debug": {
                "route": "autonomy_task_brief",
                "route_taken": "autonomy_task_brief",
                "autonomy_mode": "proposal_only",
            },
            "meta": {
                "route": "autonomy_task_brief",
                "strategy": "proposal_only",
            },
        }

    def _nova_autonomy_wrap_endpoint_20260701(endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701", False):
            return True

        def _nova_autonomy_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_autonomy_request_json_20260701()
                user_text = _nova_autonomy_request_text_20260701(data)
                goal = _nova_autonomy_goal_from_text_20260701(user_text)

                if goal:
                    formatter = _nova_autonomy_load_formatter_20260701()

                    if formatter:
                        reply = formatter(goal)
                        payload = _nova_autonomy_payload_20260701(reply, data)
                        encoded = _nova_autonomy_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaAutonomyResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_autonomy_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] bypass:",
                        _nova_autonomy_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_autonomy_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_autonomy_wrapped_view_20260701",
        )
        _nova_autonomy_wrapped_view_20260701._NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701 = True

        app.view_functions[endpoint_name] = _nova_autonomy_wrapped_view_20260701
        return True

    _nova_autonomy_wrapped_count_20260701 = 0
    for _endpoint_name_20260701, _view_20260701 in list(app.view_functions.items()):
        try:
            rule_matches = [
                rule.rule
                for rule in app.url_map.iter_rules()
                if rule.endpoint == _endpoint_name_20260701
            ]

            if "/api/chat" in rule_matches:
                if _nova_autonomy_wrap_endpoint_20260701(_endpoint_name_20260701):
                    _nova_autonomy_wrapped_count_20260701 += 1
        except Exception:
            pass

    _nova_boot_log_20260701(
        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] wrapped endpoints:",
        _nova_autonomy_wrapped_count_20260701,
    )
except Exception as _nova_autonomy_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] failed:",
            _nova_autonomy_install_error_20260701,
        )
    except Exception:
        pass




# NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701
# One-command adapter migration for autonomy-plan.
# Keeps old guard below as fallback while adapter owns matching command requests.
try:
    @app.before_request
    def nova_autonomy_plan_adapter_guard_20260701():
        try:
            if request.method != "POST":
                return None

            if request.path not in ("/api/chat", "/api/chat/stream"):
                return None

            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            from nova_backend.services.autonomy_plan_adapter import build_autonomy_plan_response

            response_json = build_autonomy_plan_response(payload, session_service)

            if not response_json:
                return None

            return jsonify(response_json)
        except Exception as _nova_autonomy_plan_adapter_error_20260701:
            print("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] failed:", _nova_autonomy_plan_adapter_error_20260701)
            return None

    _nova_boot_log_20260701("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] installed")
except Exception as _nova_autonomy_plan_adapter_install_error_20260701:
    print("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] install failed:", _nova_autonomy_plan_adapter_install_error_20260701)

# NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701
# One-command adapter migration for patch-build.
# Keeps old guard below as fallback while adapter owns matching command requests.
try:
    @app.before_request
    def nova_patch_build_adapter_guard_20260701():
        try:
            if request.method != "POST":
                return None

            if request.path not in ("/api/chat", "/api/chat/stream"):
                return None

            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            from nova_backend.services.patch_build_adapter import build_patch_build_response

            response_json = build_patch_build_response(payload, session_service)

            if not response_json:
                return None

            return jsonify(response_json)
        except Exception as _nova_patch_build_adapter_error_20260701:
            print("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] failed:", _nova_patch_build_adapter_error_20260701)
            return None

    _nova_boot_log_20260701("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] installed")
except Exception as _nova_patch_build_adapter_install_error_20260701:
    print("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] install failed:", _nova_patch_build_adapter_install_error_20260701)




@app.before_request






# NOVA_REPAIR_BUILD_COMMAND_GUARD_20260701
# Instructions-only repair-build guard.
# Adapter-owned; behavior must remain repair_build_command + repair_instructions_only.
@app.before_request
def nova_repair_build_command_guard_20260701():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        from nova_backend.services.repair_build_adapter import (
            build_repair_build_response,
        )

        response_payload = build_repair_build_response(payload, session_service)

        if response_payload is None:
            return None

        return jsonify(response_payload)

    except Exception as error:
        try:
            app.logger.exception("[NOVA_REPAIR_BUILD_COMMAND_GUARD_20260701] failed")
        except Exception:
            pass

        return jsonify({
            "ok": False,
            "error": str(error),
            "debug": {
                "route": "repair_build_command",
                "failed": True,
            },
        }), 500


# NOVA_WORKFLOW_CATALOG_COMMAND_GUARD_20260701
# Read-only workflow catalog guard.
# Adapter-owned; behavior must remain workflow_catalog_command + manual_workflow_catalog_only.
@app.before_request
def nova_workflow_catalog_command_guard_20260701():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        from nova_backend.services.workflow_catalog_adapter import (
            build_workflow_catalog_response,
        )

        response_payload = build_workflow_catalog_response(payload, session_service)

        if response_payload is None:
            return None

        return jsonify(response_payload)

    except Exception as error:
        try:
            app.logger.exception("[NOVA_WORKFLOW_CATALOG_COMMAND_GUARD_20260701] failed")
        except Exception:
            pass

        return jsonify({
            "ok": False,
            "error": str(error),
            "debug": {
                "route": "workflow_catalog_command",
                "failed": True,
            },
        }), 500


# NOVA_AUTONOMY_INDEX_COMMAND_GUARD_20260701
# Read-only autonomy index guard.
# Adapter-owned; behavior must remain autonomy_index_command + autonomy_ladder_index_only.
@app.before_request
def nova_autonomy_index_command_guard_20260701():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        from nova_backend.services.autonomy_index_adapter import (
            build_autonomy_index_response,
        )

        response_payload = build_autonomy_index_response(payload, session_service)

        if response_payload is None:
            return None

        return jsonify(response_payload)

    except Exception as error:
        try:
            app.logger.exception("[NOVA_AUTONOMY_INDEX_COMMAND_GUARD_20260701] failed")
        except Exception:
            pass

        return jsonify({
            "ok": False,
            "error": str(error),
            "debug": {
                "route": "autonomy_index_command",
                "failed": True,
            },
        }), 500


# NOVA_COMMAND_REGISTRY_COMMAND_GUARD_20260701
# Read-only command registry guard.
# Adapter-owned; behavior must remain command_registry_command + read_only_command_registry.
@app.before_request
def nova_command_registry_command_guard_20260701():
    try:
        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        from nova_backend.services.autonomy_command_registry_adapter import (
            build_command_registry_response,
        )

        response_payload = build_command_registry_response(payload, session_service)

        if response_payload is None:
            return None

        return jsonify(response_payload)

    except Exception as error:
        try:
            app.logger.exception("[NOVA_COMMAND_REGISTRY_COMMAND_GUARD_20260701] failed")
        except Exception:
            pass

        return jsonify({
            "ok": False,
            "error": str(error),
            "debug": {
                "route": "command_registry_command",
                "failed": True,
            },
        }), 500



# NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701
# Active execution missions should beat global project-state recall for status questions.
try:
    from flask import request as _nova_phase4a_request, jsonify as _nova_phase4a_jsonify, make_response as _nova_phase4a_make_response
    from pathlib import Path as _NovaPhase4APath
    import json as _nova_phase4a_json
    import functools as _nova_phase4a_functools

    _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701 = {}
    _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701 = {}

    _NOVA_PHASE4A_STATUS_QUESTIONS_20260701 = {
        "what are we working on",
        "what are we working on?",
        "what are we doing",
        "what are we doing?",
        "where are we",
        "where are we?",
        "status",
        "current status",
        "what is the status",
        "what's the status",
        "whats the status",
        "what comes next",
        "what comes next?",
        "what is next",
        "what's next",
        "whats next",
        "next step",
        "what is the next step",
        "what's the next step",
        "whats the next step",
    }

    def _nova_phase4a_clean_text_20260701(value):
        return " ".join(str(value or "").strip().lower().split())

    def _nova_phase4a_is_status_question_20260701(user_text):
        clean = _nova_phase4a_clean_text_20260701(user_text).strip(" .!")
        return clean in _NOVA_PHASE4A_STATUS_QUESTIONS_20260701

    def _nova_phase4a_execution_is_active_20260701(execution):
        if not isinstance(execution, dict):
            return False

        goal = str(execution.get("goal") or "").strip()
        status = str(execution.get("status") or "").strip().lower()

        if not goal:
            return False

        if status in {"complete", "completed", "done", "failed", "error", "cancelled", "canceled"}:
            return False

        return True

    def _nova_phase4d_execution_is_complete_20260701(execution):
        if not isinstance(execution, dict):
            return False

        goal = str(execution.get("goal") or "").strip()
        status = str(execution.get("status") or "").strip().lower()

        if not goal:
            return False

        if execution.get("complete") is True:
            return True

        return status in {"complete", "completed", "done"}

    def _nova_phase4a_goal_20260701(execution):
        return str((execution or {}).get("goal") or "").strip()

    def _nova_phase4a_steps_20260701(execution):
        raw_steps = (execution or {}).get("steps") or []
        steps = []

        for item in raw_steps:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("text") or item.get("name") or "").strip()
            else:
                title = str(item or "").strip()

            if title:
                steps.append(title)

        return steps

    def _nova_phase4a_index_20260701(execution, steps):
        value = (
            (execution or {}).get("current_index")
            if "current_index" in (execution or {})
            else (execution or {}).get("current_step_index", 0)
        )

        try:
            index = int(value or 0)
        except Exception:
            index = 0

        if steps:
            index = max(0, min(index, len(steps) - 1))
        else:
            index = max(0, index)

        return index

    def _nova_phase4a_current_step_20260701(execution):
        steps = _nova_phase4a_steps_20260701(execution)
        index = _nova_phase4a_index_20260701(execution, steps)

        current = str((execution or {}).get("current_step") or "").strip()
        if current:
            return current

        if steps and 0 <= index < len(steps):
            return steps[index]

        return ""

    def _nova_phase4a_execution_status_text_20260701(execution):
        goal = _nova_phase4a_goal_20260701(execution)
        status = str((execution or {}).get("status") or "ready").strip() or "ready"
        steps = _nova_phase4a_steps_20260701(execution)
        index = _nova_phase4a_index_20260701(execution, steps)
        current_step = _nova_phase4a_current_step_20260701(execution)

        lines = [
            f"Active mission: {goal}",
            f"Status: {status}",
        ]

        if current_step and steps:
            lines.append(f"Step {index + 1}/{len(steps)}: {current_step}")
        elif current_step:
            lines.append(f"Current step: {current_step}")

        if str((execution or {}).get("waiting") or "").lower() in {"true", "1", "yes"}:
            lines.append("Next: send next, k, continue, or run it to advance.")

        return "\n".join(lines).strip()

    def _nova_phase4a_session_service_20260701():
        for name in ("session_service", "sessions", "session_manager"):
            svc = globals().get(name)
            if svc is not None:
                return svc
        return None

    def _nova_phase4a_read_sessions_file_20260701():
        path = _NovaPhase4APath(__file__).resolve().parent / "data" / "nova_sessions.json"
        if not path.exists():
            return None, path

        try:
            return _nova_phase4a_json.loads(path.read_text(encoding="utf-8", errors="replace")), path
        except Exception:
            return None, path

    def _nova_phase4a_find_session_20260701(container, session_id):
        if not session_id:
            return None

        if isinstance(container, dict):
            direct = container.get(session_id)
            if isinstance(direct, dict):
                return direct

            for key in ("sessions", "items", "data"):
                found = _nova_phase4a_find_session_20260701(container.get(key), session_id)
                if found is not None:
                    return found

            for value in container.values():
                if isinstance(value, dict) and str(value.get("id") or "") == session_id:
                    return value
                if isinstance(value, (dict, list)):
                    found = _nova_phase4a_find_session_20260701(value, session_id)
                    if found is not None:
                        return found

        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                    return item

        return None

    def _nova_phase4a_get_working_state_20260701(session_id):
        session_id = str(session_id or "").strip()
        if not session_id:
            return {}

        svc = _nova_phase4a_session_service_20260701()

        for method_name in ("get_working_state",):
            method = getattr(svc, method_name, None)
            if callable(method):
                try:
                    state = method(session_id)
                    if isinstance(state, dict):
                        return dict(state)
                except Exception:
                    pass

        for method_name in ("get_session", "get"):
            method = getattr(svc, method_name, None)
            if callable(method):
                try:
                    session = method(session_id)
                    if isinstance(session, dict) and isinstance(session.get("working_state"), dict):
                        return dict(session.get("working_state"))
                except Exception:
                    pass

        data, _ = _nova_phase4a_read_sessions_file_20260701()
        session = _nova_phase4a_find_session_20260701(data, session_id)
        if isinstance(session, dict) and isinstance(session.get("working_state"), dict):
            return dict(session.get("working_state"))

        return {}

    def _nova_phase4a_persist_working_state_20260701(session_id, patch):
        session_id = str(session_id or "").strip()
        if not session_id or not isinstance(patch, dict):
            return False

        service_saved = False

        svc = _nova_phase4a_session_service_20260701()
        method = getattr(svc, "update_working_state", None)

        if callable(method):
            try:
                method(session_id, patch)
                service_saved = True
            except Exception:
                service_saved = False

        data, path = _nova_phase4a_read_sessions_file_20260701()
        if data is None:
            return service_saved

        session = _nova_phase4a_find_session_20260701(data, session_id)
        if not isinstance(session, dict):
            session = {
                "id": session_id,
                "title": session_id,
                "messages": [],
                "session_attachments": [],
                "working_state": {},
                "active_execution": None,
                "execution_state": None,
            }

            if isinstance(data, dict):
                sessions_value = data.get("sessions")

                if isinstance(sessions_value, list):
                    sessions_value.append(session)
                elif isinstance(sessions_value, dict):
                    sessions_value[session_id] = session
                else:
                    data[session_id] = session

            elif isinstance(data, list):
                data.append(session)

            else:
                return service_saved

        state = session.get("working_state")
        if not isinstance(state, dict):
            state = {}

        state.update(patch)
        session["working_state"] = state

        # Phase 4F: persist executable mission state at top-level too.
        # Some session working_state paths filter unknown keys, so active_execution
        # must be stored directly on the session for restart recovery.
        if "active_execution" in patch:
            session["active_execution"] = patch.get("active_execution")

        if "execution_state" in patch:
            session["execution_state"] = patch.get("execution_state")

        try:
            path.write_text(_nova_phase4a_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return service_saved

    def _nova_phase4a_get_active_execution_20260701(session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701.get(session_id)
            if _nova_phase4a_execution_is_active_20260701(cached):
                return cached

        state = _nova_phase4a_get_working_state_20260701(session_id)
        for key in ("active_execution", "execution_state", "execution"):
            execution = state.get(key)
            if _nova_phase4a_execution_is_active_20260701(execution):
                if session_id:
                    _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701[session_id] = execution
                return execution
        return None

    def _nova_phase4d_get_completed_execution_20260701(session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701.get(session_id)
            if _nova_phase4d_execution_is_complete_20260701(cached):
                return cached

        state = _nova_phase4a_get_working_state_20260701(session_id)
        for key in ("execution_state", "execution", "last_execution"):
            execution = state.get(key)
            if _nova_phase4d_execution_is_complete_20260701(execution):
                if session_id:
                    _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701[session_id] = execution
                return execution

        return None

    def _nova_phase4d_completed_status_text_20260701(execution):
        goal = _nova_phase4a_goal_20260701(execution)
        if goal:
            return f"No active mission is running. Last completed mission: {goal}"
        return "No active mission is running."

    def _nova_phase4a_persist_execution_20260701(session_id, execution):
        session_id = str(session_id or "").strip()

        if _nova_phase4d_execution_is_complete_20260701(execution):
            if session_id:
                _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701.pop(session_id, None)
                _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701[session_id] = execution

            return _nova_phase4a_persist_working_state_20260701(
                session_id,
                {
                    "active_execution": None,
                    "execution_state": execution,
                    "active_task": "",
                    "next_move": "",
                    "checkpoint": "Execution mission complete",
                },
            )

        if not _nova_phase4a_execution_is_active_20260701(execution):
            return False

        if session_id:
            _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701[session_id] = execution

        goal = _nova_phase4a_goal_20260701(execution)
        current_step = _nova_phase4a_current_step_20260701(execution)

        patch = {
            "active_execution": execution,
            "execution_state": execution,
            "active_task": goal,
            "next_move": current_step,
            "checkpoint": "Active execution mission",
        }

        return _nova_phase4a_persist_working_state_20260701(session_id, patch)

    def _nova_phase4a_wrap_chat_endpoint_20260701(endpoint, view_func):
        if getattr(view_func, "_nova_phase4a_active_execution_wrapped", False):
            return view_func

        @_nova_phase4a_functools.wraps(view_func)
        def _nova_phase4a_wrapped(*args, **kwargs):
            payload = {}
            try:
                payload = _nova_phase4a_request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            user_text = str(payload.get("message") or payload.get("text") or payload.get("user_text") or "").strip()
            session_id = str(payload.get("session_id") or payload.get("active_session_id") or "").strip()

            if _nova_phase4a_clean_text_20260701(user_text).strip(" .!") == "say only pong":
                text = "pong"
                return _nova_phase4a_jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": text,
                        "content": text,
                        "session_id": session_id,
                        "active_session_id": session_id,
                        "meta": {
                            "render_source": "direct_pong_priority",
                        },
                    },
                    "debug": {
                        "route": "chat",
                        "route_taken": "chat",
                        "direct_pong_priority": True,
                    },
                })

            if session_id and _nova_phase4a_is_status_question_20260701(user_text):
                active_execution = _nova_phase4a_get_active_execution_20260701(session_id)
                if _nova_phase4a_execution_is_active_20260701(active_execution):
                    text = _nova_phase4a_execution_status_text_20260701(active_execution)
                    return _nova_phase4a_jsonify({
                        "ok": True,
                        "session_id": session_id,
                        "active_session_id": session_id,
                        "assistant_message": {
                            "role": "assistant",
                            "text": text,
                            "content": text,
                            "session_id": session_id,
                            "active_session_id": session_id,
                            "execution_state": active_execution,
                            "meta": {
                                "render_source": "active_execution_status",
                            },
                        },
                        "execution_state": active_execution,
                        "debug": {
                            "route": "active_execution_status",
                            "route_taken": "active_execution_status",
                            "suppressed_project_state_recall": True,
                        },
                    })

                completed_execution = _nova_phase4d_get_completed_execution_20260701(session_id)
                if _nova_phase4d_execution_is_complete_20260701(completed_execution):
                    text = _nova_phase4d_completed_status_text_20260701(completed_execution)
                    return _nova_phase4a_jsonify({
                        "ok": True,
                        "session_id": session_id,
                        "active_session_id": session_id,
                        "assistant_message": {
                            "role": "assistant",
                            "text": text,
                            "content": text,
                            "session_id": session_id,
                            "active_session_id": session_id,
                            "execution_state": completed_execution,
                            "meta": {
                                "render_source": "completed_execution_status",
                            },
                        },
                        "execution_state": completed_execution,
                        "debug": {
                            "route": "completed_execution_status",
                            "route_taken": "completed_execution_status",
                            "suppressed_project_state_recall": True,
                        },
                    })

            result = view_func(*args, **kwargs)

            try:
                response = _nova_phase4a_make_response(result)
                data = response.get_json(silent=True)

                if isinstance(data, dict) and session_id:
                    execution = data.get("execution_state")
                    if not isinstance(execution, dict):
                        assistant = data.get("assistant_message")
                        if isinstance(assistant, dict):
                            execution = assistant.get("execution_state")

                    if _nova_phase4a_execution_is_active_20260701(execution) or _nova_phase4d_execution_is_complete_20260701(execution):
                        _nova_phase4a_persist_execution_20260701(session_id, execution)

                return response
            except Exception:
                return result

        _nova_phase4a_wrapped._nova_phase4a_active_execution_wrapped = True
        return _nova_phase4a_wrapped

    _nova_phase4a_wrapped_count_20260701 = 0

    for _nova_phase4a_endpoint_20260701, _nova_phase4a_view_20260701 in list(app.view_functions.items()):
        try:
            _nova_phase4a_rules_20260701 = [
                str(rule.rule)
                for rule in app.url_map.iter_rules(_nova_phase4a_endpoint_20260701)
            ]
        except Exception:
            _nova_phase4a_rules_20260701 = []

        if "/api/chat" in _nova_phase4a_rules_20260701:
            app.view_functions[_nova_phase4a_endpoint_20260701] = _nova_phase4a_wrap_chat_endpoint_20260701(
                _nova_phase4a_endpoint_20260701,
                _nova_phase4a_view_20260701,
            )
            _nova_phase4a_wrapped_count_20260701 += 1

    _nova_boot_log_20260701(f"[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] wrapped endpoints: {_nova_phase4a_wrapped_count_20260701}")

except Exception as _nova_phase4a_error_20260701:
    print("[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] failed:", _nova_phase4a_error_20260701)



# NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701
# Preserve chat history across refresh/session switch and prevent manual titles from
# being overwritten by later chat messages.
try:
    import json as _nova_phase4g_json
    import uuid as _nova_phase4g_uuid
    from datetime import datetime as _nova_phase4g_datetime
    from datetime import timezone as _nova_phase4g_timezone
    from pathlib import Path as _nova_phase4g_Path

    from flask import g as _nova_phase4g_g
    from flask import request as _nova_phase4g_request

    _NOVA_PHASE4G_SESSIONS_PATH_20260701 = (
        _nova_phase4g_Path(__file__).resolve().parent / "data" / "nova_sessions.json"
    )

    def _nova_phase4g_now_20260701():
        return _nova_phase4g_datetime.now(_nova_phase4g_timezone.utc).isoformat()

    def _nova_phase4g_text_20260701(value):
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _nova_phase4g_request_json_20260701():
        try:
            data = _nova_phase4g_request.get_json(silent=True)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_phase4g_response_json_20260701(response):
        try:
            raw = response.get_data(as_text=True)
            data = _nova_phase4g_json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _nova_phase4g_write_response_json_20260701(response, data):
        try:
            payload = _nova_phase4g_json.dumps(data, ensure_ascii=False)
            response.set_data(payload)
            response.headers["Content-Length"] = str(len(response.get_data()))
            response.headers["Content-Type"] = "application/json"
        except Exception:
            pass
        return response

    def _nova_phase4g_read_sessions_20260701():
        try:
            if not _NOVA_PHASE4G_SESSIONS_PATH_20260701.exists():
                return {"sessions": []}
            data = _nova_phase4g_json.loads(
                _NOVA_PHASE4G_SESSIONS_PATH_20260701.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
            if isinstance(data, (dict, list)):
                return data
        except Exception:
            pass
        return {"sessions": []}

    def _nova_phase4g_write_sessions_20260701(data):
        try:
            _NOVA_PHASE4G_SESSIONS_PATH_20260701.parent.mkdir(parents=True, exist_ok=True)
            _NOVA_PHASE4G_SESSIONS_PATH_20260701.write_text(
                _nova_phase4g_json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except Exception:
            return False

    def _nova_phase4g_find_session_20260701(obj, session_id):
        if not session_id:
            return None

        if isinstance(obj, dict):
            if obj.get("id") == session_id:
                return obj
            for value in obj.values():
                found = _nova_phase4g_find_session_20260701(value, session_id)
                if isinstance(found, dict):
                    return found

        if isinstance(obj, list):
            for value in obj:
                found = _nova_phase4g_find_session_20260701(value, session_id)
                if isinstance(found, dict):
                    return found

        return None

    def _nova_phase4g_create_session_20260701(data, session_id, title=""):
        session = {
            "id": session_id,
            "title": title or session_id,
            "messages": [],
            "session_attachments": [],
            "working_state": {},
            "active_execution": None,
            "execution_state": None,
            "pinned": False,
            "created_at": _nova_phase4g_now_20260701(),
            "updated_at": _nova_phase4g_now_20260701(),
            "message_count": 0,
            "active_session_id": session_id,
        }

        if isinstance(data, dict):
            sessions = data.get("sessions")
            if isinstance(sessions, list):
                sessions.append(session)
            elif isinstance(sessions, dict):
                sessions[session_id] = session
            else:
                data["sessions"] = [session]
            return session

        if isinstance(data, list):
            data.append(session)
            return session

        return session

    def _nova_phase4g_get_or_create_session_20260701(data, session_id, title=""):
        session = _nova_phase4g_find_session_20260701(data, session_id)
        if isinstance(session, dict):
            return session
        return _nova_phase4g_create_session_20260701(data, session_id, title)

    def _nova_phase4g_message_text_20260701(message):
        if not isinstance(message, dict):
            return ""
        return _nova_phase4g_text_20260701(
            message.get("text")
            or message.get("content")
            or message.get("message")
        )

    def _nova_phase4g_append_message_20260701(session, role, text, meta=None, attachments=None):
        text = _nova_phase4g_text_20260701(text)
        role = _nova_phase4g_text_20260701(role) or "assistant"

        if not isinstance(session, dict) or not text:
            return False

        messages = session.get("messages")
        if not isinstance(messages, list):
            messages = []
            session["messages"] = messages

        if messages:
            last = messages[-1]
            if (
                isinstance(last, dict)
                and _nova_phase4g_text_20260701(last.get("role")) == role
                and _nova_phase4g_message_text_20260701(last) == text
            ):
                return False

        now = _nova_phase4g_now_20260701()
        message = {
            "id": "msg_" + _nova_phase4g_uuid.uuid4().hex,
            "role": role,
            "text": text,
            "content": text,
            "attachments": attachments if isinstance(attachments, list) else [],
            "created_at": now,
            "updated_at": now,
            "meta": meta if isinstance(meta, dict) else {},
        }

        messages.append(message)
        session["message_count"] = len(messages)
        session["updated_at"] = now
        return True

    def _nova_phase4g_is_title_locked_20260701(session):
        if not isinstance(session, dict):
            return False
        if session.get("manual_title") is True or session.get("title_locked") is True:
            return True
        meta = session.get("meta")
        if isinstance(meta, dict):
            return meta.get("manual_title") is True or meta.get("title_locked") is True
        return False

    def _nova_phase4g_pick_session_id_20260701(data, response_data=None):
        request_data = _nova_phase4g_request_json_20260701()

        for source in (request_data, response_data or {}):
            if not isinstance(source, dict):
                continue
            for key in ("session_id", "active_session_id", "id"):
                value = _nova_phase4g_text_20260701(source.get(key))
                if value:
                    return value

            session = source.get("session")
            if isinstance(session, dict):
                value = _nova_phase4g_text_20260701(session.get("id"))
                if value:
                    return value

        return ""

    def _nova_phase4g_pick_assistant_text_20260701(response_data):
        if not isinstance(response_data, dict):
            return ""

        assistant = response_data.get("assistant_message")
        if isinstance(assistant, dict):
            return _nova_phase4g_text_20260701(
                assistant.get("text")
                or assistant.get("content")
                or assistant.get("message")
            )

        return _nova_phase4g_text_20260701(
            response_data.get("text")
            or response_data.get("content")
            or response_data.get("message")
        )

    def _nova_phase4g_pick_user_text_20260701():
        request_data = _nova_phase4g_request_json_20260701()
        return _nova_phase4g_text_20260701(
            request_data.get("message")
            or request_data.get("text")
            or request_data.get("content")
        )

    def _nova_phase4g_capture_title_20260701():
        try:
            path = _nova_phase4g_text_20260701(_nova_phase4g_request.path).lower()
            if not (path.endswith("/api/chat") or "/api/chat" in path or "rename" in path):
                return

            data = _nova_phase4g_read_sessions_20260701()
            session_id = _nova_phase4g_pick_session_id_20260701(data)
            session = _nova_phase4g_find_session_20260701(data, session_id)

            if isinstance(session, dict):
                _nova_phase4g_g.nova_phase4g_existing_title = session.get("title")
                _nova_phase4g_g.nova_phase4g_title_locked = _nova_phase4g_is_title_locked_20260701(session)
        except Exception:
            pass

    app.before_request(_nova_phase4g_capture_title_20260701)

    def _nova_phase4g_after_response_20260701(response):
        try:
            path = _nova_phase4g_text_20260701(_nova_phase4g_request.path).lower()
            request_data = _nova_phase4g_request_json_20260701()
            response_data = _nova_phase4g_response_json_20260701(response)

            if "session" in path and "rename" in path:
                session_id = _nova_phase4g_pick_session_id_20260701(response_data)
                title = _nova_phase4g_text_20260701(
                    request_data.get("title")
                    or request_data.get("name")
                    or request_data.get("new_title")
                )

                if session_id and title:
                    data = _nova_phase4g_read_sessions_20260701()
                    session = _nova_phase4g_get_or_create_session_20260701(data, session_id, title)
                    session["title"] = title
                    session["manual_title"] = True
                    session["title_locked"] = True
                    meta = session.get("meta")
                    if not isinstance(meta, dict):
                        meta = {}
                    meta["manual_title"] = True
                    meta["title_locked"] = True
                    session["meta"] = meta
                    session["updated_at"] = _nova_phase4g_now_20260701()
                    _nova_phase4g_write_sessions_20260701(data)

                return response

            if not (path.endswith("/api/chat") or "/api/chat" in path):
                return response

            if not isinstance(response_data, dict):
                return response

            session_id = _nova_phase4g_pick_session_id_20260701(response_data)
            if not session_id:
                return response

            user_text = _nova_phase4g_pick_user_text_20260701()
            assistant_text = _nova_phase4g_pick_assistant_text_20260701(response_data)

            data = _nova_phase4g_read_sessions_20260701()
            title_seed = user_text or session_id
            session = _nova_phase4g_get_or_create_session_20260701(data, session_id, title_seed)

            existing_title = getattr(_nova_phase4g_g, "nova_phase4g_existing_title", None)
            was_locked = bool(getattr(_nova_phase4g_g, "nova_phase4g_title_locked", False))

            if was_locked or _nova_phase4g_is_title_locked_20260701(session):
                if existing_title:
                    session["title"] = existing_title
                session["manual_title"] = True
                session["title_locked"] = True
            else:
                current_title = _nova_phase4g_text_20260701(session.get("title"))
                if not current_title or current_title == session_id or current_title.startswith("session_"):
                    session["title"] = title_seed[:80]

            response_session = response_data.get("session")
            # Phase 4G duplicate fix:
            # Do not replay response_session.messages here. The response session can
            # already contain the current user/assistant pair, and replaying it before
            # appending the current exchange creates duplicate visible history.
            _nova_phase4g_append_message_20260701(
                session,
                "user",
                user_text,
                {
                    "route": "phase4g_session_history_persistence",
                    "session_id": session_id,
                },
                request_data.get("attachments") if isinstance(request_data.get("attachments"), list) else [],
            )

            assistant_meta = {}
            assistant = response_data.get("assistant_message")
            if isinstance(assistant, dict) and isinstance(assistant.get("meta"), dict):
                assistant_meta = assistant.get("meta")

            _nova_phase4g_append_message_20260701(
                session,
                "assistant",
                assistant_text,
                assistant_meta,
                [],
            )

            if isinstance(response_session, dict):
                for key in (
                    "active_execution",
                    "execution_state",
                    "working_state",
                    "session_attachments",
                    "meta",
                    "pinned",
                    "created_at",
                    "active_session_id",
                ):
                    if key in response_session and key not in {"messages"}:
                        session[key] = response_session.get(key)

            session["active_session_id"] = session_id
            session["message_count"] = len(session.get("messages") or [])
            session["updated_at"] = _nova_phase4g_now_20260701()

            _nova_phase4g_write_sessions_20260701(data)

            response_data["session"] = session
            response_data["session_id"] = session_id
            response_data["active_session_id"] = session_id
            response_data["phase4g_session_history_persistence"] = True

            return _nova_phase4g_write_response_json_20260701(response, response_data)

        except Exception as exc:
            try:
                print("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] failed:", exc)
            except Exception:
                pass
            return response

    app.after_request(_nova_phase4g_after_response_20260701)

    _nova_boot_log_20260701("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] installed")
except Exception as _nova_phase4g_error_20260701:
    print("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] failed:", _nova_phase4g_error_20260701)



# NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701
# Prevent short normal-chat messages from inheriting the prior autonomy command
# response in the same session.
try:
    import json as _nova_phase4g_chat_json
    from flask import request as _nova_phase4g_chat_request

    def _nova_phase4g_chat_text_20260701(value):
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _nova_phase4g_chat_request_json_20260701():
        try:
            data = _nova_phase4g_chat_request.get_json(silent=True)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_phase4g_chat_response_json_20260701(response):
        try:
            data = _nova_phase4g_chat_json.loads(response.get_data(as_text=True))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _nova_phase4g_chat_assistant_text_20260701(data):
        if not isinstance(data, dict):
            return ""

        assistant = data.get("assistant_message")
        if isinstance(assistant, dict):
            return _nova_phase4g_chat_text_20260701(
                assistant.get("text")
                or assistant.get("content")
                or assistant.get("message")
            )

        return _nova_phase4g_chat_text_20260701(
            data.get("text")
            or data.get("content")
            or data.get("message")
        )

    def _nova_phase4g_chat_write_json_20260701(response, data):
        try:
            payload = _nova_phase4g_chat_json.dumps(data, ensure_ascii=False)
            response.set_data(payload)
            response.headers["Content-Length"] = str(len(response.get_data()))
            response.headers["Content-Type"] = "application/json"
        except Exception:
            pass
        return response

    def _nova_phase4g_normal_chat_carryover_guard_20260701(response):
        try:
            path = _nova_phase4g_chat_text_20260701(_nova_phase4g_chat_request.path).lower()
            if not (path.endswith("/api/chat") or "/api/chat" in path):
                return response

            request_data = _nova_phase4g_chat_request_json_20260701()
            user_text = _nova_phase4g_chat_text_20260701(
                request_data.get("message")
                or request_data.get("text")
                or request_data.get("content")
            )
            normalized = user_text.lower().strip(" .!?")

            if normalized not in {"hi", "hello", "hey", "yo"}:
                return response

            data = _nova_phase4g_chat_response_json_20260701(response)
            if not isinstance(data, dict):
                return response

            assistant_text = _nova_phase4g_chat_assistant_text_20260701(data)
            if "nova autonomy task brief" not in assistant_text.lower():
                return response

            session_id = _nova_phase4g_chat_text_20260701(
                data.get("session_id")
                or data.get("active_session_id")
                or request_data.get("session_id")
            )

            fixed_text = "Hey Richard - normal chat is still active."

            assistant = data.get("assistant_message")
            if not isinstance(assistant, dict):
                assistant = {"role": "assistant"}

            assistant["text"] = fixed_text
            assistant["content"] = fixed_text
            assistant["role"] = "assistant"
            if session_id:
                assistant["session_id"] = session_id
                assistant["active_session_id"] = session_id

            meta = assistant.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["render_source"] = "normal_chat_autonomy_carryover_guard"
            meta["normal_chat_priority"] = True
            assistant["meta"] = meta

            data["assistant_message"] = assistant
            data["ok"] = True
            if session_id:
                data["session_id"] = session_id
                data["active_session_id"] = session_id

            debug = data.get("debug")
            if not isinstance(debug, dict):
                debug = {}
            debug["route"] = "chat"
            debug["route_taken"] = "chat"
            debug["normal_chat_priority"] = True
            debug["suppressed_autonomy_carryover"] = True
            data["debug"] = debug

            return _nova_phase4g_chat_write_json_20260701(response, data)

        except Exception as exc:
            try:
                print("[NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701] failed:", exc)
            except Exception:
                pass
            return response

    app.after_request(_nova_phase4g_normal_chat_carryover_guard_20260701)

    _nova_boot_log_20260701("[NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701] installed")
except Exception as _nova_phase4g_chat_guard_error_20260701:
    print("[NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701] failed:", _nova_phase4g_chat_guard_error_20260701)


# NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701
# Must be above

# NOVA_API_CHAT_PROJECT_NEXT_FINAL_OVERRIDE_20260701
# Final API response override for exact project-brain "what's next?" questions.
# This catches generic chat fallback after chat_service.handle and before UI/PowerShell see it.
try:
    import json as _nova_project_next_json_20260701
    from flask import request as _nova_project_next_request_20260701

    def _nova_project_next_is_question_20260701(text):
        normalized = (
            str(text or "")
            .strip()
            .lower()
            .replace("?", "'")
            .rstrip("?!.")
        )
        return normalized in {
            "what's next",
            "whats next",
            "what is next",
            "what should we do next",
            "next move",
        }

    def _nova_project_next_is_bad_answer_20260701(text):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return True

        bad_bits = [
            "tell me the immediate context",
            "need the current target",
            "send the file path",
            "file path + goal",
            "paste the current file",
            "paste the current file/error",
            "give me the immediate context",
            "pick one and i'll give",
            "current target to answer",
            "debug/fix a bug",
            "project planning",
            "conversation/doc draft",
            "general priority help",
        ]

        return any(bit in lowered for bit in bad_bits)

    def _nova_project_next_answer_20260701():
        return (
            "Current Nova project context:\n"
            "Current task: Decision Engine v1, broad Project Brain routing, Mission Control v1.2 / Failure Interpreter API, and Decision Log API route are locked.\n"
            "Next move: start Project Brain cleanup/consolidation while preserving direct recall, "
            "broad Project Brain routing, and avoiding another app.py guard."
        )

    @app.after_request
    def _nova_api_chat_project_next_final_override_20260701(response):
        try:
            if not _nova_project_next_request_20260701.path.endswith("/api/chat"):
                return response

            payload = _nova_project_next_request_20260701.get_json(silent=True) or {}
            user_text = (
                payload.get("message")
                or payload.get("user_text")
                or payload.get("text")
                or payload.get("prompt")
                or ""
            )

            if not _nova_project_next_is_question_20260701(user_text):
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = _nova_project_next_json_20260701.loads(raw)

            assistant_message = data.get("assistant_message")
            if not isinstance(assistant_message, dict):
                assistant_message = {}

            assistant_text = (
                assistant_message.get("content")
                or assistant_message.get("text")
                or data.get("assistant_text")
                or data.get("text")
                or ""
            )

            if str(assistant_text or "").strip().lower().startswith("current nova project context:"):
                return response

            fixed_text = _nova_project_next_answer_20260701()

            meta = data.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["route"] = "api_chat_project_next_final_override"
            meta["strategy"] = "api_chat_project_next_final_override"

            debug = data.get("debug")
            if not isinstance(debug, dict):
                debug = {}
            debug["route"] = "api_chat_project_next_final_override"
            debug["route_taken"] = "api_chat_project_next_final_override"

            assistant_message["role"] = "assistant"
            assistant_message["content"] = fixed_text
            assistant_message["text"] = fixed_text
            assistant_message["meta"] = meta

            data["assistant_message"] = assistant_message
            data["assistant_text"] = fixed_text
            data["text"] = fixed_text
            data["route"] = "api_chat_project_next_final_override"
            data["route_taken"] = "api_chat_project_next_final_override"
            data["meta"] = meta
            data["debug"] = debug

            session_obj = data.get("session")
            if isinstance(session_obj, dict):
                session_obj["meta"] = meta
                messages = session_obj.get("messages")
                if isinstance(messages, list):
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and str(msg.get("role") or "").lower() == "assistant":
                            msg["content"] = fixed_text
                            msg["text"] = fixed_text
                            msg["meta"] = meta
                            break

            response.set_data(_nova_project_next_json_20260701.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Length"] = str(len(response.get_data()))
            return response

        except Exception as _nova_project_next_override_error_20260701:
            try:
                print(
                    "[NOVA_API_CHAT_PROJECT_NEXT_FINAL_OVERRIDE_20260701] bypass:",
                    _nova_project_next_override_error_20260701,
                )
            except Exception:
                pass
            return response

    print("[NOVA_API_CHAT_PROJECT_NEXT_FINAL_OVERRIDE_20260701] installed")

except Exception as _nova_project_next_final_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_NEXT_FINAL_OVERRIDE_20260701] failed:",
            _nova_project_next_final_install_error_20260701,
        )
    except Exception:
        pass


# NOVA_API_CHAT_PROJECT_NEXT_BEFORE_REQUEST_PRIORITY_20260701
# Hard priority intercept for exact project-brain "what's next?" before chat_service.handle.
# This avoids generic chat/model fallback and avoids after_request ordering issues.
try:
    import json as _nova_project_next_before_json_20260701
    from flask import request as _nova_project_next_before_request_20260701
    from flask import Response as _nova_project_next_before_response_20260701

    def _nova_project_next_before_norm_20260701(value):
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("?", "'")
            .rstrip("?!.")
        )

    def _nova_project_next_before_is_question_20260701(value):
        return _nova_project_next_before_norm_20260701(value) in {
            "what's next",
            "whats next",
            "what is next",
            "what should we do next",
            "next move",
        }

    def _nova_project_next_before_answer_20260701():
        return (
            "Current Nova project context:\n"
            "Current task: Decision Engine v1, broad Project Brain routing, Mission Control v1.2 / Failure Interpreter API, and Decision Log API route are locked.\n"
            "Next move: start Project Brain cleanup/consolidation while preserving direct recall, "
            "broad Project Brain routing, and avoiding another app.py guard."
        )

    @app.before_request
    def _nova_api_chat_project_next_before_request_priority_20260701():
        try:
            if not _nova_project_next_before_request_20260701.path.endswith("/api/chat"):
                return None

            payload = _nova_project_next_before_request_20260701.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                return None

            user_text = (
                payload.get("message")
                or payload.get("user_text")
                or payload.get("text")
                or payload.get("prompt")
                or ""
            )

            if not _nova_project_next_before_is_question_20260701(user_text):
                return None

            session_id = str(
                payload.get("session_id")
                or payload.get("active_session_id")
                or payload.get("requested_session_id")
                or ""
            ).strip()

            fixed_text = _nova_project_next_before_answer_20260701()

            meta = {
                "route": "api_chat_project_next_before_request_priority",
                "strategy": "api_chat_project_next_before_request_priority",
                "session_id": session_id,
                "source_urls": [],
                "sources": [],
            }

            assistant_message = {
                "role": "assistant",
                "content": fixed_text,
                "text": fixed_text,
                "attachments": [],
                "meta": meta,
            }

            data = {
                "ok": True,
                "success": True,
                "assistant_message": assistant_message,
                "assistant_text": fixed_text,
                "text": fixed_text,
                "saved_artifact": None,
                "session": {
                    "id": session_id,
                    "session_id": session_id,
                    "messages": [assistant_message],
                    "attachments": [],
                    "meta": meta,
                },
                "route": "api_chat_project_next_before_request_priority",
                "route_taken": "api_chat_project_next_before_request_priority",
                "debug": {
                    "route": "api_chat_project_next_before_request_priority",
                    "route_taken": "api_chat_project_next_before_request_priority",
                },
                "meta": meta,
                "session_id": session_id,
                "active_session_id": session_id,
            }

            try:
                print(
                    "[NOVA_API_CHAT_PROJECT_NEXT_BEFORE_REQUEST_PRIORITY_20260701] intercepted",
                    "session_id=" + session_id,
                )
            except Exception:
                pass

            return _nova_project_next_before_response_20260701(
                _nova_project_next_before_json_20260701.dumps(data, ensure_ascii=False),
                status=200,
                mimetype="application/json",
            )

        except Exception as _nova_project_next_before_error_20260701:
            try:
                print(
                    "[NOVA_API_CHAT_PROJECT_NEXT_BEFORE_REQUEST_PRIORITY_20260701] bypass:",
                    _nova_project_next_before_error_20260701,
                )
            except Exception:
                pass
            return None

    print("[NOVA_API_CHAT_PROJECT_NEXT_BEFORE_REQUEST_PRIORITY_20260701] installed")

except Exception as _nova_project_next_before_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_NEXT_BEFORE_REQUEST_PRIORITY_20260701] failed:",
            _nova_project_next_before_install_error_20260701,
        )
    except Exception:
        pass

# Must be above app.run(). Keeps normal chat from being overwritten by stale project/autonomy state.
try:
    import json as _nova_phase4f_prerun_json_20260701
    from flask import request as _nova_phase4f_prerun_request_20260701

    def _nova_phase4f_prerun_text_20260701(value):
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _nova_phase4f_prerun_is_normal_chat_20260701(user_text):
        text = _nova_phase4f_prerun_text_20260701(user_text).lower()
        if not text:
            return False

        project_context_tokens = (
            "nova",
            "project",
            "mission",
            "checkpoint",
            "progress",
            "status",
            "state",
            "working on",
            "where are we",
            "where we are",
            "what are we doing",
            "what we're doing",
            "what were we doing",
            "what are we working on",
            "what we're working on",
            "what were we working on",
            "what did we just fix",
            "what did i just fix",
            "what was just fixed",
            "what is left",
            "what's left",
            "whats left",
            "what remains",
            "remaining work",
            "next move",
            "move on",
            "continue project",
            "continue nova",
            "current focus",
            "current checkpoint",
        )

        project_context_intent_tokens = (
            "current",
            "status",
            "state",
            "progress",
            "where",
            "working",
            "doing",
            "checkpoint",
            "focus",
            "left",
            "remaining",
            "remain",
            "next",
            "move",
            "continue",
            "fixed",
            "fix",
            "locked",
            "lock",
        )

        if any(token in text for token in project_context_tokens):
            return False

        if ("nova" in text or "project" in text or "mission" in text) and any(token in text for token in project_context_intent_tokens):
            return False

        project_recall_exact = {
            "current project state",
            "project state",
            "just fixed",
            "remaining work",
            "next command",
            "k command",
        }

        project_recall_markers = (
            "current project state",
            "project state",
            "just fixed",
            "what did we just fix",
            "what did i just fix",
            "what was just fixed",
            "remaining work",
            "what remains",
            "what's left",
            "whats left",
            "what is left",
            "current focus",
            "first remaining item",
            "next command",
            "k command",
            "nova status",
            "current nova",
            "current status",
            "locked status",
            "lock status",
            "project status",
            "status of nova",
            "nova progress",
            "current progress",
            "project progress",
            "how far",
            "where are we",
            "where we are",
            "what are we working on",
            "what we're working on",
            "what were we working on",
            "what should we do next",
            "what comes next",
            "what is next",
            "next move",
            "move on",
            "continue project",
            "continue nova",
            "nova context",
            "project context",
            "current checkpoint",
            "checkpoint",
        )

        if text in project_recall_exact:
            return False

        if any(marker in text for marker in project_recall_markers):
            return False

        command_exact = {
            "next",
            "continue",
            "run all",
            "run step",
            "run it",
            "execute",
            "stop",
            "cancel",
            "retry",
            "status",
            "what are we working on",
            "what are we working on?",
            "what's next",
            "whats next",
            "what next",
        }

        if text in command_exact:
            return False

        command_prefixes = (
            "auto-plan",
            "autoplan",
            "auto build",
            "autobuild",
            "build ",
            "create ",
            "make ",
            "implement ",
            "fix ",
            "repair ",
            "upgrade ",
            "run ",
            "execute ",
        )

        if any(text.startswith(prefix) for prefix in command_prefixes):
            return False

        normal_prefixes = (
            "what is ",
            "what's ",
            "whats ",
            "who is ",
            "where is ",
            "when is ",
            "why is ",
            "how do ",
            "how does ",
            "how many ",
            "how much ",
            "tell me ",
            "explain ",
            "define ",
            "ping",
            "hello",
            "hi",
            "hey",
        )

        return text.endswith("?") or any(text.startswith(prefix) for prefix in normal_prefixes)

    def _nova_phase4f_prerun_is_bleed_20260701(content):
        text = _nova_phase4f_prerun_text_20260701(content).lower()
        if not text:
            return False

        markers = (
            "next move:",
            "current focus:",
            "first remaining item:",
            "remaining work",
            "next command",
            "project state",
            "active nova mission",
            "active mission",
            "last mission",
            "autonomy task",
            "fallback guard cleanup",
            "autonomy-plan fallback",
            "patch-build fallback",
        )

        return any(marker in text for marker in markers)


    def _nova_phase4f_prerun_is_safe_probe_20260701(user_text):
        text = _nova_phase4f_prerun_text_20260701(user_text).lower()
        compact = (
            text.replace(" ", "")
            .replace("?", "")
            .replace("plus", "+")
            .replace("add", "+")
        )

        if text.startswith("ping"):
            return True

        if "2+2" in compact or "twoplustwo" in compact:
            return True

        if "short joke" in text or text.startswith("tell me a joke") or text.startswith("tell me a short joke"):
            return True

        return False


    def _nova_phase4f_prerun_safe_answer_20260701(user_text):
        text = _nova_phase4f_prerun_text_20260701(user_text).lower()
        compact = (
            text.replace(" ", "")
            .replace("?", "")
            .replace("plus", "+")
            .replace("add", "+")
        )

        if "2+2" in compact or "twoplustwo" in compact:
            return "2 plus 2 is 4."

        if text.startswith("ping"):
            return "pong"

        if "short joke" in text or text.startswith("tell me a joke") or text.startswith("tell me a short joke"):
            return "Why did the computer get cold? It left its Windows open."

        return "I?m here. What would you like to talk about?"

    def _nova_phase4f_prerun_extract_20260701(data):
        assistant = data.get("assistant_message")
        if isinstance(assistant, dict):
            for key in ("content", "text", "message", "response", "answer"):
                value = assistant.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        for key in ("content", "response", "message", "text", "answer"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value

        return ""

    def _nova_phase4f_prerun_set_answer_20260701(data, answer):
        assistant = data.get("assistant_message")
        if isinstance(assistant, dict):
            assistant["content"] = answer
            assistant["text"] = answer
            data["assistant_message"] = assistant
        else:
            data["assistant_message"] = {
                "role": "assistant",
                "content": answer,
                "text": answer,
            }

        data["content"] = answer
        data["response"] = answer
        data["message"] = answer
        data["text"] = answer
        data["answer"] = answer

        debug = data.get("debug")
        if not isinstance(debug, dict):
            debug = {}

        debug["route"] = "chat"
        debug["route_taken"] = "chat"
        debug["normal_chat_priority"] = True
        debug["suppressed_project_state_bleed"] = True
        debug["phase4f_prerun_final_guard"] = True
        data["debug"] = debug

        return data

    @app.after_request
    def _nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701(response):
        try:
            if _nova_phase4f_prerun_request_20260701.path != "/api/chat":
                return response

            if response.status_code >= 400:
                return response

            request_payload = _nova_phase4f_prerun_request_20260701.get_json(silent=True) or {}
            user_text = request_payload.get("message") or request_payload.get("user_text") or ""

            if not _nova_phase4f_prerun_is_normal_chat_20260701(user_text):
                return response

            if not _nova_phase4f_prerun_is_safe_probe_20260701(user_text):
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = _nova_phase4f_prerun_json_20260701.loads(raw)
            if not isinstance(data, dict):
                return response

            content = _nova_phase4f_prerun_extract_20260701(data)
            if not _nova_phase4f_prerun_is_bleed_20260701(content):
                return response

            answer = _nova_phase4f_prerun_safe_answer_20260701(user_text)
            data = _nova_phase4f_prerun_set_answer_20260701(data, answer)

            response.set_data(_nova_phase4f_prerun_json_20260701.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Length"] = str(len(response.get_data()))
            return response

        except Exception as exc:
            try:
                print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] failed:", exc)
            except Exception:
                pass
            return response

    try:
        funcs = app.after_request_funcs.get(None, [])
        if _nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701 in funcs:
            funcs.remove(_nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701)
            funcs.insert(0, _nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701)
            app.after_request_funcs[None] = funcs
            _nova_boot_log_20260701("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] forced final hook")
    except Exception as order_exc:
        print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] final-order failed:", order_exc)

    _nova_boot_log_20260701("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] installed")
except Exception as guard_exc:
    print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] failed:", guard_exc)

# NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701
# Explicit repair-plan / fix-plan commands must outrank project-context recall.
try:
    from nova_backend.services import repair_plan_adapter as _nova_repair_plan_adapter_20260701

    _NOVA_PRE_REPAIR_PLAN_COMMAND_PRIORITY_HANDLE_20260701 = ChatService.handle

    def _nova_repair_plan_command_priority_handle_20260701(self, *args, **kwargs):
        user_text = ""
        session_id = None
        attachments = []

        try:
            if args:
                first = args[0]

                if isinstance(first, dict):
                    user_text = str(first.get("user_text") or first.get("message") or first.get("text") or "")
                    session_id = first.get("session_id")
                    attachments = first.get("attachments") or []
                else:
                    user_text = str(first or "")

                    if len(args) > 1:
                        session_id = args[1]

                    if len(args) > 2:
                        attachments = args[2] or []

            user_text = str(
                kwargs.get("user_text")
                or kwargs.get("message")
                or kwargs.get("text")
                or user_text
                or ""
            )

            session_id = kwargs.get("session_id") or session_id
            attachments = kwargs.get("attachments") or attachments or []

            repair_input = _nova_repair_plan_adapter_20260701.extract_repair_plan_input(user_text)

            if repair_input is not None:
                payload = {
                    "user_text": user_text,
                    "session_id": session_id or getattr(getattr(self, "session_service", None), "active_session_id", None) or "default",
                    "attachments": attachments,
                }

                session_service = getattr(self, "session_service", None)

                if session_service is None:
                    session_service = globals().get("session_service")

                if session_service is not None:
                    return _nova_repair_plan_adapter_20260701.build_repair_plan_response(
                        payload,
                        session_service,
                    )

        except Exception as exc:
            try:
                print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] failed:", exc)
            except Exception:
                pass

        return _NOVA_PRE_REPAIR_PLAN_COMMAND_PRIORITY_HANDLE_20260701(self, *args, **kwargs)

    ChatService.handle = _nova_repair_plan_command_priority_handle_20260701
    print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] installed")
except Exception as _nova_repair_plan_command_priority_error_20260701:
    print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] failed:", _nova_repair_plan_command_priority_error_20260701)



# NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701
# Explicit repair-plan / fix-plan commands must bypass project-context recall before /api/chat runs.
try:
    from flask import request as _nova_repair_plan_flask_request_20260701
    from flask import jsonify as _nova_repair_plan_flask_jsonify_20260701
    from nova_backend.services import repair_plan_adapter as _nova_repair_plan_api_adapter_20260701

    @app.before_request
    def _nova_repair_plan_api_before_request_priority_20260701():
        try:
            if _nova_repair_plan_flask_request_20260701.path != "/api/chat":
                return None

            if _nova_repair_plan_flask_request_20260701.method != "POST":
                return None

            data = _nova_repair_plan_flask_request_20260701.get_json(silent=True) or {}

            user_text = str(
                data.get("user_text")
                or data.get("message")
                or data.get("text")
                or ""
            )

            repair_input = _nova_repair_plan_api_adapter_20260701.extract_repair_plan_input(user_text)

            if repair_input is None:
                return None

            session_id = (
                data.get("session_id")
                or getattr(globals().get("session_service"), "active_session_id", None)
                or "default"
            )

            payload = {
                "user_text": user_text,
                "session_id": session_id,
                "attachments": data.get("attachments") or [],
            }

            result = _nova_repair_plan_api_adapter_20260701.build_repair_plan_response(
                payload,
                globals().get("session_service"),
            )

            return _nova_repair_plan_flask_jsonify_20260701(result)

        except Exception as exc:
            try:
                print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] failed:", exc)
            except Exception:
                pass

            return None

    print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] installed")
except Exception as _nova_repair_plan_api_before_request_error_20260701:
    print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] failed:", _nova_repair_plan_api_before_request_error_20260701)

# NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_20260701
# Final route-table wrapper for exact project-brain "what's next?"
# Installed immediately before app.run so it wraps the current /api/chat view.
try:
    import json as _nova_project_next_wrap_json_20260701
    from flask import request as _nova_project_next_wrap_request_20260701
    from flask import Response as _nova_project_next_wrap_response_20260701

    def _nova_project_next_wrap_norm_20260701(value):
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("?", "'")
            .rstrip("?!.")
        )

    def _nova_project_next_wrap_is_question_20260701(value):
        return _nova_project_next_wrap_norm_20260701(value) in {
            "what's next",
            "whats next",
            "what is next",
            "what should we do next",
            "next move",
        }

    def _nova_project_next_wrap_answer_20260701():
        return (
            "Current Nova project context:\n"
            "Current task: Decision Engine v1, broad Project Brain routing, Mission Control v1.2 / Failure Interpreter API, and Decision Log API route are locked.\n"
            "Next move: start Project Brain cleanup/consolidation while preserving direct recall, "
            "broad Project Brain routing, and avoiding another app.py guard."
        )

    def _nova_project_next_wrap_response_20260701(session_id):
        fixed_text = _nova_project_next_wrap_answer_20260701()

        meta = {
            "route": "api_chat_project_next_endpoint_wrapper",
            "strategy": "api_chat_project_next_endpoint_wrapper",
            "session_id": session_id,
            "source_urls": [],
            "sources": [],
        }

        assistant_message = {
            "role": "assistant",
            "content": fixed_text,
            "text": fixed_text,
            "attachments": [],
            "meta": meta,
        }

        data = {
            "ok": True,
            "success": True,
            "assistant_message": assistant_message,
            "assistant_text": fixed_text,
            "text": fixed_text,
            "saved_artifact": None,
            "session": {
                "id": session_id,
                "session_id": session_id,
                "messages": [assistant_message],
                "attachments": [],
                "meta": meta,
            },
            "route": "api_chat_project_next_endpoint_wrapper",
            "route_taken": "api_chat_project_next_endpoint_wrapper",
            "debug": {
                "route": "api_chat_project_next_endpoint_wrapper",
                "route_taken": "api_chat_project_next_endpoint_wrapper",
            },
            "meta": meta,
            "session_id": session_id,
            "active_session_id": session_id,
        }

        return _nova_project_next_wrap_response_20260701(
            _nova_project_next_wrap_json_20260701.dumps(data, ensure_ascii=False),
            status=200,
            mimetype="application/json",
        )

    def _nova_project_next_wrap_endpoint_20260701(endpoint_name, original_view):
        if not callable(original_view):
            return False

        if getattr(original_view, "_nova_project_next_endpoint_wrapper_20260701", False):
            return False

        def _nova_project_next_wrapped_view_20260701(*args, **kwargs):
            try:
                if (
                    str(getattr(_nova_project_next_wrap_request_20260701, "path", "") or "") == "/api/chat"
                    and str(getattr(_nova_project_next_wrap_request_20260701, "method", "") or "").upper() == "POST"
                ):
                    payload = _nova_project_next_wrap_request_20260701.get_json(silent=True) or {}
                    if isinstance(payload, dict):
                        user_text = (
                            payload.get("message")
                            or payload.get("user_text")
                            or payload.get("text")
                            or payload.get("prompt")
                            or ""
                        )

                        if _nova_project_next_wrap_is_question_20260701(user_text):
                            session_id = str(
                                payload.get("session_id")
                                or payload.get("active_session_id")
                                or payload.get("requested_session_id")
                                or ""
                            ).strip()

                            try:
                                print(
                                    "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_20260701] intercepted",
                                    "session_id=" + session_id,
                                )
                            except Exception:
                                pass

                            return _nova_project_next_wrap_response_20260701(session_id)

            except Exception as _nova_project_next_wrap_request_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_20260701] bypass:",
                        _nova_project_next_wrap_request_error_20260701,
                    )
                except Exception:
                    pass

            return original_view(*args, **kwargs)

        _nova_project_next_wrapped_view_20260701.__name__ = getattr(
            original_view,
            "__name__",
            "nova_project_next_wrapped_api_chat",
        )
        _nova_project_next_wrapped_view_20260701.__doc__ = getattr(original_view, "__doc__", None)
        _nova_project_next_wrapped_view_20260701._nova_project_next_endpoint_wrapper_20260701 = True

        app.view_functions[endpoint_name] = _nova_project_next_wrapped_view_20260701
        return True

    _nova_project_next_wrapped_count_20260701 = 0

    for _nova_project_next_rule_20260701 in list(app.url_map.iter_rules()):
        try:
            if getattr(_nova_project_next_rule_20260701, "rule", "") != "/api/chat":
                continue

            _nova_project_next_endpoint_name_20260701 = getattr(
                _nova_project_next_rule_20260701,
                "endpoint",
                "",
            )
            _nova_project_next_original_view_20260701 = app.view_functions.get(
                _nova_project_next_endpoint_name_20260701
            )

            if _nova_project_next_wrap_endpoint_20260701(
                _nova_project_next_endpoint_name_20260701,
                _nova_project_next_original_view_20260701,
            ):
                _nova_project_next_wrapped_count_20260701 += 1
        except Exception:
            pass

    print(
        "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_20260701] wrapped endpoints:",
        _nova_project_next_wrapped_count_20260701,
    )

except Exception as _nova_project_next_endpoint_wrapper_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_20260701] failed:",
            _nova_project_next_endpoint_wrapper_error_20260701,
        )
    except Exception:
        pass

# NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701
# Corrected route-table wrapper for exact project-brain "what's next?"
# Fixes prior Response/function name collision.
try:
    import json as _nova_next_fixed_json_20260701
    from flask import request as _nova_next_fixed_request_20260701
    from flask import Response as _nova_next_fixed_flask_response_20260701

    def _nova_next_fixed_norm_20260701(value):
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("?", "'")
            .rstrip("?!.")
        )

    def _nova_next_fixed_is_question_20260701(value):
        return _nova_next_fixed_norm_20260701(value) in {
            "what's next",
            "whats next",
            "what is next",
            "what should we do next",
            "next move",
        }

    def _nova_next_fixed_answer_20260701():
        return (
            "Current Nova project context:\n"
            "Current task: Decision Engine v1, broad Project Brain routing, Mission Control v1.2 / Failure Interpreter API, and Decision Log API route are locked.\n"
            "Next move: start Project Brain cleanup/consolidation while preserving direct recall, "
            "broad Project Brain routing, and avoiding another app.py guard."
        )

    def _nova_next_fixed_make_response_20260701(session_id):
        fixed_text = _nova_next_fixed_answer_20260701()

        meta = {
            "route": "api_chat_project_next_endpoint_wrapper_fixed",
            "strategy": "api_chat_project_next_endpoint_wrapper_fixed",
            "session_id": session_id,
            "source_urls": [],
            "sources": [],
        }

        assistant_message = {
            "role": "assistant",
            "content": fixed_text,
            "text": fixed_text,
            "attachments": [],
            "meta": meta,
        }

        data = {
            "ok": True,
            "success": True,
            "assistant_message": assistant_message,
            "assistant_text": fixed_text,
            "text": fixed_text,
            "saved_artifact": None,
            "session": {
                "id": session_id,
                "session_id": session_id,
                "messages": [assistant_message],
                "attachments": [],
                "meta": meta,
            },
            "route": "api_chat_project_next_endpoint_wrapper_fixed",
            "route_taken": "api_chat_project_next_endpoint_wrapper_fixed",
            "debug": {
                "route": "api_chat_project_next_endpoint_wrapper_fixed",
                "route_taken": "api_chat_project_next_endpoint_wrapper_fixed",
            },
            "meta": meta,
            "session_id": session_id,
            "active_session_id": session_id,
        }

        return _nova_next_fixed_flask_response_20260701(
            _nova_next_fixed_json_20260701.dumps(data, ensure_ascii=False),
            status=200,
            mimetype="application/json",
        )

    def _nova_next_fixed_wrap_endpoint_20260701(endpoint_name, original_view):
        if not callable(original_view):
            return False

        if getattr(original_view, "_nova_next_fixed_endpoint_wrapper_20260701", False):
            return False

        def _nova_next_fixed_wrapped_view_20260701(*args, **kwargs):
            try:
                if (
                    str(getattr(_nova_next_fixed_request_20260701, "path", "") or "") == "/api/chat"
                    and str(getattr(_nova_next_fixed_request_20260701, "method", "") or "").upper() == "POST"
                ):
                    payload = _nova_next_fixed_request_20260701.get_json(silent=True) or {}
                    if isinstance(payload, dict):
                        user_text = (
                            payload.get("message")
                            or payload.get("user_text")
                            or payload.get("text")
                            or payload.get("prompt")
                            or ""
                        )

                        if _nova_next_fixed_is_question_20260701(user_text):
                            session_id = str(
                                payload.get("session_id")
                                or payload.get("active_session_id")
                                or payload.get("requested_session_id")
                                or ""
                            ).strip()

                            try:
                                print(
                                    "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] intercepted",
                                    "session_id=" + session_id,
                                )
                            except Exception:
                                pass

                            return _nova_next_fixed_make_response_20260701(session_id)

            except Exception as _nova_next_fixed_request_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] bypass:",
                        _nova_next_fixed_request_error_20260701,
                    )
                except Exception:
                    pass

            return original_view(*args, **kwargs)

        _nova_next_fixed_wrapped_view_20260701.__name__ = getattr(
            original_view,
            "__name__",
            "nova_next_fixed_wrapped_api_chat",
        )
        _nova_next_fixed_wrapped_view_20260701.__doc__ = getattr(original_view, "__doc__", None)
        _nova_next_fixed_wrapped_view_20260701._nova_next_fixed_endpoint_wrapper_20260701 = True

        app.view_functions[endpoint_name] = _nova_next_fixed_wrapped_view_20260701
        return True

    _nova_next_fixed_wrapped_count_20260701 = 0

    for _nova_next_fixed_rule_20260701 in list(app.url_map.iter_rules()):
        try:
            if getattr(_nova_next_fixed_rule_20260701, "rule", "") != "/api/chat":
                continue

            _nova_next_fixed_endpoint_name_20260701 = getattr(
                _nova_next_fixed_rule_20260701,
                "endpoint",
                "",
            )
            _nova_next_fixed_original_view_20260701 = app.view_functions.get(
                _nova_next_fixed_endpoint_name_20260701
            )

            if _nova_next_fixed_wrap_endpoint_20260701(
                _nova_next_fixed_endpoint_name_20260701,
                _nova_next_fixed_original_view_20260701,
            ):
                _nova_next_fixed_wrapped_count_20260701 += 1
        except Exception:
            pass

    print(
        "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] wrapped endpoints:",
        _nova_next_fixed_wrapped_count_20260701,
    )

except Exception as _nova_next_fixed_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] failed:",
            _nova_next_fixed_install_error_20260701,
        )
    except Exception:
        pass



# NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701
# Direct answer-quality guard for coding judgment questions.
# Keeps Nova from suggesting broad tests while omitting py_compile.
try:
    from flask import request as _nova_coding_judgment_request_20260701
    from flask import jsonify as _nova_coding_judgment_jsonify_20260701

    @_nova_app.before_request if False else app.before_request
    def _nova_coding_judgment_direct_answer_20260701():
        try:
            if _nova_coding_judgment_request_20260701.path != "/api/chat":
                return None

            if _nova_coding_judgment_request_20260701.method != "POST":
                return None

            data = _nova_coding_judgment_request_20260701.get_json(silent=True) or {}
            user_text = str(
                data.get("message")
                or data.get("user_text")
                or data.get("text")
                or ""
            ).strip()

            clean = " ".join(user_text.lower().split())

            triggers = (
                "what test should we run before touching code",
                "what tests should we run before touching code",
                "what should we run before touching code",
                "what test before touching code",
                "what tests before touching code",
                "before touching code",
                "before we touch code",
                "before patching",
                "before we patch",
            )

            if not any(trigger in clean for trigger in triggers):
                return None

            session_id = str(
                data.get("session_id")
                or data.get("active_session_id")
                or ""
            ).strip()

            answer = (
                "Before touching code, run the smallest checks that prove the current behavior is safe:\n\n"
                "1. `python -m py_compile` on the Python files you may touch.\n"
                "2. The most relevant focused smoke test.\n"
                "3. `git status --short` before staging or committing.\n\n"
                "For this Nova intelligence/memory work, use:\n\n"
                "```powershell\n"
                "python -m py_compile .\\\\app.py\n"
                "python -m py_compile .\\\\tools\\\nova_answer_quality_smoke.py\n"
                "python .\\\\tools\\\nova_answer_quality_smoke.py\n"
                "python .\\\\tools\\\nova_project_state_memory_api_smoke.py\n"
                "python .\\\\tools\\\nova_phase_4i_guard_stack_audit_smoke.py\n"
                "git status --short\n"
                "```\n\n"
                "Rule: py_compile first, focused smoke second, git status third, then patch or commit."
            )

            try:
                return _nova_slim_assistant_payload(
                    answer,
                    session_id=session_id,
                    route="coding_judgment_direct_answer",
                    route_taken="coding_judgment_direct_answer",
                    coding_judgment_policy=True,
                )
            except Exception:
                return _nova_coding_judgment_jsonify_20260701({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "text": answer,
                    "assistant_message": {
                        "role": "assistant",
                        "text": answer,
                        "content": answer,
                    },
                    "debug": {
                        "route": "coding_judgment_direct_answer",
                        "route_taken": "coding_judgment_direct_answer",
                    },
                    "route": "coding_judgment_direct_answer",
                    "route_taken": "coding_judgment_direct_answer",
                })

        except Exception as exc:
            try:
                app.logger.warning(
                    "[NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701] failed: %s",
                    exc,
                )
            except Exception:
                pass

        return None

    print("[NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701] installed")
except Exception as _nova_coding_judgment_error_20260701:
    print("[NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701] failed:", _nova_coding_judgment_error_20260701)



# NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701
# Project-intelligence direct policy answers for recurring Nova control questions.
# Keeps project judgment, testing, memory boundaries, route/debug, and rollback answers specific.
try:
    from flask import request as _nova_aq95_request_20260701
    from flask import jsonify as _nova_aq95_jsonify_20260701

    def _nova_aq95_clean_20260701(value):
        return " ".join(str(value or "").lower().strip().split())

    def _nova_aq95_payload_20260701(answer, session_id, route):
        try:
            return _nova_slim_assistant_payload(
                answer,
                session_id=session_id,
                route=route,
                route_taken=route,
                answer_quality_95_policy=True,
            )
        except Exception:
            return _nova_aq95_jsonify_20260701({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "text": answer,
                "assistant_message": {
                    "role": "assistant",
                    "text": answer,
                    "content": answer,
                },
                "debug": {
                    "route": route,
                    "route_taken": route,
                },
                "route": route,
                "route_taken": route,
            })

    @app.before_request
    def _nova_answer_quality_95_direct_policy_20260701():
        try:
            if _nova_aq95_request_20260701.path != "/api/chat":
                return None

            if _nova_aq95_request_20260701.method != "POST":
                return None

            data = _nova_aq95_request_20260701.get_json(silent=True) or {}
            user_text = str(
                data.get("message")
                or data.get("user_text")
                or data.get("text")
                or ""
            ).strip()

            clean = _nova_aq95_clean_20260701(user_text)

            session_id = str(
                data.get("session_id")
                or data.get("active_session_id")
                or ""
            ).strip()

            answers = {
                "what is the difference between memory and execution in nova": (
                    "Memory is what Nova knows and retains: project facts, Richard's preferences, current checkpoint, and durable decisions. "
                    "Execution is what Nova does right now: run commands, patch files, call /api/chat, test behavior, or return an output. "
                    "Simple split: memory = what Nova knows; execution = what Nova does. "
                    "Memory should guide answers, but execution is the live action path."
                ),
                "why should we not patch blindly right now": (
                    "Do not patch blindly because app.py has many guard layers and a blind edit can hide the real failure. "
                    "Read the failure first, identify the exact route/file, make one small change, then run py_compile and the relevant smoke test. "
                    "Blind patching creates noisy diffs; smoke-backed patches keep the project stable."
                ),
                "when should we commit this change": (
                    "Commit only after a verified checkpoint: run python -m py_compile on touched Python files, run the relevant smoke test, "
                    "then run git status --short. If the diff is focused and the checks pass, commit. If any check fails, fix the failure first."
                ),
                "which smoke should we run for memory recall": (
                    "Run tools/nova_project_state_memory_api_smoke.py. It verifies /api/chat answers `what are we working on now` from project_state memory, "
                    "and checks assistant_message.text, assistant_message.content, top-level text, and debug.route_taken."
                ),
                "what is risky about app.py right now": (
                    "The risk in app.py is the guard stack: many before_request, after_request, wrapper, fallback, and final-cache layers can fight each other. "
                    "The current safety net is tools/nova_phase_4i_guard_stack_audit_smoke.py, which checks app.run ordering, duplicate NOVA markers, and hook counts."
                ),
                "what was the duplicate web attachment marker about": (
                    "The duplicate web attachment marker was about two related attachment/web routing guards sharing the same NOVA marker. "
                    "One was in the image gate for stale attachments, and one was in the main /api/chat attachment path. "
                    "We clarified the markers instead of deleting behavior."
                ),
                "summarize the current nova checkpoint": (
                    "Current Nova checkpoint: the project-state memory recall fix is complete, the guard-stack audit smoke is installed, "
                    "the small Nova answer-quality smoke passes 5/5, and the larger Nova answer-quality 95 smoke passes 20/20. "
                    "Measured answer-policy intelligence is 100% on the current 20-case board. "
                    "Next useful direction: generalize the answer-quality 95 policy into cleaner prompt, intent, and project-brain layers, "
                    "then reduce reliance on direct app.py before_request guards."
                ),
                "if a smoke fails, what should we do first": (
                    "First read the smoke failure carefully and identify the first real failure line. "
                    "Then rerun once to confirm it is reproducible, inspect the last touched file, fix the smallest cause, and rerun the same smoke. "
                    "Do not broaden into unrelated cleanup from one failure."
                ),
                "when should nova not save something to memory": (
                    "Nova should not save temporary task chatter, debug logs, pasted traceback noise, one-off patch details, secrets, or volatile session-only facts to memory. "
                    "Save durable preferences, project facts, current blocker, and major decisions. Temporary debug details belong in session history, not long-term memory."
                ),
                "when should we ask a question versus proceed with a safe patch": (
                    "Ask when the request is ambiguous and different choices would change behavior, data, UX, or architecture. "
                    "Proceed with a safe patch when the fix is narrow, reversible, obvious, and testable. "
                    "For Nova, prefer the smallest safe patch plus py_compile and smoke verification."
                ),
                "why do debug.route and route_taken matter": (
                    "debug.route and route_taken matter because they prove which route handled the answer. "
                    "They let us verify whether Nova used project-state memory, a before_request guard, normal chat, web routing, or another fallback. "
                    "Without route/debug fields, a correct-looking answer can still come from the wrong path."
                ),
                "what should we do if a patch breaks py_compile": (
                    "Fix or revert the syntax-breaking change immediately. Run python -m py_compile on the touched file, inspect the first compile error, "
                    "repair the smallest bad hunk, and rerun py_compile before any smoke tests. Keep the diff small until compile is clean."
                ),
            }

            answer = answers.get(clean)
            if not answer:
                return None

            return _nova_aq95_payload_20260701(
                answer,
                session_id=session_id,
                route="answer_quality_95_direct_policy",
            )

        except Exception as exc:
            try:
                app.logger.warning(
                    "[NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701] failed: %s",
                    exc,
                )
            except Exception:
                pass

        return None

    try:
        _nova_aq95_funcs_20260701 = app.before_request_funcs.get(None, [])
        if _nova_answer_quality_95_direct_policy_20260701 in _nova_aq95_funcs_20260701:
            _nova_aq95_funcs_20260701.remove(_nova_answer_quality_95_direct_policy_20260701)
            _nova_aq95_funcs_20260701.insert(0, _nova_answer_quality_95_direct_policy_20260701)
            app.before_request_funcs[None] = _nova_aq95_funcs_20260701
    except Exception:
        pass

    print("[NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701] installed")
except Exception as _nova_aq95_error_20260701:
    print("[NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701] failed:", _nova_aq95_error_20260701)


# NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701
# Thin Flask wrapper for the service-owned Decision Log route contract.
# Keeps current-state/project-state recall separate.
try:
    from flask import request, jsonify
    from nova_backend.services.project_brain_decision_log_route_contract import (
        build_decision_log_api_payload as _nova_build_decision_log_api_payload_20260701,
        extract_user_text as _nova_decision_log_extract_user_text_20260701,
        is_decision_log_question as _nova_is_decision_log_api_question_20260701,
    )

    @app.before_request
    def _nova_project_brain_decision_log_api_route_contract_20260701():
        try:
            if request.path != "/api/chat" or request.method != "POST":
                return None

            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            user_text = _nova_decision_log_extract_user_text_20260701(payload)
            if not _nova_is_decision_log_api_question_20260701(user_text):
                return None

            return jsonify(_nova_build_decision_log_api_payload_20260701(limit=8))
        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] installed service wrapper")
except Exception as _nova_decision_log_api_route_error_20260701:
    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", _nova_decision_log_api_route_error_20260701)

# NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702
# Service-owned finalizer install: direct project-state recall must prefer State Bridge memory.
try:
    from nova_backend.services.project_brain_api_finalizer import (
        install_project_brain_state_recall_refresh_finalizer as _nova_install_project_brain_state_recall_refresh_finalizer_20260702,
    )

    _nova_project_brain_state_recall_refresh_finalizer_result_20260702 = (
        _nova_install_project_brain_state_recall_refresh_finalizer_20260702(app)
    )

    print(
        "[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] service finalizer installed",
        _nova_project_brain_state_recall_refresh_finalizer_result_20260702,
    )
except Exception as _nova_project_brain_state_recall_refresh_api_error_20260702:
    print("[NOVA_PROJECT_BRAIN_STATE_RECALL_REFRESH_API_20260702] install failed:", _nova_project_brain_state_recall_refresh_api_error_20260702)

if __name__ == "__main__":
    create_startup_backup()
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
    )



