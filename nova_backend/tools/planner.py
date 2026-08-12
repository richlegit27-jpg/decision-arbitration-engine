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
            user_text,
        )

        memory_id = match.group(0) if match else ""

        return {
            "ok": True,
            "tool": "memory_delete",
            "payload": {
                "memory_id": memory_id,
            },
        }

    if (
        text.startswith("remember ")
        or text.startswith("save this ")
        or text.startswith("store this ")
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
        "what do you remember" in text
        or "show my memories" in text
        or "what memories" in text
        or "what do you know about me" in text
    ):
        return {
            "ok": True,
            "tool": "memory_read",
            "payload": {},
        }

    return {
        "ok": False,
        "tool": None,
        "payload": {},
    }