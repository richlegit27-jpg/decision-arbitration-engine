# NOVA_API_CHAT_ATTACHMENT_BOUNDARY_NORMALIZER_20260705
"""
Normalize attachment aliases at the API boundary.

The mobile/client layer has used several field names over time:
attachments, files, uploads, uploaded_files, pending_attachments, and nested payloads.

This helper does not read files and does not mutate the incoming payload.
It only returns a deduped attachment list.
"""

from __future__ import annotations

from typing import Any


_ATTACHMENT_CONTAINER_KEYS = (
    "attachments",
    "files",
    "uploads",
    "uploaded_files",
    "pending_attachments",
)

_NESTED_KEYS = (
    "payload",
    "request_json",
    "request_payload",
    "data",
    "body",
    "body_json",
    "json_data",
    "message_payload",
    "chat_payload",
    "request",
    "chat_request",
    "turn",
    "chat_turn",
)

_ATTACHMENT_ID_KEYS = (
    "id",
    "attachment_id",
    "upload_id",
    "file_id",
    "url",
    "download_url",
    "src",
    "href",
    "path",
    "local_path",
    "file_path",
    "filepath",
    "saved_path",
    "server_path",
    "filename",
    "original_filename",
    "name",
    "file_name",
)

_ATTACHMENT_SHAPE_KEYS = set(_ATTACHMENT_ID_KEYS) | {
    "mime_type",
    "content_type",
    "type",
    "media_type",
    "size",
    "size_bytes",
    "bytes",
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
}


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, bytes, int, float, bool))


def _looks_like_attachment(value: Any) -> bool:
    if not isinstance(value, dict):
        return False

    keys = set(value.keys())

    if not (keys & _ATTACHMENT_SHAPE_KEYS):
        return False

    # Avoid treating the whole chat payload as an attachment just because it has "text".
    chat_only_keys = {
        "message",
        "messages",
        "session_id",
        "sessionId",
        "user_text",
        "prompt",
    }

    has_attachment_id = bool(keys & set(_ATTACHMENT_ID_KEYS))
    has_file_type = bool(keys & {"mime_type", "content_type", "media_type"})
    has_existing_summary = bool(
        keys
        & {
            "summary",
            "attachment_summary",
            "analysis",
            "description",
            "caption",
            "ocr_text",
            "extracted_text",
            "preview",
        }
    )

    if keys & chat_only_keys and not (has_attachment_id or has_file_type or has_existing_summary):
        return False

    return has_attachment_id or has_file_type or has_existing_summary


def _dedupe_key(item: Any) -> tuple[str, str]:
    if not isinstance(item, dict):
        return ("object", str(id(item)))

    for key in _ATTACHMENT_ID_KEYS:
        value = item.get(key)

        if value:
            return (key, str(value))

    return ("object", str(id(item)))


def _collect(value: Any, depth: int = 0, seen: set[int] | None = None) -> list[Any]:
    if value is None or depth > 6 or _is_scalar(value):
        return []

    if seen is None:
        seen = set()

    marker = id(value)

    if marker in seen:
        return []

    seen.add(marker)

    found: list[Any] = []

    if isinstance(value, dict):
        if _looks_like_attachment(value):
            found.append(value)

        for key in _ATTACHMENT_CONTAINER_KEYS:
            child = value.get(key)

            if isinstance(child, (list, tuple, set)):
                for item in child:
                    if _looks_like_attachment(item):
                        found.append(item)
                    else:
                        found.extend(_collect(item, depth + 1, seen))
            elif _looks_like_attachment(child):
                found.append(child)
            else:
                found.extend(_collect(child, depth + 1, seen))

        for key in _NESTED_KEYS:
            found.extend(_collect(value.get(key), depth + 1, seen))

        return found

    if isinstance(value, (list, tuple, set)):
        for item in value:
            if _looks_like_attachment(item):
                found.append(item)
            else:
                found.extend(_collect(item, depth + 1, seen))

    return found


def normalize_api_chat_attachments(payload: Any) -> list[Any]:
    found = _collect(payload)

    unique: list[Any] = []
    seen_keys: set[tuple[str, str]] = set()

    for item in found:
        key = _dedupe_key(item)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        unique.append(item)

    return unique
