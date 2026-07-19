class ImageCommandService:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def handle_regeneration(
        self,
        user_text,
        session_id,
    ):
        regen_commands = {
            "regen",
            "regenerate",
            "redo image",
            "make another",
            "another image",
        }

        clean = str(user_text or "").lower().strip()

        if clean not in regen_commands:
            return None

        last_prompt = self.chat_service._get_session_meta(
            session_id,
            "last_image_prompt",
        ) or "generate an image"

        return self.chat_service._handle_image_generation(
            prompt=last_prompt,
            session_id=session_id,
            parent_artifact_id="",
            source_type="regenerated",
        )