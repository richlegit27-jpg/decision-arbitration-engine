from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import re
import uuid


TEXT_KEYS = (
    "message",
    "text",
    "user_text",
    "prompt",
    "content",
    "query",
)

SESSION_KEYS = (
    "session_id",
    "sessionId",
    "conversation_id",
    "conversationId",
    "chat_id",
    "chatId",
)

ATTACHMENT_KEYS = (
    "attachments",
    "files",
    "uploads",
    "pending_attachments",
    "pendingAttachments",
)


@dataclass
class AttachmentItem:
    id: str = ""
    filename: str = ""
    url: str = ""
    mime_type: str = ""
    kind: str = "file"
    raw: dict[str, Any] = field(default_factory=dict)

    def to_model_text(self) -> str:
        label = self.filename or self.id or self.url or "attachment"
        parts = [f"- {label}"]

        if self.kind:
            parts.append(f"type={self.kind}")

        if self.mime_type:
            parts.append(f"mime={self.mime_type}")

        if self.url:
            parts.append(f"url={self.url}")

        return " | ".join(parts)


@dataclass
class ChatTurn:
    request_id: str
    session_id: str
    user_text: str
    attachments: list[AttachmentItem] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    memory: list[dict[str, Any]] = field(default_factory=list)
    attachment_context: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    intent: str = "chat"
    model: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _as_text(payload.get(key))
        if value:
            return value

    return ""


def normalize_user_text(payload: dict[str, Any]) -> str:
    return _first_text(payload, TEXT_KEYS)


def normalize_session_id(payload: dict[str, Any]) -> str:
    session_id = _first_text(payload, SESSION_KEYS)

    if session_id:
        return session_id

    return "default"


def _guess_attachment_kind(filename: str, mime_type: str, url: str) -> str:
    value = " ".join([filename or "", mime_type or "", url or ""]).lower()

    if mime_type.startswith("image/") or re.search(r"\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)", value):
        return "image"

    if mime_type.startswith("audio/") or re.search(r"\.(mp3|wav|m4a|ogg|webm)(\?|#|$)", value):
        return "audio"

    if mime_type.startswith("video/") or re.search(r"\.(mp4|mov|avi|webm|mkv)(\?|#|$)", value):
        return "video"

    if re.search(r"\.(txt|md|json|csv|py|js|html|css|docx|pdf)(\?|#|$)", value):
        return "document"

    return "file"


def normalize_attachment(raw: Any) -> AttachmentItem | None:
    if raw is None:
        return None

    if isinstance(raw, str):
        text = raw.strip()

        if not text:
            return None

        filename = text.rsplit("/", 1)[-1]
        return AttachmentItem(
            id=text,
            filename=filename,
            url=text if text.startswith("/") or text.startswith("http") else "",
            kind=_guess_attachment_kind(filename, "", text),
            raw={"value": text},
        )

    if not isinstance(raw, dict):
        return None

    attachment_id = _as_text(
        raw.get("id")
        or raw.get("upload_id")
        or raw.get("uploadId")
        or raw.get("file_id")
        or raw.get("fileId")
    )

    filename = _as_text(
        raw.get("filename")
        or raw.get("name")
        or raw.get("original_name")
        or raw.get("originalName")
        or raw.get("file_name")
        or raw.get("fileName")
    )

    url = _as_text(
        raw.get("url")
        or raw.get("file_url")
        or raw.get("fileUrl")
        or raw.get("path")
        or raw.get("preview_url")
        or raw.get("previewUrl")
    )

    mime_type = _as_text(
        raw.get("mime_type")
        or raw.get("mimeType")
        or raw.get("content_type")
        or raw.get("contentType")
        or raw.get("type")
    ).lower()

    if not attachment_id and not filename and not url:
        return None

    if not filename and url:
        filename = url.rsplit("/", 1)[-1]

    return AttachmentItem(
        id=attachment_id,
        filename=filename,
        url=url,
        mime_type=mime_type,
        kind=_guess_attachment_kind(filename, mime_type, url),
        raw=dict(raw),
    )


def normalize_attachments(payload: dict[str, Any]) -> list[AttachmentItem]:
    raw_items: list[Any] = []

    for key in ATTACHMENT_KEYS:
        value = payload.get(key)

        if not value:
            continue

        if isinstance(value, list):
            raw_items.extend(value)
        else:
            raw_items.append(value)

    normalized: list[AttachmentItem] = []
    seen: set[str] = set()

    for raw in raw_items:
        item = normalize_attachment(raw)

        if item is None:
            continue

        key = "|".join([item.id, item.filename, item.url])

        if key in seen:
            continue

        seen.add(key)
        normalized.append(item)

    return normalized


