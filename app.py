from __future__ import annotations

import json
import mimetypes
import os
import re
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# APP
# =========================================================

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"

OPENAI_CLIENT = None
if OPENAI_API_KEY and OpenAI is not None:
    try:
        OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        OPENAI_CLIENT = None


# =========================================================
# HELPERS
# =========================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        write_json(path, default)
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        write_json(path, default)
        return deepcopy(default)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def summarize_text(value: str, limit: int = 120) -> str:
    text = normalize_text(value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def ensure_store_files() -> None:
    if not SESSIONS_FILE.exists():
        write_json(
            SESSIONS_FILE,
            {
                "active_session_id": "",
                "sessions": [],
            },
        )
    if not ARTIFACTS_FILE.exists():
        write_json(ARTIFACTS_FILE, [])
    if not MEMORY_FILE.exists():
        write_json(MEMORY_FILE, [])


def load_sessions_store() -> dict[str, Any]:
    ensure_store_files()
    store = read_json(
        SESSIONS_FILE,
        {
            "active_session_id": "",
            "sessions": [],
        },
    )
    if not isinstance(store, dict):
        store = {"active_session_id": "", "sessions": []}
    store["active_session_id"] = str(store.get("active_session_id") or "")
    store["sessions"] = safe_list(store.get("sessions"))
    return store


def save_sessions_store(store: dict[str, Any]) -> None:
    write_json(SESSIONS_FILE, store)


def load_artifacts() -> list[dict[str, Any]]:
    ensure_store_files()
    items = read_json(ARTIFACTS_FILE, [])
    return items if isinstance(items, list) else []


def save_artifacts(items: list[dict[str, Any]]) -> None:
    write_json(ARTIFACTS_FILE, items)

def build_artifact_viewer(artifact: dict[str, Any]) -> dict[str, Any]:
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}

    kind = str(artifact.get("kind") or "")
    body = str(artifact.get("body") or artifact.get("content") or "")
    title = str(artifact.get("title") or "Artifact")

    image_url = meta.get("image_url") or artifact.get("image_url") or ""
    source_url = meta.get("source_url") or artifact.get("source_url") or ""
    video_url = meta.get("video_url") or ""
    audio_url = meta.get("audio_url") or ""

    analysis_text = meta.get("analysis_text") or ""
    bullets = meta.get("bullets") if isinstance(meta.get("bullets"), list) else []

    return {
        "kind": kind,
        "title": title,
        "body": body,
        "image_url": image_url,
        "video_url": video_url,
        "audio_url": audio_url,
        "source_url": source_url,
        "analysis_text": analysis_text,
        "bullets": bullets,
    }


def load_memory() -> list[dict[str, Any]]:
    ensure_store_files()
    items = read_json(MEMORY_FILE, [])
    return items if isinstance(items, list) else []


def find_session(store: dict[str, Any], session_id: str) -> dict[str, Any] | None:
    for session in safe_list(store.get("sessions")):
        if str(session.get("id") or "") == str(session_id or ""):
            return session
    return None


def make_session(title: str = "New chat") -> dict[str, Any]:
    session_id = make_id("session")
    now = now_iso()
    return {
        "id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "pinned": False,
        "last_message_preview": "",
        "message_count": 0,
        "messages": [],
    }


def ensure_active_session(store: dict[str, Any]) -> dict[str, Any]:
    active_session_id = str(store.get("active_session_id") or "")
    session = find_session(store, active_session_id)
    if session:
        return session

    sessions = safe_list(store.get("sessions"))
    if sessions:
        store["active_session_id"] = sessions[0]["id"]
        save_sessions_store(store)
        return sessions[0]

    session = make_session("New chat")
    store["sessions"].append(session)
    store["active_session_id"] = session["id"]
    save_sessions_store(store)
    return session


def message_text(message: dict[str, Any]) -> str:
    return normalize_text(
        message.get("text")
        or message.get("content")
        or message.get("body")
        or message.get("message")
        or ""
    )


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(message.get("id") or make_id("msg")),
        "role": str(message.get("role") or "assistant"),
        "text": message_text(message),
        "created_at": str(message.get("created_at") or now_iso()),
        "pending": bool(message.get("pending", False)),
        "streaming": bool(message.get("streaming", False)),
        "stopped": bool(message.get("stopped", False)),
        "error": bool(message.get("error", False)),
        "source": str(message.get("source") or ""),
        "meta": message.get("meta") if isinstance(message.get("meta"), dict) else {},
        "attachments": safe_list(message.get("attachments")),
    }


