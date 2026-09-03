from __future__ import annotations

from typing import Any, Dict

from nova_backend.services.execution_handler import (
    NextMove,
)


class ProjectExecutionHandler:
    """
    Bridge between ChatExecutionService and Nova's existing
    function-based execution system.

    Project tasks are translated into NextMove objects and sent to
    the existing default_executor when execution is possible.
    """

    def __init__(
        self,
        default_executor=None,
    ):
        self.default_executor = default_executor

    def _make_move(
        self,
        current_step: Dict[str, Any],
    ) -> NextMove | None:
        step_action = str(
            current_step.get("action") or "analysis"
        ).strip().lower()

        step_id = str(
            current_step.get("id") or ""
        ).strip()

        if step_action in {
            "analysis",
            "analyze",
            "research",
            "review",
            "verify",
            "verification",
            "validate",
            "validation",
            "plan",
            "planning",
        }:
            return NextMove(
                id=step_id or "project-analysis",
                type="log",
                payload={
                    "message": str(
                        current_step.get("description")
                        or current_step.get("title")
                        or "Project analysis completed."
                    )
                },
            )

        if step_action == "create":
            return NextMove(
                id=step_id or "project-create",
                type="log",
                payload={
                    "message": str(
                        current_step.get("description")
                        or current_step.get("title")
                        or "Project creation step completed."
                    )
                },
            )

        if step_action in {
            "build",
            "implement",
            "edit",
            "write",
            "modify",
        }:
            target_files = (
                current_step.get("target_files")
                or []
            )

            if isinstance(target_files, str):
                target_files = [
                    target_files
                ]

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            if not target_files and target_file:
                target_files = [
                    target_file
                ]

            code = str(
                current_step.get("content")
                or current_step.get("code")
                or ""
            )

            if not target_files or not code.strip():
                return NextMove(
                    id=step_id or "project-build",
                    type="log",
                    payload={
                        "message": str(
                            current_step.get("description")
                            or current_step.get("title")
                            or "Project build step completed."
                        )
                    },
                )

            return NextMove(
                id=step_id or "project-fix-file",
                type="fix_file",
                payload={
                    "file_paths": target_files,
                    "file_path": (
                        target_files[0]
                        if target_files
                        else ""
                    ),
                    "code": code,
                },
            )

        if step_action == "patch":
            target_files = (
                current_step.get("target_files")
                or []
            )

            if isinstance(target_files, str):
                target_files = [
                    target_files
                ]

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            if not target_files and target_file:
                target_files = [
                    target_file
                ]

            function_name = str(
                current_step.get("target_function") or ""
            ).strip()

            replacement = str(
                current_step.get("replacement")
                or current_step.get("content")
                or current_step.get("code")
                or ""
            )

            if (
                target_files
                and function_name
                and replacement.strip()
            ):
                return NextMove(
                    id=step_id or "project-function-fix",
                    type="apply_function_fix",
                    payload={
                        "file_paths": target_files,
                        "file_path": (
                            target_files[0]
                            if target_files
                            else ""
                        ),
                        "function_name": function_name,
                        "replacement": replacement,
                    },
                )

            if target_files and replacement.strip():
                return NextMove(
                    id=step_id or "project-fix-file",
                    type="fix_file",
                    payload={
                        "file_paths": target_files,
                        "file_path": (
                            target_files[0]
                            if target_files
                            else ""
                        ),
                        "code": replacement,
                    },
                )

            return None

        if step_action in {
            "command",
            "shell",
            "run_command",
        }:
            command = str(
                current_step.get("command") or ""
            ).strip()

            if not command:
                return None

            return NextMove(
                id=step_id or "project-command",
                type="run_step",
                payload={
                    "command": command,
                    "step": current_step,
                },
            )

        return None

    def _advance_after_success(
        self,
        state: Dict[str, Any],
        steps,
        current_index: int,
        current_step: Dict[str, Any],
    ) -> Dict[str, Any]:
        current_step["status"] = "completed"

        steps[current_index] = current_step

        history = list(
            state.get("history") or []
        )

        history.append(
            {
                "step_id": current_step.get("id"),
                "task_id": current_step.get(
                    "task_id"
                ),
                "status": "completed",
                "action": current_step.get(
                    "action"
                ),
                "result": current_step.get(
                    "result"
                ),
            }
        )

        state["history"] = history

        next_index = current_index + 1

        state["steps"] = steps
        state["current_index"] = next_index

        if next_index >= len(steps):
            state["status"] = "complete"
            state["complete"] = True
            state["waiting"] = False
            state["current_step"] = None

        else:
            next_step = steps[next_index]

            if isinstance(next_step, dict):
                next_step["status"] = "active"
                steps[next_index] = next_step

            state["steps"] = steps
            state["status"] = "running"
            state["complete"] = False
            state["waiting"] = False
            state["current_step"] = next_step

        return state

    def run_next_step(
        self,
        action: str,
        session_id: str,
        execution_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = (
            dict(execution_state)
            if isinstance(execution_state, dict)
            else {}
        )

        steps = state.get("steps") or []

        current_index = int(
            state.get("current_index") or 0
        )

        if current_index >= len(steps):
            state["status"] = "complete"
            state["complete"] = True
            state["waiting"] = False
            state["current_step"] = None

            return {
                "ok": True,
                "execution_state": state,
            }

        current_step = steps[current_index]

        if not isinstance(current_step, dict):
            state["status"] = "failed"
            state["complete"] = False
            state["waiting"] = False
            state["error"] = (
                "Current execution step is invalid."
            )

            return {
                "ok": False,
                "error": state["error"],
                "execution_state": state,
            }

        current_step = dict(current_step)

        current_step["status"] = "active"

        step_action = str(
            current_step.get("action") or "analysis"
        ).strip().lower()

        title = str(
            current_step.get("title")
            or "Project task"
        ).strip()

        description = str(
            current_step.get("description") or ""
        ).strip()

        context = dict(
            state.get("context") or {}
        )

        context["project_execution"] = True
        context["execution_action"] = action
        context["current_task"] = {
            "id": current_step.get("id"),
            "task_id": current_step.get(
                "task_id"
            ),
            "title": title,
            "description": description,
            "action": step_action,
            "target_file": current_step.get(
                "target_file"
            ),
            "target_files": current_step.get(
                "target_files"
            ),
            "target_function": current_step.get(
                "target_function"
            ),
            "command": current_step.get(
                "command"
            ),
        }

        state["context"] = context
        state["current_step"] = current_step
        state["steps"] = steps

        print(
            "PROJECT EXECUTION HANDLER STEP",
            {
                "session_id": session_id,
                "action": action,
                "step_action": step_action,
                "step_id": current_step.get("id"),
                "title": title,
            },
            flush=True,
        )

        # ---------------------------------------------------------
        # ANALYSIS / REVIEW / PLANNING
        # ---------------------------------------------------------

        if step_action in {
            "analysis",
            "analyze",
            "research",
            "review",
            "verify",
            "verification",
            "validate",
            "validation",
            "plan",
            "planning",
        }:
            current_step["result"] = (
                f"{title} completed."
            )

            state = self._advance_after_success(
                state=state,
                steps=steps,
                current_index=current_index,
                current_step=current_step,
            )

            return {
                "ok": True,
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # BUILD EXECUTION MOVE
        # ---------------------------------------------------------

        move = self._make_move(
            current_step
        )

        # ---------------------------------------------------------
        # LOCAL LOG MOVE
        # ---------------------------------------------------------

        if move is not None and move.type == "log":
            current_step["result"] = str(
                move.payload.get("message")
                or f"{title} completed."
            )

            state = self._advance_after_success(
                state=state,
                steps=steps,
                current_index=current_index,
                current_step=current_step,
            )

            return {
                "ok": True,
                "execution_state": state,
                "result": current_step["result"],
            }

        # ---------------------------------------------------------
        # MISSING IMPLEMENT TARGET
        # ---------------------------------------------------------

        if move is None and step_action in {
            "build",
            "implement",
            "implementation",
            "create",
            "edit",
            "write",
            "modify",
            "patch",
            "fix",
        }:

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            target_files = (
                current_step.get("target_files")
                or []
            )

            if (
                not target_file
                and not target_files
            ):
                current_step["status"] = (
                    "waiting_for_target"
                )

                current_step["next_action"] = (
                    "request_target"
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "waiting"
                state["waiting"] = True
                state["complete"] = False
                state["current_step"] = current_step

                return {
                    "ok": True,
                    "execution_state": state,
                }

            content = str(
                current_step.get("content")
                or current_step.get("code")
                or current_step.get("replacement")
                or ""
            )

            if not content.strip():
                current_step["status"] = "waiting"

                current_step["next_action"] = (
                    "generate_file_replacement"
                )

                current_step["mutation_ready"] = True

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "waiting"
                state["waiting"] = True
                state["complete"] = False
                state["current_step"] = current_step

                return {
                    "ok": True,
                    "execution_state": state,
                }

            if not callable(self.default_executor):
                current_step["status"] = "failed"

                current_step["error"] = (
                    "Project execution has no default executor."
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

            from nova_backend.services.execution_handler import (
                make_move,
            )

            move = make_move(
                "fix_file",
                {
                    "file_path": target_file,
                    "code": content,
                },
            )

            execution_result = self.default_executor(
                move
            )

            if execution_result.status != "success":
                current_step["status"] = "failed"

                current_step["error"] = (
                    execution_result.error
                    or "Project file mutation failed."
                )

                current_step["result"] = (
                    execution_result.output
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

            current_step["status"] = "completed"

            current_step["result"] = (
                execution_result.output
            )

            current_step["next_action"] = None

            steps[current_index] = current_step

            state["steps"] = steps

            state["history"] = list(
                state.get("history") or []
            )

            state["history"].append(
                {
                    "step_id": current_step.get("id"),
                    "task_id": current_step.get(
                        "task_id"
                    ),
                    "status": "completed",
                    "action": step_action,
                    "result": execution_result.output,
                }
            )

            next_index = current_index + 1

            state["current_index"] = next_index

            if next_index >= len(steps):
                state["status"] = "complete"
                state["complete"] = True
                state["waiting"] = False
                state["current_step"] = None

            else:
                next_step = steps[next_index]

                if isinstance(next_step, dict):
                    next_step["status"] = "active"

                    # Preserve the next task's own target.
                    # Only inherit the previous target when the
                    # next task does not already have one.
                    if (
                        not next_step.get("target_file")
                        and current_step.get("target_file")
                    ):
                        next_step["target_file"] = (
                            current_step["target_file"]
                        )

                    if (
                        not next_step.get("target_files")
                        and current_step.get("target_files")
                    ):
                        next_step["target_files"] = list(
                            current_step["target_files"]
                        )

                    if (
                        not next_step.get("target_function")
                        and current_step.get("target_function")
                    ):
                        next_step["target_function"] = (
                            current_step["target_function"]
                        )

                    steps[next_index] = next_step

                state["steps"] = steps
                state["status"] = "running"
                state["complete"] = False
                state["waiting"] = False
                state["current_step"] = next_step

            return {
                "ok": True,
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # NO EXECUTOR
        # ---------------------------------------------------------

        if self.default_executor is None:
            current_step["status"] = "waiting"

            current_step["result"] = (
                "Project execution is waiting because "
                "the default executor is unavailable."
            )

            steps[current_index] = current_step

            state["steps"] = steps
            state["status"] = "waiting"
            state["waiting"] = True
            state["complete"] = False
            state["current_step"] = current_step

            return {
                "ok": True,
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # EXECUTE REAL MOVE
        # ---------------------------------------------------------

        if move is not None:
            print(
                "PROJECT EXECUTION HANDLER CALLING EXECUTOR",
                {
                    "move_type": move.type,
                    "move_id": move.id,
                    "payload": move.payload,
                },
                flush=True,
            )

            try:
                execution_result = (
                    self.default_executor(move)
                )

            except Exception as exc:
                current_step["status"] = "failed"
                current_step["error"] = str(exc)

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["complete"] = False
                state["waiting"] = False
                state["error"] = str(exc)
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": str(exc),
                    "execution_state": state,
                }

            result_status = str(
                getattr(
                    execution_result,
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            result_output = getattr(
                execution_result,
                "output",
                None,
            )

            result_error = str(
                getattr(
                    execution_result,
                    "error",
                    "",
                )
                or ""
            ).strip()

            print(
                "PROJECT EXECUTION HANDLER RESULT",
                {
                    "move_type": move.type,
                    "status": result_status,
                    "error": result_error,
                },
                flush=True,
            )

            if result_status in {
                "success",
                "completed",
                "complete",
            }:
                current_step["result"] = result_output

                current_step.pop(
                    "error",
                    None,
                )

                state = self._advance_after_success(
                    state=state,
                    steps=steps,
                    current_index=current_index,
                    current_step=current_step,
                )

                return {
                    "ok": True,
                    "execution_state": state,
                    "result": result_output,
                }

            current_step["status"] = "failed"

            current_step["error"] = (
                result_error
                or "Project execution failed."
            )

            current_step["result"] = result_output

            steps[current_index] = current_step

            state["steps"] = steps
            state["status"] = "failed"
            state["complete"] = False
            state["waiting"] = False
            state["error"] = current_step["error"]
            state["current_step"] = current_step

            return {
                "ok": False,
                "error": current_step["error"],
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # NO EXECUTOR
        # ---------------------------------------------------------

        if self.default_executor is None:
            current_step["status"] = "waiting"

            current_step["result"] = (
                "Project execution is waiting because "
                "the default executor is unavailable."
            )

            steps[current_index] = current_step

            state["steps"] = steps
            state["status"] = "waiting"
            state["waiting"] = True
            state["complete"] = False
            state["current_step"] = current_step

            return {
                "ok": True,
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # EXECUTE REAL MOVE
        # ---------------------------------------------------------

        if move is not None:
            print(
                "PROJECT EXECUTION HANDLER CALLING EXECUTOR",
                {
                    "move_type": move.type,
                    "move_id": move.id,
                    "payload": move.payload,
                },
                flush=True,
            )

            try:
                execution_result = (
                    self.default_executor(move)
                )

            except Exception as exc:
                current_step["status"] = "failed"
                current_step["error"] = str(exc)

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["complete"] = False
                state["waiting"] = False
                state["error"] = str(exc)
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": str(exc),
                    "execution_state": state,
                }

            result_status = str(
                getattr(
                    execution_result,
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            result_output = getattr(
                execution_result,
                "output",
                None,
            )

            result_error = str(
                getattr(
                    execution_result,
                    "error",
                    "",
                )
                or ""
            ).strip()

            print(
                "PROJECT EXECUTION HANDLER RESULT",
                {
                    "move_type": move.type,
                    "status": result_status,
                    "error": result_error,
                },
                flush=True,
            )

            if result_status in {
                "success",
                "completed",
                "complete",
            }:
                current_step["result"] = result_output

                current_step.pop(
                    "error",
                    None,
                )

                state = self._advance_after_success(
                    state=state,
                    steps=steps,
                    current_index=current_index,
                    current_step=current_step,
                )

                return {
                    "ok": True,
                    "execution_state": state,
                    "result": result_output,
                }

            current_step["status"] = "failed"

            current_step["error"] = (
                result_error
                or "Project execution failed."
            )

            current_step["result"] = result_output

            steps[current_index] = current_step

            state["steps"] = steps
            state["status"] = "failed"
            state["complete"] = False
            state["waiting"] = False
            state["error"] = current_step["error"]
            state["current_step"] = current_step

            return {
                "ok": False,
                "error": current_step["error"],
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # UNSUPPORTED ACTION
        # ---------------------------------------------------------

        current_step["status"] = "failed"

        current_step["error"] = (
            f"Unsupported project execution action: "
            f"{step_action}"
        )

        steps[current_index] = current_step

        state["steps"] = steps
        state["status"] = "failed"
        state["waiting"] = False
        state["complete"] = False
        state["error"] = current_step["error"]

        return {
            "ok": False,
            "error": current_step["error"],
            "execution_state": state,
        }