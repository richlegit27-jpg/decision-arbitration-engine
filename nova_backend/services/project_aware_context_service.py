from typing import Any


class ProjectAwareContextService:

    def __init__(
        self,
        memory_context_service,
        session_service,
    ):
        self.memory_context_service = memory_context_service
        self.session_service = session_service

    def _memory_text(self, item):
        if not isinstance(item, dict):
            return ""

        for key in (
            "text",
            "content",
            "message",
            "body",
        ):
            value = item.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""


    def _message_text(self, message):
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

    def build_project_aware_context(
        self,
        user_text,
        *,
        session_id="",
        requested_session_id="",
    ):
        context_lines = []

        try:
            memory_lines = self.memory_context_service.get_memory_context(
                user_text
            )
        except Exception:
            memory_lines = []

        if memory_lines:
            context_lines.append("Relevant persistent memory:")
            context_lines.extend(memory_lines)

        session_context_id = str(
            session_id or requested_session_id or ""
        ).strip()

        try:
            recent_lines = self.memory_context_service.get_recent_session_context(
                session_context_id
            )
        except Exception:
            recent_lines = []

        if recent_lines:
            if context_lines:
                context_lines.append("")

            context_lines.append("Recent session context:")
            context_lines.extend(recent_lines)

        if not context_lines:
            return ""

        return "\n".join(
            [
                "",
                "Project-aware context for Nova:",
                *context_lines,
            ]
        ).strip()

