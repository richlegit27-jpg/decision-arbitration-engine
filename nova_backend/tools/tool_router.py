from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.planner import (
    plan_tool_request,
)

from nova_backend.tools.confidence import (
    tool_confidence,
    requires_approval,
)

from nova_backend.tools.executor import (
    execute_tool,
)

from nova_backend.tools.result_formatter import (
    format_tool_result,
)


def handle_tool_request(
    user_text: str,
) -> Dict[str, Any]:

    plan = plan_tool_request(user_text)

    if not plan.get("ok"):

        return {
            "handled": False,
            "reason": "no_matching_tool",
            "plan": plan,
        }

    tool_name = plan.get("tool")
    payload = plan.get("payload") or {}

    if requires_approval(plan):

        return {
            "handled": True,
            "status": "approval_required",
            "tool": tool_name,
            "payload": payload,
            "plan": plan,
            "message": (
                f"Nova wants to run "
                f"'{tool_name}', which requires approval."
            ),
        }

    if not tool_confidence(plan):

        return {
            "handled": False,
            "reason": "tool_not_safe_for_auto_execution",
            "plan": plan,
        }

    result = execute_tool(
        tool_name,
        payload,
    )

    formatted = format_tool_result(
        tool_name,
        result,
    )

    return {
        "handled": True,
        "status": "executed",
        "tool": tool_name,
        "payload": payload,
        "plan": plan,
        "result": result,
        "formatted": formatted,
    }