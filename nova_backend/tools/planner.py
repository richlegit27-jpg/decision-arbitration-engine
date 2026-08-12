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
        import re

        match = re.search(
            r"memory_[a-zA-Z0-9]+",
            user_text
        )

        memory_id = match.group(0) if match else ""

        return {
            "ok": True,
            "tool": "memory_delete",
            "payload": {
                "memory_id": memory_id,
            },
        }