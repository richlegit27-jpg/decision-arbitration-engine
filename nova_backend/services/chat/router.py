# nova_backend/services/chat/router.py

class ChatRouter:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def handle(self, user_text, session_id="", attachments=None):
        return self.chat_service._single_router(
            user_text,
            session_id=session_id,
            attachments=attachments,
        )

    def runtime_route(self, user_text):
        if self.chat_service.safe_str(user_text).startswith("/runtime"):
            return {
                "route": "runtime",
                "intent": "runtime",
                "mode": "runtime",
                "runtime_command": user_text,
                "confidence": 1.0,
                "reasons": [
                    "User requested runtime cognition lane."
                ],
            }

        return None

    def decide(
        self,
        user_text,
        attachments=None,
        session_id="",
    ):
        runtime = self.runtime_route(user_text)

        if runtime:
            return runtime

        return self.chat_service._decide_route(
            user_text=user_text,
            attachments=attachments,
            session_id=session_id,
        )