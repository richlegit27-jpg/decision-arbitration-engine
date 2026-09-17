def apply_api_chat_final_response(
    result,
    image_command_user_text,
    attachment_content_lines,
    attachment_analysis_service,
    attachment_summary_lock_service,
    summarize_attachments_for_session,
    session_id,
    requested_session_id,
    attachments,
    logger,
    response_quality_service,
    apply_final_attachment_response,
    apply_session_attachment_response,
    apply_real_response_attachment_lock,
):
    if result is None:
        result = {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": "Nova returned no response during finalization.",
            },
            "session_id": session_id,
        }

    result = response_quality_service.replace_weak_backend_reply(
        image_command_user_text,
        result,
    ) or result

    result = apply_final_attachment_response(
        result,
        attachment_content_lines,
        attachment_analysis_service,
        attachment_summary_lock_service,
    ) or result

    result = apply_session_attachment_response(
        result,
        summarize_attachments_for_session,
        session_id,
        requested_session_id,
    ) or result

    # NOVA_SESSION_ATTACHMENT_TOP_LEVEL_SYNC_20260913
    # Ensure the final nested session payload exposes the same
    # attachment registry as the top-level response.
    if isinstance(result, dict):
        session_attachments = result.get(
            "session_attachments"
        )

        if not isinstance(session_attachments, list):
            session_attachments = []

        session_payload = result.get("session")

        if not isinstance(session_payload, dict):
            session_payload = {}

        session_payload["id"] = (
            session_payload.get("id")
            or result.get("session_id")
            or session_id
        )
        session_payload["session_id"] = (
            session_payload.get("session_id")
            or result.get("session_id")
            or session_id
        )
        session_payload["attachments"] = session_attachments

        result["session"] = session_payload

    result = apply_real_response_attachment_lock(
        result,
        attachments,
        requested_session_id,
        logger,
    ) or result

    if not isinstance(result, dict):
        logger.warning(
            "[api_chat_final_response] invalid result after finalization: %r",
            result,
        )

        result = {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": "Nova response finalization failed.",
            },
            "session_id": session_id,
        }

    logger.info(
        "[api_chat] returned session attachment memory count=%s session_id=%s",
        len(result.get("session_attachments") or []),
        session_id,
    )

    return result