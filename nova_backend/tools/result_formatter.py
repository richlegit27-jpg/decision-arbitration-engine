from __future__ import annotations

import json
from typing import Any


def format_tool_result(
    tool_name: str,
    result: Any,
) -> str:

    try:

        formatted = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    except Exception:

        formatted = str(result)

    return (
        f"[NOVA TOOL RESULT]\n"
        f"Tool: {tool_name}\n\n"
        f"{formatted}\n"
        f"[/NOVA TOOL RESULT]"
    )