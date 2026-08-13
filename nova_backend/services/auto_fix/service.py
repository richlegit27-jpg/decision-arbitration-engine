class AutoFixService:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def execute_file_fix(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        return {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": "AutoFixService is connected. Migration step pending."
            },
            "session_id": session_id,
        }