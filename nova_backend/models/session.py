from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List
from uuid import uuid4

from nova_backend.utils.time_utils import iso_now


SessionDict = Dict[str, Any]
MessageDict = Dict[str, Any]


def _now() -> str:
    return iso_now()


def _session_title_from_messages(messages: List[MessageDict]) -> str:
    for message in messages:
        if str(message.get("role", "")).strip().lower() == "user":
            text = str(message.get("text", "")).strip()
            if text:
                return text[:80]
    return "New chat"


def new_message(
    role: str = "user",
    text: str = "",
    message_id: str | None = None,
    attachments: List[Dict[str, Any]] | None = None,
    meta: Dict[str, Any] | None = None,
    source: str = "",
    pending: bool = False,
    streaming: bool = False,
    error: bool = False,
    stopped: bool = False,
    created_at: str | None = None,
    **extra: Any,
) -> MessageDict:
    message: MessageDict = {
        "id": str(message_id or f"msg_{uuid4().hex}"),
        "role": str(role or "user").strip().lower(),
        "text": str(text or ""),
        "source": str(source or ""),
        "created_at": str(created_at or _now()),
        "attachments": attachments if isinstance(attachments, list) else [],
        "meta": meta if isinstance(meta, dict) else {},
        "pending": bool(pending),
        "streaming": bool(streaming),
        "error": bool(error),
        "stopped": bool(stopped),
    }

    if extra:
        message.update(extra)

    return normalize_message(message)


def normalize_message(message: Dict[str, Any] | None) -> MessageDict:
    payload: Dict[str, Any] = deepcopy(message or {})
    now = _now()

    payload["id"] = str(payload.get("id") or f"msg_{uuid4().hex}")
    payload["role"] = str(payload.get("role") or "user").strip().lower()
    payload["text"] = str(payload.get("text") or "")
    payload["source"] = str(payload.get("source") or "")
    payload["created_at"] = str(payload.get("created_at") or now)

    attachments = payload.get("attachments")
    payload["attachments"] = attachments if isinstance(attachments, list) else []

    meta = payload.get("meta")
    payload["meta"] = meta if isinstance(meta, dict) else {}

    payload["pending"] = bool(payload.get("pending", False))
    payload["streaming"] = bool(payload.get("streaming", False))
    payload["error"] = bool(payload.get("error", False))
    payload["stopped"] = bool(payload.get("stopped", False))

    return payload


def normalize_session(session: Dict[str, Any] | None) -> SessionDict:
    payload: Dict[str, Any] = deepcopy(session or {})
    now = _now()

    messages_raw = payload.get("messages")
    messages_list = messages_raw if isinstance(messages_raw, list) else []
    messages = [normalize_message(message) for message in messages_list]

    title = str(payload.get("title") or "").strip()
    if not title:
        title = _session_title_from_messages(messages)

    updated_at = str(payload.get("updated_at") or payload.get("created_at") or now)
    created_at = str(payload.get("created_at") or updated_at or now)

    last_message_preview = ""
    if messages:
        last_text = str(messages[-1].get("text") or "").strip()
        last_message_preview = last_text[:160]

    normalized: SessionDict = {
        "id": str(payload.get("id") or f"session_{uuid4().hex}"),
        "title": title or "New chat",
        "created_at": created_at,
        "updated_at": updated_at,
        "messages": messages,
        "message_count": int(payload.get("message_count") or len(messages)),
        "last_message_preview": str(
            payload.get("last_message_preview") or last_message_preview
        ),
        "pinned": bool(payload.get("pinned", False)),
        "archived": bool(payload.get("archived", False)),
        "meta": payload.get("meta") if isinstance(payload.get("meta"), dict) else {},
    }

    return normalized


def new_session(
    title: str = "New chat",
    session_id: str | None = None,
    messages: List[MessageDict] | None = None,
    **extra: Any,
) -> SessionDict:
    now = _now()
    normalized_messages = [normalize_message(message) for message in (messages or [])]

    resolved_title = str(title or "").strip()
    if not resolved_title:
        resolved_title = _session_title_from_messages(normalized_messages)

    session: SessionDict = {
        "id": str(session_id or f"session_{uuid4().hex}"),
        "title": resolved_title or "New chat",
        "created_at": now,
        "updated_at": now,
        "messages": normalized_messages,
        "message_count": len(normalized_messages),
        "last_message_preview": (
            str(normalized_messages[-1].get("text") or "").strip()[:160]
            if normalized_messages
            else ""
        ),
        "pinned": False,
        "archived": False,
        "meta": {},
    }

    if extra:
        session.update(extra)

    return normalize_session(session)


def create_session(
    title: str = "New chat",
    session_id: str | None = None,
    messages: List[MessageDict] | None = None,
    **extra: Any,
) -> SessionDict:
    return new_session(
        title=title,
        session_id=session_id,
        messages=messages,
        **extra,
    )


def touch_session(session: Dict[str, Any]) -> SessionDict:
    payload = normalize_session(session)
    payload["updated_at"] = _now()
    payload["message_count"] = len(payload["messages"])

    if payload["messages"]:
        payload["last_message_preview"] = str(
            payload["messages"][-1].get("text") or ""
        ).strip()[:160]
    else:
        payload["last_message_preview"] = ""

    if not str(payload.get("title") or "").strip():
        payload["title"] = _session_title_from_messages(payload["messages"])

    return payload


def append_message(session: Dict[str, Any], message: Dict[str, Any]) -> SessionDict:
    payload = normalize_session(session)
    payload["messages"].append(normalize_message(message))
    return touch_session(payload)


__all__ = [
    "SessionDict",
    "MessageDict",
    "new_message",
    "normalize_message",
    "normalize_session",
    "new_session",
    "create_session",
    "touch_session",
    "append_message",
]