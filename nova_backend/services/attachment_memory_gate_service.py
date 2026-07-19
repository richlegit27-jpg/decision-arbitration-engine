import json


class AttachmentMemoryGateService:

    def __init__(
        self,
        attachment_gate_service,
        attachment_memory_service,
    ):
        self.attachment_gate_service = attachment_gate_service
        self.attachment_memory_service = attachment_memory_service

    def install(self, app):
        from flask import request

        @app.before_request
        def nova_stop_fake_attachment_chat_gate_20260610():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                return self.attachment_gate_service.handle_stop_fake_attachment_chat_gate(
                    payload
                )

            except Exception:
                return None

        @app.before_request
        def nova_attachment_followup_recall_gate_20260611():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                return self.attachment_gate_service.handle_attachment_followup_recall_gate(
                    payload
                )

            except Exception:
                return None

        @app.before_request
        def nova_session_attachment_memory_gate_20260611():
            try:
                if request.path not in (
                    "/api/chat",
                    "/api/chat/stream",
                ) or request.method != "POST":
                    return None

                payload = request.get_json(silent=True) or {}

                return self.attachment_gate_service.handle_session_attachment_memory_gate(
                    payload,
                    self.attachment_memory_service,
                )

            except Exception:
                return None