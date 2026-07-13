from __future__ import annotations


def clean_stale_working_state_history(
    response_json: dict,
    session_id: str,
) -> dict:
    if not isinstance(response_json, dict):
        return response_json

    response_session = response_json.get("session")

    if not isinstance(response_session, dict):
        return response_json

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

    messages = response_session.get("messages")

    if not isinstance(messages, list):
        return response_json

    for msg in messages:
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

        meta = msg.get("meta")

        if not isinstance(meta, dict):
            meta = {}

        meta["route"] = (
            "stale_working_state_history_cleanup"
        )
        meta["session_id"] = session_id
        meta["render_source"] = "assistant_message_only"
        meta["stale_working_state_history_cleaned"] = True

        msg["meta"] = meta

    response_session["messages"] = messages
    response_json["session"] = response_session

    return response_json