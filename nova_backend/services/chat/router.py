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