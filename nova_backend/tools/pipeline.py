from __future__ import annotations

from nova_backend.tools.planner import plan_tool_request
from nova_backend.tools.router import route_tool_request
from nova_backend.tools.executor import execute_tool


def run_tool_pipeline(
    user_text: str,
):
    plan = plan_tool_request(user_text)

    if not plan.get("ok"):
        return {
            "ok": False,
            "message": "No tool selected.",
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