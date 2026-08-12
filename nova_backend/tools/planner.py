from __future__ import annotations


def plan_tool_request(
    user_text: str,
):
    text = (user_text or "").lower()

    if (
        "forget" in text
        or "delete memory" in text
        or "remove memory" in text
    ):
        return {
            "ok": True,
            "tool": "memory_delete",
            "payload": {
                "memory_id": "",
            },
        }

    if (
        "remember" in text
        or "save this" in text
        or "store this" in text
    ):
        content = user_text

        for prefix in [
            "remember that ",
            "remember ",
            "save this ",
            "store this ",
        ]:
            if content.lower().startswith(prefix):
                content = content[len(prefix):]
                break

        return {
            "ok": True,
            "tool": "memory_write",
            "payload": {
                "content": content.strip(),
            },
        }

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