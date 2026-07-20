class MemoryCommandService:

    def __init__(self, session_service):
        self.session_service = session_service

    def extract_explicit_memory_live(self, user_text):
        raw = str(user_text or "").strip()
        lowered = raw.lower().strip()

        project_brain_memory_concept_markers = (
            "what nova remembers",
            "what nova is actively doing",
            "separate what",
            "separate memory",
            "memory from execution",
            "remembered from active",
        )

        if any(
            marker in lowered
            for marker in project_brain_memory_concept_markers
        ):
            return ""

        prefixes = (
            "remember that ",
            "remember this ",
            "remember ",
            "save that ",
            "save this ",
            "store that ",
            "store this ",
            "note that ",
            "memorize that ",
            "add to memory that ",
            "add this to memory ",
        )

        for prefix in prefixes:
            if lowered.startswith(prefix):
                return raw[len(prefix):].strip(" .\n\r\t")

        return ""


    def memory_kind_live(self, clean):
        lowered = str(clean or "").lower()

        if (
            "favorite color" in lowered
            or "favourite color" in lowered
            or "prefer" in lowered
            or "from now on" in lowered
            or "always" in lowered
            or "call me" in lowered
            or "my name is" in lowered
        ):
            return "preference"

        return "fact"


    def memory_response_live(
        self,
        raw_user_text,
        session_id,
        clean,
    ):
        assistant_text = f"Saved to memory: {clean}"

        user_msg = {
            "role": "user",
            "text": raw_user_text,
            "attachments": [],
            "meta": {},
        }

        assistant_msg = {
            "role": "assistant",
            "text": assistant_text,
            "content": assistant_text,
            "attachments": [],
            "memory_used": [],
            "meta": {
                "mode": "explicit_memory_command",
                "route": "memory_save",
                "save_memory": True,
                "use_memory": True,
                "early_api_guard": True,
            },
        }

        try:
            self.session_service.add_message(
                session_id,
                user_msg,
            )

            self.session_service.add_message(
                session_id,
                assistant_msg,
            )

        except Exception:
            pass

        return {
            "ok": True,
            "active_session_id": session_id,
            "assistant_message": assistant_msg,
            "attachment_debug": {
                "requested_session_id": session_id,
                "active_session_id": session_id,
                "session_attachments_count": 0,
            },
            "debug": {
                "route": "api_chat_early_explicit_memory_guard",
                "route_taken": "memory_save",
            },
            "runtime": {},
            "session": self.session_service.get_session(session_id) or {
                "id": session_id,
                "messages": [
                    user_msg,
                    assistant_msg,
                ],
            },
            "session_attachments": [],
        }