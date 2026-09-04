from __future__ import annotations


READ_ONLY_TOOLS = {
    "memory_read",
    "file_read",
    "file_list",
    "code_search",
    "git_status",
    "git_diff",
    "git_log",
    "git_show",
}


LOW_RISK_WRITE_TOOLS = {
    "memory_write",
    "project_workspace_update",
    "directory_create",
}


HIGH_RISK_TOOLS = {
    "memory_delete",
    "file_write",
    "file_delete",
    "code_replace",
    "file_move",
    "git_commit",
    "process_start",
}


def get_tool_risk(
    tool_name: str | None,
):
    if not tool_name:
        return "unknown"

    if tool_name in READ_ONLY_TOOLS:
        return "safe"

    if tool_name in LOW_RISK_WRITE_TOOLS:
        return "low"

    if tool_name in HIGH_RISK_TOOLS:
        return "high"

    return "unknown"


def tool_confidence(
    plan: dict,
):
    if not plan:
        return False

    if not plan.get("ok"):
        return False

    tool = plan.get("tool")

    risk = get_tool_risk(tool)

    return risk in {
        "safe",
        "low",
    }


def requires_approval(
    plan: dict,
):
    if not plan:
        return False

    if not plan.get("ok"):
        return False

    tool = plan.get("tool")

    return get_tool_risk(tool) == "high"