class ToolBridge:
    """
    External Tool Gateway for Nova.

    THIS is the ONLY place allowed to talk to external systems:
    - email
    - calendar
    - web APIs
    - future integrations
    """

    def __init__(self, tool_executor):
        self.tool_executor = tool_executor

        # safe tool registry (start locked down)
        self.allowed_external_tools = {
            "web.search",
            "file.read",
            "file.write",
        }

        # sensitive tools (require confirmation later)
        self.sensitive_tools = {
            "email.send",
            "calendar.create",
        }

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run_tool(self, tool_name: str, payload: dict, confirm: bool = False):
        tool_name = (tool_name or "").strip().lower()

        if not tool_name:
            return {"ok": False, "error": "Missing tool name"}

        # -------------------------
        # BLOCK UNKNOWN TOOLS
        # -------------------------
        if (
            tool_name not in self.allowed_external_tools
            and tool_name not in self.sensitive_tools
        ):
            return {
                "ok": False,
                "error": f"Tool not registered: {tool_name}"
            }

        # -------------------------
        # CONFIRMATION GATE
        # -------------------------
        if tool_name in self.sensitive_tools and not confirm:
            return {
                "ok": False,
                "requires_confirmation": True,
                "tool": tool_name,
                "payload": payload
            }

        # -------------------------
        # EXECUTE THROUGH TOOL EXECUTOR
        # -------------------------
        return self.tool_executor.run(tool_name, payload)

    # =========================================================
    # FUTURE: AI DECISION ENTRY POINT
    # =========================================================
    def auto_route(self, intent: str, payload: dict):
        """
        AI → intent → tool routing layer
        """

        mapping = {
            "search": "web.search",
            "email": "email.send",
            "calendar": "calendar.create",
            "read_file": "file.read",
            "write_file": "file.write",
        }

        tool = mapping.get(intent.lower())

        if not tool:
            return {
                "ok": False,
                "error": f"No tool mapping for intent: {intent}"
            }

        return self.run_tool(tool, payload)