class AutoFixService:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def execute_file_fix(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        return self.chat_service._execute_auto_fix_file(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )