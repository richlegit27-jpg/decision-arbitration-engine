from __future__ import annotations

from nova_backend.tools.pipeline import run_tool_pipeline
from nova_backend.tools.response_formatter import (
    format_tool_result,
)


def maybe_run_tool(user_text: str):
    result = run_tool_pipeline(
        user_text
    )

    if not result.get("ok"):
        return None

    return {
        "ok": True,
        "text": format_tool_result(result),
        "tool_result": result,
    }