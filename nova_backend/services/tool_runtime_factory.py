from __future__ import annotations

from nova_backend.services.action_router import ActionRouter
from nova_backend.services.tool_bridge import ToolBridge
from nova_backend.services.tool_executor import ToolExecutor
from nova_backend.services.tool_registry import ToolRegistry


def build_tool_runtime(
    session_service=None,
    chat_service=None,
    attachment_service=None,
) -> dict:
    missing_dependencies = []

    if session_service is None:
        missing_dependencies.append("session_service")

    if chat_service is None:
        missing_dependencies.append("chat_service")

    if attachment_service is None:
        missing_dependencies.append("attachment_service")

    if missing_dependencies:
        return {
            "ok": False,
            "error": "Missing tool runtime dependencies.",
            "missing_dependencies": missing_dependencies,
            "action_router": None,
            "tool_executor": None,
            "tool_registry": None,
            "tool_bridge": None,
        }

    action_router = ActionRouter(
        session_service=session_service,
        chat_service=chat_service,
        attachment_service=attachment_service,
    )

    tool_executor = ToolExecutor(
        action_router=action_router,
    )

    tool_registry = ToolRegistry(
        tool_executor=tool_executor,
        chat_service=chat_service,
    )

    tool_bridge = ToolBridge(
        tool_registry=tool_registry,
        tool_executor=tool_executor,
    )

    return {
        "ok": True,
        "action_router": action_router,
        "tool_executor": tool_executor,
        "tool_registry": tool_registry,
        "tool_bridge": tool_bridge,
    }