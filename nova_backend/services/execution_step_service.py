from pathlib import Path

from nova_backend.services.execution_approval_service import (
    ExecutionApprovalService,
)

from nova_backend.services.ai_execution_service import (
    AIExecutionService,
)


class ExecutionStepService:

    AI_ACTIONS = {
        "analysis",
        "analyze",
        "diagnose",
        "diagnosis",
        "fix",
        "repair",
        "validate",
        "validation",
        "verify",
        "review",
        "research",
        "organize",
        "summarize",
        "summary",
        "planning",
        "plan",
        "architecture",
        "design",
        "integration",
        "optimize",
        "optimization",
        "delivery",
        "build",
    }

    IMPLEMENT_ACTIONS = {
        "implement",
        "implementation",
        "coding",
        "code",
        "build",
        "create",
        "write",
        "edit",
        "modify",
        "fix",
        "repair",
    }

    RUN_ACTIONS = {
        "test",
        "testing",
        "run",
        "execute",
    }

    ACTION_ALIASES = {
        "analyse": "analyze",
        "diagnosis": "diagnose",
        "repair": "fix",
        "validation": "validate",
        "summary": "summarize",
        "research": "design",
        "review": "design",
        "plan": "planning",
        "optimize": "optimization",
        "coding": "implement",
        "code": "implement",
    }

    def __init__(
        self,
        safe_str=None,
        python_runner=None,
        approval_service=None,
        ai_execution_service=None,
        tool_executor=None,
    ):
        self.safe_str = safe_str
        self.python_runner = python_runner
        self.tool_executor = tool_executor

        self.approval_service = (
            approval_service
            or ExecutionApprovalService()
        )

        self.ai_execution_service = (
            ai_execution_service
            or AIExecutionService(
                safe_str=self._safe_str,
            )
        )

    def _safe_str(
        self,
        value,
    ):
        if callable(self.safe_str):
            return self.safe_str(value)

        return str(value or "")

    def _implementation_content(
        self,
        step,
    ):
        for key in (
            "content",
            "file_content",
            "code",
        ):
            value = step.get(key)

            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value

        return ""

    def _execute_tool_step(
        self,
        step,
    ):
        if self.tool_executor is None:
            raise RuntimeError(
                "Nova tool executor is not configured."
            )

        tool_name = self._safe_str(
            step.get("tool_name")
            or step.get("tool")
            or step.get("tool_action")
        ).strip()

        if not tool_name:
            raise RuntimeError(
                "Tool execution step is missing a tool name."
            )

        payload = (
            step.get("payload")
            or step.get("tool_payload")
            or step.get("arguments")
            or {}
        )

        if not isinstance(payload, dict):
            payload = {}

        confirm = bool(
            step.get("confirm")
            or step.get("confirmed")
        )

        result = self.tool_executor.run(
            tool_name,
            payload,
            confirm=confirm,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Tool executor returned an invalid result."
            )

        if not result.get("ok"):
            raise RuntimeError(
                self._safe_str(
                    result.get("error")
                    or "Tool execution failed."
                )
            )

        step["result"] = result
        step["error"] = None

        step["execution_metadata"] = {
            "executor": "unified_tool_executor",
            "tool_name": tool_name,
            "success": True,
        }

        return step

    def _execute_ai_step(
        self,
        session_id,
        step,
    ):
        ai_result = (
            self.ai_execution_service.execute_step(
                session_id=session_id,
                step=step,
                context={
                    "project_context": self._safe_str(
                        step.get("project_context")
                        or step.get("context")
                        or step.get("input")
                        or ""
                    ),
                },
            )
        )

        if not isinstance(ai_result, dict):
            raise RuntimeError(
                "AI execution returned an invalid result."
            )

        if not ai_result.get("ok"):
            raise RuntimeError(
                self._safe_str(
                    ai_result.get("error")
                    or "AI execution failed."
                )
            )

        result = self._safe_str(
            ai_result.get("output")
        ).strip()

        if not result:
            raise RuntimeError(
                "AI execution returned an empty result."
            )

        step["result"] = result
        step["error"] = None

        return step

    def _generate_file_replacement(
        self,
        session_id,
        step,
    ):

        target_file = self._safe_str(
            step.get("target_file")
            or step.get("path")
            or ""
        ).strip()

        existing_content = ""

        if (
            target_file
            and self.python_runner is not None
            and self.python_runner.is_path_allowed(
                target_file
            )
        ):
            resolved_target = (
                self.python_runner.resolve_sandbox_path(
                    target_file
                )
            )

            if Path(resolved_target).is_file():
                existing_content = (
                    Path(resolved_target).read_text(
                        encoding="utf-8"
                    )
                )

        step["existing_content"] = existing_content

        ai_result = (
            self.ai_execution_service.generate_file_replacement(
                session_id=session_id,
                step=step,
                context={
                    "project_context": self._safe_str(
                        step.get("project_context")
                        or step.get("context")
                        or step.get("input")
                        or ""
                    ),
                    "previous_results": (
                        step.get("previous_results")
                        or ""
                    ),
                    "existing_content": self._safe_str(
                        step.get("existing_content")
                        or ""
                    ),
                },
            )
        )

        if not isinstance(ai_result, dict):
            raise RuntimeError(
                "File replacement generation returned an invalid result."
            )

        if not ai_result.get("ok"):
            raise RuntimeError(
                self._safe_str(
                    ai_result.get("error")
                    or "File replacement generation failed."
                )
            )

        content = self._safe_str(
            ai_result.get("content")
        )

        if not content.strip():
            raise RuntimeError(
                "File replacement generation returned empty content."
            )

        step["content"] = content
        step["code"] = content

        step["next_action"] = "write_file"
        step["mutation_ready"] = True
        step["payload_required"] = False

        step["error"] = None

        return step

    def _execute_file_implementation(
        self,
        step,
        target_file,
        content,
    ):
        if self.python_runner is None:
            raise RuntimeError(
                "Python execution service is not available."
            )

        if not self.python_runner.is_path_allowed(
            target_file
        ):
            raise PermissionError(
                "Write blocked: target is outside "
                "Nova's execution sandbox."
            )

        resolved_target = str(
            self.python_runner.resolve_sandbox_path(
                target_file
            )
        )

        step["target_file"] = resolved_target

        Path(resolved_target).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not content.endswith("\n"):
            content += "\n"

        Path(resolved_target).write_text(
            content,
            encoding="utf-8",
        )

        step["result"] = (
            f"Created file: {resolved_target}"
        )

        step["error"] = None

        return step

    def _execute_local_run(
        self,
        step,
        target_file,
    ):
        if self.python_runner is None:
            raise RuntimeError(
                "Python execution service is not available."
            )

        python_result = (
            self.python_runner.run_file(
                target_file
            )
        )

        result = (
            f"STDOUT={python_result.get('stdout')} | "
            f"STDERR={python_result.get('stderr')} | "
            f"ERROR={python_result.get('error')}"
        )

        step["result"] = result

        step["error"] = (
            None
            if python_result.get("ok")
            else result
        )

        if not python_result.get("ok"):
            raise RuntimeError(result)

        return step

    def _normalize_tool_step(
        self,
        step,
    ):
        if not isinstance(step, dict):
            return step

        action = self._safe_str(
            step.get("action")
        ).strip().lower()

        if not action:
            title = self._safe_str(
                step.get("title")
                or step.get("name")
                or step.get("description")
            ).strip().lower()

            if title.startswith("pin "):
                action = "pin"

            elif title.startswith("rename "):
                action = "rename"

            elif title.startswith("delete "):
                action = "delete"

            elif title.startswith("read "):
                action = "read_file"

            elif title.startswith("write "):
                action = "write_file"

            elif title.startswith("search "):
                action = "search_code"

            elif title.startswith("run "):
                action = "run_python"

        tool_name = self._safe_str(
            step.get("tool_name")
            or step.get("tool")
            or step.get("tool_action")
        ).strip()

        if tool_name:
            step["tool_name"] = tool_name

            payload = (
                step.get("payload")
                or step.get("tool_payload")
                or step.get("arguments")
                or {}
            )

            if isinstance(payload, dict):
                step["payload"] = payload
            else:
                step["payload"] = {}

            return step

        tool_aliases = {
            # Session actions
            "rename": "session.rename",
            "pin": "session.pin",
            "delete": "session.delete",

            # Attachment actions
            "upload": "attachment.upload",
            "analyze_attachment": "attachment.analyze",

            # File actions
            "read_file": "file_read",
            "list_files": "file_list",
            "write_file": "file_write",
            "delete_file": "file_delete",
            "move_file": "file_move",

            # Directory actions
            "create_directory": "directory_create",
            "delete_directory": "directory_delete",

            # Code actions
            "search_code": "code_search",
            "replace_code": "code_replace",

            # Python actions
            "run_python": "python_run",
            "compile_python": "python_compile",

            # Process actions
            "check_processes": "process_list",
            "start_process": "process_start",
            "stop_process": "process_stop",

            # Git actions
            "git_status": "git_status",
            "git_diff": "git_diff",
            "git_log": "git_log",
            "git_show": "git_show",
            "git_commit": "git_commit",

            # Shell actions
            "run_shell": "shell_command",
            "run_terminal": "terminal_execute",
            "shell": "shell_command",
            "terminal": "terminal_execute",
        }

        mapped_tool = tool_aliases.get(action)

        if mapped_tool:
            step["tool_name"] = mapped_tool

            if not isinstance(
                step.get("payload"),
                dict,
            ):
                step["payload"] = {}

            if mapped_tool.startswith("session."):
                session_id = self._safe_str(
                    step.get("session_id")
                    or step["payload"].get("session_id")
                ).strip()

                if session_id:
                    step["payload"]["session_id"] = session_id

                if mapped_tool == "session.pin":
                    step["payload"].setdefault(
                        "pinned",
                        True,
                    )

            if mapped_tool == "session.rename":
                title = self._safe_str(
                    step.get("new_title")
                    or step.get("title")
                ).strip()

                if title:
                    step["payload"].setdefault(
                        "title",
                        title,
                    )

        target_file = self._safe_str(
            step.get("target_file")
            or step.get("path")
        ).strip()

        payload = step.get("payload")

        if not isinstance(payload, dict):
            payload = {}

        file_tools = {
            "file_read",
            "file_write",
            "file_delete",
            "file_exists",
            "file_info",
            "file_append",
            "python_compile",
            "python_run",
        }

        current_tool = self._safe_str(
            step.get("tool_name")
        ).strip()

        if (
            current_tool in file_tools
            and target_file
            and not payload.get("path")
        ):
            payload["path"] = target_file

        step["payload"] = payload

        return step

    def execute_step_logic(
        self,
        session_id,
        step,
    ):
        step = (
            step
            if isinstance(step, dict)
            else {}
        )

        step = self._normalize_tool_step(
            step
        )

        execution_mode = self._safe_str(
            step.get("execution_mode")
        ).strip().lower()

        dependencies = step.get(
            "dependencies",
            []
        )

        if not isinstance(
            dependencies,
            list,
        ):
            dependencies = []

        expected_output = self._safe_str(
            step.get("expected_output")
        ).strip()

        completion_criteria = step.get(
            "completion_criteria",
            []
        )

        if not isinstance(
            completion_criteria,
            list,
        ):
            completion_criteria = []

        step["execution_mode"] = execution_mode
        step["dependencies"] = dependencies
        step["expected_output"] = expected_output
        step["completion_criteria"] = completion_criteria

        print(
            "DEBUG EXECUTOR RECEIVED STEP =",
            step,
            flush=True,
        )

        print(
            "DEBUG EXECUTOR PLANNING METADATA =",
            {
                "execution_mode": execution_mode,
                "dependencies": dependencies,
                "expected_output": expected_output,
                "completion_criteria": completion_criteria,
            },
            flush=True,
        )

        try:
            approval = (
                self.approval_service.evaluate(
                    step
                )
            )

            if approval.get("waiting"):
                step["status"] = "waiting_approval"
                step["result"] = ""
                step["error"] = (
                    approval.get("reason")
                    or "Approval required before execution."
                )

                step["execution_metadata"] = {
                    "success": False,
                    "waiting_approval": True,
                    "action": self._safe_str(
                        step.get("action")
                    ),
                }

                return step

            step["status"] = "running"

            step_action = self._safe_str(
                step.get("action")
            ).strip().lower()

            if not step_action:
                step_action = "design"

                print(
                    "DEBUG EXECUTOR: missing action, "
                    "defaulting to AI execution",
                    flush=True,
                )

            step_action = self.ACTION_ALIASES.get(
                step_action,
                step_action,
            )

            target_file = self._safe_str(
                step.get("target_file")
            ).strip()

            content = (
                self._implementation_content(
                    step
                )
            )

            print(
                "DEBUG EXECUTOR NORMALIZED ACTION =",
                {
                    "action": step_action,
                    "target_file": target_file,
                    "has_content": bool(content),
                },
                flush=True,
            )

            next_action = self._safe_str(
                step.get("next_action")
            ).strip().lower()

            print(
                "DEBUG EXECUTOR NEXT ACTION =",
                {
                    "next_action": next_action,
                    "target_file": target_file,
                },
                flush=True,
            )

            if (
                next_action == "generate_file_replacement"
                and step_action in self.IMPLEMENT_ACTIONS
                and target_file
                and not content
            ):
                self._generate_file_replacement(
                    session_id=session_id,
                    step=step,
                )

                content = self._implementation_content(
                    step
                )

                if not content.strip():
                    raise RuntimeError(
                        "Generated file replacement content was empty."
                    )

                self._execute_file_implementation(
                    step=step,
                    target_file=target_file,
                    content=content,
                )

            # ---------------------------------
            # REAL NOVA TOOL EXECUTION
            # ---------------------------------

            if (
                step.get("tool_name")
                or step.get("tool")
                or step.get("tool_action")
            ):
                self._execute_tool_step(
                    step=step,
                )

            # ---------------------------------
            # FILE IMPLEMENTATION
            # ---------------------------------

            elif (
                step_action in self.IMPLEMENT_ACTIONS
                and target_file
                and content
            ):
                self._execute_file_implementation(
                    step=step,
                    target_file=target_file,
                    content=content,
                )

            # ---------------------------------
            # LOCAL TEST / RUN
            # ---------------------------------

            elif (
                step_action in self.RUN_ACTIONS
                and target_file
                and self.python_runner is not None
            ):
                self._execute_local_run(
                    step=step,
                    target_file=target_file,
                )

            # ---------------------------------
            # AI IMPLEMENTATION FALLBACK
            #
            # "implement" without an explicit
            # target file and code is reasoning
            # work, not a failed file operation.
            # ---------------------------------

            elif step_action in self.IMPLEMENT_ACTIONS:
                self._execute_ai_step(
                    session_id=session_id,
                    step=step,
                )

            # ---------------------------------
            # AI TASKS
            # ---------------------------------

            elif step_action in self.AI_ACTIONS:
                self._execute_ai_step(
                    session_id=session_id,
                    step=step,
                )

            # ---------------------------------
            # UNKNOWN ACTION
            #
            # Unknown natural-language actions
            # should still be given to the AI
            # execution engine rather than
            # immediately killing the plan.
            # ---------------------------------

            else:
                print(
                    "DEBUG EXECUTOR: unknown action "
                    "falling back to AI execution =",
                    step_action,
                    flush=True,
                )

                self._execute_ai_step(
                    session_id=session_id,
                    step=step,
                )

            step["status"] = "completed"

        except Exception as exc:
            error_message = self._safe_str(
                exc
            )

            print(
                "EXECUTION STEP FAILED DEBUG =",
                {
                    "step_id": step.get("id"),
                    "title": step.get("title"),
                    "action": step.get("action"),
                    "error": error_message,
                },
                flush=True,
            )

            step["status"] = "failed"
            step["error"] = error_message

            execution_metadata = step.get(
                "execution_metadata"
            )

            if not isinstance(
                execution_metadata,
                dict,
            ):
                execution_metadata = {}

            execution_metadata.update(
                {
                    "success": False,
                    "error": error_message,
                    "action": self._safe_str(
                        step.get("action")
                    ),
                    "tool_name": self._safe_str(
                        step.get("tool_name")
                    ),
                }
            )

            step["execution_metadata"] = (
                execution_metadata
            )

        return step
