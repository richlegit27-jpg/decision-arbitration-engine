def normalize_assistant_message(result, user_text, response_quality_service):
    assistant_message = result.get("assistant_message") or {
        "role": "assistant",
        "text": "",
    }

    if not isinstance(assistant_message, dict):
        assistant_message = {
            "role": "assistant",
            "text": str(assistant_message or "").strip(),
        }

    assistant_message.setdefault("role", "assistant")

    assistant_text = str(
        assistant_message.get("text")
        or assistant_message.get("content")
        or assistant_message.get("message")
        or ""
    ).strip()

    if not assistant_text and result.get("ok", True):
        assistant_text = (
            "Nova completed the request but returned "
            "an empty assistant response."
        )

    assistant_text = response_quality_service.prevent_bad_exact_pong_response(
        assistant_text,
        user_text,
    )

    assistant_message["text"] = assistant_text
    assistant_message["content"] = assistant_text

    return assistant_message