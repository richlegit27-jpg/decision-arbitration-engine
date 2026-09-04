from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.tool_orchestrator import (
    tool_orchestrator,
)


def process_tool_request(
    user_text: str,
    approved: bool = False,
) -> Dict[str, Any]:

    result = tool_orchestrator.handle(
        user_text=user_text,
        approved=approved,
    )

    if not result.get("handled"):

        return {
            "handled": False,
            "approval_required": False,
            "plan": result.get("plan"),
            "result": None,
            "formatted": None,
        }

    if (
        result.get("status")
        == "approval_required"
    ):

        return {
            "handled": True,
            "approval_required": True,
            "plan": {
                "ok": True,
                "tool": result.get("tool"),
                "payload": result.get("payload"),
            },
            "result": None,
            "formatted": None,
        }

    return {
        "handled": True,
        "approval_required": False,
        "plan": {
            "ok": True,
            "tool": result.get("tool"),
            "payload": result.get("payload"),
        },
        "result": result.get("result"),
        "formatted": result.get("formatted"),
    }
