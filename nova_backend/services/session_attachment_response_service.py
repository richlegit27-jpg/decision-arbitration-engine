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

    session_attachments = summarize_attachments_for_session(
        active_attachment_session_id,
        limit=25,
        client_session_id=requested_session_id,
    )

    if not isinstance(session_attachments, list):
        session_attachments = []

    result["session_attachments"] = session_attachments

    # NOVA_SESSION_ATTACHMENT_TOP_LEVEL_SYNC_20260913
    # Keep the nested session payload synchronized with the same
    # attachment registry returned at the top level.
    session_payload = result.get("session")

    if isinstance(session_payload, dict):
        session_payload["attachments"] = session_attachments

    return result
