def apply_final_attachment_response(
    result,
    attachment_content_lines,
    attachment_analysis_service,
    attachment_summary_lock_service,
):
    return attachment_summary_lock_service.apply_attachment_summary_lock(
        result,
        attachment_content_lines,
        attachment_analysis_service,
    )