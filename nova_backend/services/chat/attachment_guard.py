def handle_attachment_guard(
    service,
    user_text,
    attachments=None,
):
    """
    Handles attachment-only early returns.
    Returns a response dict if handled.
    Returns None to continue normal chat flow.
    """

    try:
        if not attachments:
            return None

        txt = str(user_text or "").lower()

        has_attachment_context = any(
            marker in txt
            for marker in [
                "attachment content:",
                "uploaded attachment context below",
                "extracted attachment text",
                "[mobile quick action attachment context active]",
                "uploaded pdf attachment",
                "uploaded attachment",
            ]
        )

        attachment_intent = any(
            keyword in txt
            for keyword in [
                "summarize",
                "summary",
                "keypoint",
                "key point",
                "continue",
            ]
        )

        if not (has_attachment_context and attachment_intent):
            return None

        return None

    except Exception:
        return None