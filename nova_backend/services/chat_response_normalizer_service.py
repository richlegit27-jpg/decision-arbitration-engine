def normalize_chat_result(result, session_id):
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

    assistant_message = result.get("assistant_message") or {
        "role": "assistant",
        "text": "",
    }

    if not isinstance(assistant_message, dict):
        assistant_message = {
            "role": "assistant",
            "text": str(assistant_message or "").strip(),
        }

    assistant_message.setdefault(
        "role",
        "assistant",
    )

    result["assistant_message"] = assistant_message

    return result