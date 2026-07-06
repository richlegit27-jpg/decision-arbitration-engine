class ActionRouter:
    """
    Nova Unified Action Layer
    Replaces scattered API endpoints with one controlled system.
    """

    def __init__(self, session_service, chat_service, attachment_service):
        self.session_service = session_service
        self.chat_service = chat_service
        self.attachment_service = attachment_service

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def execute(self, action_type: str, payload: dict):
        if not action_type:
            return {"ok": False, "error": "Missing action_type"}

        action_type = action_type.lower().strip()

        routes = {
            # CHAT
            "chat.send": self._chat_send,

            # SESSIONS
            "session.rename": self._session_rename,
            "session.pin": self._session_pin,
            "session.delete": self._session_delete,

            # ATTACHMENTS
            "attachment.upload": self._attachment_upload,
            "attachment.analyze": self._attachment_analyze,
        }

        handler = routes.get(action_type)

        if not handler:
            return {"ok": False, "error": f"Unknown action: {action_type}"}

        return handler(payload)

    # =========================================================
    # CHAT
    # =========================================================
    def _chat_send(self, payload):
        return self.chat_service.handle(
            user_text=payload.get("text"),
            session_id=payload.get("session_id"),
            attachments=payload.get("attachments", [])
        )

    # =========================================================
    # SESSIONS
    # =========================================================
    def _session_rename(self, payload):
        return self.session_service.rename_session(
            session_id=payload["session_id"],
            title=payload["title"]
        )

    def _session_pin(self, payload):
        return self.session_service.pin_session(
            session_id=payload["session_id"],
            pinned=payload.get("pinned", True)
        )

    def _session_delete(self, payload):
        return self.session_service.delete_session(
            session_id=payload["session_id"]
        )

    # =========================================================
    # ATTACHMENTS
    # =========================================================
    def _attachment_upload(self, payload):
        return self.attachment_service.upload(
            file=payload["file"]
        )

    def _attachment_analyze(self, payload):
        return self.attachment_service.analyze(
            file_id=payload["file_id"]
        )