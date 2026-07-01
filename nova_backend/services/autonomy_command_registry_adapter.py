from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nova_backend.services.autonomy_command_registry import format_autonomy_command_registry


COMMAND_REGISTRY_PREFIXES = (
    "command-registry:",
    "command registry:",
    "registry:",
    "autonomy-registry:",
    "autonomy registry:",
)


def extract_command_registry_input(user_text: str) -> Optional[str]:
    raw = str(user_text or "").strip()
    lowered = raw.lower()

    for prefix in COMMAND_REGISTRY_PREFIXES:
        if lowered.startswith(prefix):
            return raw[len(prefix):].strip()

    return None


def _payload_user_text(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("user_text")
        or payload.get("text")
        or payload.get("message")
        or ""
    ).strip()


def _payload_session_id(payload: Dict[str, Any], session_service: Any = None) -> str:
    session_id = str(
        payload.get("session_id")
        or payload.get("active_session_id")
        or payload.get("requested_session_id")
        or ""
    ).strip()

    if session_id:
        return session_id

    if session_service is not None:
        try:
            active = str(getattr(session_service, "active_session_id", "") or "").strip()
            if active:
                return active
        except Exception:
            pass

    return "command_registry"


def build_command_registry_response(
    payload: Dict[str, Any],
    session_service: Any = None,
) -> Optional[Dict[str, Any]]:
    data = payload if isinstance(payload, dict) else {}
    user_text = _payload_user_text(data)
    registry_input = extract_command_registry_input(user_text)

    if registry_input is None:
        return None

    assistant_text = format_autonomy_command_registry(registry_input)
    session_id = _payload_session_id(data, session_service)
    now = datetime.now(timezone.utc).isoformat()

    user_msg = {
        "role": "user",
        "text": user_text,
        "content": user_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "command_registry_command",
        },
    }

    assistant_msg = {
        "role": "assistant",
        "text": assistant_text,
        "content": assistant_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "command_registry_command",
            "mode": "read_only_command_registry",
        },
    }

    session = None

    if session_service is not None:
        try:
            session_service.add_message(session_id, user_msg)
            session_service.add_message(session_id, assistant_msg)
        except Exception:
            pass

        try:
            session = session_service.get_session(session_id)
        except Exception:
            session = None

    if not isinstance(session, dict):
        session = {
            "id": session_id,
            "messages": [user_msg, assistant_msg],
        }

    return {
        "ok": True,
        "session_id": session_id,
        "active_session_id": session_id,
        "assistant_message": assistant_msg,
        "session": session,
        "runtime": {},
        "debug": {
            "route": "command_registry_command",
            "mode": "read_only_command_registry",
            "adapter": "autonomy_command_registry_adapter",
        },
    }
