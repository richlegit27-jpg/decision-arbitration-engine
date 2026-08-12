from __future__ import annotations


def tool_confidence(plan: dict):
    if not plan:
        return False

    if not plan.get("ok"):
        return False

    tool = plan.get("tool")

    allowed_tools = {
        "memory_write",
        "memory_read",
        "memory_delete",
        "project_workspace_update",
    }

    return tool in allowed_tools