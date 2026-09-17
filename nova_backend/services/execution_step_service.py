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
        payload = step.get("payload")

        if not isinstance(payload, dict):
            payload = {}

        for value in (
            step.get("content"),
            step.get("file_content"),
            step.get("code"),
            step.get("generated_content"),
            step.get("expected_output"),
            payload.get("content"),
            payload.get("file_content"),
            payload.get("code"),
            payload.get("generated_content"),
            payload.get("expected_output"),
        ):
            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value

        return ""

    def _execute_project_python_file(
        self,
        step,
        execution_file,
    ):
        if self.python_runner is None:
            raise RuntimeError(
                "Python runner is not configured "
                "for explicit execution."
            )

        execution_path = Path(
            execution_file
        ).expanduser()

        if not execution_path.is_absolute():
            execution_path = (
                Path.cwd()
                / execution_path
            )

        python_result = (
            self.python_runner.run_file(
                execution_path
            )
        )

        if not isinstance(
            python_result,
            dict,
        ):
            raise RuntimeError(
                "Python runner returned an invalid "
                "execution result."
            )

        stdout = self._safe_str(
            python_result.get("stdout")
        )

        stderr = self._safe_str(
            python_result.get("stderr")
        )

        error = self._safe_str(
            python_result.get("error")
        )

        ok = bool(
            python_result.get("ok")
        )

        step["result"] = stdout
        step["execution_file"] = str(
            execution_path
        )
        step["execution_output"] = stdout
        step["execution_stderr"] = stderr
        step["execution_returncode"] = (
            python_result.get("returncode")
        )

        if not ok:
            step["status"] = "failed"
            step["error"] = (
                error
                or stderr
                or "Explicit Python execution failed."
            )
            return step

        step["status"] = "completed"
        step["error"] = None

        return step

    def _execute_tool_step(
        self,
        step,
    ):
        payload = step.get("payload")

        if not isinstance(payload, dict):
            payload = {}

        tool_name = self._safe_str(
            step.get("tool_name")
            or step.get("tool")
            or step.get("tool_action")
            or "terminal_execute"
        ).strip()

        confirm = bool(
            step.get("confirm", True)
        )

        target_file = self._safe_str(
            step.get("target_file")
            or step.get("path")
            or payload.get("path")
            or payload.get("cwd")
        ).strip()

        if target_file and not payload.get("path"):
            payload["path"] = target_file

        timeout = (
            payload.get("timeout")
            or step.get("timeout")
        )

        if timeout:
            payload.setdefault(
                "timeout",
                timeout,
            )

        command = self._safe_str(
            step.get("command")
            or payload.get("command")
            or step.get("shell_command")
            or step.get("cmd")
        ).strip()

        if command and not payload.get("command"):
            payload["command"] = command

        step["payload"] = payload
        step["confirm"] = True
        step["status"] = "running"
        step["error"] = None

        print(
            "DEBUG EXECUTOR TOOL CALL =",
            {
                "tool_name": tool_name,
                "command": command,
                "payload": payload,
                "confirm": confirm,
            },
            flush=True,
        )

        result = self.tool_executor.run(
            tool_name,
            payload,
            confirm=confirm,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Tool execution returned an invalid result."
            )

        ok = bool(result.get("ok"))

        stdout = self._safe_str(
            result.get("stdout")
        ).strip()

        stderr = self._safe_str(
            result.get("stderr")
        ).strip()

        output = self._safe_str(
            result.get("output")
            or result.get("message")
            or stdout
        ).strip()

        if not output and stdout:
            output = stdout

        step["result"] = output

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
                "executor": "unified_tool_executor",
                "tool_name": tool_name,
                "success": ok,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "raw_result": result,
            }
        )

        step["execution_metadata"] = (
            execution_metadata
        )

        if not ok:
            error_message = self._safe_str(
                result.get("error")
                or stderr
                or result.get("message")
                or "Tool execution failed."
            ).strip()

            step["status"] = "failed"
            step["error"] = error_message

            raise RuntimeError(
                error_message
            )

        step["status"] = "completed"
        step["completion_status"] = "completed"
        step["execution_status"] = "completed"
        step["error"] = None

        print(
            "DEBUG EXECUTOR TOOL SUCCESS =",
            {
                "tool_name": tool_name,
                "command": command,
                "result": output,
                "status": step["status"],
            },
            flush=True,
        )

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
            or ai_result.get("message")
            or ai_result.get("response")
        ).strip()

        if not result:
            raise RuntimeError(
                "AI execution returned an empty result."
            )

        step["result"] = result
        step["error"] = None

        # Preserve explicit waiting/clarification signals returned by
        # the AI execution service. These must not be converted into
        # completed steps by execute_step_logic().
        clarification_text = self._safe_str(
            ai_result.get("clarification")
            or ai_result.get("clarification_question")
            or ai_result.get("question")
            or ""
        ).strip()

        output_lower = result.lower()

        clarification_language = any(
            marker in output_lower
            for marker in (
                "could you please specify",
                "please specify",
                "please provide",
                "need to clarify",
                "to proceed accurately",
                "what specific",
                "which context",
                "relevant details or files",
            )
        )

        waiting = bool(
            ai_result.get("waiting")
            or ai_result.get("needs_clarification")
            or ai_result.get("requires_clarification")
            or ai_result.get("clarification_required")
            or ai_result.get("blocked")
            or clarification_text
            or clarification_language
        )

        if waiting:
            step["status"] = "waiting"

            step["waiting"] = True
            step["needs_clarification"] = bool(
                ai_result.get("needs_clarification")
                or ai_result.get("requires_clarification")
                or ai_result.get("clarification_required")
            )

            step["clarification"] = (
                clarification_text
                or result
            )

            step["execution_metadata"] = {
                "executor": "ai_execution_service",
                "success": True,
                "waiting": True,
                "needs_clarification": step[
                    "needs_clarification"
                ],
            }

            return step

        step["waiting"] = False
        step["needs_clarification"] = False

        step["execution_metadata"] = {
            "executor": "ai_execution_service",
            "success": True,
            "waiting": False,
        }

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

        command = self._safe_str(
            step.get("command")
            or payload.get("command")
            or step.get("shell_command")
            or step.get("cmd")
        ).strip()

        if command and not payload.get("command"):
            payload["command"] = command

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

    def _verify_project_execution_step(
        self,
        step,
    ):
        import importlib.util
        import re
        import tempfile

        target_file = self._safe_str(
            step.get("target_file")
        ).strip()

        if not target_file:
            description = self._safe_str(
                step.get("description")
                or step.get("text")
                or step.get("title")
            ).strip()

            path_match = re.search(
                r'([A-Za-z]:\\[^<>:"|?*\r\n]+\.py)',
                description,
                flags=re.IGNORECASE,
            )

            if path_match:
                target_file = path_match.group(1).strip()

        if not target_file:
            raise RuntimeError(
                "Verification failed: target_file is missing."
            )

        file_path = Path(target_file)

        if not file_path.exists():
            raise RuntimeError(
                f"Verification failed: file does not exist: {target_file}"
            )

        expected_output = self._safe_str(
            step.get("expected_output")
        ).strip()

        if not expected_output:
            raise RuntimeError(
                "Verification failed: expected output is missing."
            )

        source = file_path.read_text(
            encoding="utf-8"
        )

        if expected_output not in source:
            raise RuntimeError(
                "Verification failed: expected output marker "
                f"{expected_output!r} was not found in {target_file}."
            )

        function_name = self._safe_str(
            step.get("function_name")
        ).strip()

        if not function_name:
            description = self._safe_str(
                step.get("description")
                or step.get("text")
                or step.get("title")
            ).strip()

            function_match = re.search(
                r"function\s+(?:named\s+)?([A-Za-z_][A-Za-z0-9_]*)",
                description,
                flags=re.IGNORECASE,
            )

            if function_match:
                candidate = function_match.group(1).strip()

                if candidate.lower() not in {
                    "that",
                    "which",
                    "to",
                    "return",
                    "returns",
                    "containing",
                    "called",
                    "named",
                }:
                    function_name = candidate

        if not function_name:
            function_name = file_path.stem

            if function_name.startswith("http_"):
                function_name = function_name[len("http_"):]

            function_name = re.sub(
                r"[^A-Za-z0-9_]+",
                "_",
                function_name,
            ).strip("_")

        module_name = (
            "nova_verification_"
            + re.sub(
                r"[^A-Za-z0-9_]+",
                "_",
                file_path.stem,
            )
        )

        spec = importlib.util.spec_from_file_location(
            module_name,
            str(file_path),
        )

        if spec is None or spec.loader is None:
            raise RuntimeError(
                f"Verification failed: unable to load {target_file}."
            )

        module = importlib.util.module_from_spec(
            spec
        )

        spec.loader.exec_module(module)

        function = getattr(
            module,
            function_name,
            None,
        )

        if not callable(function):
            raise RuntimeError(
                "Verification failed: function "
                f"{function_name!r} was not found in {target_file}."
            )

        actual_output = function()

        if expected_output and str(actual_output) != expected_output:
            raise RuntimeError(
                "Verification failed: function returned "
                f"{actual_output!r}; expected {expected_output!r}."
            )

        step["target_file"] = target_file
        step["function_name"] = function_name
        step["result"] = str(actual_output)
        step["expected_output"] = expected_output
        step["verification_result"] = {
            "success": True,
            "target_file": target_file,
            "function_name": function_name,
            "expected_output": expected_output,
            "actual_output": str(actual_output),
            "file_exists": True,
            "import_success": True,
        }
        step["execution_metadata"] = {
            "success": True,
            "verified": True,
            "target_file": target_file,
            "function_name": function_name,
            "expected_output": expected_output,
            "actual_output": str(actual_output),
        }
        step["status"] = "completed"

        print(
            "DEBUG EXECUTOR VERIFICATION SUCCESS =",
            step["verification_result"],
            flush=True,
        )

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

        print("DEBUG EXECUTOR RAW STEP BEFORE NORMALIZE =", step, flush=True)

        step = self._normalize_tool_step(
            step
        )

        print("DEBUG EXECUTOR STEP AFTER NORMALIZE =", step, flush=True)

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
                or step.get("type")
                or step.get("step_action")
            ).strip().lower()

            if not step_action:
                step_action = "design"

                print(
                    "DEBUG EXECUTOR: missing action, "
                    "using AI execution fallback",
                    flush=True,
                )

            step_action = self.ACTION_ALIASES.get(
                step_action,
                step_action,
            )

            step_action_aliases = {
                "run_step": "command",
                "execute": "command",
                "run": "command",
                "shell": "command",
                "run_command": "command",
                "terminal_execute": "command",
                "write": "implement",
                "build": "implement",
                "edit": "implement",
                "modify": "implement",
                "patch": "implement",
                "fix": "implement",
            }

            step_action = step_action_aliases.get(
                step_action,
                step_action,
            )

            step["action"] = step_action

            # -------------------------------------------------
            # HARD WAITING-STATE EXECUTION BARRIER
            # -------------------------------------------------
            # A step that is waiting for clarification, payload,
            # content, approval, or another external input must
            # never fall through into generation, tool execution,
            # placeholder creation, or file writing.
            # -------------------------------------------------
            if (
                step.get("status") == "waiting"
                or step.get("waiting") is True
                or step.get("needs_clarification") is True
                or step.get("status") == "waiting_for_payload"
                or step.get("status") == "waiting_approval"
            ):
                step["result"] = (
                    step.get("result")
                    or step.get("clarification")
                    or step.get("clarification_text")
                    or step.get("error")
                    or "Waiting for required input before execution."
                )
                step["execution_metadata"] = {
                    "success": False,
                    "waiting": True,
                    "needs_clarification": bool(
                        step.get("needs_clarification")
                    ),
                    "action": step_action,
                }
                return step
            # -------------------------------------------------
            # NATURAL-LANGUAGE FILE IMPLEMENTATION NORMALIZATION
            # -------------------------------------------------
            #
            # A planner may incorrectly classify a natural-language
            # file request as "command". Reclassify it before the
            # command dispatcher can send the English sentence to
            # PowerShell.
            #
            # Example:
            # Create C:\path\test.txt containing the text VALUE.
            #
            # This must happen before the IMPLEMENT_ACTIONS guard.
            # -------------------------------------------------
            import re

            natural_description = self._safe_str(
                step.get("description")
                or step.get("text")
                or step.get("title")
                or (
                    step.get("payload", {}).get("command")
                    if isinstance(step.get("payload"), dict)
                    else ""
                )
            ).strip()

            natural_target_file = self._safe_str(
                step.get("target_file")
            ).strip()

            if (
                not natural_target_file
                and natural_description
            ):
                natural_path_match = re.search(
                    r"([A-Za-z]:\\[^<>:\"|?*\r\n]+)",
                    natural_description,
                    flags=re.IGNORECASE,
                )

                if natural_path_match:
                    natural_target_file = (
                        natural_path_match.group(1).strip()
                    )

                    natural_target_file = re.sub(
                        r"\s+(?:containing|with|that|which|and|by)\b.*$",
                        "",
                        natural_target_file,
                        flags=re.IGNORECASE,
                    ).strip()

            natural_content = self._implementation_content(step)

            if (
                not natural_content
                and natural_description
            ):
                natural_content_match = re.search(
                    r"""
                    (?:
                        containing(?:\s+the)?\s+text
                        |containing\s+exactly
                        |containing
                        |exact\s+content
                        |with(?:\s+the)?\s+text
                        |with\s+content
                    )
                    \s*
                    ['"`]?
                    (.+?)
                    ['"`]?
                    \s*$
                    """,
                    natural_description,
                    flags=re.IGNORECASE | re.VERBOSE,
                )

                if natural_content_match:
                    natural_content = (
                        natural_content_match.group(1)
                        .strip()
                    )

                    # Remove a trailing verification clause from
                    # the requested file content.
                    natural_content = re.split(
                        r"\s*,\s*(?:then\s+)?verify\b"
                        r"|\s+(?:then\s+)?verify\b",
                        natural_content,
                        maxsplit=1,
                        flags=re.IGNORECASE,
                    )[0].strip()

                    natural_content = re.sub(
                        r"^\s*exactly\s+",
                        "",
                        natural_content,
                        flags=re.IGNORECASE,
                    ).strip()

                    if (
                        len(natural_content) >= 2
                        and natural_content[0] in "\"'`"
                        and natural_content[-1] == natural_content[0]
                    ):
                        natural_content = (
                            natural_content[1:-1]
                            .strip()
                        )

                    if (
                        natural_content.endswith(".")
                        and not natural_description.rstrip().endswith(
                            f'"{natural_content}"'
                        )
                        and not natural_description.rstrip().endswith(
                            f"'{natural_content}'"
                        )
                    ):
                        natural_content = (
                            natural_content[:-1]
                        ).strip()

            if (
                natural_target_file
                and natural_content
                and re.search(
                    r"\b(?:create|write|save|make|generate|add|put|place|containing|with)\b",
                    natural_description,
                    flags=re.IGNORECASE,
                )
            ):
                step_action = "implement"
                step["action"] = "implement"
                step["target_file"] = natural_target_file
                step["content"] = natural_content
                step["generated_content"] = natural_content
                step["expected_output"] = natural_content
                step["next_action"] = "write_file"
                step["mutation_ready"] = True
                step["payload_required"] = False

                target_file = natural_target_file
                content = natural_content

                print(
                    "DEBUG EXECUTOR NATURAL FILE REQUEST RECLASSIFIED =",
                    {
                        "action": step_action,
                        "target_file": target_file,
                        "content": content,
                    },
                    flush=True,
                )

            # -------------------------------------------------
            # IMPLEMENTATION NORMALIZATION
            # -------------------------------------------------
            # Natural-language file requests are classified above.
            # At this point, preserve the structured values already
            # extracted by that classification block.
            print(
                "DEBUG EXECUTOR NORMALIZED ACTION =",
                step_action,
                flush=True,
            )

            target_file = self._safe_str(
                step.get("target_file")
            ).strip()

            execution_file = self._safe_str(
                step.get("execution_file")
            ).strip()

            content = self._implementation_content(
                step
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

            print(
                "DEBUG EXECUTOR FULL IMPLEMENTATION STEP =",
                {
                    "title": step.get("title"),
                    "description": step.get("description"),
                    "text": step.get("text"),
                    "request": step.get("request"),
                    "target_file": step.get("target_file"),
                    "content": step.get("content"),
                    "file_content": step.get("file_content"),
                    "generated_content": step.get("generated_content"),
                    "expected_output": step.get("expected_output"),
                    "payload": step.get("payload"),
                    "next_action": step.get("next_action"),
                    "mutation_ready": step.get("mutation_ready"),
                    "payload_required": step.get("payload_required"),
                },
                flush=True,
            )

            # ---------------------------------
            # RESOLVE EXPLICIT FILE CONTENT
            # ---------------------------------
            payload = step.get("payload")

            if not isinstance(payload, dict):
                payload = {}

            content = self._safe_str(
                step.get("content")
                or step.get("file_content")
                or step.get("generated_content")
                or payload.get("content")
                or payload.get("file_content")
                or payload.get("generated_content")
                or ""
            ).strip()

            print(
                "DEBUG EXECUTOR CONTENT RESOLUTION =",
                {
                    "step_action": step_action,
                    "target_file": target_file,
                    "next_action": next_action,
                    "content": content,
                    "content_length": len(content),
                    "step_content": step.get("content"),
                    "step_file_content": step.get("file_content"),
                    "step_generated_content": step.get("generated_content"),
                    "payload_content": payload.get("content"),
                    "payload_file_content": payload.get("file_content"),
                    "payload_generated_content": payload.get(
                        "generated_content"
                    ),
                },
                flush=True,
            )

            # ---------------------------------
            # DIRECT EXPLICIT FILE IMPLEMENTATION
            # ---------------------------------
            # Explicit target_file + content must
            # always write the requested content directly.
            # This branch must execute before any
            # generated replacement or command logic.

            if (
                step_action in self.IMPLEMENT_ACTIONS
                and target_file
                and content.strip()
            ):
                print(
                    "DEBUG EXECUTOR DIRECT FILE IMPLEMENTATION =",
                    {
                        "target_file": target_file,
                        "content": content,
                        "content_length": len(content),
                    },
                    flush=True,
                )

                step = self._execute_file_implementation(
                    step=step,
                    target_file=target_file,
                    content=content,
                )

                step["status"] = "completed"
                step["action"] = "implement"
                step["next_action"] = None
                step["mutation_ready"] = False
                step["payload_required"] = False
                step["error"] = None

                print(
                    "DEBUG EXECUTOR DIRECT FILE IMPLEMENTATION COMPLETE =",
                    {
                        "target_file": target_file,
                        "content_length": len(content),
                    },
                    flush=True,
                )

                return step

            elif (
                step_action in self.IMPLEMENT_ACTIONS
                and target_file
                and not content.strip()
            ):
                step["status"] = "waiting"
                step["waiting"] = True
                step["needs_clarification"] = True
                step["next_action"] = "request_content"
                step["payload_required"] = True
                step["mutation_ready"] = False
                step["result"] = (
                    step.get("result")
                    or (
                        "Waiting for required file content before writing "
                        f"{target_file}."
                    )
                )
                step["execution_metadata"] = {
                    "success": False,
                    "waiting": True,
                    "needs_clarification": True,
                    "action": step_action,
                    "target_file": target_file,
                }

                print(
                    "DEBUG EXECUTOR WAITING FOR FILE CONTENT =",
                    {
                        "action": step_action,
                        "target_file": target_file,
                        "next_action": step["next_action"],
                    },
                    flush=True,
                )

                return step

            # ---------------------------------
            # REAL NOVA TOOL EXECUTION
            # ---------------------------------
            # Explicit Python execution takes
            # priority over every other branch.

            if step_action in {
                "verify",
                "verification",
                "verify_result",
                "verify-result",
            }:

                print(
                    "DEBUG EXECUTOR DIRECT VERIFICATION =",
                    {
                        "target_file": target_file,
                        "expected_output": expected_output,
                    },
                    flush=True,
                )

                self._verify_project_execution_step(
                    step=step,
                )

            elif execution_file:
                print(
                    "DEBUG EXECUTOR EXPLICIT PYTHON FILE =",
                    execution_file,
                    flush=True,
                )

                self._execute_project_python_file(
                    step=step,
                    execution_file=execution_file,
                )

            # ---------------------------------
            # REAL NOVA TOOL EXECUTION
            # ---------------------------------
            # Explicit Python execution takes
            # priority over every other branch.

            if step_action in {
                "verify",
                "verification",
                "verify_result",
                "verify-result",
            }:
                print(
                    "DEBUG EXECUTOR DIRECT VERIFICATION =",
                    {
                        "target_file": target_file,
                        "expected_output": expected_output,
                    },
                    flush=True,
                )

                self._verify_project_execution_step(
                    step=step,
                )

            elif execution_file:
                print(
                    "DEBUG EXECUTOR EXPLICIT PYTHON FILE =",
                    execution_file,
                    flush=True,
                )

                self._execute_project_python_file(
                    step=step,
                    execution_file=execution_file,
                )


                print(
                    "DEBUG EXECUTOR DIRECT FILE IMPLEMENTATION =",
                    {
                        "target_file": target_file,
                        "content": content,
                    },
                    flush=True,
                )

                self._execute_file_implementation(
                    step=step,
                    target_file=target_file,
                    content=content,
                )

            elif step_action in {
                "command",
                "shell",
                "run_command",
                "execute",
                "run",
                "run_file",
                "run_script",
            }:

                step["tool_name"] = (
                    self._safe_str(
                        step.get("tool_name")
                        or step.get("tool")
                        or step.get("tool_action")
                    ).strip()
                    or "terminal_execute"
                )

                payload = step.get("payload")

                if not isinstance(
                    payload,
                    dict,
                ):
                    payload = {}

                step_text = self._safe_str(
                    step.get("text")
                    or step.get("description")
                    or step.get("title")
                ).strip()

                command = self._safe_str(
                    step.get("command")
                    or step.get("cmd")
                    or payload.get("command")
                    or payload.get("cmd")
                ).strip()

                if not command:
                    description = self._safe_str(
                        step.get("description")
                        or step.get("text")
                        or step.get("title")
                    ).strip()

                    target_file = self._safe_str(
                        step.get("target_file")
                    ).strip()

                    if not target_file:
                        target_files = step.get(
                            "target_files"
                        ) or []

                        if isinstance(
                            target_files,
                            str,
                        ):
                            target_files = [
                                target_files
                            ]

                        if target_files:
                            target_file = self._safe_str(
                                target_files[0]
                            ).strip()

                    import re

                    if not target_file and description:
                        path_match = re.search(
                            r"([A-Za-z]:\\[^<>:\"|?*\r\n]+)",
                            description,
                            flags=re.IGNORECASE,
                        )

                        if path_match:
                            target_file = (
                                path_match.group(1).strip()
                            )

                            target_file = re.sub(
                                r"\s+by\s+creating\s+it.*$",
                                "",
                                target_file,
                                flags=re.IGNORECASE,
                            ).strip()

                    content_match = re.search(
                        r"exact\s+content\s+['\"]?(.+?)['\"]?\s*$",
                        description,
                        flags=re.IGNORECASE,
                    )

                    if (
                        target_file
                        and content_match
                        and re.search(
                            r"\b(?:create|write|save|fix|update)\b",
                            description,
                            flags=re.IGNORECASE,
                        )
                    ):
                        content = content_match.group(1).strip()

                        content = content.rstrip(
                            "\"'"
                        ).strip()

                        escaped_file = target_file.replace(
                            "'",
                            "''",
                        )

                        escaped_content = content.replace(
                            "'",
                            "''",
                        )

                        command = (
                            "Set-Content "
                            f"-LiteralPath '{escaped_file}' "
                            f"-Value '{escaped_content}' "
                            "-NoNewline"
                        )

                        step["target_file"] = target_file
                        step["generated_content"] = content

                    elif target_file:
                        marker_match = re.search(
                            r"returns?\s+([A-Za-z_][A-Za-z0-9_]*)",
                            description,
                            flags=re.IGNORECASE,
                        )

                        return_value = (
                            marker_match.group(1)
                            if marker_match
                            else "HTTP_EXECUTION_OK"
                        )

                        function_match = re.search(
                            r"function\s+(?:named\s+)?([A-Za-z_][A-Za-z0-9_]*)",
                            description,
                            flags=re.IGNORECASE,
                        )

                        candidate_function_name = (
                            function_match.group(1).strip()
                            if function_match
                            else ""
                        )

                        invalid_function_names = {
                            "that",
                            "which",
                            "to",
                            "return",
                            "returns",
                            "containing",
                            "called",
                            "named",
                        }

                        if (
                            candidate_function_name
                            and candidate_function_name.lower()
                            not in invalid_function_names
                        ):
                            function_name = candidate_function_name
                        else:
                            function_name = Path(
                                target_file
                            ).stem

                            if function_name.startswith("http_"):
                                function_name = function_name[
                                    len("http_"):
                                ]

                            function_name = re.sub(
                                r"[^A-Za-z0-9_]+",
                                "_",
                                function_name,
                            ).strip("_")

                            if not function_name:
                                function_name = (
                                    "execution_acceptance"
                                )

                            if function_name[0].isdigit():
                                function_name = (
                                    f"generated_{function_name}"
                                )

                        escaped_file = target_file.replace(
                            "'",
                            "''",
                        )

                        python_content = (
                            f"def {function_name}():\n"
                            f"    return "
                            f"{return_value!r}\n"
                        )

                        encoded_content = (
                            python_content.encode("utf-8")
                        )

                        import base64

                        content_b64 = base64.b64encode(
                            encoded_content
                        ).decode("ascii")

                        command = (
                            "$content = "
                            f"[Convert]::FromBase64String("
                            f"'{content_b64}'"
                            "); "
                            f"[IO.File]::WriteAllBytes("
                            f"'{escaped_file}', "
                            "$content)"
                        )

                        step["target_file"] = target_file
                        step["generated_content"] = (
                            python_content
                        )

                if command and not payload.get("command"):
                    payload["command"] = command

                step["payload"] = payload

                # Explicit project command steps are
                # authorized for execution.
                step["confirm"] = True

                print(
                    "DEBUG EXECUTOR COMMAND TOOL =",
                    {
                        "tool_name": step["tool_name"],
                        "command": payload.get("command"),
                        "confirm": step["confirm"],
                    },
                    flush=True,
                )

                self._execute_tool_step(
                    step=step,
                )

            # ---------------------------------
            # REAL NOVA TOOL EXECUTION
            # ---------------------------------

            elif (
                step.get("tool_name")
                or step.get("tool")
                or step.get("tool_action")
            ):
                self._execute_tool_step(
                    step=step,
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

            result_status = self._safe_str(
                step.get("status")
            ).strip().lower()

            if result_status in {
                "failed",
                "error",
            }:
                raise RuntimeError(
                    self._safe_str(
                        step.get("error")
                        or "Execution step failed."
                    )
                )

            if result_status in {
                "waiting",
                "waiting_approval",
            }:
                return step

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















