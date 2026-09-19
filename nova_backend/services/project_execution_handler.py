from __future__ import annotations

from pathlib import Path

from typing import Any, Dict

from nova_backend.services.execution_handler import (
    NextMove,
)

print(
    "[PROJECT EXECUTION HANDLER LOADED]",
    __file__,
    flush=True,
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
        execution_step_service=None,
    ):
        self.default_executor = default_executor
        self.execution_step_service = execution_step_service

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
            "design",
            "architecture",
            "architect",
            "document",
            "documentation",
            "specify",
            "specification",
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

        if step_action in {
            "execute",
            "run",
            "run_file",
            "run_script",
        }:
            execution_file = str(
                current_step.get("execution_file")
                or ""
            ).strip()

            command = str(
                current_step.get("command")
                or ""
            ).strip()

            description = str(
                current_step.get("description")
                or current_step.get("text")
                or current_step.get("title")
                or ""
            ).strip()

            target_file = str(
                current_step.get("target_file")
                or ""
            ).strip()

            if not target_file:
                target_files = (
                    current_step.get("target_files")
                    or []
                )

                if isinstance(target_files, str):
                    target_files = [
                        target_files
                    ]

                if target_files:
                    target_file = str(
                        target_files[0]
                    ).strip()

            if (
                not execution_file
                and not command
                and target_file
            ):
                execution_file = target_file

            if (
                not execution_file
                and not command
                and description
            ):
                import re

                path_match = re.search(
                    r"([A-Za-z]:\\[^<>:\"|?*\r\n]+\.py)",
                    description,
                    flags=re.IGNORECASE,
                )

                if path_match:
                    execution_file = path_match.group(1).strip()

            if (
                not execution_file
                and not command
            ):
                return None

            payload = dict(current_step)

            if execution_file:
                payload["execution_file"] = execution_file

            if command:
                payload["command"] = command

            return NextMove(
                id=step_id or "project-execution",
                type="execute",
                payload=payload,
            )


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
                current_step["next_action"] = (
                    "execute_general_task"
                )

                current_step["mutation_ready"] = True

                if self.execution_step_service is None:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "ExecutionStepService is unavailable for "
                        "general task execution."
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

                try:
                    execution_meta = (
                        state.get("meta")
                        or state.get("execution_metadata")
                        or {}
                    )

                    if not isinstance(execution_meta, dict):
                        execution_meta = {}

                    current_task = (
                        state.get("context", {}).get("current_task", {})
                    )

                    if not isinstance(current_task, dict):
                        current_task = {}

                    if not current_step.get("target_file"):
                        current_step["target_file"] = (
                            execution_meta.get("target_file")
                            or current_task.get("target_file")
                            or execution_meta.get("file_path")
                            or ""
                        )

                    if not current_step.get("content"):
                        current_step["content"] = (
                            execution_meta.get("content")
                            or current_task.get("content")
                            or current_task.get("file_content")
                            or current_task.get("code")
                            or execution_meta.get("file_content")
                            or execution_meta.get("code")
                            or ""
                        )

                    if not current_step.get("mutation_mode"):
                        current_step["mutation_mode"] = (
                            execution_meta.get("mutation_mode")
                            or current_task.get("mutation_mode")
                            or ""
                        )

                    if execution_meta.get("mutation_request"):
                        current_step["mutation_request"] = True

                    if current_task.get("mutation_request"):
                        current_step["mutation_request"] = True

                    if current_step.get("content"):
                        current_step["file_content"] = current_step["content"]

                    if current_step.get("target_file"):
                        current_step["target_files"] = [
                            current_step["target_file"]
                        ]

                    generated_step = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=current_step,
                        )
                    )

                    if isinstance(generated_step, dict):
                        updated_step = dict(current_step)
                        updated_step.update(generated_step)
                        current_step = updated_step

                    steps[current_index] = current_step
                    state["steps"] = steps
                    state["current_step"] = current_step

                    step_status = str(
                        current_step.get("status") or ""
                    ).strip().lower()

                    completion_status = str(
                        current_step.get("completion_status")
                        or current_step.get("execution_status")
                        or ""
                    ).strip().lower()

                    is_waiting = bool(
                        current_step.get("waiting")
                        or current_step.get("needs_input")
                        or current_step.get("payload_required")
                        or current_step.get("clarification")
                        or step_status in {
                            "waiting",
                            "waiting_approval",
                            "needs_input",
                            "blocked",
                        }
                        or completion_status in {
                            "waiting",
                            "waiting_approval",
                            "needs_input",
                            "incomplete",
                        }
                    )

                    if step_status in {
                        "failed",
                        "error",
                    }:
                        state["status"] = "failed"
                        state["complete"] = False
                        state["waiting"] = False
                        state["error"] = str(
                            current_step.get("error")
                            or "Project execution step failed."
                        )

                        return {
                            "ok": False,
                            "error": state["error"],
                            "execution_state": state,
                        }

                    if is_waiting:
                        current_step["status"] = "waiting"
                        state["steps"] = steps
                        state["current_step"] = current_step
                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                            "result": current_step.get("result")
                            or current_step.get("clarification")
                            or "",
                        }

                    current_step["status"] = "completed"

                    state = self._advance_after_success(
                        state=state,
                        steps=steps,
                        current_index=current_index,
                        current_step=current_step,
                    )

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": current_step.get("result"),
                    }

                except Exception as exc:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        f"Project general task execution failed: {exc}"
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

            content = str(
                current_step.get("content")
                or current_step.get("code")
                or current_step.get("replacement")
                or ""
            )

            if not content.strip():
                if self.execution_step_service is None:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "ExecutionStepService is unavailable for "
                        "file replacement generation."
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

                current_step["next_action"] = (
                    "generate_file_replacement"
                )

                current_step["mutation_ready"] = True

                try:
                    generated_step = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=current_step,
                        )
                    )

                    if isinstance(generated_step, dict):
                        updated_step = dict(current_step)
                        updated_step.update(generated_step)
                        current_step = updated_step

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = False

                    step_status = str(
                        current_step.get("status") or ""
                    ).strip().lower()

                    if step_status in {
                        "failed",
                        "error",
                    }:
                        state["status"] = "failed"
                        state["complete"] = False
                        state["error"] = (
                            current_step.get("error")
                            or "Project execution step failed."
                        )

                        return {
                            "ok": False,
                            "error": state["error"],
                            "execution_state": state,
                        }

                    if step_status in {
                        "waiting",
                        "waiting_approval",
                    }:
                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                        }

                    step_status = str(
                        current_step.get("status") or ""
                    ).strip().lower()

                    if step_status in {
                        "failed",
                        "error",
                    }:
                        state["status"] = "failed"
                        state["waiting"] = False
                        state["complete"] = False
                        state["error"] = (
                            current_step.get("error")
                            or "Project file generation failed."
                        )

                        return {
                            "ok": False,
                            "error": state["error"],
                            "execution_state": state,
                        }

                    # File replacement generation only prepares the mutation.
                    # It must not complete or advance the project step until
                    # the actual write_file operation succeeds.


                    if step_status in {
                        "waiting",
                        "waiting_approval",
                    }:
                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                        }

                    current_step["status"] = "completed"
                    current_step["completion_status"] = "completed"
                    current_step["next_action"] = None
                    current_step["mutation_ready"] = False
                    current_step["payload_required"] = False
                    current_step["mutation_mode"] = None
                    current_step["error"] = None

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["current_step"] = current_step

                    state = self._advance_after_success(
                        state=state,
                        steps=steps,
                        current_index=current_index,
                        current_step=current_step,
                    )

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": current_step.get("result"),
                    }

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": current_step.get("result"),
                    }

                except Exception as exc:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        f"Project file generation failed: {exc}"
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

                content = str(
                    current_step.get("content")
                    or current_step.get("code")
                    or current_step.get("replacement")
                    or ""
                )

                if not content.strip():
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "File generation completed without usable content."
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

        # ---------------------------------------------------------
        # EXECUTE TASK
        # ---------------------------------------------------------

        if move is None and step_action in {
            "execute",
            "run",
            "run_file",
            "run_script",
        }:
            execution_file = str(
                current_step.get("execution_file")
                or ""
            ).strip()

            command = str(
                current_step.get("command")
                or ""
            ).strip()

            # An execution task must contain a concrete executable file
            # or command. Never silently downgrade it to analysis,
            # because that would allow an execution task to complete
            # without performing real execution.
            if not execution_file and not command:
                current_step["status"] = "failed"
                current_step["error"] = (
                    "Execution task is missing execution_file or command."
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
            else:

                execute_payload = dict(current_step)

                if execution_file:
                    execute_payload["execution_file"] = (
                        execution_file
                    )

                if command:
                    execute_payload["command"] = command

                move = self._make_move(
                    execute_payload
                )

                if move is None:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "Execute task could not be converted "
                        "into an execution move."
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

                # -----------------------------------------------------
                # NO EXECUTOR
                # -----------------------------------------------------

                if not callable(self.default_executor):
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
                        "waiting": True,
                        "execution_state": state,
                    }
            if not callable(self.default_executor):
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
                "PROJECT MOVE DISPATCH DIAGNOSTIC",
                {
                    "move_type": getattr(
                        move,
                        "type",
                        None,
                    ),
                    "move_id": getattr(
                        move,
                        "id",
                        None,
                    ),
                    "payload_type": type(
                        getattr(
                            move,
                            "payload",
                            None,
                        )
                    ).__name__,
                    "payload": getattr(
                        move,
                        "payload",
                        None,
                    ),
                    "payload_step_action": (
                        getattr(
                            move,
                            "payload",
                            {},
                        ).get(
                            "step",
                            {},
                        ).get(
                            "action",
                        )
                        if isinstance(
                            getattr(
                                move,
                                "payload",
                                None,
                            ),
                            dict,
                        )
                        and isinstance(
                            getattr(
                                move,
                                "payload",
                                {},
                            ).get(
                                "step",
                            ),
                            dict,
                        )
                        else None
                    ),
                },
                flush=True,
            )

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

                if (
                    move.type == "run_step"
                    and isinstance(
                        move.payload,
                        dict,
                    )
                    and isinstance(
                        move.payload.get("step"),
                        dict,
                    )
                    and str(
                        move.payload["step"].get(
                            "action",
                            "",
                        )
                    ).strip().lower()

                    in {
                        "command",
                        "shell",
                        "run_command",
                        "execute",
                        "run",
                        "run_file",
                        "run_script",
                    }
                ):

                    if self.execution_step_service is None:
                        raise RuntimeError(
                            "ExecutionStepService is unavailable "
                            "for command execution."
                        )

                    command_step = move.payload["step"]

                    execution_result = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=command_step,
                        )
                    )

                    print(
                        "[PROJECT EXECUTION SERVICE RESULT]",
                        {
                            "type": type(
                                execution_result
                            ).__name__,
                            "result": execution_result,
                            "status": (
                                execution_result.get("status")
                                if isinstance(
                                    execution_result,
                                    dict,
                                )
                                else None
                            ),
                            "completion_status": (
                                execution_result.get(
                                    "completion_status"
                                )
                                if isinstance(
                                    execution_result,
                                    dict,
                                )
                                else None
                            ),
                            "execution_status": (
                                execution_result.get(
                                    "execution_status"
                                )
                                if isinstance(
                                    execution_result,
                                    dict,
                                )
                                else None
                            ),
                        },
                        flush=True,
                    )

                    current_step = dict(command_step)

                    if isinstance(
                        execution_result,
                        dict,
                    ):
                        current_step.update(
                            execution_result
                        )

                        print(
                            "[PROJECT CURRENT STEP AFTER UPDATE]",
                            {
                                "status": current_step.get(
                                    "status"
                                ),
                                "completion_status": (
                                    current_step.get(
                                        "completion_status"
                                    )
                                ),
                                "execution_status": (
                                    current_step.get(
                                        "execution_status"
                                    )
                                ),
                                "result": current_step.get(
                                    "result"
                                ),
                                "error": current_step.get(
                                    "error"
                                ),
                            },
                            flush=True,
                        )
                    else:
                        current_step = command_step

                    steps[current_index] = current_step
                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = False

                    result_status = str(
                        current_step.get(
                            "status",
                            "",
                        )
                        or ""
                    ).strip().lower()
                    result_output = current_step.get(
                        "result"
                    )
                    result_error = str(
                        current_step.get(
                            "error",
                            "",
                        )
                        or ""
                    ).strip()

                    print(
                        "PROJECT EXECUTION HANDLER COMMAND RESULT",
                        {
                            "status": result_status,
                            "error": result_error,
                            "result": result_output,
                        },
                        flush=True,
                    )

                    if result_status in {
                        "failed",
                        "error",
                    }:

                        current_step["status"] = "failed"

                        current_step["error"] = (
                            result_error
                            or "Command execution failed."
                        )

                        steps[current_index] = current_step

                        state["steps"] = steps
                        state["status"] = "failed"
                        state["complete"] = False
                        state["waiting"] = False
                        state["error"] = (
                            current_step["error"]
                        )
                        state["current_step"] = current_step

                        return {
                            "ok": False,
                            "error": current_step[
                                "error"
                            ],
                            "execution_state": state,
                            "result": result_output,
                        }

                    if result_status in {
                        "waiting",
                        "waiting_approval",
                    }:

                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                            "result": result_output,
                        }

                    if result_status not in {
                        "completed",
                        "complete",
                        "success",
                    }:

                        current_step["status"] = "failed"

                        current_step["error"] = (
                            result_error
                            or (
                                "Command execution returned "
                                "an invalid completion status."
                            )
                        )

                        steps[current_index] = current_step

                        state["steps"] = steps
                        state["status"] = "failed"
                        state["complete"] = False
                        state["waiting"] = False
                        state["error"] = (
                            current_step["error"]
                        )
                        state["current_step"] = current_step

                        return {
                            "ok": False,
                            "error": current_step[
                                "error"
                            ],
                            "execution_state": state,
                            "result": result_output,
                        }

                    original_step = dict(steps[current_index])

                    original_step.update(current_step)
                    original_step["status"] = "completed"

                    steps[current_index] = original_step
                    current_step = original_step

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
                if (
                    move.type == "fix_file"
                    and isinstance(move.payload, dict)
                    and self.execution_step_service is not None
                ):
                    payload = move.payload

                    target_file = str(
                        payload.get("file_path")
                        or (
                            payload.get("file_paths") or [""]
                        )[0]
                    ).strip()

                    code = str(
                        payload.get("code")
                        or payload.get("content")
                        or ""
                    )

        
                    if not target_file:
                        raise RuntimeError(
                            "fix_file move is missing file_path."
                        )

                    if not code.strip():
                        raise RuntimeError(
                            "fix_file move is missing code."
                        )

                    bridge_step = {
                        "id": current_step.get("id")
                        or move.id
                        or "project-fix-file",
                        "action": "implement",
                        "target_file": target_file,
                        "file_path": target_file,
                        "content": code,
                        "code": code,
                        "description": (
                            current_step.get("description")
                            or current_step.get("title")
                            or "Create or update project file."
                        ),
                    }

                    # Preserve deterministic file content through the executor
                    # handoff. The planner/parser may provide content under
                    # content, code, file_content, or payload.
                    bridge_payload = bridge_step.get("payload")

                    if not isinstance(bridge_payload, dict):
                        bridge_payload = {}

                    bridge_content = (
                        bridge_step.get("content")
                        if bridge_step.get("content") is not None
                        else bridge_step.get("code")
                    )

                    if bridge_content is None:
                        bridge_content = bridge_step.get("file_content")

                    if bridge_content is None:
                        bridge_content = bridge_payload.get("content")

                    if bridge_content is None:
                        bridge_content = bridge_payload.get("file_content")

                    if bridge_content is not None:
                        bridge_step["content"] = str(bridge_content)
                        bridge_step["code"] = str(bridge_content)
                        bridge_step["file_content"] = str(bridge_content)

                        bridge_payload["content"] = str(bridge_content)
                        bridge_payload["code"] = str(bridge_content)
                        bridge_payload["file_content"] = str(bridge_content)

                    bridge_step["payload"] = bridge_payload

                    print(
                        "[PROJECT EXECUTION BRIDGE STEP]",
                        {
                            "target_file": bridge_step.get("target_file"),
                            "has_content": bool(
                                str(bridge_step.get("content") or "").strip()
                            ),
                            "content": bridge_step.get("content"),
                        },
                        flush=True,
                    )

                    execution_result = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=bridge_step,
                        )
                    )
                else:
                    execution_result = (
                        self.default_executor(move)
                    )

            except Exception as exc:
                original_error = str(exc)

                print(
                    "PROJECT EXECUTION HANDLER EXCEPTION",
                    {
                        "move_type": getattr(move, "type", None),
                        "move_id": getattr(move, "id", None),
                        "current_index": current_index,
                        "current_step_defined": "current_step" in locals(),
                        "error": original_error,
                    },
                    flush=True,
                )

                if (
                    "current_step" not in locals()
                    or not isinstance(current_step, dict)
                ):
                    current_step = {
                        "id": getattr(move, "id", None)
                        or f"project-step-{current_index}",
                        "action": "unknown",
                        "status": "failed",
                    }

                current_step["status"] = "failed"
                current_step["error"] = original_error

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["complete"] = False
                state["waiting"] = False
                state["error"] = original_error
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": original_error,
                    "execution_state": state,
                }

            if isinstance(
                execution_result,
                dict,
            ):
                result_status = str(
                    execution_result.get("status")
                    or execution_result.get("step_status")
                    or execution_result.get("execution_status")
                    or execution_result.get("completion_status")
                    or ""
                ).strip().lower()

                result_output = (
                    execution_result.get("result")
                    or execution_result.get("output")
                    or execution_result.get("stdout")
                    or execution_result.get("message")
                )

                result_error = str(
                    execution_result.get("error")
                    or ""
                ).strip()

            else:
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

        if (
            "current_step" not in locals()
            or not isinstance(current_step, dict)
        ):
            current_step = {
                "id": getattr(move, "id", None)
                or f"project-step-{current_index}",
                "action": step_action,
                "status": "failed",
            }

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
        state["current_step"] = current_step

        return {
            "ok": False,
            "error": current_step["error"],
            "execution_state": state,
        }


















































