from __future__ import annotations


class ChatRequestContextService:

    def build_context(self, payload):
        if not isinstance(payload, dict):
            payload = {}

        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        attachments = payload.get("attachments") or []

        if not isinstance(attachments, list):
            attachments = []

        return {
            "user_text": user_text,
            "session_id": session_id,
            "attachments": attachments,
        }