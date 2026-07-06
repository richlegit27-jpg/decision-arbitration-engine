from nova_backend.services.tools.email_tool import EmailTool
from nova_backend.services.tools.calendar_tool import CalendarTool


class ToolExecutor:
    """
    Central Tool Gate for Nova.

    SAFETY LAYER + TOOL ROUTER
    """

    def __init__(self, action_router):
        self.action_router = action_router

        # internal tools handled by ActionRouter
        self.internal_tools = {
            "chat.send",
            "session.rename",
            "session.pin",
            "session.delete",
            "attachment.upload",
            "attachment.analyze",
        }

        # external tools (REAL WORLD)
        self.email_tool = EmailTool()
        self.calendar_tool = CalendarTool()

        self.external_tools = {
            "email.send",
            "calendar.create",
        }

        # require confirmation
        self.requires_confirmation = {
            "email.send",
            "calendar.create",
        }

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run(self, tool_name: str, payload: dict, confirm: bool = False):
        tool_name = (tool_name or "").lower().strip()

        if not tool_name:
            return {"ok": False, "error": "Missing tool name"}

        # -------------------------
        # CONFIRMATION GATE
        # -------------------------
        if tool_name in self.requires_confirmation and not confirm:
            return {
                "ok": False,
                "requires_confirmation": True,
                "tool": tool_name,
                "payload": payload
            }

        # -------------------------
        # INTERNAL TOOLS
        # -------------------------
        if tool_name in self.internal_tools:
            result = self.action_router.execute(tool_name, payload)
            return {
                "ok": True,
                "tool": tool_name,
                "result": result
            }

        # -------------------------
        # EMAIL TOOL
        # -------------------------
        if tool_name == "email.send":
            return self.email_tool.send(
                to=payload.get("to"),
                subject=payload.get("subject"),
                body=payload.get("body")
            )

        # -------------------------
        # CALENDAR TOOL
        # -------------------------
        if tool_name == "calendar.create":
            return self.calendar_tool.create_event(
                title=payload.get("title"),
                time=payload.get("time"),
                description=payload.get("description", "")
            )

        return {
            "ok": False,
            "error": f"Tool not registered: {tool_name}"
        }

    # =========================================================
    # AI MODE (later)
    # =========================================================
    def auto_decide_and_run(self, intent: str, payload: dict):

        intent_map = {
            "rename": "session.rename",
            "pin": "session.pin",
            "delete": "session.delete",
            "upload": "attachment.upload",
            "analyze": "attachment.analyze",
            "chat": "chat.send",

            # external
            "email": "email.send",
            "calendar": "calendar.create",
        }

        tool = intent_map.get((intent or "").lower())

        if not tool:
            return {
                "ok": False,
                "error": f"No tool mapped for intent: {intent}"
            }

        return self.run(tool, payload)

def auto_decide_and_run(self, intent: str, payload: dict):
    intent_map = {
        "rename": "session.rename",
        "pin": "session.pin",
        "delete": "session.delete",
        "upload": "attachment.upload",
        "analyze": "attachment.analyze",
        "chat": "chat.send",

        # external tools
        "email": "email.send",
        "calendar": "calendar.create",
    }

    tool = intent_map.get((intent or "").lower())

    if not tool:
        return {
            "ok": False,
            "error": f"No tool mapped for intent: {intent}"
        }

    return self.run(tool, payload)