class ChatAttachmentGuardService:

    def __init__(self):
        pass

    def handle_attachment_guard(
        self,
        request,
        session_service=None,
        execution_service=None,
        attachment_text_service=None,
        *args,
        **kwargs,
    ):
        return None

    def handle_web_attachment_guard(
        self,
        request,
        data,
        user_text,
        attachments,
    ):
        clean = " ".join(
            str(user_text or "").lower().split()
        )

        web_terms = (
            "latest news",
            "news about",
            "today in",
            "what happened today",
            "current news",
            "breaking news",
            "recent news",
            "latest tech news",
            "latest sports",
            "weather",
            "forecast",
            "current events",
        )

        if (
            request.environ.get(
                "NOVA_IGNORE_STALE_ATTACHMENTS_20260609"
            ) == "1"
            or any(term in clean for term in web_terms)
        ):
            attachments = []

            try:
                data["attachments"] = []
                request.environ[
                    "NOVA_FORCE_WEB_INTENT_20260609"
                ] = "1"
                request.environ[
                    "NOVA_IGNORE_STALE_ATTACHMENTS_20260609"
                ] = "1"
            except Exception:
                pass

        return attachments