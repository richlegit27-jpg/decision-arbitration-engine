from __future__ import annotations

from nova_backend.tools.planner import plan_tool_request
from nova_backend.tools.router import route_tool_request
from nova_backend.tools.executor import execute_tool
from nova_backend.tools.confidence import tool_confidence


def run_tool_pipeline(user_text: str):
    plan = plan_tool_request(user_text)

    if not plan.get("ok"):
        return {
            "ok": False,
            "message": "No tool selected.",
        }

    if not tool_confidence(plan):
        return {
            "ok": False,
            "message": "Tool confidence too low.",
        }

    route = route_tool_request(
        plan["tool"]
    )

    if not route.get("ok"):
        return route

    return execute_tool(
        plan["tool"],
        plan.get("payload", {}),
    )