def session_messages(session: dict[str, Any]) -> list[dict[str, Any]]:
    messages = safe_list(session.get("messages"))
    session["messages"] = messages
    return messages


def recalc_session(session: dict[str, Any]) -> None:
    messages = session_messages(session)
    session["message_count"] = len(messages)
    session["updated_at"] = now_iso()
    preview = ""
    if messages:
        preview = summarize_text(message_text(messages[-1]), 100)
    session["last_message_preview"] = preview


def append_message(session: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    msg = normalize_message(message)
    session_messages(session).append(msg)
    recalc_session(session)
    return msg


def replace_message(session: dict[str, Any], message_id: str, new_message: dict[str, Any]) -> dict[str, Any] | None:
    messages = session_messages(session)
    for index, item in enumerate(messages):
        if str(item.get("id") or "") == str(message_id or ""):
            msg = normalize_message(new_message)
            messages[index] = msg
            recalc_session(session)
            return msg
    return None


def find_message(session: dict[str, Any], message_id: str) -> dict[str, Any] | None:
    for item in session_messages(session):
        if str(item.get("id") or "") == str(message_id or ""):
            return item
    return None


def sanitize_filename(filename: str) -> str:
    raw = Path(str(filename or "upload.bin")).name
    raw = re.sub(r"[^A-Za-z0-9._ -]+", "_", raw).strip()
    return raw or "upload.bin"


def file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0


def normalize_attachment(item: dict[str, Any]) -> dict[str, Any]:
    item = item if isinstance(item, dict) else {}
    attachment_id = str(item.get("id") or item.get("attachment_id") or make_id("att"))
    filename = sanitize_filename(
        str(item.get("filename") or item.get("name") or item.get("title") or "upload.bin")
    )
    stored_name = sanitize_filename(
        str(item.get("stored_name") or item.get("stored_filename") or filename)
    )
    url = str(item.get("url") or item.get("file_url") or item.get("source_url") or "").strip()
    mime_type = str(
        item.get("mime_type")
        or item.get("type")
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    ).strip()
    size = int(item.get("size") or 0) if str(item.get("size") or "").strip() else 0

    return {
        "id": attachment_id,
        "name": filename,
        "filename": filename,
        "stored_name": stored_name,
        "url": url,
        "mime_type": mime_type or "application/octet-stream",
        "size": size,
    }


def normalize_attachments(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in safe_list(items):
        normalized = normalize_attachment(item if isinstance(item, dict) else {})
        out.append(normalized)
    return out


def make_user_message(text: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return normalize_message(
        {
            "id": make_id("user"),
            "role": "user",
            "text": normalize_text(text),
            "created_at": now_iso(),
            "attachments": normalize_attachments(attachments),
        }
    )


def make_assistant_message(
    text: str,
    *,
    message_id: str | None = None,
    source: str = "",
    pending: bool = False,
    streaming: bool = False,
    stopped: bool = False,
    error: bool = False,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return normalize_message(
        {
            "id": message_id or make_id("assistant"),
            "role": "assistant",
            "text": normalize_text(text),
            "created_at": now_iso(),
            "pending": pending,
            "streaming": streaming,
            "stopped": stopped,
            "error": error,
            "source": source,
            "meta": meta or {},
        }
    )


def session_contract_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "session": {
            "id": session.get("id") or "",
            "title": session.get("title") or "Untitled chat",
            "created_at": session.get("created_at") or "",
            "updated_at": session.get("updated_at") or "",
            "pinned": bool(session.get("pinned", False)),
            "last_message_preview": session.get("last_message_preview") or "",
            "message_count": int(session.get("message_count") or 0),
            "messages": session_messages(session),
        },
        "active_session_id": session.get("id") or "",
    }


def session_delete_contract_payload(
    deleted_session_id: str,
    active_session: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "deleted_session_id": deleted_session_id,
        "session": {
            "id": active_session.get("id") or "",
            "title": active_session.get("title") or "Untitled chat",
            "created_at": active_session.get("created_at") or "",
            "updated_at": active_session.get("updated_at") or "",
            "pinned": bool(active_session.get("pinned", False)),
            "last_message_preview": active_session.get("last_message_preview") or "",
            "message_count": int(active_session.get("message_count") or 0),
            "messages": session_messages(active_session),
        },
        "active_session_id": active_session.get("id") or "",
    }


def session_error_payload(
    *,
    error: str,
    active_session_id: str = "",
    deleted_session_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": error,
        "session": None,
        "active_session_id": active_session_id or "",
    }
    if deleted_session_id is not None:
        payload["deleted_session_id"] = deleted_session_id
    return payload


def resolve_session_id_from_request(data: dict[str, Any]) -> str:
    return str(
        data.get("session_id")
        or data.get("id")
        or data.get("active_session_id")
        or ""
    ).strip()


def state_payload(session: dict[str, Any] | None = None) -> dict[str, Any]:
    store = load_sessions_store()
    active = session or ensure_active_session(store)

    raw_artifacts = load_artifacts()
    artifacts: list[dict[str, Any]] = []
    for item in raw_artifacts:
        enriched = dict(item)
        enriched["viewer"] = build_artifact_viewer(item)
        artifacts.append(enriched)

    memory = load_memory()

    sessions_summary: list[dict[str, Any]] = []
    for item in safe_list(store.get("sessions")):
        sessions_summary.append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "Untitled chat",
                "created_at": item.get("created_at") or "",
                "updated_at": item.get("updated_at") or "",
                "pinned": bool(item.get("pinned", False)),
                "last_message_preview": item.get("last_message_preview") or "",
                "message_count": int(item.get("message_count") or 0),
                "messages": safe_list(item.get("messages")),
            }
        )

    return {
        "ok": True,
        "session_id": active.get("id") or "",
        "active_session_id": active.get("id") or "",
        "session": {
            "id": active.get("id") or "",
            "title": active.get("title") or "Untitled chat",
            "created_at": active.get("created_at") or "",
            "updated_at": active.get("updated_at") or "",
            "pinned": bool(active.get("pinned", False)),
            "last_message_preview": active.get("last_message_preview") or "",
            "message_count": int(active.get("message_count") or 0),
            "messages": session_messages(active),
        },
        "messages": session_messages(active),
        "sessions": sessions_summary,
        "artifacts": artifacts,
        "memory": memory,
        "debug": {
            "route_build": "attachment-pipeline-polish-2026-04-07-001",
            "has_openai_api_key": bool(OPENAI_API_KEY),
            "openai_configured": OPENAI_CLIENT is not None,
            "chat_model": OPENAI_MODEL,
            "timestamp": now_iso(),
        },
    }

# =========================================================
# MEMORY + ATTACHMENT INJECTION LOCK
# =========================================================

MEMORY_MAX_ITEMS = 8
MEMORY_MAX_CHARS = 2400
MODEL_HISTORY_LIMIT = 16
ATTACHMENT_CONTEXT_MAX_ITEMS = 6


def _textish(value: Any) -> str:
    return str(value or "").strip()


def _tokenize(value: str) -> list[str]:
    raw = _textish(value).lower()
    parts: list[str] = []
    current: list[str] = []
    for ch in raw:
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                parts.append("".join(current))
                current = []
    if current:
        parts.append("".join(current))
    return parts


def _session_keyword_text(session: dict[str, Any]) -> str:
    bits: list[str] = []
    bits.append(_textish(session.get("title")))
    for msg in safe_list(session.get("messages"))[-12:]:
        role = _textish(msg.get("role")).lower()
        if role in {"user", "assistant"}:
            bits.append(_textish(msg.get("content") or msg.get("text")))
    return " ".join(bit for bit in bits if bit)


def _memory_score(item: dict[str, Any], query_terms: set[str]) -> int:
    text = _textish(item.get("text") or item.get("content") or item.get("body"))
    if not text:
        return -1

    kind = _textish(item.get("kind")).lower()
    source = _textish(item.get("source")).lower()
    hay_terms = set(_tokenize(text))

    overlap = len(query_terms.intersection(hay_terms))
    durable_bonus = 0

    if kind in {"preference", "project", "profile", "instruction", "note"}:
        durable_bonus += 3
    if source in {"manual", "assistant", "memory"}:
        durable_bonus += 1

    return overlap * 5 + durable_bonus


def build_memory_context_block(
    *,
    user_text: str,
    session: dict[str, Any] | None,
) -> str:
    memory_items = safe_list(load_memory())
    if not memory_items:
        return ""

    session = session or {}
    session_text = _session_keyword_text(session)
    query_terms = set(_tokenize(user_text)) | set(_tokenize(session_text))

    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in memory_items:
        score = _memory_score(item, query_terms)
        if score >= 0:
            ranked.append((score, item))

    ranked.sort(
        key=lambda pair: (
            -pair[0],
            _textish(pair[1].get("updated_at") or pair[1].get("created_at")),
        ),
        reverse=False,
    )

    selected: list[str] = []
    total_chars = 0

    for score, item in ranked:
        text = _textish(item.get("text") or item.get("content") or item.get("body"))
        if not text:
            continue

        line = f"- {text}"
        next_len = total_chars + len(line) + 1

        if selected and next_len > MEMORY_MAX_CHARS:
            break
        if len(selected) >= MEMORY_MAX_ITEMS:
            break

        selected.append(line)
        total_chars = next_len

    if not selected:
        return ""

    return "Relevant memory for this request:\n" + "\n".join(selected)


def build_attachment_context_block(attachments: list[dict[str, Any]] | None) -> str:
    normalized = normalize_attachments(attachments)
    if not normalized:
        return ""

    selected = normalized[:ATTACHMENT_CONTEXT_MAX_ITEMS]
    lines: list[str] = []

    for item in selected:
        label = _textish(item.get("filename") or item.get("name") or "Attachment")
        mime_type = _textish(item.get("mime_type") or "application/octet-stream")
        size = int(item.get("size") or 0)
        size_text = f"{size} bytes" if size > 0 else "size unknown"
        lines.append(f"- {label} ({mime_type}, {size_text})")

    return "Attachments for this request:\n" + "\n".join(lines)


def build_messages_for_model(
    session: dict[str, Any],
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
) -> list[dict[str, str]]:
    model_messages: list[dict[str, str]] = []

    memory_block = build_memory_context_block(
        user_text=user_text,
        session=session,
    )
    if memory_block:
        model_messages.append(
            {
                "role": "system",
                "content": (
                    "Use the following durable memory only when it is relevant. "
                    "Do not mention memory explicitly unless the user asks.\n\n"
                    f"{memory_block}"
                ),
            }
        )

    attachment_block = build_attachment_context_block(attachments)
    if attachment_block:
        model_messages.append(
            {
                "role": "system",
                "content": (
                    "The user included file attachments. Use this attachment metadata only when relevant. "
                    "Do not claim to have fully read file contents unless those contents are actually available.\n\n"
                    f"{attachment_block}"
                ),
            }
        )

    history = session_messages(session)[-MODEL_HISTORY_LIMIT:]
    for msg in history:
        role = str(msg.get("role") or "assistant")
        if role not in {"system", "user", "assistant"}:
            continue
        text = message_text(msg).strip()
        if not text:
            continue
        model_messages.append({"role": role, "content": text})

    if regenerate_of:
        target = find_message(session, regenerate_of)
        target_text = message_text(target or {})
        if target_text.strip():
            model_messages.append(
                {
                    "role": "user",
                    "content": (
                        "Please regenerate the assistant answer for the previously generated message below. "
                        "Return a fresh better version only.\n\n"
                        f"Target assistant message:\n{target_text}"
                    ),
                }
            )
    else:
        clean_user_text = normalize_text(user_text).strip()
        if clean_user_text:
            model_messages.append({"role": "user", "content": clean_user_text})
        elif attachment_block:
            model_messages.append(
                {
                    "role": "user",
                    "content": "Please respond using the attached files as context.",
                }
            )

    return model_messages


def local_fallback_response(
    session: dict[str, Any],
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
) -> str:
    if regenerate_of:
        target = find_message(session, regenerate_of)
        target_text = message_text(target or {})
        return (
            "Regenerated response.\n\n"
            f"Target message preview:\n{target_text[:500]}\n\n"
            "No live model is configured, so this is the local fallback path."
        )

    attachment_block = build_attachment_context_block(attachments)
    attachment_suffix = f"\n\n{attachment_block}" if attachment_block else ""
    previous_user_count = sum(1 for m in session_messages(session) if str(m.get("role")) == "user")

    if normalize_text(user_text).strip():
        return (
            f"You said:\n{normalize_text(user_text)}"
            f"{attachment_suffix}\n\n"
            f"This is local fallback reply #{previous_user_count} because no live model is configured."
        )

    return (
        "You sent attachments without text."
        f"{attachment_suffix}\n\n"
        f"This is local fallback reply #{previous_user_count} because no live model is configured."
    )

def stream_model_text(
    session: dict[str, Any],
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
) -> Generator[str, None, None]:
    model_messages = build_messages_for_model(
        session,
        user_text,
        attachments=attachments,
        regenerate_of=regenerate_of,
    )

    if OPENAI_CLIENT is None:
        fallback_text = local_fallback_response(
            session,
            user_text,
            attachments=attachments,
            regenerate_of=regenerate_of,
        )
        for ch in fallback_text:
            yield ch
        return

    stream = OPENAI_CLIENT.chat.completions.create(
        model=OPENAI_MODEL,
        messages=model_messages,
        stream=True,
    )

    for chunk in stream:
        try:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue

            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            content = getattr(delta, "content", None)
            if content:
                yield str(content)
        except Exception:
            continue

# =========================================================
# STREAM CONTRACT LOCK
# =========================================================

def chat_stream_generator(
    *,
    session_id: str,
    user_text: str,
    attachments: list[dict[str, Any]] | None,
    regenerate_of: str | None,
) -> Generator[str, None, None]:
    """
    Backend-true contract:
    - exactly one start
    - zero or more token
    - exactly one final OR one error
    - on abort/disconnect, do not write a second assistant message
    """
    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        session = ensure_active_session(store)

    attachments = normalize_attachments(attachments)

    if not regenerate_of and (normalize_text(user_text).strip() or attachments):
        append_message(session, make_user_message(user_text, attachments))

    target_message = find_message(session, regenerate_of) if regenerate_of else None

    assistant_message_id = (target_message or {}).get("id") if target_message else make_id("assistant")
    assistant_created_at = now_iso()
    final_text = ""
    final_written = False
    started = False

    def persist_final(*, stopped: bool = False, error: bool = False, error_message: str = "") -> dict[str, Any]:
        nonlocal final_written

        if final_written:
            existing = find_message(session, assistant_message_id)
            return existing or {}

        text_value = final_text
        if error and error_message:
            text_value = (text_value + ("\n\n" if text_value else "") + f"[Error] {error_message}").strip()

        assistant_message = normalize_message(
            {
                "id": assistant_message_id,
                "role": "assistant",
                "text": text_value,
                "created_at": assistant_created_at,
                "pending": False,
                "streaming": False,
                "stopped": stopped,
                "error": error,
                "source": "regenerate" if regenerate_of else "send",
                "meta": {
                    "regenerate_of": regenerate_of or "",
                },
            }
        )

        if regenerate_of and target_message:
            replace_message(session, assistant_message_id, assistant_message)
        else:
            existing = find_message(session, assistant_message_id)
            if existing:
                replace_message(session, assistant_message_id, assistant_message)
            else:
                append_message(session, assistant_message)

        save_sessions_store(store)
        final_written = True
        return assistant_message

    try:
        start_event = {
            "type": "start",
            "session_id": session.get("id") or session_id,
            "message_id": assistant_message_id,
            "assistant_message_id": assistant_message_id,
            "mode": "regenerate" if regenerate_of else "send",
        }
        started = True
        yield sse(start_event)

        for token in stream_model_text(
            session,
            user_text,
            attachments=attachments,
            regenerate_of=regenerate_of,
        ):
            final_text += token
            yield sse(
                {
                    "type": "token",
                    "session_id": session.get("id") or session_id,
                    "message_id": assistant_message_id,
                    "assistant_message_id": assistant_message_id,
                    "token": token,
                }
            )

        final_message = persist_final(stopped=False, error=False)

        yield sse(
            {
                "type": "final",
                "ok": True,
                "session_id": session.get("id") or session_id,
                "message_id": assistant_message_id,
                "assistant_message_id": assistant_message_id,
                "message": final_message,
                "messages": session_messages(session),
                "artifacts": load_artifacts(),
                "memory": load_memory(),
            }
        )

    except GeneratorExit:
        raise

    except BrokenPipeError:
        raise

    except Exception as exc:
        error_text = str(exc) or "Generation failed."

        if started:
            try:
                final_message = persist_final(stopped=False, error=True, error_message=error_text)
                yield sse(
                    {
                        "type": "error",
                        "ok": False,
                        "session_id": session.get("id") or session_id,
                        "message_id": assistant_message_id,
                        "assistant_message_id": assistant_message_id,
                        "message": final_message,
                        "error": error_text,
                    }
                )
            except Exception:
                yield sse(
                    {
                        "type": "error",
                        "ok": False,
                        "session_id": session.get("id") or session_id,
                        "message_id": assistant_message_id,
                        "assistant_message_id": assistant_message_id,
                        "error": error_text,
                    }
                )
        else:
            yield sse(
                {
                    "type": "error",
                    "ok": False,
                    "session_id": session.get("id") or session_id,
                    "error": error_text,
                }
            )


def run_non_stream_chat(
    *,
    session_id: str,
    user_text: str,
    attachments: list[dict[str, Any]] | None,
    regenerate_of: str | None,
) -> dict[str, Any]:
    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        session = ensure_active_session(store)

    attachments = normalize_attachments(attachments)

    if not regenerate_of and (normalize_text(user_text).strip() or attachments):
        append_message(session, make_user_message(user_text, attachments))

    target_message = find_message(session, regenerate_of) if regenerate_of else None
    assistant_message_id = (target_message or {}).get("id") if target_message else make_id("assistant")

    parts: list[str] = []
    for chunk in stream_model_text(
        session,
        user_text,
        attachments=attachments,
        regenerate_of=regenerate_of,
    ):
        parts.append(chunk)
    final_text = "".join(parts)

    assistant_message = normalize_message(
        {
            "id": assistant_message_id,
            "role": "assistant",
            "text": final_text,
            "created_at": now_iso(),
            "pending": False,
            "streaming": False,
            "stopped": False,
            "error": False,
            "source": "regenerate" if regenerate_of else "send",
            "meta": {"regenerate_of": regenerate_of or ""},
        }
    )

    if regenerate_of and target_message:
        replace_message(session, assistant_message_id, assistant_message)
    else:
        append_message(session, assistant_message)

    save_sessions_store(store)

    payload = state_payload(session)
    payload["assistant_message"] = assistant_message
    return payload


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def index() -> Any:
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>Nova</h1>", 200


@app.get("/api/health")
def api_health() -> Any:
    return jsonify(
        {
            "ok": True,
            "route_build": "attachment-pipeline-polish-2026-04-07-001",
            "has_openai_api_key": bool(OPENAI_API_KEY),
            "openai_configured": OPENAI_CLIENT is not None,
            "chat_model": OPENAI_MODEL,
            "timestamp": now_iso(),
        }
    )


@app.get("/api/state")
def api_state() -> Any:
    return jsonify(state_payload())


@app.post("/api/upload")
def api_upload() -> Any:
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"ok": False, "error": "file is required"}), 400

    original_name = sanitize_filename(uploaded.filename or "upload.bin")
    attachment_id = make_id("att")
    stored_name = f"{attachment_id}_{original_name}"
    target_path = UPLOADS_DIR / stored_name

    try:
        uploaded.save(target_path)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc) or "upload failed"}), 500

    mime_type = (
        str(uploaded.mimetype or "").strip()
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )

    attachment = normalize_attachment(
        {
            "id": attachment_id,
            "name": original_name,
            "filename": original_name,
            "stored_name": stored_name,
            "url": f"/api/uploads/{stored_name}",
            "mime_type": mime_type,
            "size": file_size(target_path),
        }
    )

    return jsonify(
        {
            "ok": True,
            "attachment": attachment,
            "id": attachment["id"],
            "name": attachment["name"],
            "filename": attachment["filename"],
            "url": attachment["url"],
            "mime_type": attachment["mime_type"],
            "size": attachment["size"],
        }
    )


