# notepad C:\Users\Owner\nova\app.py
from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from flask import Flask, Response, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException

try:
    from flask_cors import CORS
except Exception:
    CORS = None  # type: ignore

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

try:
    from services.document_service import analyze_document_attachment, is_document_attachment
except Exception:
    analyze_document_attachment = None  # type: ignore
    is_document_attachment = None  # type: ignore

try:
    from services.web_service import build_web_debug_payload, merge_web_prompt_into_message_context
except Exception:
    build_web_debug_payload = None  # type: ignore
    merge_web_prompt_into_message_context = None  # type: ignore


# =========================================================
# paths + config
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_PATH = DATA_DIR / "nova_sessions.json"
MEMORY_PATH = DATA_DIR / "nova_memory.json"
ARTIFACTS_PATH = DATA_DIR / "nova_artifacts.json"

APP_NAME = "Nova"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

MAX_HISTORY_MESSAGES = 24
MAX_MEMORY_ITEMS = 50
MAX_MEMORY_PROMPT_ITEMS = 12
MAX_CONTEXT_BLOCK_CHARS = 8000
MAX_DEBUG_PREVIEW_CHARS = 2000
MAX_SESSION_TITLE_CHARS = 120
STREAM_EVENT_RETRY_MS = 1000

SYSTEM_PROMPT = """You are Nova, a sharp, practical, high-agency assistant.
Be direct, useful, and accurate. Prefer concrete action over vague advice.

Use provided context when it is relevant.
Do not claim to have used context that is empty or unavailable.
If attached material is insufficient, say so plainly."""

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)

if CORS:
    CORS(app)


# =========================================================
# helpers
# =========================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def collapse_ws(value: Any) -> str:
    return " ".join(clean_text(value).split()).strip()


