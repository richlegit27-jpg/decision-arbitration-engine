import re


class ProjectFocusMemoryService:

    def __init__(
        self,
        memory_service,
        session_service,
    ):
        self.memory_service = memory_service
        self.session_service = session_service

    def project_focus_memory_text(
        self,
        focus,
    ):
        focus_value = str(focus or "").strip()

        if not focus_value:
            return ""

        return f"Current project focus: {focus_value}"

    def extract_project_focus_from_text(
        self,
        text_value,
    ):
        raw = str(text_value or "").strip()

        if not raw:
            return ""

        patterns = [
            r"\bmy\s+current\s+project\s+focus\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bcurrent\s+project\s+focus\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bproject\s+focus\s+is\s+(.+?)(?:[.!?\n]|$)",
            r"\bfocus\s+is\s+(.+?)(?:[.!?\n]|$)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                raw,
                re.IGNORECASE,
            )

            if not match:
                continue

            focus = str(
                match.group(1) or ""
            ).strip()

            focus = re.sub(
                r"\s+",
                " ",
                focus,
            ).strip(" .!?")

            if focus:
                return focus

        return ""

    def message_text(
        self,
        message,
    ):
        if isinstance(message, str):
            return message.strip()

        if not isinstance(message, dict):
            return ""

        for key in (
            "text",
            "content",
            "message",
            "body",
        ):
            value = message.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def save_project_focus_memory(
        self,
        user_text,
        session_id,
    ):
        focus = self.extract_project_focus_from_text(
            user_text
        )

        if not focus:
            return None

        memory_text = self.project_focus_memory_text(
            focus
        )

        if not memory_text:
            return None

        target_session_id = str(
            session_id or ""
        ).strip()

        for item in self.memory_service.all() or []:
            if not isinstance(item, dict):
                continue

            item_text = str(
                item.get("text") or ""
            ).strip().lower()

            item_session = str(
                item.get("session_id") or ""
            ).strip()

            if (
                item_text == memory_text.lower()
                and item_session == target_session_id
            ):
                return item

        return self.memory_service.add_memory(
            {
                "text": memory_text,
                "kind": "project_focus",
                "source": "project_focus_direct",
                "session_id": target_session_id,
            }
        )

    def find_project_focus_memory(
        self,
        session_id,
    ):
        target_session_id = str(
            session_id or ""
        ).strip()

        candidates = []

        for item in self.memory_service.all() or []:
            if not isinstance(item, dict):
                continue

            item_text = str(
                item.get("text") or ""
            ).strip()

            item_session = str(
                item.get("session_id") or ""
            ).strip()

            item_kind = str(
                item.get("kind") or ""
            ).strip().lower()

            if not item_text.lower().startswith(
                "current project focus:"
            ):
                continue

            if (
                target_session_id
                and item_session
                and item_session != target_session_id
            ):
                continue

            focus = item_text.split(
                ":",
                1,
            )[1].strip()

            if not focus:
                continue

            score = 0

            if item_session == target_session_id:
                score += 100

            if item_kind == "project_focus":
                score += 25

            candidates.append(
                (
                    score,
                    item.get("updated_at")
                    or item.get("created_at")
                    or "",
                    focus,
                )
            )

        if not candidates:
            return ""

        candidates.sort(
            reverse=True
        )

        return str(
            candidates[0][2]
        ).strip()

    def find_recent_project_focus(
        self,
        session_id,
    ):
        target_session_id = str(
            session_id or ""
        ).strip()

        if not target_session_id:
            return ""

        session = self.session_service.get_session(
            target_session_id
        )

        if not isinstance(session, dict):
            return ""

        messages = session.get(
            "messages"
        ) or []

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            role = str(
                message.get("role") or ""
            ).lower()

            if role not in {
                "user",
                "message",
            }:
                continue

            focus = self.extract_project_focus_from_text(
                self.message_text(message)
            )

            if focus:
                return focus

        return ""

    def is_project_focus_recall_question(
        self,
        user_text,
    ):
        text_value = str(
            user_text or ""
        ).strip().lower()

        if not text_value:
            return False

        project_terms = (
            "project focus",
            "current focus",
            "focus right now",
            "what was my focus",
            "what is my focus",
            "what's my focus",
        )

        personal_terms = (
            "my ",
            "i ",
            "me",
            "our ",
            "nova",
            "current",
        )

        return (
            any(
                term in text_value
                for term in project_terms
            )
            and any(
                term in text_value
                for term in personal_terms
            )
        )