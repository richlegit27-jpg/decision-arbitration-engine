from __future__ import annotations

from typing import Any


class ExecutionLoopService:
    def __init__(
        self,
        execution_handler=None,
        runtime_service=None,
    ):
        self.execution_handler = execution_handler
        self.runtime = runtime_service

    def normalize_result(
        self,
        result: Any,
        fallback_state: dict | None = None,
    ) -> dict:
        if isinstance(result, dict):
            return result

        return {
            "status": "unknown",
            "message": str(result),
            "execution_state": fallback_state or {},
        }

    def is_complete(
        self,
        execution_state: dict | None,
        status: str = "",
    ) -> bool:
        state = execution_state if isinstance(execution_state, dict) else {}
        status_value = str(status or state.get("status") or "").lower()

        return status_value in {
            "complete",
            "completed",
            "success",
            "done",
        }

    def is_failed(
        self,
        execution_state: dict | None,
        status: str = "",
    ) -> bool:
        state = execution_state if isinstance(execution_state, dict) else {}
        status_value = str(status or state.get("status") or "").lower()

        return status_value in {
            "failed",
            "error",
            "failure",
        }

    def should_stop(
        self,
        execution_state: dict | None,
        status: str = "",
    ) -> bool:
        return (
            self.is_complete(
                execution_state,
                status,
            )
            or self.is_failed(
                execution_state,
                status,
            )
        )

    def should_abort_from_failures(
        self,
        working_state: dict | None,
    ) -> bool:
        state = (
            working_state
            if isinstance(working_state, dict)
            else {}
        )

        score = int(
            state.get("execution_reward_score") or 0
        )

        last_reward = int(
            state.get("last_execution_reward") or 0
        )

        failure_count = int(
            state.get("execution_failure_count") or 0
        )

        if failure_count >= 5:
            return True

        if score <= -10:
            return True

        if last_reward <= -5:
            return True

        return False

    def handle_auto_fix_retry_state(
        self,
        execution_state: dict,
    ):
        execution_state = execution_state or {}

        retry_count = int(
            execution_state.get("auto_fix_retry_count") or 0
        ) + 1

        execution_state["auto_fix_retry_count"] = retry_count

        if retry_count >= 3:
            execution_state["status"] = "needs_strategy_change"
            execution_state["next_move"] = (
                "review_failure_pattern_before_retry"
            )

            return {
                "retry_count": retry_count,
                "capped": True,
                "execution_state": execution_state,
            }

        execution_state["status"] = "retry_ready"
        execution_state["next_move"] = "run_step"

        return {
            "retry_count": retry_count,
            "capped": False,
            "execution_state": execution_state,
        }

    def get_status(
        self,
        result: dict,
        execution_state: dict | None = None,
    ) -> str:
        state = execution_state if isinstance(execution_state, dict) else {}

        return str(
            result.get("status")
            or state.get("status")
            or "unknown"
        ).strip().lower()

    def get_execution_state(
        self,
        result: dict | None,
        fallback_state: dict | None = None,
    ) -> dict:
        if isinstance(result, dict):
            state = result.get("execution_state")

            if isinstance(state, dict):
                return state

        return fallback_state if isinstance(fallback_state, dict) else {}

    def get_message(
        self,
        result: dict | None,
        default: str = "",
    ) -> str:
        if not isinstance(result, dict):
            return default

        return str(
            result.get("message")
            or result.get("result")
            or result.get("text")
            or default
        ).strip()

    def command_alias(
        self,
        command: str,
    ) -> str:
        command = str(command or "").strip().lower()

        aliases = {
            "next": "run_step",
            "nex": "run_step",
            "continue": "run_step",
            "continue on": "run_step",
            "go": "run_step",
            "run next": "run_step",
            "next step": "run_step",
            "run all": "run_all",
            "run_all": "run_all",
            "execute": "run_all",
            "execute all": "run_all",
            "run it": "run_all",
            "retry": "retry_failed",
            "retry failed": "retry_failed",
            "rerun failed": "retry_failed",
            "try again": "retry_failed",
            "cancel": "cancel",
            "stop": "cancel",
            "test_fail": "test_fail",
            "test fail": "test_fail",
            "apply auto fix": "apply_auto_fix",
            "apply_auto_fix": "apply_auto_fix",
            "auto fix": "apply_auto_fix",
            "autofix": "apply_auto_fix",
        }

        return aliases.get(command, command)

    def has_active_plan(
        self,
        execution_state: dict | None,
    ) -> bool:
        state = execution_state if isinstance(execution_state, dict) else {}
        steps = state.get("steps")

        return isinstance(steps, list) and len(steps) > 0

    def current_step_title(
        self,
        execution_state: dict | None,
    ) -> str:
        state = execution_state if isinstance(execution_state, dict) else {}

        title = (
            state.get("current_step_title")
            or state.get("current_step")
            or ""
        )

        return str(title).strip()

    def completed_step_titles(
        self,
        execution_state: dict | None,
    ) -> list[str]:
        state = execution_state if isinstance(execution_state, dict) else {}
        steps = state.get("steps") or []

        completed = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            status = str(step.get("status") or "").strip().lower()

            if status in {
                "completed",
                "complete",
                "done",
                "success",
            }:
                completed.append(
                    str(
                        step.get("title")
                        or step.get("id")
                        or "step"
                    ).strip()
                )

        return completed

    def failed_step_titles(
        self,
        execution_state: dict | None,
    ) -> list[str]:
        state = execution_state if isinstance(execution_state, dict) else {}
        steps = state.get("steps") or []

        failed = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            status = str(step.get("status") or "").strip().lower()

            if status in {
                "failed",
                "error",
                "failure",
            }:
                failed.append(
                    str(
                        step.get("title")
                        or step.get("id")
                        or "step"
                    ).strip()
                )

        return failed

    def summarize_execution(
        self,
        command: str,
        execution_state: dict | None = None,
        status: str = "",
    ) -> str:
        state = execution_state if isinstance(execution_state, dict) else {}

        completed = self.completed_step_titles(state)
        failed = self.failed_step_titles(state)

        lines = []

        status = str(
            state.get("status") or "unknown"
        ).strip().lower()

        if self.is_complete(state, status):
            lines.append("Execution chain complete.")

        elif self.is_failed(state, status):
            lines.append("Execution chain failed.")

        else:
            lines.append("Execution chain running.")

        if completed:
            lines.append(
                "Completed steps: "
                + ", ".join(completed)
            )

        if failed:
            lines.append(
                "Failed steps: "
                + ", ".join(failed)
            )

        if command:
            lines.append(
                f"Last command: {command}"
            )

        return "\n".join(lines).strip()

    def run(
        self,
        command: str,
        session_id: str,
        execution_state: dict | None = None,
    ) -> dict:
        command = self.command_alias(command)

        state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        if not self.execution_handler:
            return {
                "ok": False,
                "status": "error",
                "message": "Execution handler missing.",
                "execution_state": state,
            }

        try:
            if hasattr(self.execution_handler, "run_next_move"):
                result = self.execution_handler.run_next_move(
                    action=command,
                    session_id=session_id,
                    execution_state=state,
                )

            elif hasattr(self.execution_handler, "run_next_step"):
                result = self.execution_handler.run_next_step(
                    action=command,
                    session_id=session_id,
                    execution_state=state,
                )

            elif hasattr(self.execution_handler, "run_chain"):
                result = self.execution_handler.run_chain(
                    action=command,
                    session_id=session_id,
                    execution_state=state,
                )

            else:
                return {
                    "ok": False,
                    "status": "error",
                    "message": (
                        "Execution handler has no runnable method."
                    ),
                    "execution_state": state,
                }

            normalized = self.normalize_result(
                result,
                fallback_state=state,
            )

            normalized.setdefault("ok", True)

            normalized.setdefault(
                "execution_state",
                state,
            )

            return normalized

        except Exception as e:
            return {
                "ok": False,
                "status": "error",
                "message": (
                    f"Execution crashed: {repr(e)}"
                ),
                "error": repr(e),
                "execution_state": state,
            }

    def record_history(
        self,
        history_callback,
        session_id: str,
        event_type: str,
        details: dict | None = None,
    ) -> None:
        if not callable(history_callback):
            return

        try:
            history_callback(
                session_id=session_id,
                event_type=event_type,
                details=details,
            )

        except Exception:
            pass

    def archive_execution(
        self,
        archive_callback,
        session_id: str,
        execution_state: dict,
        command: str = "",
    ) -> None:
        if not callable(archive_callback):
            return

        try:
            archive_callback(
                session_id=session_id,
                execution_state=execution_state,
                command=command,
            )

        except Exception:
            pass