def classify_intent(user_text: str, attachments: list[AttachmentItem]) -> str:
    text = (user_text or "").lower()
    has_attachments = bool(attachments)
    has_image = any(item.kind == "image" for item in attachments)

    if has_image and re.search(r"\b(image|photo|picture|screenshot|see|look|what is this|attached)\b", text):
        return "image_attachment"

    if has_attachments and re.search(r"\b(file|attached|attachment|summarize|read|analyze)\b", text):
        return "file_attachment"

    if re.search(r"\b(auto-plan|plan|build|implement|fix|repair|upgrade)\b", text):
        return "build_or_plan"

    if re.search(r"\b(search|latest|today|news|web|look up)\b", text):
        return "fresh_info"

    return "chat"


def _format_history(history: list[dict[str, Any]], limit: int = 12) -> str:
    if not history:
        return ""

    lines: list[str] = []

    for item in history[-limit:]:
        role = _as_text(item.get("role") or item.get("sender") or "message")
        content = _as_text(item.get("content") or item.get("text") or item.get("message"))

        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


def _format_memory(memory: list[dict[str, Any]], limit: int = 8) -> str:
    if not memory:
        return ""

    lines: list[str] = []

    for item in memory[:limit]:
        if isinstance(item, dict):
            text = _as_text(
                item.get("text")
                or item.get("content")
                or item.get("memory")
                or item.get("summary")
            )
        else:
            text = _as_text(item)

        if text:
            lines.append(f"- {text}")

    return "\n".join(lines)


def _format_attachment_context(context: list[dict[str, Any]]) -> str:
    if not context:
        return ""

    lines: list[str] = []

    for item in context:
        if isinstance(item, dict):
            filename = _as_text(item.get("filename") or item.get("name") or item.get("id") or "attachment")
            summary = _as_text(item.get("summary") or item.get("text") or item.get("description") or item.get("content"))
            if summary:
                lines.append(f"- {filename}: {summary}")
        else:
            text = _as_text(item)
            if text:
                lines.append(f"- {text}")

    return "\n".join(lines)


def build_chat_turn_from_request(
    payload: dict[str, Any],
    *,
    history: list[dict[str, Any]] | None = None,
    memory: list[dict[str, Any]] | None = None,
    attachment_context: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    model: str = "",
    metadata: dict[str, Any] | None = None,
) -> ChatTurn:
    if not isinstance(payload, dict):
        payload = {}

    user_text = normalize_user_text(payload)
    attachments = normalize_attachments(payload)

    return ChatTurn(
        request_id=str(uuid.uuid4()),
        session_id=normalize_session_id(payload),
        user_text=user_text,
        attachments=attachments,
        history=history or [],
        memory=memory or [],
        attachment_context=attachment_context or [],
        tool_results=tool_results or [],
        intent=classify_intent(user_text, attachments),
        model=model,
        metadata=metadata or {},
    )


def build_model_messages(turn: ChatTurn) -> list[dict[str, str]]:
    system_parts = [
        "You are Nova.",
        "Answer clearly and use the prepared backend context.",
        "Do not invent attachment contents that are not provided in attachment context.",
    ]

    if turn.intent:
        system_parts.append(f"Detected intent: {turn.intent}.")

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "\n".join(system_parts),
        }
    ]

    history_text = _format_history(turn.history)
    if history_text:
        messages.append(
            {
                "role": "system",
                "content": "Recent session history:\n" + history_text,
            }
        )

    memory_text = _format_memory(turn.memory)
    if memory_text:
        messages.append(
            {
                "role": "system",
                "content": "Relevant memory:\n" + memory_text,
            }
        )

    if turn.attachments:
        attachment_lines = "\n".join(item.to_model_text() for item in turn.attachments)
        messages.append(
            {
                "role": "system",
                "content": "Uploaded attachments:\n" + attachment_lines,
            }
        )

    attachment_context_text = _format_attachment_context(turn.attachment_context)
    if attachment_context_text:
        messages.append(
            {
                "role": "system",
                "content": "Attachment analysis/context:\n" + attachment_context_text,
            }
        )

    if turn.tool_results:
        messages.append(
            {
                "role": "system",
                "content": "Tool results:\n" + _format_attachment_context(turn.tool_results),
            }
        )

    messages.append(
        {
            "role": "user",
            "content": turn.user_text or "",
        }
    )

    return messages


__all__ = [
    "AttachmentItem",
    "ChatTurn",
    "build_chat_turn_from_request",
    "build_model_messages",
    "classify_intent",
    "normalize_attachments",
    "normalize_session_id",
    "normalize_user_text",
]
