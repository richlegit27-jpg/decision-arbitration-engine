from __future__ import annotations


class ToolExecutor:
    """
    Central execution gate for registered Nova tools.

    Routes internal application actions through ActionRouter and
    real Nova tools through nova_backend.tools.registry.
    """

    INTERNAL_TOOLS = {
        "chat.send",
        "session.rename",
        "session.pin",
        "session.delete",
        "attachment.upload",
        "attachment.analyze",
    }

    PLANNED_EXTERNAL_TOOLS = {
        "email.send",
        "calendar.create",
    }

    REQUIRES_CONFIRMATION = {
        "email.send",
        "calendar.create",
    }

    INTENT_MAP = {
        "rename": "session.rename",
        "pin": "session.pin",
        "delete": "session.delete",
        "upload": "attachment.upload",
        "analyze": "attachment.analyze",
        "chat": "chat.send",
        "email": "email.send",
        "calendar": "calendar.create",

        # REAL NOVA TOOLS
        "memory_write": "memory_write",
        "memory_read": "memory_read",
        "memory_delete": "memory_delete",

        "workspace": "project_workspace_update",
        "project_tree": "project_tree",

        "file_read": "file_read",
        "file_list": "file_list",
        "file_write": "file_write",
        "file_delete": "file_delete",
        "file_move": "file_move",

        "directory_create": "directory_create",
        "directory_delete": "directory_delete",

        "code_search": "code_search",
        "code_replace": "code_replace",

        "git_status": "git_status",
        "git_diff": "git_diff",
        "git_log": "git_log",
        "git_show": "git_show",
        "git_commit": "git_commit",

        "shell": "shell_command",
        "terminal": "terminal_execute",

        "process_list": "process_list",
        "process_start": "process_start",
        "process_stop": "process_stop",
    }

    def __init__(
        self,
        action_router=None,
        nova_tool_registry=None,
    ):
        self.action_router = action_router
        self.nova_tool_registry = nova_tool_registry

    def run(
        self,
        tool_name: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        normalized_name = str(
            tool_name or ""
        ).lower().strip()

        safe_payload = (
            payload
            if isinstance(payload, dict)
            else {}
        )

        if not normalized_name:
            return {
                "ok": False,
                "error": "Missing tool name",
            }

        # =====================================================
        # INTERNAL NOVA APPLICATION ACTIONS
        # =====================================================

        if normalized_name in self.INTERNAL_TOOLS:

            if self.action_router is None:
                return {
                    "ok": False,
                    "tool": normalized_name,
                    "error": (
                        "Action router is not configured."
                    ),
                }

            try:
                result = self.action_router.execute(
                    normalized_name,
                    safe_payload,
                )

            except Exception as error:
                return {
                    "ok": False,
                    "tool": normalized_name,
                    "error": str(error),
                }

            if isinstance(result, dict):

                normalized_result = dict(result)

                normalized_result.setdefault(
                    "tool",
                    normalized_name,
                )

                normalized_result.setdefault(
                    "tool_name",
                    normalized_name,
                )

                # Internal application actions may return the
                # resource directly instead of an {"ok": True}
                # envelope. Only explicit False is a failure.
                if normalized_result.get("ok") is False:

                    normalized_result.setdefault(
                        "status",
                        "failed",
                    )

                else:

                    normalized_result.setdefault(
                        "ok",
                        True,
                    )

                    normalized_result.setdefault(
                        "status",
                        "executed",
                    )

                return normalized_result

            return {
                "ok": True,
                "tool": normalized_name,
                "tool_name": normalized_name,
                "status": "executed",
                "result": result,
            }

        # =====================================================
        # REAL NOVA TOOL REGISTRY
        # =====================================================

        if self.nova_tool_registry is not None:

            tool = self.nova_tool_registry.get(
                normalized_name
            )

            if tool is not None:

                requires_confirmation = bool(
                    getattr(
                        tool,
                        "requires_confirmation",
                        False,
                    )
                )

                if (
                    requires_confirmation
                    and not confirm
                ):
                    return {
                        "ok": False,
                        "requires_confirmation": True,
                        "tool": normalized_name,
                        "payload": safe_payload,
                    }

                print(
                    "DEBUG TOOL EXECUTOR DISPATCH =",
                    {
                        "tool_name": normalized_name,
                        "tool_class": type(tool).__name__,
                        "payload": safe_payload,
                    },
                    flush=True,
                )

                try:
                    result = tool.run(
                        **safe_payload
                    )

                except Exception as error:
                    return {
                        "ok": False,
                        "tool": normalized_name,
                        "error": str(error),
                    }
                if isinstance(result, dict):

                    normalized_result = dict(result)

                    normalized_result.setdefault(
                        "tool",
                        normalized_name,
                    )

                    normalized_result.setdefault(
                        "tool_name",
                        normalized_name,
                    )

                    if normalized_result.get("ok") is True:

                        normalized_result.setdefault(
                            "status",
                            "executed",
                        )

                    elif normalized_result.get("ok") is False:

                        normalized_result.setdefault(
                            "status",
                            "failed",
                        )

                    return normalized_result

                return {
                    "ok": True,
                    "tool": normalized_name,
                    "tool_name": normalized_name,
                    "status": "executed",
                    "result": result,
                }

        # =====================================================
        # PLANNED EXTERNAL TOOLS
        # =====================================================

        if normalized_name in self.PLANNED_EXTERNAL_TOOLS:

            if (
                normalized_name
                in self.REQUIRES_CONFIRMATION
                and not confirm
            ):
                return {
                    "ok": False,
                    "requires_confirmation": True,
                    "tool": normalized_name,
                    "payload": safe_payload,
                }

            return {
                "ok": False,
                "tool": normalized_name,
                "implemented": False,
                "error": (
                    "Tool is registered but not implemented yet: "
                    f"{normalized_name}"
                ),
            }

        return {
            "ok": False,
            "tool": normalized_name,
            "error": (
                f"Tool not registered: {normalized_name}"
            ),
        }

    def auto_decide_and_run(
        self,
        intent: str,
        payload: dict | None = None,
        confirm: bool = False,
    ) -> dict:
        normalized_intent = str(
            intent or ""
        ).lower().strip()

        tool_name = self.INTENT_MAP.get(
            normalized_intent
        )

        if not tool_name:
            return {
                "ok": False,
                "error": (
                    f"No tool mapped for intent: {intent}"
                ),
            }

        return self.run(
            tool_name,
            payload or {},
            confirm=confirm,
        )