@app.post("/api/sessions/new")
def api_sessions_new() -> Any:
    store = load_sessions_store()
    session = make_session("New chat")
    store["sessions"].insert(0, session)
    store["active_session_id"] = session["id"]
    save_sessions_store(store)
    return jsonify(session_contract_payload(session))


@app.post("/api/sessions/open")
def api_sessions_open() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = resolve_session_id_from_request(data)

    store = load_sessions_store()
    current_active = str(store.get("active_session_id") or "")

    if not session_id:
        return jsonify(
            session_error_payload(
                error="session_id is required.",
                active_session_id=current_active,
            )
        ), 400

    session = find_session(store, session_id)
    if not session:
        return jsonify(
            session_error_payload(
                error="Session not found.",
                active_session_id=current_active,
            )
        ), 404

    store["active_session_id"] = session["id"]
    save_sessions_store(store)

    return jsonify(session_contract_payload(session))


@app.post("/api/sessions/rename")
def api_sessions_rename() -> Any:
    data = request.get_json(silent=True) or {}

    session_id = resolve_session_id_from_request(data)
    title = str(data.get("title") or "").strip()

    store = load_sessions_store()
    current_active = str(store.get("active_session_id") or "")

    if not session_id:
        return jsonify(
            session_error_payload(
                error="session_id is required.",
                active_session_id=current_active,
            )
        ), 400

    if not title:
        return jsonify(
            session_error_payload(
                error="title is required.",
                active_session_id=current_active,
            )
        ), 400

    session = find_session(store, session_id)
    if not session:
        return jsonify(
            session_error_payload(
                error="Session not found.",
                active_session_id=current_active,
            )
        ), 404

    session["title"] = title
    session["updated_at"] = now_iso()
    save_sessions_store(store)

    return jsonify(session_contract_payload(session))


