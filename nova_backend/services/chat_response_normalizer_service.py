def normalize_chat_result(
    result,
    session_id,
):
    if result is None:
        result = {}

    if isinstance(result, str):
        result = {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "content": result,
                "text": result,
            },
            "text": result,
            "session_id": session_id,
            "active_session_id": session_id,
            "debug": {
                "normalized_string_result": True,
                "route_taken": "attachment_analysis",
            },
        }

    if isinstance(result, list):
        list_text = "\n".join(
            str(item)
            for item in result
        )

        result = {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "content": list_text,
                "text": list_text,
            },
            "text": list_text,
            "session_id": session_id,
            "active_session_id": session_id,
            "debug": {
                "normalized_list_result": True,
                "route_taken": "list_result_contract_guard",
            },
        }

    if not isinstance(result, dict):
        result = {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": str(result),
            },
            "session_id": session_id,
            "active_session_id": session_id,
        }

    result.setdefault(
        "session_id",
        session_id,
    )

    result.setdefault(
        "active_session_id",
        session_id,
    )

    status = str(
        result.get("status") or ""
    ).strip()

    if status == "tool_approval_required":

        message = (
            result.get("message")
            or "Tool approval required."
        )

        assistant_message = (
            result.get("assistant_message")
            or {
                "role": "assistant",
                "text": message,
                "content": message,
            }
        )

        if isinstance(assistant_message, dict):

            assistant_message.setdefault(
                "role",
                "assistant",
            )

            assistant_message.setdefault(
                "text",
                message,
            )

            assistant_message.setdefault(
                "content",
                assistant_message.get(
                    "text",
                    message,
                ),
            )

        else:

            assistant_message = {
                "role": "assistant",
                "text": str(
                    assistant_message
                ),
                "content": str(
                    assistant_message
                ),
            }

        result["assistant_message"] = (
            assistant_message
        )

        return result

    if status == "tool_executed":

        message = (
            result.get("message")
            or result.get("response")
            or ""
        )

        assistant_message = (
            result.get("assistant_message")
            or {
                "role": "assistant",
                "text": message,
                "content": message,
            }
        )

        if isinstance(assistant_message, dict):

            assistant_message.setdefault(
                "role",
                "assistant",
            )

            assistant_message.setdefault(
                "text",
                message,
            )

            assistant_message.setdefault(
                "content",
                assistant_message.get(
                    "text",
                    message,
                ),
            )

        else:

            assistant_message = {
                "role": "assistant",
                "text": str(
                    assistant_message
                ),
                "content": str(
                    assistant_message
                ),
            }

        result["assistant_message"] = (
            assistant_message
        )

        return result

    assistant_message = (
        result.get("assistant_message")
        or {
            "role": "assistant",
            "text": "",
        }
    )

    if not isinstance(
        assistant_message,
        dict,
    ):
        assistant_message = {
            "role": "assistant",
            "text": str(
                assistant_message or ""
            ).strip(),
        }

    assistant_message.setdefault(
        "role",
        "assistant",
    )

    assistant_message.setdefault(
        "text",
        "",
    )

    assistant_message.setdefault(
        "content",
        assistant_message.get(
            "text",
            "",
        ),
    )

    result["assistant_message"] = (
        assistant_message
    )

    return result