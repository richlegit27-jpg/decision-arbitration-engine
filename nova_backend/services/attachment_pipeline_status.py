# NOVA_ATTACHMENT_PIPELINE_STATUS_SERVICE_20260705
"""
Safe attachment pipeline capability status.

This returns feature flags only. It must not expose uploaded file contents,
attachment summaries, extracted text, or debug payload previews.
"""

from __future__ import annotations

from typing import Any


def get_attachment_pipeline_status() -> dict[str, Any]:
    modules = {
        "upload_response_normalizer": False,
        "payload_normalizer": False,
        "hydrator": False,
        "context_builder": False,
        "intent_guard": False,
        "web_guard": False,
    }

    details: dict[str, str] = {}

    try:
        from nova_backend.services.upload_attachment_response_normalizer import (
            normalize_upload_response_payload,
        )

        modules["upload_response_normalizer"] = callable(normalize_upload_response_payload)
    except Exception as exc:
        details["upload_response_normalizer_error"] = str(exc)

    try:
        from nova_backend.services.chat_attachment_payload_normalizer import (
            normalize_api_chat_attachments,
        )

        modules["payload_normalizer"] = callable(normalize_api_chat_attachments)
    except Exception as exc:
        details["payload_normalizer_error"] = str(exc)

    try:
        from nova_backend.services.chat_turn_attachment_hydrator import (
            hydrate_attachments_for_context,
        )

        modules["hydrator"] = callable(hydrate_attachments_for_context)
    except Exception as exc:
        details["hydrator_error"] = str(exc)

    try:
        from nova_backend.services.chat_turn_attachment_context import (
            build_attachment_context_text,
        )

        modules["context_builder"] = callable(build_attachment_context_text)
    except Exception as exc:
        details["context_builder_error"] = str(exc)

    try:
        from nova_backend.services.chat_attachment_intent_guard import (
            should_suppress_web_for_attachment,
        )

        modules["intent_guard"] = callable(should_suppress_web_for_attachment)
    except Exception as exc:
        details["intent_guard_error"] = str(exc)

    try:
        from nova_backend.services.chat_service import ChatService

        modules["web_guard"] = bool(
            getattr(ChatService, "_nova_attachment_guard_web_suppression_installed", False)
            or getattr(ChatService, "_nova_attachment_guard_web_routing_suppression_installed", False)
        )
    except Exception as exc:
        details["web_guard_error"] = str(exc)

    return {
        "ready": all(modules.values()),
        "attachment_pipeline": modules,
        "debug_routes_require_env": True,
        "debug_env": "NOVA_DEBUG_ROUTES=1",
        "details": details,
    }
