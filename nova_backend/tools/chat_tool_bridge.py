from __future__ import annotations

from nova_backend.tools.pipeline import run_tool_pipeline


def maybe_run_tool(user_text: str):
    result = run_tool_pipeline(user_text)

    if result.get("ok"):
        return result

    return None