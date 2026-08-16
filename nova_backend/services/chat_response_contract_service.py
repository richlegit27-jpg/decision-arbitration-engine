def normalize_assistant_message(
    result,
    user_text,
    response_quality_service,
):
    assistant_message = result.get("assistant_message") or {}

    if not isinstance(assistant_message, dict):
        assistant_message = {
            "role": "assistant",
            "text": str(assistant_message or "").strip(),
        }

    assistant_message.setdefault(
        "role",
        "assistant",
    )

    assistant_text = (
        assistant_message.get("text")
        or assistant_message.get("content")
        or assistant_message.get("message")
        or ""
    )

    if not assistant_text:
        assistant_text = (
            "Nova completed the request but returned "
            "an empty response."
        )

    assistant_message["text"] = assistant_text
    assistant_message["content"] = assistant_text

    if not isinstance(
        assistant_message.get("meta"),
        dict,
    ):
        assistant_message["meta"] = {}

    return assistant_message