@app.post("/api/sessions/delete")
def api_sessions_delete() -> Any:
    data = request.get_json(silent=True) or {}

    session_id = resolve_session_id_from_request(data)

    store = load_sessions_store()
    current_active = str(store.get("active_session_id") or "")
    sessions = safe_list(store.get("sessions"))

    if not session_id:
        return jsonify(
            session_error_payload(
                error="session_id is required.",
                active_session_id=current_active,
                deleted_session_id=None,
            )
        ), 400

    delete_index = -1

    for index, session in enumerate(sessions):
        if str(session.get("id") or "") == session_id:
            delete_index = index
            break

    if delete_index < 0:
        return jsonify(
            session_error_payload(
                error="Session not found.",
                active_session_id=current_active,
                deleted_session_id=None,
            )
        ), 404

    deleted_session = sessions.pop(delete_index)
    store["sessions"] = sessions

    active_session: dict[str, Any] | None = None

    if not sessions:
        replacement = make_session("New chat")
        sessions.append(replacement)
        store["sessions"] = sessions
        store["active_session_id"] = replacement["id"]
        active_session = replacement
    else:
        if current_active == session_id:
            store["active_session_id"] = str(sessions[0].get("id") or "")

        active_session = find_session(store, store.get("active_session_id") or "")
        if not active_session:
            active_session = sessions[0]
            store["active_session_id"] = str(active_session.get("id") or "")

    save_sessions_store(store)

    return jsonify(
        session_delete_contract_payload(
            deleted_session.get("id") or "",
            active_session,
        )
    )

