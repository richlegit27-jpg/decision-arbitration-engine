from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nova_backend.services.autonomy_patch_planner import format_autonomy_patch_plan


AUTONOMY_PLAN_PREFIXES = (
    "autonomy-plan:",
    "autonomy plan:",
    "plan-autonomy:",
    "plan autonomy:",
)


def extract_autonomy_plan_input(user_text: str) -> Optional[str]:
    raw = str(user_text or "").strip()
    lowered = raw.lower()

    for prefix in AUTONOMY_PLAN_PREFIXES:
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

    return "autonomy_plan"


def build_autonomy_plan_response(
    payload: Dict[str, Any],
    session_service: Any = None,
) -> Optional[Dict[str, Any]]:
    data = payload if isinstance(payload, dict) else {}
    user_text = _payload_user_text(data)
    goal = extract_autonomy_plan_input(user_text)

    if goal is None:
        return None

    assistant_text = format_autonomy_patch_plan(goal)
    session_id = _payload_session_id(data, session_service)
    now = datetime.now(timezone.utc).isoformat()

    user_msg = {
        "role": "user",
        "text": user_text,
        "content": user_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "autonomy_plan_command",
        },
    }

    assistant_msg = {
        "role": "assistant",
        "text": assistant_text,
        "content": assistant_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "autonomy_plan_command",
            "mode": "patch_proposal_only",
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
            "route": "autonomy_plan_command",
            "mode": "proposal_only",
            "adapter": "autonomy_plan_adapter",
        },
    }