def truncate(value: Any, limit: int) -> str:
    text = clean_text(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "...(truncated)"


def coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return collapse_ws(value).lower() in {"1", "true", "yes", "on"}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def json_ok(**payload: Any):
    payload.setdefault("ok", True)
    return jsonify(payload)


def json_error(message: str, status: int = 400, **extra: Any):
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return jsonify(payload), status


def request_json() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def make_message(role: str, content: str, **extra: Any) -> Dict[str, Any]:
    msg = {
        "id": new_id(),
        "role": role,
        "content": clean_text(content),
        "created_at": now_iso(),
    }
    if extra:
        msg.update(extra)
    return msg


def summarize_title_from_text(text: str) -> str:
    text = collapse_ws(text)
    if not text:
        return "New Chat"
    return truncate(text, MAX_SESSION_TITLE_CHARS)


# =========================================================
# session store
# =========================================================

def load_sessions() -> List[Dict[str, Any]]:
    data = load_json_file(SESSIONS_PATH, [])
    if not isinstance(data, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in data:
        item = coerce_dict(item)
        normalized.append(
            {
                "id": clean_text(item.get("id")) or new_id(),
                "title": clean_text(item.get("title")) or "New Chat",
                "created_at": clean_text(item.get("created_at")) or now_iso(),
                "updated_at": clean_text(item.get("updated_at")) or now_iso(),
                "pinned": safe_bool(item.get("pinned")),
                "messages": coerce_list(item.get("messages")),
                "meta": coerce_dict(item.get("meta")),
            }
        )
    return normalized


def save_sessions(sessions: List[Dict[str, Any]]) -> None:
    save_json_file(SESSIONS_PATH, sessions)


def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    session_id = clean_text(session_id).strip()
    for session in load_sessions():
        if clean_text(session.get("id")) == session_id:
            return session
    return None


def upsert_session(session: Dict[str, Any]) -> Dict[str, Any]:
    session = coerce_dict(session)
    sessions = load_sessions()
    session_id = clean_text(session.get("id")) or new_id()
    found = False

    normalized = {
        "id": session_id,
        "title": clean_text(session.get("title")) or "New Chat",
        "created_at": clean_text(session.get("created_at")) or now_iso(),
        "updated_at": clean_text(session.get("updated_at")) or now_iso(),
        "pinned": safe_bool(session.get("pinned")),
        "messages": coerce_list(session.get("messages")),
        "meta": coerce_dict(session.get("meta")),
    }

    for idx, existing in enumerate(sessions):
        if clean_text(existing.get("id")) == session_id:
            sessions[idx] = normalized
            found = True
            break

    if not found:
        sessions.append(normalized)

    save_sessions(sessions)
    return normalized


def delete_session(session_id: str) -> bool:
    session_id = clean_text(session_id).strip()
    sessions = load_sessions()
    kept = [s for s in sessions if clean_text(s.get("id")) != session_id]
    if len(kept) == len(sessions):
        return False
    save_sessions(kept)
    return True


def ensure_session(session_id: Optional[str], first_user_text: str = "") -> Dict[str, Any]:
    if session_id:
        existing = get_session_by_id(session_id)
        if existing:
            return existing

    title = summarize_title_from_text(first_user_text) or "New Chat"
    created = {
        "id": new_id(),
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "pinned": False,
        "messages": [],
        "meta": {},
    }
    return upsert_session(created)


def session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    messages = coerce_list(session.get("messages"))
    last_message = coerce_dict(messages[-1]) if messages else {}
    return {
        "id": clean_text(session.get("id")),
        "title": clean_text(session.get("title")) or "New Chat",
        "created_at": clean_text(session.get("created_at")),
        "updated_at": clean_text(session.get("updated_at")),
        "pinned": safe_bool(session.get("pinned")),
        "message_count": len(messages),
        "last_message_preview": truncate(last_message.get("content", ""), 180),
    }


# =========================================================
# memory store
# =========================================================

def load_memory() -> List[Dict[str, Any]]:
    data = load_json_file(MEMORY_PATH, [])
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        item = coerce_dict(item)
        out.append(
            {
                "id": clean_text(item.get("id")) or new_id(),
                "kind": clean_text(item.get("kind")) or "note",
                "value": clean_text(item.get("value")),
                "created_at": clean_text(item.get("created_at")) or now_iso(),
                "updated_at": clean_text(item.get("updated_at")) or now_iso(),
                "pinned": safe_bool(item.get("pinned")),
            }
        )
    return out[:MAX_MEMORY_ITEMS]


def save_memory(items: List[Dict[str, Any]]) -> None:
    save_json_file(MEMORY_PATH, items[:MAX_MEMORY_ITEMS])


def add_memory_item(kind: str, value: str, pinned: bool = False) -> Dict[str, Any]:
    items = load_memory()
    normalized_value = clean_text(value).strip()
    normalized_kind = clean_text(kind).strip() or "note"

    for item in items:
        if (
            clean_text(item.get("kind")).lower() == normalized_kind.lower()
            and clean_text(item.get("value")).strip().lower() == normalized_value.lower()
        ):
            item["updated_at"] = now_iso()
            item["pinned"] = safe_bool(item.get("pinned")) or pinned
            save_memory(items)
            return item

    created = {
        "id": new_id(),
        "kind": normalized_kind,
        "value": normalized_value,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "pinned": pinned,
    }
    items.insert(0, created)
    save_memory(items)
    return created


def delete_memory_item(memory_id: str) -> bool:
    memory_id = clean_text(memory_id).strip()
    items = load_memory()
    kept = [m for m in items if clean_text(m.get("id")) != memory_id]
    if len(kept) == len(items):
        return False
    save_memory(kept)
    return True


def score_memory_item(item: Dict[str, Any], text: str) -> int:
    hay = collapse_ws(item.get("value")).lower()
    needle = collapse_ws(text).lower()
    if not hay or not needle:
        return 0

    score = 0
    for token in set(needle.split()):
        if len(token) < 3:
            continue
        if token in hay:
            score += 3

    if safe_bool(item.get("pinned")):
        score += 2

    kind = collapse_ws(item.get("kind")).lower()
    if kind in {"preference", "project", "goal", "workflow"}:
        score += 1

    return score


def select_relevant_memory(text: str) -> List[Dict[str, Any]]:
    items = load_memory()
    ranked = sorted(items, key=lambda x: score_memory_item(x, text), reverse=True)
    strong = [item for item in ranked if score_memory_item(item, text) > 0]
    selected = strong[:MAX_MEMORY_PROMPT_ITEMS]
    if not selected:
        selected = [item for item in ranked if safe_bool(item.get("pinned"))][:MAX_MEMORY_PROMPT_ITEMS]
    return selected


# =========================================================
# artifact store
# =========================================================

def load_artifacts() -> List[Dict[str, Any]]:
    data = load_json_file(ARTIFACTS_PATH, [])
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        item = coerce_dict(item)
        out.append(
            {
                "id": clean_text(item.get("id")) or new_id(),
                "title": clean_text(item.get("title")) or "Untitled Artifact",
                "content": clean_text(item.get("content")),
                "kind": clean_text(item.get("kind")) or "text",
                "session_id": clean_text(item.get("session_id")),
                "created_at": clean_text(item.get("created_at")) or now_iso(),
                "updated_at": clean_text(item.get("updated_at")) or now_iso(),
                "pinned": safe_bool(item.get("pinned")),
                "meta": coerce_dict(item.get("meta")),
            }
        )
    return out


def save_artifacts(items: List[Dict[str, Any]]) -> None:
    save_json_file(ARTIFACTS_PATH, items)


def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    artifact_id = clean_text(artifact_id).strip()
    for item in load_artifacts():
        if clean_text(item.get("id")) == artifact_id:
            return item
    return None


def upsert_artifact(item: Dict[str, Any]) -> Dict[str, Any]:
    item = coerce_dict(item)
    artifact_id = clean_text(item.get("id")) or new_id()
    artifacts = load_artifacts()
    normalized = {
        "id": artifact_id,
        "title": clean_text(item.get("title")) or "Untitled Artifact",
        "content": clean_text(item.get("content")),
        "kind": clean_text(item.get("kind")) or "text",
        "session_id": clean_text(item.get("session_id")),
        "created_at": clean_text(item.get("created_at")) or now_iso(),
        "updated_at": now_iso(),
        "pinned": safe_bool(item.get("pinned")),
        "meta": coerce_dict(item.get("meta")),
    }

    found = False
    for idx, existing in enumerate(artifacts):
        if clean_text(existing.get("id")) == artifact_id:
            normalized["created_at"] = clean_text(existing.get("created_at")) or normalized["created_at"]
            artifacts[idx] = normalized
            found = True
            break

    if not found:
        artifacts.insert(0, normalized)

    save_artifacts(artifacts)
    return normalized


def delete_artifact(artifact_id: str) -> bool:
    artifact_id = clean_text(artifact_id).strip()
    items = load_artifacts()
    kept = [a for a in items if clean_text(a.get("id")) != artifact_id]
    if len(kept) == len(items):
        return False
    save_artifacts(kept)
    return True


# =========================================================
# context building
# =========================================================

def normalize_attachments(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in coerce_list(raw):
        item = coerce_dict(item)
        out.append(
            {
                "id": clean_text(item.get("id")) or new_id(),
                "name": clean_text(item.get("name")),
                "mime_type": clean_text(item.get("mime_type") or item.get("type")),
                "type": clean_text(item.get("type")),
                "stored_path": clean_text(item.get("stored_path") or item.get("path")),
                "path": clean_text(item.get("path") or item.get("stored_path")),
                "size": safe_int(item.get("size")),
                "meta": coerce_dict(item.get("meta")),
            }
        )
    return out


def analyze_document_attachments(attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for attachment in attachments:
        try:
            if is_document_attachment and is_document_attachment(attachment):
                if analyze_document_attachment:
                    analyzed = analyze_document_attachment(attachment)
                    if isinstance(analyzed, dict):
                        results.append(analyzed)
        except Exception:
            continue
    return results


def build_context_blocks(
    user_text: str,
    attachments: List[Dict[str, Any]],
) -> Tuple[List[str], Dict[str, Any]]:
    blocks: List[str] = []
    debug: Dict[str, Any] = {
        "memory": [],
        "documents": [],
        "attachments": attachments,
        "web": {},
    }

    memory_items = select_relevant_memory(user_text)
    if memory_items:
        memory_lines = []
        for item in memory_items:
            line = f"- [{clean_text(item.get('kind'))}] {clean_text(item.get('value'))}"
            memory_lines.append(line)
        block = "Saved user memory:\n" + "\n".join(memory_lines)
        blocks.append(truncate(block, MAX_CONTEXT_BLOCK_CHARS))
        debug["memory"] = memory_items

    document_results = analyze_document_attachments(attachments)
    if document_results:
        for doc in document_results:
            prompt_text = clean_text(doc.get("prompt_text"))
            if prompt_text:
                blocks.append(truncate(prompt_text, MAX_CONTEXT_BLOCK_CHARS))
        debug["documents"] = document_results

    if merge_web_prompt_into_message_context:
        try:
            merged = merge_web_prompt_into_message_context(user_text, blocks)
            if isinstance(merged, dict):
                blocks = coerce_list(merged.get("context_blocks")) or blocks
                debug["web"] = coerce_dict(merged.get("web"))
        except Exception:
            debug["web"] = {}

    return blocks, debug


def build_model_messages(
    user_text: str,
    session: Dict[str, Any],
    context_blocks: List[str],
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context_blocks:
        context_text = "\n\n---\n\n".join([clean_text(x) for x in context_blocks if clean_text(x).strip()])
        if context_text.strip():
            messages.append(
                {
                    "role": "system",
                    "content": truncate(context_text, MAX_CONTEXT_BLOCK_CHARS),
                }
            )

    history = coerce_list(session.get("messages"))[-MAX_HISTORY_MESSAGES:]
    for item in history:
        role = clean_text(coerce_dict(item).get("role")).strip().lower()
        content = clean_text(coerce_dict(item).get("content"))
        if role in {"user", "assistant", "system"} and content.strip():
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": clean_text(user_text)})
    return messages


def messages_preview(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in messages:
        out.append(
            {
                "role": clean_text(item.get("role")),
                "content": truncate(item.get("content", ""), MAX_DEBUG_PREVIEW_CHARS),
            }
        )
    return out


# =========================================================
# model
# =========================================================

def model_available() -> bool:
    return client is not None


def create_assistant_text(messages: List[Dict[str, str]], model: str) -> str:
    if not client:
        raise RuntimeError("OpenAI client is not configured. Set OPENAI_API_KEY.")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    choice = response.choices[0]
    content = choice.message.content if choice and choice.message else ""
    return clean_text(content).strip()


def stream_assistant_text(messages: List[Dict[str, str]], model: str) -> Generator[str, None, None]:
    if not client:
        raise RuntimeError("OpenAI client is not configured. Set OPENAI_API_KEY.")

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content or ""
        except Exception:
            delta = ""
        if delta:
            yield delta


# =========================================================
# core chat workflow
# =========================================================

def run_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = coerce_dict(payload)

    user_text = clean_text(payload.get("content") or payload.get("message") or "").strip()
    if not user_text:
        raise ValueError("Missing content.")

    model = clean_text(payload.get("model")) or DEFAULT_MODEL
    session_id = clean_text(payload.get("session_id")).strip() or None
    attachments = normalize_attachments(payload.get("attachments"))

    session = ensure_session(session_id, first_user_text=user_text)

    context_blocks, debug = build_context_blocks(user_text, attachments)
    built_messages = build_model_messages(user_text, session, context_blocks)

    user_message = make_message("user", user_text, attachments=attachments)
    session_messages = coerce_list(session.get("messages"))
    session_messages.append(user_message)
    session["messages"] = session_messages
    session["updated_at"] = now_iso()

    assistant_text = create_assistant_text(built_messages, model=model)
    assistant_message = make_message("assistant", assistant_text, model=model)

    session_messages.append(assistant_message)
    session["messages"] = session_messages
    if len(session_messages) == 2 and clean_text(session.get("title")) == "New Chat":
        session["title"] = summarize_title_from_text(user_text)
    session["updated_at"] = now_iso()
    saved = upsert_session(session)

    return {
        "ok": True,
        "session": saved,
        "message": assistant_message,
        "debug": {
            "model": model,
            "history_count": len(coerce_list(session.get("messages"))) - 2,
            "message_count": len(built_messages),
            "messages_preview": messages_preview(built_messages),
            "memory": debug.get("memory", []),
            "documents": debug.get("documents", []),
            "attachments": attachments,
            "web": debug.get("web", {}),
            "system_prompt_preview": truncate(SYSTEM_PROMPT, MAX_DEBUG_PREVIEW_CHARS),
            "memory_update": "",
        },
    }


# =========================================================
# routes
# =========================================================

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    sessions = load_sessions()
    return json_ok(
        app=APP_NAME,
        status="ok",
        model=DEFAULT_MODEL,
        model_connected=model_available(),
        key_present=bool(OPENAI_API_KEY),
        key_prefix=(OPENAI_API_KEY[:7] + "***") if OPENAI_API_KEY else "",
        sessions_count=len(sessions),
    )


@app.get("/api/models")
def api_models():
    models = []
    for name in [DEFAULT_MODEL, "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"]:
        if name not in models:
            models.append(name)
    return json_ok(default=DEFAULT_MODEL, models=models)


@app.get("/api/state")
def api_state():
    sessions = load_sessions()
    ordered = sorted(
        sessions,
        key=lambda s: (
            0 if safe_bool(s.get("pinned")) else 1,
            clean_text(s.get("updated_at")),
        ),
        reverse=False,
    )
    ordered = sorted(
        ordered,
        key=lambda s: safe_bool(s.get("pinned")),
        reverse=True,
    )
    ordered = sorted(
        ordered,
        key=lambda s: clean_text(s.get("updated_at")),
        reverse=True,
    )
    summaries = [session_summary(s) for s in ordered]
    return json_ok(
        app=APP_NAME,
        model=DEFAULT_MODEL,
        sessions=summaries,
        active_session_id=summaries[0]["id"] if summaries else None,
    )


@app.post("/api/session/new")
def api_session_new():
    payload = request_json()
    title = clean_text(payload.get("title")).strip() or "New Chat"
    session = {
        "id": new_id(),
        "title": truncate(title, MAX_SESSION_TITLE_CHARS),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "pinned": False,
        "messages": [],
        "meta": {},
    }
    saved = upsert_session(session)
    return json_ok(session=saved)


@app.post("/api/session/delete")
def api_session_delete():
    payload = request_json()
    session_id = clean_text(payload.get("session_id")).strip()
    if not session_id:
        return json_error("Missing session_id.")
    ok = delete_session(session_id)
    if not ok:
        return json_error("Session not found.", status=404)
    return json_ok(deleted=True, session_id=session_id)


@app.post("/api/session/rename")
def api_session_rename():
    payload = request_json()
    session_id = clean_text(payload.get("session_id")).strip()
    title = clean_text(payload.get("title")).strip()
    if not session_id:
        return json_error("Missing session_id.")
    session = get_session_by_id(session_id)
    if not session:
        return json_error("Session not found.", status=404)
    session["title"] = truncate(title or "New Chat", MAX_SESSION_TITLE_CHARS)
    session["updated_at"] = now_iso()
    saved = upsert_session(session)
    return json_ok(session=saved)


@app.post("/api/session/duplicate")
def api_session_duplicate():
    payload = request_json()
    session_id = clean_text(payload.get("session_id")).strip()
    source = get_session_by_id(session_id)
    if not source:
        return json_error("Session not found.", status=404)

    duplicated = {
        "id": new_id(),
        "title": truncate(f"{clean_text(source.get('title'))} Copy", MAX_SESSION_TITLE_CHARS),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "pinned": False,
        "messages": coerce_list(source.get("messages")),
        "meta": coerce_dict(source.get("meta")),
    }
    saved = upsert_session(duplicated)
    return json_ok(session=saved)


@app.post("/api/session/pin")
def api_session_pin():
    payload = request_json()
    session_id = clean_text(payload.get("session_id")).strip()
    pinned = safe_bool(payload.get("pinned"))
    session = get_session_by_id(session_id)
    if not session:
        return json_error("Session not found.", status=404)
    session["pinned"] = pinned
    session["updated_at"] = now_iso()
    saved = upsert_session(session)
    return json_ok(session=saved)


@app.get("/api/chat/<session_id>")
def api_chat_get(session_id: str):
    session = get_session_by_id(session_id)
    if not session:
        return json_error("Session not found.", status=404)
    return json_ok(session=session)


@app.post("/api/chat")
def api_chat():
    try:
        result = run_chat(request_json())
        return jsonify(result)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except Exception as exc:
        return json_error(
            f"Chat failed: {exc}",
            status=500,
            trace=traceback.format_exc(limit=2),
        )


@app.post("/api/chat/stream")
def api_chat_stream():
    payload = request_json()
    user_text = clean_text(payload.get("content") or payload.get("message") or "").strip()
    if not user_text:
        return json_error("Missing content.")

    model = clean_text(payload.get("model")) or DEFAULT_MODEL
    session_id = clean_text(payload.get("session_id")).strip() or None
    attachments = normalize_attachments(payload.get("attachments"))

    session = ensure_session(session_id, first_user_text=user_text)
    context_blocks, debug = build_context_blocks(user_text, attachments)
    built_messages = build_model_messages(user_text, session, context_blocks)

    user_message = make_message("user", user_text, attachments=attachments)
    session_messages = coerce_list(session.get("messages"))
    session_messages.append(user_message)
    session["messages"] = session_messages
    session["updated_at"] = now_iso()
    if len(session_messages) == 1 and clean_text(session.get("title")) == "New Chat":
        session["title"] = summarize_title_from_text(user_text)
    session = upsert_session(session)

    def event(name: str, data: Dict[str, Any]) -> str:
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate() -> Generator[str, None, None]:
        collected: List[str] = []
        try:
            yield f"retry: {STREAM_EVENT_RETRY_MS}\n\n"
            yield event(
                "start",
                {
                    "ok": True,
                    "session_id": clean_text(session.get("id")),
                    "model": model,
                    "debug": {
                        "message_count": len(built_messages),
                        "messages_preview": messages_preview(built_messages),
                        "memory": debug.get("memory", []),
                        "documents": debug.get("documents", []),
                        "attachments": attachments,
                        "web": debug.get("web", {}),
                        "system_prompt_preview": truncate(SYSTEM_PROMPT, MAX_DEBUG_PREVIEW_CHARS),
                    },
                },
            )

            for token in stream_assistant_text(built_messages, model=model):
                collected.append(token)
                yield event("delta", {"delta": token})

            final_text = "".join(collected).strip()
            assistant_message = make_message("assistant", final_text, model=model)

            latest = get_session_by_id(clean_text(session.get("id"))) or session
            latest_messages = coerce_list(latest.get("messages"))
            latest_messages.append(assistant_message)
            latest["messages"] = latest_messages
            latest["updated_at"] = now_iso()
            saved = upsert_session(latest)

            yield event(
                "done",
                {
                    "ok": True,
                    "session": session_summary(saved),
                    "message": assistant_message,
                },
            )
        except Exception as exc:
            yield event(
                "error",
                {
                    "ok": False,
                    "error": f"Stream failed: {exc}",
                },
            )

    return Response(generate(), mimetype="text/event-stream")


@app.post("/api/debug/brain")
def api_debug_brain():
    payload = request_json()
    user_text = clean_text(payload.get("content") or payload.get("message") or "").strip()
    if not user_text:
        return json_error("Missing content.")

    session_id = clean_text(payload.get("session_id")).strip() or None
    attachments = normalize_attachments(payload.get("attachments"))
    session = ensure_session(session_id, first_user_text=user_text)
    context_blocks, debug = build_context_blocks(user_text, attachments)
    built_messages = build_model_messages(user_text, session, context_blocks)

    return json_ok(
        debug={
            "model": clean_text(payload.get("model")) or DEFAULT_MODEL,
            "history_count": len(coerce_list(session.get("messages"))),
            "message_count": len(built_messages),
            "messages_preview": messages_preview(built_messages),
            "memory": debug.get("memory", []),
            "documents": debug.get("documents", []),
            "attachments": attachments,
            "web": debug.get("web", {}),
            "memory_update": "",
            "system_prompt_preview": truncate(SYSTEM_PROMPT, MAX_DEBUG_PREVIEW_CHARS),
        }
    )


@app.post("/api/debug/web_preview")
def api_debug_web_preview():
    payload = request_json()
    text = clean_text(payload.get("text") or payload.get("content")).strip()
    if not text:
        return json_error("Missing text.")

    if build_web_debug_payload:
        try:
            return json_ok(debug=build_web_debug_payload(text))
        except Exception as exc:
            return json_error(f"Web preview failed: {exc}", status=500)

    return json_ok(
        debug={
            "enabled": False,
            "input": truncate(text, 500),
            "summary": "web_service is unavailable.",
            "previews": [],
            "urls": [],
            "meta": {},
        }
    )


# =========================================================
# memory routes
# =========================================================

@app.get("/api/memory")
def api_memory_list():
    items = load_memory()
    return json_ok(items=items)


@app.post("/api/memory/add")
def api_memory_add():
    payload = request_json()
    kind = clean_text(payload.get("kind")).strip() or "note"
    value = clean_text(payload.get("value")).strip()
    pinned = safe_bool(payload.get("pinned"))
    if not value:
        return json_error("Missing value.")
    item = add_memory_item(kind=kind, value=value, pinned=pinned)
    return json_ok(item=item)


@app.post("/api/memory/delete")
def api_memory_delete():
    payload = request_json()
    memory_id = clean_text(payload.get("id") or payload.get("memory_id")).strip()
    if not memory_id:
        return json_error("Missing id.")
    ok = delete_memory_item(memory_id)
    if not ok:
        return json_error("Memory item not found.", status=404)
    return json_ok(deleted=True, id=memory_id)


# =========================================================
# artifact routes
# =========================================================

@app.get("/api/artifacts")
def api_artifacts_list():
    session_id = clean_text(request.args.get("session_id")).strip()
    items = load_artifacts()
    if session_id:
        items = [item for item in items if clean_text(item.get("session_id")) == session_id]

    items = sorted(
        items,
        key=lambda a: (safe_bool(a.get("pinned")), clean_text(a.get("updated_at"))),
        reverse=True,
    )
    return json_ok(artifacts=items)


@app.get("/api/artifacts/<artifact_id>")
def api_artifacts_get(artifact_id: str):
    item = get_artifact(artifact_id)
    if not item:
        return json_error("Artifact not found.", status=404)
    return json_ok(artifact=item)


@app.post("/api/artifacts/create")
def api_artifacts_create():
    payload = request_json()
    item = upsert_artifact(
        {
            "title": clean_text(payload.get("title")).strip() or "Untitled Artifact",
            "content": clean_text(payload.get("content")),
            "kind": clean_text(payload.get("kind")).strip() or "text",
            "session_id": clean_text(payload.get("session_id")).strip(),
            "meta": coerce_dict(payload.get("meta")),
            "pinned": safe_bool(payload.get("pinned")),
        }
    )
    return json_ok(artifact=item)


@app.post("/api/artifacts/save")
def api_artifacts_save():
    payload = request_json()
    item = upsert_artifact(
        {
            "id": clean_text(payload.get("id")).strip(),
            "title": clean_text(payload.get("title")).strip() or "Untitled Artifact",
            "content": clean_text(payload.get("content")),
            "kind": clean_text(payload.get("kind")).strip() or "text",
            "session_id": clean_text(payload.get("session_id")).strip(),
            "meta": coerce_dict(payload.get("meta")),
            "pinned": safe_bool(payload.get("pinned")),
        }
    )
    return json_ok(artifact=item)


@app.post("/api/artifacts/update")
def api_artifacts_update():
    payload = request_json()
    artifact_id = clean_text(payload.get("id")).strip()
    existing = get_artifact(artifact_id)
    if not existing:
        return json_error("Artifact not found.", status=404)

    existing["title"] = clean_text(payload.get("title") or existing.get("title")).strip() or "Untitled Artifact"
    existing["content"] = clean_text(payload.get("content") if "content" in payload else existing.get("content"))
    existing["kind"] = clean_text(payload.get("kind") or existing.get("kind")).strip() or "text"
    existing["session_id"] = clean_text(payload.get("session_id") or existing.get("session_id")).strip()
    existing["meta"] = coerce_dict(payload.get("meta") or existing.get("meta"))
    if "pinned" in payload:
        existing["pinned"] = safe_bool(payload.get("pinned"))

    item = upsert_artifact(existing)
    return json_ok(artifact=item)


@app.post("/api/artifacts/delete")
def api_artifacts_delete():
    payload = request_json()
    artifact_id = clean_text(payload.get("id")).strip()
    if not artifact_id:
        return json_error("Missing id.")
    ok = delete_artifact(artifact_id)
    if not ok:
        return json_error("Artifact not found.", status=404)
    return json_ok(deleted=True, id=artifact_id)


@app.post("/api/artifacts/pin")
def api_artifacts_pin():
    payload = request_json()
    artifact_id = clean_text(payload.get("id")).strip()
    existing = get_artifact(artifact_id)
    if not existing:
        return json_error("Artifact not found.", status=404)
    existing["pinned"] = safe_bool(payload.get("pinned"))
    item = upsert_artifact(existing)
    return json_ok(artifact=item)


@app.post("/api/artifacts/toggle-pin")
def api_artifacts_toggle_pin():
    payload = request_json()
    artifact_id = clean_text(payload.get("id")).strip()
    existing = get_artifact(artifact_id)
    if not existing:
        return json_error("Artifact not found.", status=404)
    existing["pinned"] = not safe_bool(existing.get("pinned"))
    item = upsert_artifact(existing)
    return json_ok(artifact=item)


@app.post("/api/artifacts/export")
def api_artifacts_export():
    payload = request_json()
    artifact_id = clean_text(payload.get("id")).strip()
    item = get_artifact(artifact_id)
    if not item:
        return json_error("Artifact not found.", status=404)

    export_path = DATA_DIR / f"artifact_{artifact_id}.txt"
    export_text = (
        f"Title: {clean_text(item.get('title'))}\n"
        f"Kind: {clean_text(item.get('kind'))}\n"
        f"Session: {clean_text(item.get('session_id'))}\n"
        f"Created: {clean_text(item.get('created_at'))}\n"
        f"Updated: {clean_text(item.get('updated_at'))}\n\n"
        f"{clean_text(item.get('content'))}"
    )
    export_path.write_text(export_text, encoding="utf-8")
    return send_file(export_path, as_attachment=True, download_name=f"{clean_text(item.get('title')) or 'artifact'}.txt")


# =========================================================
# error handlers
# =========================================================

@app.errorhandler(HTTPException)
def handle_http_exception(exc: HTTPException):
    return json_error(exc.description or exc.name, status=exc.code or 500)


@app.errorhandler(Exception)
def handle_exception(exc: Exception):
    return json_error(
        f"Server error: {exc}",
        status=500,
        trace=traceback.format_exc(limit=3),
    )


# =========================================================
# main
# =========================================================

if __name__ == "__main__":
    port = safe_int(os.getenv("PORT"), 5001)
    debug = safe_bool(os.getenv("FLASK_DEBUG", "true"))
    app.run(host="127.0.0.1", port=port, debug=debug, threaded=True)