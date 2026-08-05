def apply_attachment_summary_lock(
    result,
    attachment_content_lines,
    attachment_analysis_service,
):
    if not attachment_content_lines:
        return result

    if not isinstance(result, dict):
        return result

    assistant_message = result.get("assistant_message")

    if not isinstance(assistant_message, dict):
        return result

    current_reply = str(
        assistant_message.get("text")
        or assistant_message.get("content")
        or ""
    ).strip()

    lower_reply = current_reply.lower()

    is_canned_attachment_reply = (
        "i received the attachment" in lower_reply
        and "instead of generating an image" in lower_reply
    )

    if not is_canned_attachment_reply:
        return result

    extracted_text = "\n\n".join(
        str(item or "")
        for item in attachment_content_lines
    ).strip()

    try:
        summary_payload = attachment_analysis_service.local_summary_from_text(
            extracted_text
        )
    except Exception:
        summary_payload = None

    if isinstance(summary_payload, dict):
        summary = str(
            summary_payload.get("summary") or ""
        ).strip()

        key_points = summary_payload.get("key_points") or []

        preview = str(
            summary_payload.get("preview") or ""
        ).strip()
    else:
        summary = "I extracted readable text from the attachment."
        key_points = []
        preview = ""

    replacement = (
        "Attachment analysis:\n"
        + summary
    ).strip()

    assistant_message["text"] = replacement
    assistant_message["content"] = replacement

    result["assistant_message"] = assistant_message

    return result