from __future__ import annotations


def tool_confidence(plan: dict):
    if not plan:
        return False

    if not plan.get("ok"):
        return False

    tool = plan.get("tool")

    if tool in {
        "memory_write",
        "project_workspace_update",
    }:
        return True

    return False