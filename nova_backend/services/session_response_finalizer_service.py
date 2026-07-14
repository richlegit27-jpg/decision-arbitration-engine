from __future__ import annotations

from typing import Any, Dict, List


def assistant_message_already_saved(
    messages,
    assistant_text: str,
    assistant_id: str = "",
) -> bool:
    try:
        for existing_msg in reversed(messages or []):
            if not isinstance(existing_msg, dict):
                continue

            existing_id = str(
                existing_msg.get("id") or ""
            ).strip()

            if assistant_id and existing_id == assistant_id:
                return True

            existing_text = str(
                existing_msg.get("text")
                or existing_msg.get("content")
                or existing_msg.get("message")
                or ""
            ).strip()

            if assistant_text and existing_text == assistant_text:
                return True

    except Exception:
        pass

    return False

def user_message_already_saved(
    messages,
    user_text: str,
) -> bool:
    if not user_text:
        return False

    try:
        user_text_norm = str(user_text or "").strip()

        for existing_msg in messages or []:
            if not isinstance(existing_msg, dict):
                continue

            existing_role = str(
                existing_msg.get("role")
                or existing_msg.get("sender")
                or ""
            ).strip().lower()

            existing_text = str(
                existing_msg.get("text")
                or existing_msg.get("content")
                or existing_msg.get("message")
                or ""
            ).strip()

            if (
                existing_role == "user"
                and existing_text == user_text_norm
            ):
                return True

    except Exception:
        pass

    return False


def assistant_same_text_already_saved(
    messages,
    assistant_text: str,
) -> bool:
    if not assistant_text:
        return False

    try:
        assistant_text_norm = str(
            assistant_text or ""
        ).strip()

        for existing_msg in messages or []:
            if not isinstance(existing_msg, dict):
                continue

            existing_role = str(
                existing_msg.get("role")
                or existing_msg.get("sender")
                or ""
            ).strip().lower()

            existing_text = str(
                existing_msg.get("text")
                or existing_msg.get("content")
                or existing_msg.get("message")
                or ""
            ).strip()

            if (
                existing_role == "assistant"
                and existing_text == assistant_text_norm
            ):
                return True

    except Exception:
        pass

    return False

def finalize_session_response(
    response_json: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    response_json["finalizer_service"] = True
    response_json["finalizer_session_id"] = session_id

    return response_json