from __future__ import annotations

import time
import uuid
from typing import Any


class ExecutionStreamService:

    def __init__(
        self,
        session_service,
        chat_service,
        default_executor,
        next_move_class,
        update_execution_state_safe,
    ):
        self.session_service = session_service
        self.chat_service = chat_service
        self.default_executor = default_executor
        self.NextMove = next_move_class

        self.update_execution_state_safe = (
            update_execution_state_safe
        )

    # ==========================================================
    # SSE EVENTS
    # ==========================================================

    def send_event(
        self,
        name,
        payload,
    ):
        import json

        return (
            f"event: {name}\n"
            f"data: {json.dumps(payload)}\n\n"
        )

    # ==========================================================
    # EXECUTION PERSISTENCE
    # ==========================================================

    def save_execution(
        self,
        session_id,
        execution,
    ):
        if not session_id:
            return

        if not isinstance(
            execution,
            dict,
        ):
            execution = {}

        self.session_service.update_working_state(
            session_id,
            {
                "execution": execution,
            },
        )

    # ==========================================================
    # EXECUTION LIFECYCLE
    # ==========================================================

    def create_execution(
        self,
        title="Execution",
    ):
        return {
            "id": (
                f"execution_"
                f"{uuid.uuid4().hex}"
            ),
            "title": str(
                title or "Execution"
            ),
            "status": "pending",
            "current_step": "",
            "steps": [],
            "started_at": None,
            "completed_at": None,
            "error": None,
        }

    def start_execution(
        self,
        execution,
    ):
        if not isinstance(
            execution,
            dict,
        ):
            return execution

        execution["status"] = "running"

        if not execution.get("started_at"):
            execution["started_at"] = time.time()

        return execution

    def complete_execution(
        self,
        execution,
    ):
        if not isinstance(
            execution,
            dict,
        ):
            return execution

        execution["status"] = "complete"
        execution["completed_at"] = time.time()
        execution["current_step"] = ""

        return execution

    def fail_execution(
        self,
        execution,
        error=None,
    ):
        if not isinstance(
            execution,
            dict,
        ):
            return execution

        execution["status"] = "error"
        execution["completed_at"] = time.time()

        if error:
            execution["error"] = str(error)

        return execution

    # ==========================================================
    # STEP LIFECYCLE
    # ==========================================================

    def create_step(
        self,
        title,
        action,
        move=None,
    ):
        return {
            "id": (
                f"step_"
                f"{uuid.uuid4().hex}"
            ),
            "title": str(
                title or action or "Execution step"
            ),
            "action": str(
                action or "unknown"
            ),
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "move": (
                move
                if isinstance(move, dict)
                else {}
            ),
            "output": {},
            "error": None,
            "attempt": 0,
        }

    def start_step(
        self,
        execution,
        step,
    ):
        if not isinstance(
            step,
            dict,
        ):
            return step

        step["status"] = "running"
        step["started_at"] = time.time()

        step["attempt"] = (
            int(
                step.get("attempt") or 0
            )
            + 1
        )

        if isinstance(
            execution,
            dict,
        ):
            execution["current_step"] = (
                step.get("title")
                or step.get("action")
                or ""
            )

            execution["status"] = "running"

        return step

    def complete_step(
        self,
        execution,
        step,
        output=None,
    ):
        if not isinstance(
            step,
            dict,
        ):
            return step

        step["status"] = "done"
        step["completed_at"] = time.time()

        step["output"] = (
            output
            if isinstance(output, dict)
            else {
                "result": output
            }
        )

        step["error"] = None

        if isinstance(
            execution,
            dict,
        ):
            execution["current_step"] = ""

        return step

    def fail_step(
        self,
        execution,
        step,
        error=None,
        output=None,
    ):
        if not isinstance(
            step,
            dict,
        ):
            return step

        step["status"] = "failed"
        step["completed_at"] = time.time()

        if error:
            step["error"] = str(error)

        if output is not None:
            step["output"] = (
                output
                if isinstance(output, dict)
                else {
                    "result": output
                }
            )

        if isinstance(
            execution,
            dict,
        ):
            execution["current_step"] = ""

        return step

    def retry_step(
        self,
        execution,
        step,
    ):
        if not isinstance(
            step,
            dict,
        ):
            return step

        step["status"] = "retrying"
        step["error"] = None

        if isinstance(
            execution,
            dict,
        ):
            execution["current_step"] = (
                step.get("title")
                or step.get("action")
                or ""
            )

        return step

    # ==========================================================
    # RUNTIME STRATEGY MEMORY
    # ==========================================================

    def record_runtime_signal(
        self,
        action,
        success,
    ):
        runtime = getattr(
            self.chat_service,
            "runtime",
            None,
        )

        if runtime is None:
            return

        runtime_strategy_memory = getattr(
            runtime,
            "runtime_strategy_memory",
            None,
        )

        if not isinstance(
            runtime_strategy_memory,
            list,
        ):
            return

        runtime_strategy_memory.append(
            {
                "action": str(
                    action or "unknown"
                ),
                "success": bool(success),
                "failure": not bool(success),
                "runtime_signal": (
                    "execution_success"
                    if success
                    else "execution_failure"
                ),
                "score_delta": (
                    1
                    if success
                    else -1
                ),
            }
        )

    # ==========================================================
    # STEP EXECUTION
    # ==========================================================

    def execute_step(
        self,
        execution,
        step,
    ):
        if not isinstance(
            execution,
            dict,
        ):
            return {
                "ok": False,
                "error": "invalid_execution",
            }

        if not isinstance(
            step,
            dict,
        ):
            return {
                "ok": False,
                "error": "invalid_step",
            }

        self.start_execution(
            execution
        )

        self.start_step(
            execution,
            step,
        )

        move = step.get("move")

        if not isinstance(
            move,
            dict,
        ):
            self.fail_step(
                execution,
                step,
                error="No move stored on step.",
            )

            self.fail_execution(
                execution,
                error="Step execution failed.",
            )

            return {
                "ok": False,
                "step": step,
                "execution": execution,
                "error": "missing_move",
            }

        try:

            result = self.default_executor(
                self.NextMove(
                    id=str(
                        move.get("id")
                        or f"move-{uuid.uuid4().hex}"
                    ),
                    type=str(
                        move.get("type")
                        or "echo"
                    ),
                    payload=(
                        move.get("payload")
                        if isinstance(
                            move.get("payload"),
                            dict,
                        )
                        else {}
                    ),
                )
            )

            success = bool(
                getattr(
                    result,
                    "success",
                    False,
                )
            )

            output = getattr(
                result,
                "output",
                {},
            )

            action = (
                move.get("type")
                or step.get("action")
                or "unknown"
            )

            self.record_runtime_signal(
                action=action,
                success=success,
            )

            if success:

                self.complete_step(
                    execution,
                    step,
                    output=output,
                )

                return {
                    "ok": True,
                    "step": step,
                    "execution": execution,
                    "output": output,
                }

            error = str(
                getattr(
                    result,
                    "error",
                    None,
                )
                or "Step execution failed."
            )

            self.fail_step(
                execution,
                step,
                error=error,
                output=output,
            )

            return {
                "ok": False,
                "step": step,
                "execution": execution,
                "output": output,
                "error": error,
            }

        except Exception as exc:

            self.record_runtime_signal(
                action=(
                    step.get("action")
                    or "unknown"
                ),
                success=False,
            )

            self.fail_step(
                execution,
                step,
                error=str(exc),
            )

            return {
                "ok": False,
                "step": step,
                "execution": execution,
                "error": str(exc),
            }

    # ==========================================================
    # REPLAY EXISTING STEP
    # ==========================================================

    def replay_existing_step(
        self,
        execution,
        replay_step,
        step_title,
        action,
    ):
        if not isinstance(
            replay_step,
            dict,
        ):
            return None

        move = replay_step.get(
            "move"
        )

        if not isinstance(
            move,
            dict,
        ):
            self.fail_step(
                execution,
                replay_step,
                error=(
                    "Replay failed: "
                    "no move stored on step."
                ),
            )

            self.fail_execution(
                execution,
                error=(
                    f"Replay failed: "
                    f"{step_title}"
                ),
            )

            return replay_step

        if not replay_step.get("title"):
            replay_step["title"] = step_title

        if not replay_step.get("action"):
            replay_step["action"] = action

        self.retry_step(
            execution,
            replay_step,
        )

        result = self.execute_step(
            execution,
            replay_step,
        )

        replay_ok = bool(
            result.get("ok")
        )

        if replay_ok:

            self.complete_execution(
                execution
            )

        else:

            self.fail_execution(
                execution,
                error=result.get("error"),
            )

        execution["current_step"] = (
            "Replay complete"
            if replay_ok
            else (
                f"Replay failed: "
                f"{step_title}"
            )
        )

        return replay_step