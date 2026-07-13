"""
NOVA session response cleanup service.

Extracted from:
NOVA_FINAL_CACHE_STALE_WORKING_STATE_HISTORY_CLEANUP_20260630
"""


def cleanup_session_response(
    response_session,
    session_id="",
):
    try:
        if not isinstance(response_session, dict):
            return response_session

        working_state = response_session.get("working_state")

        if not isinstance(working_state, dict):
            working_state = {}

        current_file = str(
            working_state.get("current_file")
            or ""
        ).strip()

        active_task = str(
            working_state.get("active_task")
            or ""
        ).strip()

        returned_messages = response_session.get("messages")

        if not isinstance(returned_messages, list):
            return response_session

        for msg in returned_messages:
            if not isinstance(msg, dict):
                continue

            if str(msg.get("role") or "").lower() != "assistant":
                continue

            msg_text = str(
                msg.get("text")
                or msg.get("content")
                or ""
            ).strip()

            fixed_text = ""

            if (
                current_file
                and msg_text in {
                    "Current file:\nNo active file is currently tracked.",
                    "No active file is currently tracked.",
                    "No active file is currently tracked",
                }
            ):
                fixed_text = f"Current file:\n{current_file}"

            if (
                active_task
                and msg_text in {
                    "Active task:\nNo active task is currently tracked.",
                    "Active task:\nNo active task is currently tracked yet.",
                    "No active task is currently tracked.",
                    "No active task is currently tracked",
                    "No active task is currently tracked yet.",
                }
            ):
                fixed_text = f"Active task:\n{active_task}"

            if not fixed_text:
                continue

            msg["text"] = fixed_text
            msg["content"] = fixed_text
            msg["attachments"] = msg.get("attachments") or []
            msg["session_id"] = session_id
            msg["active_session_id"] = session_id

            msg_meta = msg.get("meta")

            if not isinstance(msg_meta, dict):
                msg_meta = {}

            msg_meta["route"] = (
                "final_cache_stale_working_state_history_cleanup"
            )
            msg_meta["session_id"] = session_id
            msg_meta["render_source"] = "assistant_message_only"
            msg_meta["stale_working_state_history_cleaned"] = True

            msg["meta"] = msg_meta

        response_session["messages"] = returned_messages

    except Exception:
        pass

    return response_session