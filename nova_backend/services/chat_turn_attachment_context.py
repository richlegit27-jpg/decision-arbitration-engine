# NOVA_CHAT_TURN_ATTACHMENT_CONTEXT_20260705
"""
Backend-owned attachment context helpers for ChatTurn.

This module is intentionally conservative:
- It only uses already-provided attachment metadata/content.
- It does not read files from disk.
- It keeps context compact so model calls do not get bloated.
"""

from __future__ import annotations

from typing import Any


_CONTEXT_MARKER = "NOVA_ATTACHMENT_CONTEXT_20260705"
_MAX_ATTACHMENT_CHARS = 1400
_MAX_TOTAL_CHARS = 4200


def _stringify(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return ""

    if isinstance(value, str):
        return value

    try:
        return str(value)
    except Exception:
        return ""


def _first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)

        if value:
            text = _stringify(value).strip()

            if text:
                return text

    return ""


def _normalize_attachment(item: Any, index: int) -> dict[str, str]:
    if isinstance(item, dict):
        data = item
    else:
        data = {
            "filename": getattr(item, "filename", None) or getattr(item, "name", None),
            "mime_type": getattr(item, "mime_type", None) or getattr(item, "content_type", None),
            "size": getattr(item, "size", None) or getattr(item, "size_bytes", None),
            "summary": getattr(item, "summary", None),
            "text": getattr(item, "text", None),
            "description": getattr(item, "description", None),
        }

    filename = _first_text(
        data,
        (
            "filename",
            "original_filename",
            "name",
            "file_name",
            "title",
            "path",
            "url",
        ),
    )

    mime_type = _first_text(
        data,
        (
            "mime_type",
            "content_type",
            "type",
            "media_type",
        ),
    )

    size = _first_text(
        data,
        (
            "size_bytes",
            "bytes",
            "size",
            "length",
        ),
    )

    summary = _first_text(
        data,
        (
            "summary",
            "attachment_summary",
            "analysis",
            "description",
            "caption",
            "ocr_text",
            "extracted_text",
            "text",
            "content",
            "body",
            "preview",
        ),
    )

    if len(summary) > _MAX_ATTACHMENT_CHARS:
        summary = summary[:_MAX_ATTACHMENT_CHARS].rstrip() + "..."

    return {
        "index": str(index),
        "filename": filename or f"attachment_{index}",
        "mime_type": mime_type,
        "size": size,
        "summary": summary,
    }


def _collect_attachments_from_value(value: Any) -> list[Any]:
    if not value:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, dict):
        for key in (
            "attachments",
            "files",
            "uploads",
            "uploaded_files",
            "pending_attachments",
        ):
            nested = value.get(key)

            if nested:
                return _collect_attachments_from_value(nested)

    return []


def collect_attachments_from_scope(scope: dict[str, Any] | None) -> list[Any]:
    if not isinstance(scope, dict):
        return []

    attachments: list[Any] = []

    for key in (
        "attachments",
        "files",
        "uploads",
        "uploaded_files",
        "pending_attachments",
    ):
        attachments.extend(_collect_attachments_from_value(scope.get(key)))

    for key in (
        "payload",
        "request_json",
        "request_payload",
        "data",
        "body",
        "body_json",
        "json_data",
    ):
        attachments.extend(_collect_attachments_from_value(scope.get(key)))

    seen: set[int] = set()
    unique: list[Any] = []

    for item in attachments:
        marker = id(item)

        if marker in seen:
            continue

        seen.add(marker)
        unique.append(item)

    return unique


def build_attachment_context_text(attachments: list[Any] | tuple[Any, ...] | None) -> str:
    items = list(attachments or [])

    if not items:
        return ""

    lines = [
        f"{_CONTEXT_MARKER}",
        "The user attached file(s). Use this backend-provided attachment context when answering.",
    ]

    for index, item in enumerate(items, start=1):
        normalized = _normalize_attachment(item, index)

        header = f"{index}. {normalized['filename']}"

        details = []

        if normalized["mime_type"]:
            details.append(f"type={normalized['mime_type']}")

        if normalized["size"]:
            details.append(f"size={normalized['size']}")

        if details:
            header += " (" + ", ".join(details) + ")"

        lines.append(header)

        if normalized["summary"]:
            lines.append(f"   summary: {normalized['summary']}")

    text = "\n".join(lines).strip()

    if len(text) > _MAX_TOTAL_CHARS:
        text = text[:_MAX_TOTAL_CHARS].rstrip() + "..."

    return text


def messages_have_attachment_context(messages: Any) -> bool:
    if not isinstance(messages, list):
        return False

    for message in messages:
        if not isinstance(message, dict):
            continue

        content = message.get("content")

        if isinstance(content, str) and _CONTEXT_MARKER in content:
            return True

    return False


def inject_attachment_context_message(
    messages: Any,
    attachments: list[Any] | tuple[Any, ...] | None,
) -> Any:
    if not isinstance(messages, list):
        return messages

    if messages_have_attachment_context(messages):
        return messages

    context = build_attachment_context_text(attachments)

    if not context:
        return messages

    context_message = {
        "role": "system",
        "content": context,
    }

    output = list(messages)

    insert_at = 0

    while insert_at < len(output):
        message = output[insert_at]

        if not isinstance(message, dict):
            break

        if message.get("role") != "system":
            break

        insert_at += 1

    output.insert(insert_at, context_message)

    return output


def nova_chat_turn_inject_attachment_context_from_locals(
    messages: Any,
    scope: dict[str, Any] | None = None,
) -> Any:
    attachments = collect_attachments_from_scope(scope)
    return inject_attachment_context_message(messages, attachments)


# NOVA_CHAT_TURN_ATTACHMENT_HYDRATOR_WIRING_20260705
def nova_chat_turn_inject_attachment_context_from_locals(
    messages: Any,
    scope: dict[str, Any] | None = None,
) -> Any:
    attachments = collect_attachments_from_scope(scope)

    # NOVA_API_CHAT_ATTACHMENT_BOUNDARY_G_CONTEXT_20260705
    try:
        from flask import g, has_request_context

        if has_request_context():
            boundary_attachments = getattr(g, "nova_api_chat_attachments", None) or []
            attachments = list(attachments or []) + list(boundary_attachments or [])
    except Exception:
        pass

    try:
        from nova_backend.services.chat_turn_attachment_hydrator import (
            hydrate_attachments_for_context,
        )

        attachments = hydrate_attachments_for_context(attachments)
    except Exception:
        pass

    return inject_attachment_context_message(messages, attachments)

