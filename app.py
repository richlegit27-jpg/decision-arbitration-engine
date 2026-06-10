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


# NOVA_WEAK_BACKEND_RESPONSE_GUARD_LOCK
# NOVA_WEAK_BACKEND_RESPONSE_MOJIBAKE_GUARD_LOCK
def _nova_replace_weak_backend_reply(user_text, result):
    """
    Last-mile response guard.

    Prevents weak generic fallback text like:
    "I'm ready. What are we working on?"
    from being returned as the final assistant response.

    Also catches mojibake variants like:
    "IÃ¢â‚¬â„¢m ready. What are we working on?"
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
            .replace("’", "'")
            .replace("`", "'")
            .replace("´", "'")
            .replace("â€™", "'")
            .replace("ã¢â‚¬â„¢", "'")
            .replace("iã¢â‚¬â„¢m", "i'm")
            .replace("iâ€™m", "i'm")
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
        
                "I’m here. The active Nova phase is frontend/mobile polish. "
                "Give me the next task and I’ll move directly on it."
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
        "ad ·",
        "ads ·",
        "shop ›",
        "wall art ›",
        "free_shipping",
        "furniture & décor",
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

        low = line.lower().strip(" :;-•*|")
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

    return "I’m here. The active Nova phase is frontend/mobile polish. Give me the next task and I’ll move directly on it."


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

        if request.path != "/api/chat" or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        user_text = str(payload.get("user_text") or "").strip()
        # NOVA_AUTO_PLAN_EXECUTION_START_GUARD_20260607
        auto_plan_execution_result = _nova_try_auto_plan_execution_start_20260607(session_id, user_text)
        if auto_plan_execution_result is not None:
            return jsonify(auto_plan_execution_result)
        # NOVA_EXECUTION_STATUS_GUARD_20260607
        execution_status_result = _nova_try_execution_status_20260607(session_id, user_text)
        if execution_status_result is not None:
            return jsonify(execution_status_result)
        # NOVA_EXECUTION_AUTOPLAN_START_GUARD_20260607
        execution_start_result = _nova_try_execution_autoplan_start_20260607(session_id, user_text)
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
            "sup": "I’m here.",
            "how are you": "I’m good. Ready when you are.",
            "how are u": "I’m good. Ready when you are.",
            "how you doing": "I’m good. Ready when you are.",
            "whats up": "I’m here. Ready for the next move.",
            "what's up": "I’m here. Ready for the next move.",
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
            "text": str(user_text or "").strip(),
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
                "text": str(user_text or "").strip(),
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
                            _nova_original_user_text_before_project_context,
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
        if _nova_exec_clean.startswith("auto-plan "):
            _nova_exec_goal = _nova_exec_user_text[len("auto-plan "):].strip() or "Untitled execution mission"
            _nova_goal_lower = _nova_exec_goal.lower()

            if "attachment" in _nova_goal_lower or "upload" in _nova_goal_lower or "preview" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect the attachment upload, payload, and preview flow",
                    "Patch the smallest broken link between upload capture and preview rendering",
                    "Test upload preview, send payload, and attachment summary behavior",
                ]
            elif "mobile" in _nova_goal_lower or "ui" in _nova_goal_lower or "css" in _nova_goal_lower:
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

        _nova_early_auto_plan_result = _nova_try_auto_plan_execution_start_20260607(
            _nova_early_session_id,
            _nova_early_user_text,
        )

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
    data = request_json()

    user_text = str(data.get("user_text") or "").strip()
    requested_session_id = str(data.get("session_id") or "").strip()
    session_id = requested_session_id

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

    attachments = normalize_attachments(data.get("attachments"))

    attachments = normalize_attachments(request.json.get("attachments", []))

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
                .replace("’", "'")
                .replace("â€™", "'")
                .replace("ã¢â‚¬â„¢", "'")
                .replace("iã¢â‚¬â„¢m", "i'm")
                .replace("iâ€™m", "i'm")
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

    if not session_id:
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
                    line += f" — {item.get('url')}"
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

        allow_remembered_attachment_injection = (
            bool(current_request_attachments)
            or any(word in attachment_gate_text for word in attachment_intent_words)
        )

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

        if remembered_session_attachments and not skip_remembered_attachment_context:
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
                _nova_original_user_text_before_project_context,
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
        if attachment_content_lines:
            attachments_for_chat_service = attachments or []
            app.logger.info(
                "[AttachmentContentGate] extracted attachment text handoff active; raw attachments suppressed for chat_service session_id=%s extracted_count=%s",
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
                    "furniture & décor",
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

                    _nova_low = _nova_line.lower().strip(" :;-•*|")
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
                    _nova_topic = "; ".join(_nova_top[:3])
                    _nova_reply = "Attachment analysis:\n"
                    _nova_reply += f"This uploaded attachment contains readable text about: {_nova_topic}.\n\n"
                    _nova_reply += "Key points:\n"
                    for _nova_index, _nova_item in enumerate(_nova_top, start=1):
                        _nova_reply += f"{_nova_index}. {_nova_item}\n"
                    _nova_reply += "\nPreview:\n" + "\n".join(_nova_top[:6])
                else:
                    _nova_reply = (
                        "Attachment analysis:\n"
                        "The attachment was received and text was extracted, but the available extraction looks too noisy to summarize cleanly."
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

            if False and _has_current_attachment and _is_attachment_action:  # DISABLED_20260605 let chat_service summarize attachments
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
                    "furniture & décor",
                    "kitchen appliances",
                    "love, horror and more themes",
                    "plain field in front of mountain peak",
                    "free stock photo",
                    "news.google.com",
                    "direct_url_patch_hit",
                )

                _lines = []
                _seen = set()

                for _raw in _raw_text.splitlines():
                    _line = _nova_attach_re.sub(r"^\s*\d+\.\s*", "", str(_raw or "")).strip()
                    _line = _line.replace("Attachment <unknown>", "uploaded attachment")
                    _line = _line.replace("Attachment content:", "").strip()
                    _line = _nova_attach_re.sub(r"\s+", " ", _line).strip()

                    if not _line:
                        continue

                    _low = _line.lower().strip(" :;-•*|")
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
                        line += f" — {url}"
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

        result = chat_service.handle(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments_for_chat_service,
        )

        try:
            app.logger.info(
                "[api_chat] chat_service.handle result ok=%s active_session_id=%s keys=%s",
                result.get("ok") if isinstance(result, dict) else None,
                result.get("active_session_id") if isinstance(result, dict) else None,
                sorted(list(result.keys())) if isinstance(result, dict) else type(result).__name__,
            )
            # NOVA_SAFE_API_CHAT_WEAK_GUARD_AFTER_HANDLE_LOCK
            result = _nova_replace_weak_backend_reply(user_text, result)

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
                                line = line.replace("", "").strip()
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

                                low = line.lower().strip(" :;-•*|")
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


# FIX_ATTACHMENT_ANALYZER_ROUTE_AND_CALL_LOCK
# Safety repair: make sure /api/chat points to api_chat, not helper functions.
try:
    if "api_chat" in globals():
        for _nova_rule in app.url_map.iter_rules():
            if str(_nova_rule.rule) == "/api/chat":
                app.view_functions[_nova_rule.endpoint] = api_chat
                print(f"[NOVA ROUTE REPAIR] /api/chat endpoint={_nova_rule.endpoint} rebound to api_chat")
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
            line = line.replace("", "").strip()
            line = _nova_endpoint_re.sub(r"^\\s*\\d+\\.\\s*", "", line).strip()
            line = _nova_endpoint_re.sub(r"\\s+", " ", line).strip()

            if not line:
                return ""

            low = line.lower().strip(" :;-•*|")
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
                "furniture décor",
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
                "› shop ›",
                "› wall art ›",
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
        import json
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
            "furniture & décor",
            "kitchen appliances",
            "love, horror and more themes",
            "plain field in front of mountain peak",
            "free stock photo",
            "6000 ×",
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

            low = cleaned.lower().strip(" :;-•*|")
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

        assistant_message["text"] = cleaned_text.strip()
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
        import json
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
            "furniture & décor",
            "kitchen appliances",
            "related content",
        )

        useful = []
        seen = set()

        for raw_line in text_value.splitlines():
            line = re.sub(r"^\s*\d+\.\s*", "", str(raw_line or "")).strip()
            line = line.replace("", "").strip()
            line = line.replace("Attachment <unknown>", "uploaded attachment")
            line = re.sub(r"\s+", " ", line).strip()

            if not line:
                continue

            low = line.lower().strip(" :;-•*|")
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

        assistant_message["text"] = cleaned.strip()
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
        import json
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
            line = line.replace("", "").strip()
            line = re.sub(r"\s+", " ", line).strip()

            if not line:
                continue

            low = line.lower().strip(" :;-•*|")
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

        assistant_message["text"] = cleaned.strip()
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
        import json
        from pathlib import Path

        if request.path != "/api/chat" or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        user_text = str(payload.get("user_text") or "").strip()
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

        store_path = Path(__file__).resolve().parent / "data" / "nova_sessions.json"
        if not store_path.exists():
            return None

        data = json.loads(store_path.read_text(encoding="utf-8"))
        sessions = data.get("sessions") if isinstance(data, dict) else data
        if not isinstance(sessions, list):
            return None

        session = None
        for item in sessions:
            if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                session = item
                break

        if not isinstance(session, dict):
            return None

        messages = session.get("messages") or []
        found_text = ""

        for msg in reversed(messages):
            if not isinstance(msg, dict):
                continue

            text_value = str(msg.get("text") or "")
            if "Attachment " not in text_value or " content:" not in text_value:
                continue

            if "[Attachment file was remembered, but readable text content was not available on disk.]" in text_value:
                continue

            marker_index = text_value.find("Attachment ")
            found_text = text_value[marker_index:].strip()

            for stop_marker in [
                "\n\nSession attachment memory:",
                "\n\nProject-aware context for Nova:",
                "\n\nRelevant persistent memory:",
            ]:
                if stop_marker in found_text:
                    found_text = found_text.split(stop_marker, 1)[0].strip()

            break

        if not found_text:
            return None

        answer = "The last readable attachment content I found in this session was:\n\n" + found_text

        return jsonify({
            "ok": True,
            "active_session_id": session_id,
            "session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "text": answer,
                "attachments": [],
                "meta": {
                    "route": "attachment_followup_recall_gate"
                }
            },
            "debug": {
                "route": "attachment_followup_recall_gate"
            },
            "session_attachments": []
        })

    except Exception:
        return None



# STOP_FAKE_ATTACHMENT_CHAT_20260604
@app.before_request
def _nova_stop_fake_attachment_chat_gate():
    try:
        from flask import request, jsonify

        if request.path != "/api/chat" or request.method != "POST":
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
                "text": "I’m good. Ready when you are.",
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
        import json
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
            raw = sessions_path.read_text(encoding="utf-8").strip()
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



if __name__ == "__main__":
    create_startup_backup()
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
        use_reloader=False,
    )

# ATTACHMENT_MEMORY_SESSION_ALIAS_APP_LOCK



# ATTACHMENT_UI_JUNK_FILTER_LOCK

# ACTUAL_STOP_STALE_ATTACHMENT_MEMORY_LOCK

# KILL_STALE_ATTACHMENT_LOOP_DIRECT_LOCK

# SKIP_PROJECT_CONTEXT_FOR_CASUAL_SHORT_MESSAGES_LOCK

# HARD_BYPASS_CASUAL_GREETINGS_LOCK


# CLEAN_IMAGE_PROMPT_RIGHT_BEFORE_CHAT_SERVICE_LOCK

