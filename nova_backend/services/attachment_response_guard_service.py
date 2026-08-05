def normalize_attachment_response(
    assistant_message,
    replacement_text,
):
    assistant_message = assistant_message or {}

    existing_content = str(
        assistant_message.get("content") or ""
    ).strip()

    replacement_text = str(
        replacement_text or ""
    ).strip()

    if (
        existing_content.startswith("Attachment analysis:")
        and "Attachment " in existing_content
        and " content:" in existing_content
        and "This uploaded attachment contains readable text about:"
        in replacement_text
    ):
        assistant_message["text"] = existing_content
        assistant_message["content"] = existing_content
    else:
        assistant_message["text"] = replacement_text
        assistant_message["content"] = replacement_text

    return assistant_message