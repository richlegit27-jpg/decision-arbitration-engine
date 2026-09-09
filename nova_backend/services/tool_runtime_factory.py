from __future__ import annotations


from nova_backend.services.action_router import (
    ActionRouter,
)

from nova_backend.services.tool_bridge import (
    ToolBridge,
)

from nova_backend.services.tool_executor import (
    ToolExecutor,
)

from nova_backend.services.tool_registry import (
    ToolRegistry,
)

from nova_backend.tools.loader import (
    load_tools,
)

from nova_backend.tools.registry import (
    registry as nova_tool_registry,
)


def build_tool_runtime(
    session_service=None,
    chat_service=None,
    attachment_service=None,
) -> dict:

    missing_dependencies = []

    if session_service is None:
        missing_dependencies.append(
            "session_service"
        )

    if missing_dependencies:
        return {
            "ok": False,
            "error": (
                "Missing tool runtime dependencies."
            ),
            "missing_dependencies": (
                missing_dependencies
            ),
            "action_router": None,
            "tool_executor": None,
            "tool_registry": None,
            "tool_bridge": None,
            "nova_tool_registry": None,
            "real_tool_count": None,
        }

    # =========================================================
    # LOAD REAL NOVA TOOLS
    #
    # The tool runtime owns real tool registration.
    # ChatService is optional and is only passed to tools that
    # need access to it, such as legacy workflow adapters.
    # =========================================================

    load_tools(
        chat_service=chat_service,
    )


    # =========================================================
    # INTERNAL ACTION ROUTER
    # =========================================================

    action_router = ActionRouter(
        session_service=session_service,
        chat_service=chat_service,
        attachment_service=attachment_service,
    )

    # =========================================================
    # UNIFIED EXECUTOR
    # =========================================================

    tool_executor = ToolExecutor(
        action_router=action_router,
        nova_tool_registry=nova_tool_registry,
    )

    # =========================================================
    # SERVICE TOOL REGISTRY
    # =========================================================

    tool_registry = ToolRegistry(
        tool_executor=tool_executor,
        chat_service=chat_service,
        nova_tool_registry=nova_tool_registry,
    )

    # =========================================================
    # TOOL BRIDGE
    # =========================================================

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
        "nova_tool_registry": nova_tool_registry,
        "real_tool_count": len(
            nova_tool_registry.list_tools()
        ),
    }
