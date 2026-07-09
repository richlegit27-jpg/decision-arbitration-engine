from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nova_backend.services.autonomy_repair_planner import format_autonomy_repair_plan


REPAIR_PLAN_PREFIXES = (
    "repair-plan:",
    "repair plan:",
    "repair:",
    "fix-plan:",
    "fix plan:",
)


def extract_repair_plan_input(user_text: str) -> Optional[str]:
    raw = str(user_text or "").strip()
    lowered = raw.lower()

    for prefix in REPAIR_PLAN_PREFIXES:
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

    return "repair_plan"


def build_repair_plan_response(
    payload: Dict[str, Any],
    session_service: Any = None,
) -> Optional[Dict[str, Any]]:
    data = payload if isinstance(payload, dict) else {}
    user_text = _payload_user_text(data)
    failed_output = extract_repair_plan_input(user_text)

    if failed_output is None:
        return None

    assistant_text = format_autonomy_repair_plan(failed_output)
    session_id = _payload_session_id(data, session_service)
    now = datetime.now(timezone.utc).isoformat()

    user_msg = {
        "role": "user",
        "text": user_text,
        "content": user_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "repair_plan_command",
        },
    }

    assistant_msg = {
        "role": "assistant",
        "text": assistant_text,
        "content": assistant_text,
        "attachments": [],
        "created_at": now,
        "meta": {
            "route": "repair_plan_command",
            "mode": "repair_proposal_only",
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
            "route": "repair_plan_command",
            "mode": "repair_proposal_only",
            "adapter": "repair_plan_adapter",
        },
    }

# NOVA_REPAIR_PLAN_VISIBLE_SAFETY_LINE_20260701
# Ensures supervised repair proposals visibly expose the safety contract.
_NOVA_PRE_SAFETY_BUILD_REPAIR_PLAN_RESPONSE_20260701 = build_repair_plan_response


def _nova_repair_plan_add_visible_safety_line_20260701(text: str) -> str:
    safety_line = "Safety: Proposal only; no file edits, no command execution."

    value = str(text or "")

    if "safety" in value.lower():
        return value

    if "Failure type:" in value:
        return value.replace("Failure type:", safety_line + "\nFailure type:", 1)

    if "Mode: repair_proposal_only" in value:
        return value.replace(
            "Mode: repair_proposal_only",
            "Mode: repair_proposal_only\n" + safety_line,
            1,
        )

    return value + "\n\n" + safety_line


def build_repair_plan_response(payload, session_service):
    result = _NOVA_PRE_SAFETY_BUILD_REPAIR_PLAN_RESPONSE_20260701(payload, session_service)

    try:
        assistant_message = result.get("assistant_message") or {}
        original_text = str(assistant_message.get("text") or "")
        fixed_text = _nova_repair_plan_add_visible_safety_line_20260701(original_text)

        if fixed_text != original_text:
            assistant_message["text"] = fixed_text
            result["assistant_message"] = assistant_message

            try:
                session_id = (
                    (payload or {}).get("session_id")
                    or getattr(session_service, "active_session_id", None)
                    or "default"
                )
                session = session_service.get_session(session_id)
                messages = session.get("messages") if isinstance(session, dict) else None

                if isinstance(messages, list):
                    for message in reversed(messages):
                        if not isinstance(message, dict):
                            continue

                        if message.get("role") == "assistant":
                            if message.get("text") == original_text:
                                message["text"] = fixed_text
                            if message.get("content") == original_text:
                                message["content"] = fixed_text
                            break
            except Exception:
                pass

    except Exception:
        return result

    return result