@app.post("/api/chat")
def api_chat() -> Any:
    data = request.get_json(silent=True) or {}

    requested_session_id = str(data.get("session_id") or "").strip()
    user_text = normalize_text(data.get("user_text") or "")
    attachments = normalize_attachments(safe_list(data.get("attachments")))
    regenerate_of = str(data.get("regenerate_of") or "").strip() or None

    wants_stream = bool(data.get("stream", False))
    if user_text.lower().startswith("/image"):
        wants_stream = False

    store = load_sessions_store()
    session = find_session(store, requested_session_id) if requested_session_id else None
    if not session:
        session = ensure_active_session(store)
        requested_session_id = session["id"]

    store["active_session_id"] = session["id"]
    save_sessions_store(store)

    print(
        "api_chat debug:",
        {
            "requested_session_id": requested_session_id,
            "raw_user_text": data.get("user_text"),
            "normalized_user_text": user_text,
            "attachments_count": len(attachments),
            "regenerate_of": regenerate_of,
            "wants_stream": wants_stream,
        },
    )

    if not regenerate_of and not user_text.strip() and not attachments:
        return jsonify({"ok": False, "error": "user_text or attachments required for send."}), 400

    if regenerate_of and not find_message(session, regenerate_of):
        return jsonify({"ok": False, "error": "regenerate target not found."}), 404

    if wants_stream:
        return Response(
            chat_stream_generator(
                session_id=requested_session_id,
                user_text=user_text,
                attachments=attachments,
                regenerate_of=regenerate_of,
            ),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:

        # =========================================================
        # IMAGE GENERATION (HARD LOCK)
        # =========================================================

        if user_text.lower().startswith("/image") and not regenerate_of:
            prompt = user_text[len("/image"):].strip()

            if not prompt:
                return jsonify({
                    "ok": False,
                    "error": "Missing prompt after /image"
                }), 400

            if OPENAI_CLIENT is None:
                return jsonify({
                    "ok": False,
                    "error": "OpenAI not configured"
                }), 500

            import base64

            result = OPENAI_CLIENT.images.generate(
                model=os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5"),
                prompt=prompt,
                size=os.getenv("NOVA_IMAGE_SIZE", "1024x1024"),
            )

            image_b64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)

            filename = f"generated_{uuid.uuid4().hex}.png"
            filepath = UPLOADS_DIR / filename

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            image_url = f"/api/uploads/{filename}"
            created_at = now_iso()

            assistant_message = {
                "id": make_id("assistant"),
                "role": "assistant",
                "text": f"![Generated image]({image_url})",
                "created_at": created_at,
                "attachments": [
                    {
                        "id": make_id("att"),
                        "url": image_url,
                        "mime_type": "image/png",
                        "filename": filename,
                        "stored_name": filename,
                        "size": len(image_bytes),
                    }
                ],
                "error": False,
                "pending": False,
                "streaming": False,
                "stopped": False,
                "source": "send",
                "meta": {"regenerate_of": ""},
            }

            append_message(session, assistant_message)
            save_sessions_store(store)

            return jsonify({
                "ok": True,
                "assistant_message": assistant_message,
                "session": session,
                "session_id": session["id"],
                "active_session_id": session["id"],
                "artifacts": [],
                "memory": [],
            })

        # IMAGE ROUTE
        if user_text.lower().startswith("/image") and not regenerate_of:
            prompt = user_text[len("/image"):].strip()

            if not prompt:
                assistant_message = {
                    "id": f"assistant_{uuid.uuid4().hex}",
                    "role": "assistant",
                    "text": "Give me a prompt after /image",
                    "created_at": now_iso(),
                    "attachments": [],
                    "error": False,
                    "pending": False,
                    "streaming": False,
                    "stopped": False,
                    "source": "send",
                    "meta": {"regenerate_of": ""},
                }

                session.setdefault("messages", []).append(assistant_message)
                session["updated_at"] = now_iso()
                session["last_message_preview"] = assistant_message["text"][:140]
                session["message_count"] = len(session.get("messages") or [])

                store["active_session_id"] = session["id"]
                save_sessions_store(store)

                return jsonify(
                    {
                        "ok": True,
                        "assistant_message": assistant_message,
                        "session": session,
                        "session_id": session["id"],
                        "active_session_id": session["id"],
                        "artifacts": [],
                        "memory": [],
                    }
                )

            import base64

            client = OpenAI()

            result = client.images.generate(
                model=os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5"),
                prompt=prompt,
                size=os.getenv("NOVA_IMAGE_SIZE", "1024x1024"),
            )

            image_b64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)

            filename = f"generated_{uuid.uuid4().hex}.png"
            filepath = UPLOADS_DIR / filename

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            image_url = f"/api/uploads/{filename}"
            created_at = now_iso()

            assistant_message = {
                "id": f"assistant_{uuid.uuid4().hex}",
                "role": "assistant",
                "text": f"![Generated image]({image_url})",
                "created_at": created_at,
                "attachments": [
                    {
                        "id": f"att_{uuid.uuid4().hex}",
                        "url": image_url,
                        "mime_type": "image/png",
                        "filename": filename,
                        "stored_name": filename,
                        "size": len(image_bytes),
                        "status": "uploaded",
                        "upload_error": "",
                    }
                ],
                "error": False,
                "pending": False,
                "streaming": False,
                "stopped": False,
                "source": "send",
                "meta": {"regenerate_of": ""},
            }

            artifact = {
                "id": make_id("artifact"),
                "title": f"Image: {prompt[:60]}",
                "kind": "image_generation",
                "image_url": image_url,
                "body": prompt,
                "preview": prompt[:120],
                "session_id": session["id"],
                "created_at": created_at,
                "updated_at": created_at,
                "meta": {
                    "image_url": image_url,
                    "source_url": "",
                    "analysis_text": "",
                    "bullets": [],
                },
            }

            artifact["viewer"] = build_artifact_viewer(artifact)

            append_message(session, assistant_message)

            session["updated_at"] = created_at
            session["last_message_preview"] = f"Generated image: {prompt[:80]}"
            session["message_count"] = len(session.get("messages") or [])

            store["active_session_id"] = session["id"]
            save_sessions_store(store)

            artifacts_store = load_artifacts()
            artifacts_store.insert(0, artifact)
            save_artifacts(artifacts_store)

            payload = state_payload(session)
            payload["assistant_message"] = assistant_message
            return jsonify(payload)

        # NORMAL FLOW
        payload = run_non_stream_chat(
            session_id=requested_session_id,
            user_text=user_text,
            attachments=attachments,
            regenerate_of=regenerate_of,
        )

        return jsonify(payload)

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc) or "Chat failed."}), 500

@app.get("/api/uploads/<path:filename>")
def api_uploads(filename: str) -> Any:
    safe_name = Path(str(filename or "")).name.strip()
    if not safe_name:
        return jsonify({"ok": False, "error": "filename is required"}), 400

    target_path = UPLOADS_DIR / safe_name
    if not target_path.exists() or not target_path.is_file():
        return jsonify({"ok": False, "error": "upload not found"}), 404

    return send_from_directory(UPLOADS_DIR, safe_name)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    ensure_store_files()
    app.run(host="127.0.0.1", port=5001, debug=True)