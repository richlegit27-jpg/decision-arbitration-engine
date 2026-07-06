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

# NOVA_ATTACHMENT_PIPELINE_STATUS_WEB_GUARD_COMPAT_20260705
def _nova_attachment_status_web_guard_ready():
    try:
        from nova_backend.services import chat_service

        required = (
            "_nova_attachment_guard_should_suppress_current_web_call",
            "_nova_attachment_guard_install_web_routing_suppression",
            "_nova_install_attachment_guard_web_suppression",
        )

        if not all(hasattr(chat_service, name) for name in required):
            return False

        installer = getattr(
            chat_service,
            "_nova_attachment_guard_install_web_routing_suppression",
            None,
        )

        if callable(installer):
            result = installer()

            if isinstance(result, dict) and result.get("ok") is False:
                return False

        return True
    except Exception:
        return False


def _nova_attachment_status_patch_payload(payload):
    if not isinstance(payload, dict):
        return payload

    capabilities = payload.get("capabilities")

    if isinstance(capabilities, dict):
        capabilities["web_guard"] = _nova_attachment_status_web_guard_ready()
        payload["ready"] = all(bool(value) for value in capabilities.values())

    return payload


try:
    _nova_original_get_attachment_pipeline_status = get_attachment_pipeline_status

    def get_attachment_pipeline_status():
        return _nova_attachment_status_patch_payload(
            _nova_original_get_attachment_pipeline_status()
        )
except Exception:
    pass


try:
    _nova_original_attachment_pipeline_status = attachment_pipeline_status

    def attachment_pipeline_status():
        return _nova_attachment_status_patch_payload(
            _nova_original_attachment_pipeline_status()
        )
except Exception:
    pass


try:
    _nova_original_get_status = get_status

    def get_status():
        return _nova_attachment_status_patch_payload(_nova_original_get_status())
except Exception:
    pass

# NOVA_ATTACHMENT_PIPELINE_STATUS_SHAPE_V2_20260705
def _nova_attachment_status_web_guard_ready_v2():
    try:
        from nova_backend.services import chat_service

        required = (
            "_nova_attachment_guard_should_suppress_current_web_call",
            "_nova_attachment_guard_install_web_routing_suppression",
            "_nova_install_attachment_guard_web_suppression",
        )

        if not all(hasattr(chat_service, name) for name in required):
            return False

        installer = getattr(
            chat_service,
            "_nova_attachment_guard_install_web_routing_suppression",
            None,
        )

        if callable(installer):
            result = installer()

            if isinstance(result, dict) and result.get("ok") is False:
                return False

        return True
    except Exception:
        return False


def _nova_attachment_status_patch_payload_v2(payload):
    if not isinstance(payload, dict):
        return payload

    web_guard_ready = _nova_attachment_status_web_guard_ready_v2()

    for key in ("attachment_pipeline", "capabilities"):
        flags = payload.get(key)

        if isinstance(flags, dict):
            flags["web_guard"] = web_guard_ready
            payload[key] = flags
            payload["ready"] = all(bool(value) for value in flags.values())

    return payload


for _name in (
    "get_attachment_pipeline_status",
    "attachment_pipeline_status",
    "get_status",
):
    try:
        _original = globals().get(_name)

        if callable(_original) and not getattr(_original, "_nova_status_shape_v2_wrapped", False):
            def _make_wrapper(fn):
                def _wrapped(*args, **kwargs):
                    return _nova_attachment_status_patch_payload_v2(fn(*args, **kwargs))

                _wrapped._nova_status_shape_v2_wrapped = True
                return _wrapped

            globals()[_name] = _make_wrapper(_original)
    except Exception:
        pass
