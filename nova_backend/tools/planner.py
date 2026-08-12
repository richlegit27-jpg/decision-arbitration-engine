from __future__ import annotations


def plan_tool_request(
    user_text: str,
):
    text = (user_text or "").lower()

    if (
        "update project" in text
        or "change project status" in text
        or "set project status" in text
    ):
        return {
            "ok": True,
            "tool": "project_workspace_update",
            "payload": {
                "project_id": "",
                "field": "status",
                "value": "active",
            },
        }

    return {
        "ok": False,
        "tool": None,
        "payload": {},
    }