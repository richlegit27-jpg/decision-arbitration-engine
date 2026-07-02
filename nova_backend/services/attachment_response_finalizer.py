
from __future__ import annotations

from copy import deepcopy
from typing import Any


ATTACHMENT_RESPONSE_FINALIZER_NAME = "nova_attachment_response_finalizer_v1"


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def clean_attachment_item(item: Any) -> dict:
    if not isinstance(item, dict):
        return {}

    cleaned = {}

    for key in (
        "filename",
        "name",
        "original_name",
        "path",
        "url",
        "mime_type",
        "content_type",
        "size",
        "size_bytes",
        "kind",
        "type",
        "summary",
        "text",
    ):
        value = item.get(key)
        if value is not None and value != "":
            cleaned[key] = value

    return cleaned


def normalize_attachments(value: Any) -> list[dict]:
    result = []
    seen = set()

    for item in _as_list(value):
        cleaned = clean_attachment_item(item)
        if not cleaned:
            continue

        identity = (
            str(cleaned.get("filename") or cleaned.get("name") or "").strip(),
            str(cleaned.get("url") or cleaned.get("path") or "").strip(),
            str(cleaned.get("mime_type") or cleaned.get("content_type") or "").strip(),
        )

        if identity in seen:
            continue

        seen.add(identity)
        result.append(cleaned)

    return result


def extract_response_attachments(payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        return []

    assistant_message = _as_dict(payload.get("assistant_message"))
    debug = _as_dict(payload.get("debug"))

    candidates = []

    for key in ("attachments", "session_attachments", "uploaded_attachments"):
        candidates.extend(_as_list(payload.get(key)))

    for key in ("attachments", "session_attachments"):
        candidates.extend(_as_list(assistant_message.get(key)))

    for key in ("attachments", "session_attachments"):
        candidates.extend(_as_list(debug.get(key)))

    return normalize_attachments(candidates)


def should_finalize_attachment_response(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    if extract_response_attachments(payload):
        return True

    assistant_message = _as_dict(payload.get("assistant_message"))

    return any(
        key in payload or key in assistant_message
        for key in ("attachments", "session_attachments", "uploaded_attachments")
    )


def finalize_attachment_response_payload(
    payload: dict,
    *,
    preserve_existing: bool = True,
) -> dict:
    if not should_finalize_attachment_response(payload):
        return payload

    attachments = extract_response_attachments(payload)

    result = deepcopy(payload)

    if not preserve_existing or "attachments" not in result:
        result["attachments"] = attachments

    if not preserve_existing or "session_attachments" not in result:
        result["session_attachments"] = attachments

    assistant_message = result.get("assistant_message")
    if isinstance(assistant_message, dict):
        if not preserve_existing or "attachments" not in assistant_message:
            assistant_message["attachments"] = attachments
        result["assistant_message"] = assistant_message

    debug = result.get("debug")
    if not isinstance(debug, dict):
        debug = {}

    debug["attachment_response_finalizer"] = True
    debug["attachment_count"] = len(attachments)
    debug["session_attachments_count"] = len(attachments)
    result["debug"] = debug

    return result
