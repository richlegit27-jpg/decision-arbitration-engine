from __future__ import annotations


import logging
import time
import uuid
from nova_backend.services.python_runner_service import PythonRunnerService
from nova_backend.services.tool_sandbox import ToolSandbox
from nova_backend.tools.risk_policy import tool_risk_metadata, tool_requires_approval


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

    SAFE_ERROR_CATEGORIES = {
        "approval_required", "invalid_tool_input", "sandbox_unavailable",
        "sandbox_path_blocked", "tool_execution_failed", "tool_failed",
        "invalid_tool_result", "tool_not_registered", "tool_runtime_unavailable",
    }

    def __init__(
        self,
        action_router=None,
        nova_tool_registry=None,
        python_runner=None,
    ):
        self.action_router = action_router
        self.nova_tool_registry = nova_tool_registry
        self.python_runner = python_runner or PythonRunnerService()
        self.tool_sandbox = ToolSandbox(self.python_runner)
        self.logger = logging.getLogger("nova.tools")

    def _validate_tool_payload(self, tool_name, payload):
        tool = self.nova_tool_registry.get(tool_name) if self.nova_tool_registry is not None else None
        if tool is None and tool_name in self.INTERNAL_TOOLS:
            return None
        if tool is None or not callable(getattr(tool, "get_metadata", None)):
            return {"ok": False, "tool": tool_name, "status": "failed", "error": "tool_not_registered", "error_category": "tool_not_registered", "summary": "This tool is not available."}
        if not isinstance(payload, dict):
            return {"ok": False, "tool": tool_name, "status": "failed", "error": "tool_parameter_invalid", "error_category": "invalid_tool_input", "summary": "Tool arguments must be an object."}
        schema = tool.get_metadata().get("parameter_schema") or {}
        if not isinstance(schema, dict) or schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
            return {"ok": False, "tool": tool_name, "status": "unavailable", "error": "tool_schema_unavailable", "error_category": "tool_runtime_unavailable", "summary": "This tool is temporarily unavailable."}
        properties = schema.get("properties") or {}
        for key in schema.get("required") or []:
            if key not in payload:
                return {"ok": False, "tool": tool_name, "status": "failed", "error": "tool_parameter_required", "error_category": "invalid_tool_input", "summary": f"The {key} parameter is required."}
        type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
        for key, value in payload.items():
            definition = properties.get(key)
            if not definition:
                if schema.get("additionalProperties", False) is False:
                    return {"ok": False, "tool": tool_name, "status": "failed", "error": "tool_parameter_unknown", "error_category": "invalid_tool_input", "summary": f"The {key} parameter is not supported."}
                continue
            expected = type_map.get(definition.get("type"))
            if expected and (not isinstance(value, expected) or (definition.get("type") in {"integer", "number"} and isinstance(value, bool))):
                return {"ok": False, "tool": tool_name, "status": "failed", "error": "tool_parameter_invalid", "error_category": "invalid_tool_input", "summary": f"The {key} parameter has an invalid type."}
        return None

    def run(self, tool_name: str, payload: dict | None = None, confirm: bool = False) -> dict:
        name = str(tool_name or "").strip().lower()
        safe_log_tool_name = name if len(name) <= 80 and all(char.isalnum() or char in "_.-" for char in name) else "unknown_tool"
        args = payload if isinstance(payload, dict) else {}
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        tool = self.nova_tool_registry.get(name) if self.nova_tool_registry is not None else None
        risk = tool_risk_metadata(name, tool)
        self.logger.info("tool execution started", extra={"tool_name": safe_log_tool_name, "request_id": request_id, "risk_class": risk["risk_class"]})
        invalid = self._validate_tool_payload(name, args)
        safe_args, blocked = self.tool_sandbox.validate_payload(name, args)
        if invalid or blocked:
            result = invalid or blocked
        elif tool_requires_approval(name, tool) and confirm is not True:
            result = {"ok": False, "tool": name, "status": "approval_required", "requires_confirmation": True,
                      "error": "approval_required", "error_category": "approval_required"}
        else:
            result = self._run_impl(name, safe_args, confirm=confirm)
        if not isinstance(result, dict):
            result = {"ok": False, "error": "invalid_tool_result"}
        result.setdefault("request_id", request_id)
        result.setdefault("risk_class", risk["risk_class"])
        result.setdefault("requires_approval", risk["requires_approval"])
        result.setdefault("status", "executed" if result.get("ok") is True else "failed")
        result.setdefault("summary", str(result.get("message") or result.get("error") or ("Tool completed." if result.get("ok") else "Tool failed.")))
        if "data" not in result or result.get("data") is None:
            result["data"] = result.get("result")
            if result["data"] is None and result.get("ok") is True:
                envelope_keys = {
                    "ok", "request_id", "risk_class", "requires_approval", "status",
                    "summary", "data", "artifact", "error_category", "retryable", "diagnostics",
                }
                result["data"] = {key: value for key, value in result.items() if key not in envelope_keys}
        result.setdefault("artifact", result.get("artifact_id"))
        if result.get("ok") is True:
            result.setdefault("error_category", None)
        else:
            raw_category = str(result.get("error_category") or result.get("error") or "").strip().lower()
            result["error_category"] = raw_category if raw_category in self.SAFE_ERROR_CATEGORIES else "tool_failed"
            # Tool implementations and provider errors are untrusted. Keep
            # their details in server logs only; model-visible results use a
            # stable safe category and message.
            result["error"] = result["error_category"]
            result["message"] = (
                "Approval is required before this action can run."
                if result["error_category"] == "approval_required"
                else "The requested tool could not be completed."
            )
            result["summary"] = result["message"]
            result["data"] = None
            result["diagnostics"] = None
        result.setdefault("retryable", False)
        result.setdefault("diagnostics", None)
        self.logger.info("tool execution finished", extra={
            "tool_name": safe_log_tool_name, "request_id": request_id, "duration_ms": round((time.monotonic() - started) * 1000),
            "success": bool(result.get("ok")), "status": result.get("status"),
            "error_category": result.get("error_category"), "approval_state": "approved" if confirm is True else "not_approved",
        })
        return result

    def _run_impl(
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



