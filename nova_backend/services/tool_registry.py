from __future__ import annotations

from typing import Any


class ToolRegistry:
    def __init__(
        self,
        tool_executor=None,
        chat_service=None,
    ):
        self.tool_executor = tool_executor
        self.chat_service = chat_service

        self._tools = {
            "chat.send": {
                "name": "chat.send",
                "category": "internal",
                "requires_confirmation": False,
                "aliases": ["chat"],
            },
            "session.rename": {
                "name": "session.rename",
                "category": "internal",
                "requires_confirmation": False,
                "aliases": ["rename"],
            },
            "session.pin": {
                "name": "session.pin",
                "category": "internal",
                "requires_confirmation": False,
                "aliases": ["pin"],
            },
            "session.delete": {
                "name": "session.delete",
                "category": "internal",
                "requires_confirmation": False,
                "aliases": ["delete"],
            },
            "attachment.upload": {
                "name": "attachment.upload",
                "category": "internal",
                "requires_confirmation": False,
                "aliases": ["upload"],
            },
            "attachment.analyze": {
                "name": "attachment.analyze",
                "category": "internal",
                "requires_confirmation": False,
                "aliases": ["analyze"],
            },
            "email.send": {
                "name": "email.send",
                "category": "external",
                "requires_confirmation": True,
                "aliases": ["email"],
            },
            "calendar.create": {
                "name": "calendar.create",
                "category": "external",
                "requires_confirmation": True,
                "aliases": ["calendar"],
            },
        }

    def get_available_tools(self) -> dict[str, dict[str, Any]]:
        return {
            name: dict(metadata)
            for name, metadata in self._tools.items()
        }

    def get_tool(self, tool_name: str) -> dict[str, Any] | None:
        normalized = self.resolve_tool_name(tool_name)

        if not normalized:
            return None

        tool = self._tools.get(normalized)

        if not tool:
            return None

        return dict(tool)

    def resolve_tool_name(self, tool_name: str) -> str:
        normalized = str(tool_name or "").lower().strip()

        if not normalized:
            return ""

        if normalized in self._tools:
            return normalized

        for name, metadata in self._tools.items():
            aliases = metadata.get("aliases") or []

            if normalized in aliases:
                return name

        return ""

    def requires_confirmation(self, tool_name: str) -> bool:
        tool = self.get_tool(tool_name)

        if not tool:
            return False

        return bool(tool.get("requires_confirmation"))

    def execute(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        return self.execute_tool(
            tool_name,
            payload=payload,
            confirm=confirm,
        )

    def execute_tool(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        resolved_name = self.resolve_tool_name(tool_name)

        if not resolved_name:
            return {
                "ok": False,
                "tool_name": tool_name,
                "error": f"Tool not registered: {tool_name}",
            }

        if self.tool_executor is None:
            return {
                "ok": False,
                "tool_name": resolved_name,
                "error": "Tool executor is not configured.",
            }

        return self.tool_executor.run(
            resolved_name,
            payload or {},
            confirm=confirm,
        )