# NOVA_CHAT_ATTACHMENT_INTENT_GUARD_20260705
"""
Attachment intent guard.

Purpose:
When the user has attached files, phrases like "summarize this", "what is this",
"read this file", or "describe the attachment" should stay on the attachment path.
They should not be routed to web/search fallback merely because the text is vague.
"""

from __future__ import annotations

from typing import Any
import re


_ATTACHMENT_REFERENCE_RE = re.compile(
    r"\b("
    r"attach(?:ed|ment|ments)?|"
    r"file|files|upload|uploads|uploaded|"
    r"document|doc|pdf|image|picture|photo|screenshot|"
    r"this|these|it"
    r")\b",
    re.IGNORECASE,
)

_ATTACHMENT_ACTION_RE = re.compile(
    r"\b("
    r"summarize|summary|sum up|read|analy[sz]e|explain|describe|"
    r"what(?:'s| is)|tell me|extract|ocr|transcribe|"
    r"look at|check|review|scan"
    r")\b",
    re.IGNORECASE,
)

_WEB_INTENT_RE = re.compile(
    r"\b("
    r"search|web|internet|google|look up online|browse|latest|current news|"
    r"today|news|price|weather|stock|score"
    r")\b",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    try:
        return str(value)
    except Exception:
        return ""


def has_attachments(payload_or_attachments: Any) -> bool:
    if isinstance(payload_or_attachments, (list, tuple, set)):
        return bool(payload_or_attachments)

    try:
        from nova_backend.services.chat_attachment_payload_normalizer import (
            normalize_api_chat_attachments,
        )

        return bool(normalize_api_chat_attachments(payload_or_attachments))
    except Exception:
        return False


def is_attachment_focused_message(user_text: Any, payload_or_attachments: Any = None) -> bool:
    text = _text(user_text).strip()

    if not text:
        return False

    if not has_attachments(payload_or_attachments):
        return False

    has_reference = bool(_ATTACHMENT_REFERENCE_RE.search(text))
    has_action = bool(_ATTACHMENT_ACTION_RE.search(text))

    if has_reference and has_action:
        return True

    # Very short vague messages after an upload are usually about the upload.
    compact = re.sub(r"\s+", " ", text).strip().lower()

    if compact in {
        "summarize",
        "summary",
        "analyze",
        "analyse",
        "describe",
        "read",
        "what is this",
        "what's this",
        "what is it",
        "explain this",
        "tell me about this",
    }:
        return True

    return False


def should_suppress_web_for_attachment(user_text: Any, payload_or_attachments: Any = None) -> bool:
    if not is_attachment_focused_message(user_text, payload_or_attachments):
        return False

    text = _text(user_text)

    # Explicit online/current requests should still be allowed to use web.
    if _WEB_INTENT_RE.search(text):
        return False

    return True


def attachment_guard_metadata(user_text: Any, payload_or_attachments: Any = None) -> dict[str, Any]:
    attachments_present = has_attachments(payload_or_attachments)
    attachment_focused = is_attachment_focused_message(user_text, payload_or_attachments)
    suppress_web = should_suppress_web_for_attachment(user_text, payload_or_attachments)

    return {
        "attachments_present": attachments_present,
        "attachment_focused": attachment_focused,
        "suppress_web": suppress_web,
    }

# NOVA_ATTACHMENT_INTENT_EXPLICIT_WEB_COMPAT_20260705
def is_attachment_focused_message(message, payload=None, *args, **kwargs):
    try:
        from nova_backend.services.chat_attachment_payload_normalizer import (
            normalize_api_chat_attachments,
        )

        attachments = normalize_api_chat_attachments(payload or {})
    except Exception:
        attachments = []

    if not attachments:
        return False

    text = str(message or "").lower()

    attachment_terms = (
        "attached",
        "attachment",
        "file",
        "upload",
        "uploaded",
        "image",
        "photo",
        "picture",
        "document",
        "pdf",
        "summarize this",
        "what is this",
        "read this",
        "analyze this",
    )

    return any(term in text for term in attachment_terms)
