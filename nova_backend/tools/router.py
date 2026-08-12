from __future__ import annotations

from nova_backend.tools.manager import tool_manager


def route_tool_request(name: str):
    if not tool_manager.has_tool(name):
        return {
            "ok": False,
            "error": "tool_not_available",
            "tool": name,
        }

    return {
        "ok": True,
        "tool": name,
    }