from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nova_backend.services.autonomy_workflow_catalog import format_safe_workflow_catalog


WORKFLOW_CATALOG_PREFIXES = (
    "workflow-catalog:",
    "workflow catalog:",
    "safe-workflow:",
    "safe workflow:",
    "workflow:",
)


def extract_workflow_catalog_input(user_text: str) -> Optional[str]:
    raw = str(user_text or "").strip()
    lowered = raw.lower()

    for prefix in WORKFLOW_CATALOG_PREFIXES:
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

    return "workflow_catalog"


def build_workflow_catalog_response(
    payload: Dict[str, Any],
    session_service: Any = None,
) -> Optional[Dict[str, Any]]:
    data = payload if isinstance(payload, dict) else {}
    user_text = _payload_user_text(data)
    goal = extract_workflow_catalog_input(user_text)

    if goal is None:
        return None

    assistant_text = format_safe_workflow_catalog(goal)
    session_id = _payload_session_id(data, session_service)
    now = datetime.now(timezone.utc).isoformat()

    user_msg = {
        "role": "user",
        "text": user_text,
        "content": user_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "workflow_catalog_command",
        },
    }

    assistant_msg = {
        "role": "assistant",
        "text": assistant_text,
        "content": assistant_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "workflow_catalog_command",
            "mode": "manual_workflow_catalog_only",
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
            "route": "workflow_catalog_command",
            "mode": "manual_workflow_catalog_only",
            "adapter": "workflow_catalog_adapter",
        },
    }
