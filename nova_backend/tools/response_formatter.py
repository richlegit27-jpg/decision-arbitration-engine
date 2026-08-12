from __future__ import annotations


def format_tool_result(result: dict):
    if not result:
        return None

    if result.get("ok"):
        tool = result.get("tool", "")

        if tool == "project_workspace_update":
            return "Project workspace updated successfully."

        return "Tool completed successfully."

    return (
        "Tool execution failed: "
        + str(result.get("error", "unknown error"))
    )