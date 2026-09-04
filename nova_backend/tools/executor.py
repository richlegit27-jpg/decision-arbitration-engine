from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.manager import tool_manager


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

    if (
        getattr(
            tool,
            "requires_confirmation",
            False,
        )
        and not confirm
    ):

        return {
            "ok": False,
            "tool": normalized_name,
            "requires_confirmation": True,
            "risk_level": getattr(
                tool,
                "risk_level",
                "high",
            ),
            "payload": safe_payload,
        }

    try:

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
            "details": repr(exc),
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
