from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.registry import registry


def execute_tool(
    name: str,
    payload: Dict[str, Any] | None = None,
):
    payload = payload or {}

    tool = registry.get(name)

    if not tool:
        return {
            "ok": False,
            "error": "tool_not_found",
            "tool": name,
        }

    try:
        result = tool.run(**payload)

        return {
            "ok": True,
            "tool": name,
            "result": result,
        }

    except Exception as exc:
        import traceback

        traceback.print_exc()

        return {
            "ok": False,
            "tool": name,
            "error": repr(exc),
        }