from __future__ import annotations

import time
import uuid
from typing import Any, Dict


class ExecutionEngineService:

    def __init__(
        self,
        session_service,
        execution_service,
        default_executor,
        next_move_class,
        update_execution_state_safe,
    ):
        self.session_service = session_service
        self.execution_service = execution_service
        self.default_executor = default_executor
        self.NextMove = next_move_class
        self.update_execution_state_safe = (
            update_execution_state_safe
        )

    def get_execution(
        self,
        session_id: str,
    ) -> Dict[str, Any]:

        session_id = str(
            session_id or ""
        ).strip()

        if not session_id:
            return {}

        try:
            state = self.execution_service.get_state(
                session_id
            )

            if isinstance(state, dict):
                return state

        except Exception as exc:

            print(
                "[EXECUTION ENGINE GET STATE ERROR]",
                repr(exc),
                flush=True,
            )

        return {}

    def get_next_pending_step(
        self,
        execution: Dict[str, Any],
    ):

        steps = execution.get("steps")

        if not isinstance(
            steps,
            list,
        ):
            return None, None

        for index, step in enumerate(steps):

            if not isinstance(
                step,
                dict,
            ):
                continue

            status = str(
                step.get("status") or ""
            ).strip().lower()

            if status in {
                "",
                "pending",
                "queued",
                "ready",
            }:
                return index, step

        return None, None

        steps = execution.get("steps")

        if not isinstance(steps, list):
            return None, None

        for index, step in enumerate(steps):

            if not isinstance(step, dict):
                continue

            status = str(
                step.get("status") or ""
            ).strip().lower()

            if status in {
                "",
                "pending",
                "queued",
                "ready",
            }:
                return index, step

        return None, None

    def mark_step_running(
        self,
        execution: Dict[str, Any],
        step_index: int,
    ):

        steps = execution.get("steps") or []

        if (
            step_index < 0
            or step_index >= len(steps)
        ):
            return

        step = steps[step_index]

        if not isinstance(step, dict):
            return

        step["status"] = "running"

        execution["status"] = "running"

        execution["current_step"] = (
            step.get("title")
            or step.get("action")
            or f"Step {step_index + 1}"
        )

        execution["current_step_index"] = step_index

        step["started_at"] = time.time()

    def mark_step_complete(
        self,
        execution: Dict[str, Any],
        step_index: int,
        output: Any,
    ):

        steps = execution.get("steps") or []

        if (
            step_index < 0
            or step_index >= len(steps)
        ):
            return

        step = steps[step_index]

        if not isinstance(step, dict):
            return

        step["status"] = "completed"
        step["output"] = output
        step["completed_at"] = time.time()

        next_index = step_index + 1

        execution["steps"] = steps
        execution["current_index"] = next_index

        if next_index >= len(steps):

            execution["status"] = "completed"
            execution["current_step"] = None
            execution["current_step_index"] = None
            execution["waiting"] = False
            execution["complete"] = True

        else:

            next_step = steps[next_index]

            if isinstance(next_step, dict):

                next_status = str(
                    next_step.get("status") or ""
                ).strip().lower()

                if next_status in {
                    "",
                    "pending",
                    "queued",
                    "ready",
                }:
                    next_step["status"] = "pending"

                execution["current_step"] = (
                    next_step.get("title")
                    or next_step.get("action")
                    or f"Step {next_index + 1}"
                )

            else:

                execution["current_step"] = None

            execution["current_step_index"] = next_index
            execution["status"] = "ready"
            execution["waiting"] = False
            execution["complete"] = False

    def mark_step_failed(
        self,
        execution: Dict[str, Any],
        step_index: int,
        error: str,
    ):

        steps = execution.get("steps") or []

        if (
            step_index < 0
            or step_index >= len(steps)
        ):
            return

        step = steps[step_index]

        if not isinstance(step, dict):
            return

        step["status"] = "failed"

        step["error"] = str(error)

        step["failed_at"] = time.time()

        execution["status"] = "error"

    def build_move(
        self,
        step: Dict[str, Any],
    ):
        if not isinstance(step, dict):
            step = {}

        move = step.get("move")

        if not isinstance(move, dict):
            move = {}

        move_id = (
            move.get("id")
            or step.get("id")
            or uuid.uuid4().hex
        )

        move_type = str(
            move.get("type")
            or step.get("action")
            or step.get("type")
            or ""
        ).strip().lower()

        payload = move.get("payload")

        if not isinstance(payload, dict):
            payload = {}

        step_payload = {}

        for key in (
            "file_path",
            "file_paths",
            "target_file",
            "target_files",
            "function_name",
            "target_function",
            "replacement",
            "replacement_code",
            "code",
            "content",
            "goal",
            "title",
            "description",
            "mutation_mode",
        ):
            value = step.get(key)

            if value not in (
                None,
                "",
                [],
                {},
            ):
                step_payload[key] = value

        merged_payload = {
            **step_payload,
            **payload,
        }

        if (
            not merged_payload.get("file_path")
            and merged_payload.get("target_file")
        ):
            merged_payload["file_path"] = (
                merged_payload["target_file"]
            )

        if (
            not merged_payload.get("file_paths")
            and merged_payload.get("target_files")
        ):
            merged_payload["file_paths"] = (
                merged_payload["target_files"]
            )

        if (
            not merged_payload.get("function_name")
            and merged_payload.get("target_function")
        ):
            merged_payload["function_name"] = (
                merged_payload["target_function"]
            )

        if (
            not merged_payload.get("replacement")
            and merged_payload.get("replacement_code")
        ):
            merged_payload["replacement"] = (
                merged_payload["replacement_code"]
            )

        if (
            not merged_payload.get("replacement")
            and merged_payload.get("content")
        ):
            merged_payload["replacement"] = (
                merged_payload["content"]
            )

        if not move_type:
            function_name = str(
                merged_payload.get("function_name") or ""
            ).strip()

            replacement = str(
                merged_payload.get("replacement") or ""
            ).strip()

            code = str(
                merged_payload.get("code") or ""
            ).strip()

            file_path = str(
                merged_payload.get("file_path") or ""
            ).strip()

            if (
                file_path
                and function_name
                and replacement
            ):
                move_type = "apply_function_fix"

            elif (
                file_path
                and code
            ):
                move_type = "fix_file"

            else:
                move_type = "echo"

        aliases = {
            "fix_function": "apply_function_fix",
            "repair_function": "apply_function_fix",
            "replace_function": "apply_function_fix",
            "apply_fix": "apply_function_fix",
            "edit_function": "apply_function_fix",

            "repair_file": "fix_file",
            "replace_file": "fix_file",
            "write_file": "fix_file",
        }

        move_type = aliases.get(
            move_type,
            move_type,
        )

        if move_type in {
            "fix",
            "repair",
            "edit",
            "mutate",
            "apply",
        }:
            function_name = str(
                merged_payload.get("function_name") or ""
            ).strip()

            replacement = str(
                merged_payload.get("replacement") or ""
            ).strip()

            code = str(
                merged_payload.get("code")
                or merged_payload.get("content")
                or ""
            ).strip()

            if function_name and replacement:
                move_type = "apply_function_fix"

            elif code:
                move_type = "fix_file"

        return self.NextMove(
            id=str(move_id),
            type=str(move_type or "echo"),
            payload=merged_payload,
        )

    def save_execution(
        self,
        session_id: str,
        execution: Dict[str, Any],
    ):

        session_id = str(
            session_id or ""
        ).strip()

        if not session_id:
            return

        if not isinstance(
            execution,
            dict,
        ):
            return

        execution_copy = dict(
            execution
        )

        try:

            execution_copy = (
                self.normalize_execution_status(
                    execution_copy
                )
            )

        except Exception as exc:

            print(
                "[EXECUTION ENGINE NORMALIZE SAVE ERROR]",
                repr(exc),
                flush=True,
            )

        try:

            self.execution_service._states[
                session_id
            ] = execution_copy

            self.execution_service._save_states()

        except Exception as exc:

            print(
                "[EXECUTION ENGINE CHAT STATE SAVE ERROR]",
                repr(exc),
                flush=True,
            )

        try:

            self.session_service.update_working_state(
                session_id,
                {
                    "execution": execution_copy,
                    "execution_state": execution_copy,
                    "active_execution": execution_copy,
                    "last_execution": execution_copy,
                },
            )

        except Exception as exc:

            print(
                "[EXECUTION ENGINE SESSION SAVE ERROR]",
                repr(exc),
                flush=True,
            )

        execution_state_service = getattr(
            self.execution_service,
            "execution_state_service",
            None,
        )

        if execution_state_service:

            try:

                execution_state_service.save_execution_state(
                    session_id,
                    execution_copy,
                )

            except Exception as exc:

                print(
                    "[EXECUTION ENGINE PERSISTED STATE SAVE ERROR]",
                    repr(exc),
                    flush=True,
                )

    def normalize_execution_status(
        self,
        execution: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(execution, dict):
            execution = {}

        steps = execution.get("steps")

        if not isinstance(steps, list):
            steps = []
            execution["steps"] = steps

        first_pending_index = None
        running_index = None
        failed_index = None

        has_pending = False
        has_running = False
        has_failed = False

        for index, step in enumerate(steps):

            if not isinstance(step, dict):
                continue

            status = str(
                step.get("status") or ""
            ).strip().lower()

            if status in {
                "",
                "pending",
                "queued",
                "ready",
            }:

                has_pending = True

                if first_pending_index is None:
                    first_pending_index = index

            elif status == "running":

                has_running = True

                if running_index is None:
                    running_index = index

            elif status in {
                "failed",
                "error",
            }:

                has_failed = True

                if failed_index is None:
                    failed_index = index

        if has_running:

            execution["status"] = "running"
            execution["complete"] = False
            execution["current_index"] = running_index

            running_step = steps[running_index]

            execution["current_step"] = (
                running_step.get("title")
                or running_step.get("action")
                or f"Step {running_index + 1}"
            )

        elif has_pending:

            execution["status"] = "ready"
            execution["complete"] = False
            execution["current_index"] = first_pending_index

            pending_step = steps[first_pending_index]

            execution["current_step"] = (
                pending_step.get("title")
                or pending_step.get("action")
                or f"Step {first_pending_index + 1}"
            )

        elif has_failed:

            execution["status"] = "error"
            execution["complete"] = False
            execution["current_index"] = failed_index

            failed_step = steps[failed_index]

            execution["current_step"] = (
                failed_step.get("title")
                or failed_step.get("action")
                or f"Step {failed_index + 1}"
            )

        else:

            if steps:

                execution["status"] = "complete"
                execution["complete"] = True
                execution["current_index"] = len(steps)
                execution["current_step"] = None
                execution["current_step_index"] = None
                execution["waiting"] = False

            else:

                execution["status"] = "idle"
                execution["complete"] = False
                execution["current_index"] = 0
                execution["current_step"] = None
                execution["current_step_index"] = None
                execution["waiting"] = False

        return execution

    def execute_next_step(
        self,
        session_id: str,
        execution: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        session_id = str(
            session_id or ""
        ).strip()

        if not session_id:

            return {
                "ok": False,
                "error": "missing_session_id",
            }

        if isinstance(execution, dict) and execution:

            execution = dict(execution)

        else:

            execution = self.get_execution(
                session_id
            )

        if not isinstance(execution, dict):

            return {
                "ok": False,
                "error": "execution_not_found",
            }

        execution = self.normalize_execution_status(
            execution
        )

        step_index, step = (
            self.get_next_pending_step(
                execution
            )
        )

        if step is None:

            execution["status"] = "complete"

            self.save_execution(
                session_id,
                execution,
            )

            return {
                "ok": True,
                "status": "complete",
                "execution": execution,
                "message": (
                    "No pending execution steps."
                ),
            }

        self.mark_step_running(
            execution,
            step_index,
        )

        self.save_execution(
            session_id,
            execution,
        )

        try:

            print(
                "[EXECUTION ENGINE STEP BEFORE BUILD]",
                {
                    "session_id": session_id,
                    "step_index": step_index,
                    "step": step,
                },
                flush=True,
            )

            move = self.build_move(step)

            print(
                "[EXECUTION ENGINE MOVE BUILT]",
                {
                    "session_id": session_id,
                    "step_index": step_index,
                    "move_id": move.id,
                    "move_type": move.type,
                    "move_payload": move.payload,
                },
                flush=True,
            )

            result = self.default_executor(
                move
            )

            result_status = str(
                getattr(
                    result,
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            success = result_status in {
                "success",
                "completed",
                "complete",
                "ok",
            }

            output = getattr(
                result,
                "output",
                {},
            )

            if success:

                self.mark_step_complete(
                    execution,
                    step_index,
                    output,
                )

                remaining_index, remaining_step = (
                    self.get_next_pending_step(
                        execution
                    )
                )

                if remaining_step is None:

                    execution["status"] = "complete"

                else:

                    execution["status"] = "ready"

                self.update_execution_state_safe(
                    execution,
                    status=execution.get(
                        "status"
                    ),
                )

                self.save_execution(
                    session_id,
                    execution,
                )

                return {
                    "ok": True,
                    "status": execution.get(
                        "status"
                    ),
                    "step_index": step_index,
                    "step": step,
                    "output": output,
                    "execution": execution,
                }

            error = str(
                getattr(
                    result,
                    "error",
                    "",
                )
                or f"Execution failed with status: {result_status or 'unknown'}"
            )

            self.mark_step_failed(
                execution,
                step_index,
                error,
            )

            self.save_execution(
                session_id,
                execution,
            )

            return {
                "ok": False,
                "status": "error",
                "step_index": step_index,
                "step": step,
                "error": error,
                "execution": execution,
            }

        except Exception as exc:

            error = str(exc)

            self.mark_step_failed(
                execution,
                step_index,
                error,
            )

            self.save_execution(
                session_id,
                execution,
            )

            print(
                "[EXECUTION ENGINE ERROR]",
                repr(exc),
                flush=True,
            )

            return {
                "ok": False,
                "status": "error",
                "step_index": step_index,
                "error": error,
                "execution": execution,
            }
