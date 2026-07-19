class ChatAttachmentGuardService:

    def handle(
        self,
        payload,
        request,
        jsonify,
        attachment_utils_service,
        attachment_context_service,
        attachment_text_service,
    ):
        try:
            ...