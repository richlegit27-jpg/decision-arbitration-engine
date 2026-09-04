from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.planner import (
    plan_tool_request,
)

from nova_backend.tools.confidence import (
    get_tool_risk,
    tool_confidence,
    requires_approval,
)

from nova_backend.tools.executor import (
    execute_tool,
)

from nova_backend.tools.result_formatter import (
    format_tool_result,
)


class ToolOrchestrator:

    def handle(
        self,
        user_text: str,
        approved: bool = False,
    ) -> Dict[str, Any]:

        plan = plan_tool_request(
            user_text
        )

        if not plan.get("ok"):

            return {
                "ok": False,
                "handled": False,
                "reason": "no_tool_match",
                "plan": plan,
            }

        tool_name = plan.get("tool")

        payload = (
            plan.get("payload")
            or {}
        )

        risk = get_tool_risk(
            tool_name
        )

        needs_approval = requires_approval(
            plan
        )

        if needs_approval and not approved:

            return {
                "ok": True,
                "handled": True,
                "status": "approval_required",
                "tool": tool_name,
                "payload": payload,
                "risk": risk,
                "requires_approval": True,
                "message": (
                    f"Nova wants to run "
                    f"the tool '{tool_name}'. "
                    f"This action requires approval."
                ),
            }

        result = execute_tool(
            tool_name,
            payload,
            confirm=approved,
        )

        formatted = format_tool_result(
            tool_name,
            result,
        )

        return {
            "ok": result.get(
                "ok",
                False,
            ),
            "handled": True,
            "status": (
                "executed"
                if result.get("ok")
                else "failed"
            ),
            "tool": tool_name,
            "payload": payload,
            "risk": risk,
            "auto_run": tool_confidence(
                plan
            ),
            "requires_approval": needs_approval,
            "approved": bool(
                approved
            ),
            "result": result,
            "formatted": formatted,
        }


tool_orchestrator = ToolOrchestrator()
