class AttachmentPipelineService:

    def process(
        self,
        user_text,
        attachments,
        session_id,
        requested_session_id=None,
        **services
    ):
        return {
            "user_text": user_text,
            "remembered_session_attachments": [],
            "raw_injection_attachments": [],
            "attachment_content_lines": [],
        }


attachment_pipeline_service = AttachmentPipelineService()