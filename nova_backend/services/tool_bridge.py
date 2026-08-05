from __future__ import annotations


class ToolBridge:
    """
    Compatibility gateway for Nova tool execution.

    Tool discovery, aliases, and confirmation metadata belong to
    ToolRegistry. ToolBridge only forwards validated requests.
    """

    INTENT_MAP = {
        "chat": "chat.send",
        "rename": "session.rename",
        "pin": "session.pin",
        "delete": "session.delete",
        "upload": "attachment.upload",
        "analyze": "attachment.analyze",
        "email": "email.send",
        "calendar": "calendar.create",
    }

    def __init__(
        self,
        tool_registry=None,
        tool_executor=None,
    ):
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor

    def run_tool(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        safe_payload = payload if isinstance(payload, dict) else {}

        if self.tool_registry is not None:
            return self.tool_registry.execute(
                tool_name,
                safe_payload,
                confirm=confirm,
            )

        if self.tool_executor is not None:
            return self.tool_executor.run(
                tool_name,
                safe_payload,
                confirm=confirm,
            )

        return {
            "ok": False,
            "tool": str(tool_name or "").strip().lower(),
            "error": "Tool bridge is not configured.",
        }

    def auto_route(
        self,
        intent: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        normalized_intent = str(intent or "").lower().strip()
        tool_name = self.INTENT_MAP.get(normalized_intent)

        if not tool_name:
            return {
                "ok": False,
                "error": f"No tool mapping for intent: {intent}",
            }

        return self.run_tool(
            tool_name,
            payload or {},
            confirm=confirm,
        )