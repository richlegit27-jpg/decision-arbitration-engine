def apply_session_attachment_response(
    result,
    summarize_attachments_for_session,
    session_id,
    requested_session_id,
):
    if not isinstance(result, dict):
        return result

    active_attachment_session_id = str(
        result.get("active_session_id")
        or session_id
        or ""
    ).strip()

    result["session_attachments"] = summarize_attachments_for_session(
        active_attachment_session_id,
        limit=25,
        client_session_id=requested_session_id,
    )

    return result