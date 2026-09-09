from __future__ import annotations

from typing import Any


class ToolRegistry:
    """
    Unified Nova tool registry.

    Combines:

    - Internal Nova application actions
    - Real Nova executable tools
    - Planned external integrations

    Tool execution remains the responsibility of ToolExecutor.
    """

    INTERNAL_TOOLS = {
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
    }

    EXTERNAL_TOOLS = {
        "email.send": {
            "name": "email.send",
            "category": "external",
            "requires_confirmation": True,
            "aliases": ["email"],
            "implemented": False,
        },
        "calendar.create": {
            "name": "calendar.create",
            "category": "external",
            "requires_confirmation": True,
            "aliases": ["calendar"],
            "implemented": False,
        },
    }

    def __init__(
        self,
        tool_executor=None,
        chat_service=None,
        nova_tool_registry=None,
    ):
        self.tool_executor = tool_executor
        self.chat_service = chat_service
        self.nova_tool_registry = nova_tool_registry

        self._tools = {}

        self._register_internal_tools()
        self._register_real_nova_tools()
        self._register_external_tools()

    # =========================================================
    # REGISTRATION
    # =========================================================

    def _register_internal_tools(self):
        for name, metadata in self.INTERNAL_TOOLS.items():
            self._tools[name] = dict(metadata)

    def _register_external_tools(self):
        for name, metadata in self.EXTERNAL_TOOLS.items():
            self._tools[name] = dict(metadata)

    def _register_real_nova_tools(self):

        if self.nova_tool_registry is None:
            return

        try:
            tool_names = (
                self.nova_tool_registry.list_tools()
            )

        except Exception:
            return

        for tool_name in tool_names:

            tool = self.nova_tool_registry.get(
                tool_name
            )

            if tool is None:
                continue

            aliases = getattr(
                tool,
                "aliases",
                [],
            )

            if not isinstance(aliases, list):
                aliases = []

            requires_confirmation = bool(
                getattr(
                    tool,
                    "requires_confirmation",
                    False,
                )
            )

            category = getattr(
                tool,
                "category",
                "nova",
            )

            self._tools[tool_name] = {
                "name": tool_name,
                "category": category,
                "requires_confirmation": (
                    requires_confirmation
                ),
                "aliases": list(aliases),
                "implemented": True,
                "source": "nova",
            }

    # =========================================================
    # DISCOVERY
    # =========================================================

    def get_available_tools(
        self,
    ) -> dict[str, dict[str, Any]]:

        return {
            name: dict(metadata)
            for name, metadata
            in self._tools.items()
        }

    def list_tool_names(self) -> list[str]:

        return sorted(
            self._tools.keys()
        )

    def get_tool_count(self) -> int:

        return len(self._tools)

    def get_tool(
        self,
        tool_name: str,
    ) -> dict[str, Any] | None:

        normalized = self.resolve_tool_name(
            tool_name
        )

        if not normalized:
            return None

        tool = self._tools.get(normalized)

        if not tool:
            return None

        return dict(tool)

    # =========================================================
    # RESOLUTION
    # =========================================================

    def resolve_tool_name(
        self,
        tool_name: str,
    ) -> str:

        normalized = str(
            tool_name or ""
        ).lower().strip()

        if not normalized:
            return ""

        if normalized in self._tools:
            return normalized

        for name, metadata in self._tools.items():

            aliases = (
                metadata.get("aliases")
                or []
            )

            normalized_aliases = [
                str(alias).lower().strip()
                for alias in aliases
            ]

            if normalized in normalized_aliases:
                return name

        return ""

    # =========================================================
    # METADATA
    # =========================================================

    def requires_confirmation(
        self,
        tool_name: str,
    ) -> bool:

        tool = self.get_tool(tool_name)

        if not tool:
            return False

        return bool(
            tool.get(
                "requires_confirmation"
            )
        )

    # =========================================================
    # EXECUTION
    # =========================================================

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

        resolved_name = self.resolve_tool_name(
            tool_name
        )

        if not resolved_name:
            return {
                "ok": False,
                "tool": tool_name,
                "tool_name": tool_name,
                "status": "failed",
                "error": (
                    f"Tool not registered: "
                    f"{tool_name}"
                ),
            }

        if self.tool_executor is None:
            return {
                "ok": False,
                "tool": resolved_name,
                "tool_name": resolved_name,
                "status": "failed",
                "error": (
                    "Tool executor is not configured."
                ),
            }

        result = self.tool_executor.run(
            resolved_name,
            payload or {},
            confirm=confirm,
        )

        if not isinstance(
            result,
            dict,
        ):
            return {
                "ok": True,
                "tool": resolved_name,
                "tool_name": resolved_name,
                "status": "executed",
                "result": result,
            }

        normalized_result = dict(result)

        normalized_result.setdefault(
            "tool",
            resolved_name,
        )

        normalized_result.setdefault(
            "tool_name",
            resolved_name,
        )

        if (
            normalized_result.get(
                "requires_confirmation"
            )
            is True
        ):
            normalized_result.setdefault(
                "status",
                "awaiting_confirmation",
            )

        elif normalized_result.get("ok") is True:
            normalized_result.setdefault(
                "status",
                "executed",
            )

        elif normalized_result.get("ok") is False:
            normalized_result.setdefault(
                "status",
                "failed",
            )

        return normalized_result
