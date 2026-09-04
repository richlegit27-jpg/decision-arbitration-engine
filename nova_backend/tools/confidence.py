from __future__ import annotations

from nova_backend.tools.manager import (
    tool_manager,
)


def get_tool(
    tool_name: str | None,
):

    if not tool_name:
        return None

    return tool_manager.get_tool(
        str(tool_name).strip()
    )


def get_tool_risk(
    tool_name: str | None,
):

    tool = get_tool(tool_name)

    if not tool:
        return "unknown"

    risk = getattr(
        tool,
        "risk_level",
        None,
    )

    if not risk:
        return "unknown"

    return str(
        risk
    ).strip().lower()


def tool_confidence(
    plan: dict,
):

    if not plan:
        return False

    if not plan.get("ok"):
        return False

    tool_name = plan.get("tool")

    tool = get_tool(tool_name)

    if not tool:
        return False

    requires_confirmation_flag = bool(
        getattr(
            tool,
            "requires_confirmation",
            False,
        )
    )

    if requires_confirmation_flag:
        return False

    risk = get_tool_risk(
        tool_name
    )

    return risk in {
        "low",
        "safe",
        "medium",
    }


def requires_approval(
    plan: dict,
):

    if not plan:
        return False

    if not plan.get("ok"):
        return False

    tool_name = plan.get("tool")

    tool = get_tool(tool_name)

    if not tool:
        return True

    return bool(
        getattr(
            tool,
            "requires_confirmation",
            False,
        )
    )
