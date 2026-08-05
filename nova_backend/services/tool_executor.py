from __future__ import annotations


class ToolExecutor:
    """
    Central execution gate for registered Nova tools.

    Internal tools execute through ActionRouter.
    Planned external tools fail safely until their adapters exist.
    """

    INTERNAL_TOOLS = {
        "chat.send",
        "session.rename",
        "session.pin",
        "session.delete",
        "attachment.upload",
        "attachment.analyze",
    }

    PLANNED_EXTERNAL_TOOLS = {
        "email.send",
        "calendar.create",
    }

    REQUIRES_CONFIRMATION = {
        "email.send",
        "calendar.create",
    }

    INTENT_MAP = {
        "rename": "session.rename",
        "pin": "session.pin",
        "delete": "session.delete",
        "upload": "attachment.upload",
        "analyze": "attachment.analyze",
        "chat": "chat.send",
        "email": "email.send",
        "calendar": "calendar.create",
    }

    def __init__(self, action_router=None):
        self.action_router = action_router

    def run(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        normalized_name = str(tool_name or "").lower().strip()
        safe_payload = payload if isinstance(payload, dict) else {}

        if not normalized_name:
            return {
                "ok": False,
                "error": "Missing tool name",
            }

        if (
            normalized_name in self.REQUIRES_CONFIRMATION
            and not confirm
        ):
            return {
                "ok": False,
                "requires_confirmation": True,
                "tool": normalized_name,
                "payload": safe_payload,
            }

        if normalized_name in self.INTERNAL_TOOLS:
            if self.action_router is None:
                return {
                    "ok": False,
                    "tool": normalized_name,
                    "error": "Action router is not configured.",
                }

            try:
                result = self.action_router.execute(
                    normalized_name,
                    safe_payload,
                )
            except Exception as error:
                return {
                    "ok": False,
                    "tool": normalized_name,
                    "error": str(error),
                }

            if isinstance(result, dict):
                return {
                    "tool": normalized_name,
                    **result,
                }

            return {
                "ok": True,
                "tool": normalized_name,
                "result": result,
            }

        if normalized_name in self.PLANNED_EXTERNAL_TOOLS:
            return {
                "ok": False,
                "tool": normalized_name,
                "implemented": False,
                "error": (
                    f"Tool is registered but not implemented yet: "
                    f"{normalized_name}"
                ),
            }

        return {
            "ok": False,
            "tool": normalized_name,
            "error": f"Tool not registered: {normalized_name}",
        }

    def auto_decide_and_run(
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
                "error": f"No tool mapped for intent: {intent}",
            }

        return self.run(
            tool_name,
            payload or {},
            confirm=confirm,
        )