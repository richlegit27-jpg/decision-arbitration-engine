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
    result = response_quality_service.replace_weak_backend_reply(
        image_command_user_text,
        result,
    )

    result = apply_final_attachment_response(
        result,
        attachment_content_lines,
        attachment_analysis_service,
        attachment_summary_lock_service,
    )

    result = apply_session_attachment_response(
        result,
        summarize_attachments_for_session,
        session_id,
        requested_session_id,
    )

    result = apply_real_response_attachment_lock(
        result,
        attachments,
        requested_session_id,
        logger,
    )

    logger.info(
        "[api_chat] returned session attachment memory count=%s session_id=%s",
        len(result.get("session_attachments") or []),
        session_id,
    )

    return result