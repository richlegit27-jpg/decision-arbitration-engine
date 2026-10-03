from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.manager import tool_manager
from nova_backend.tools.risk_policy import tool_requires_approval


def execute_tool(
    name: str,
    payload: Dict[str, Any] | None = None,
    confirm: bool = False,
):

    normalized_name = str(
        name or ""
    ).strip()

    safe_payload = (
        payload
        if isinstance(payload, dict)
        else {}
    )

    if not normalized_name:

        return {
            "ok": False,
            "error": "tool_name_required",
        }

    tool = tool_manager.get_tool(
        normalized_name
    )

    if not tool:

        return {
            "ok": False,
            "error": "tool_not_found",
            "tool": normalized_name,
        }

    if tool_requires_approval(normalized_name, tool) and confirm is not True:

        return {
            "ok": False,
            "tool": normalized_name,
            "requires_confirmation": True,
            "status": "approval_required",
            "error": "approval_required",
            "risk_level": getattr(
                tool,
                "risk_level",
                "high",
            ),
        }

    try:

        from nova_backend.services.tool_sandbox import ToolSandbox
        safe_payload, blocked = ToolSandbox().validate_payload(normalized_name, safe_payload)
        if blocked:
            return blocked

        result = tool.run(
            **safe_payload
        )

        if isinstance(result, dict):

            return {
                "tool": normalized_name,
                **result,
            }

        return {
            "ok": True,
            "tool": normalized_name,
            "result": result,
        }

    except Exception as exc:

        return {
            "ok": False,
            "tool": normalized_name,
            "error": "tool_execution_failed",
            "status": "failed",
            "error_category": "tool_execution_failed",
        }


def get_tool_metadata(
    name: str,
):

    normalized_name = str(
        name or ""
    ).strip()

    tool = tool_manager.get_tool(
        normalized_name
    )

    if not tool:

        return {
            "ok": False,
            "error": "tool_not_found",
            "tool": normalized_name,
        }

    if hasattr(
        tool,
        "get_metadata",
    ):

        return {
            "ok": True,
            "tool": tool.get_metadata(),
        }

    return {
        "ok": False,
        "error": "tool_metadata_unavailable",
        "tool": normalized_name,
    }


def list_registered_tools():

    tools = []

    for tool_name in tool_manager.list_tools():

        tool = tool_manager.get_tool(
            tool_name
        )

        if not tool:
            continue

        if hasattr(
            tool,
            "get_metadata",
        ):

            tools.append(
                tool.get_metadata()
            )

        else:

            tools.append(
                {
                    "name": tool_name,
                }
            )

    return {
        "ok": True,
        "count": len(tools),
        "tools": tools,
    }
