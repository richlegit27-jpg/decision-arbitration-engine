from __future__ import annotations

from datetime import datetime, timezone


class ExecutionRuntimeService:
    def __init__(self, session_service=None):
        self.sessions = session_service

    def summarize_execution_command_result(
        self,
        command: str,
        execution_state: dict | None = None,
        status: str = "",
    ) -> str:

        state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        steps = (
            state.get("steps")
            if isinstance(state.get("steps"), list)
            else []
        )

        current_index = int(
            state.get("current_index") or 0
        )

        total = len(steps)

        completed = [
            str(
                step.get("title")
                or step.get("action")
                or "step"
            )
            for step in steps
            if (
                isinstance(step, dict)
                and str(
                    step.get("status") or ""
                ).lower()
                in {
                    "completed",
                    "complete",
                    "success",
                }
            )
        ]

        failed = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and str(
                    step.get("status") or ""
                ).lower()
                in {
                    "failed",
                    "error",
                }
            )
        ]

        if failed:
            step = failed[-1]

            title = str(
                step.get("title")
                or step.get("action")
                or "step"
            )

            error = str(
                step.get("error")
                or "Unknown error."
            )

            return (
                f"Step failed: {title}\n"
                f"Status: failed\n"
                f"Error: {error}"
            )

        if total and len(completed) >= total:
            return (
                "Execution chain complete.\n"
                f"Completed steps: "
                f"{', '.join(completed)}"
            )

        if total:
            active_step = None

            if 0 <= current_index - 1 < total:
                active_step = steps[current_index - 1]

            if not active_step and completed:
                active_step = next(
                    (
                        step
                        for step in reversed(steps)
                        if (
                            isinstance(step, dict)
                            and str(
                                step.get("status") or ""
                            ).lower()
                            in {
                                "completed",
                                "complete",
                                "success",
                            }
                        )
                    ),
                    None,
                )

            title = str(
                (active_step or {}).get("title")
                or (active_step or {}).get("action")
                or "step"
            )

            next_title = (
                steps[current_index].get("title")
                if (
                    current_index < total
                    and isinstance(
                        steps[current_index],
                        dict,
                    )
                )
                else "done"
            )

            return (
                f"Step "
                f"{min(current_index, total)}/{total} "
                f"complete: {title}\n"
                f"Completed so far: "
                f"{', '.join(completed) if completed else 'none'}\n"
                f"Next: {next_title}"
            )

        return (
            f"Execution command completed: "
            f"{command}"
        )

    def archive_execution_state(
        self,
        session_id: str,
        execution_state: dict,
        command: str = "",
    ) -> None:

        if not self.sessions:
            return

        try:
            execution_state = execution_state or {}

            steps = (
                execution_state.get("steps")
                or []
            )

            completed_steps = []
            failed_steps = []

            for step in steps:

                if not isinstance(step, dict):
                    continue

                title = str(
                    step.get("title")
                    or step.get("id")
                    or "step"
                ).strip()

                status = str(
                    step.get("status")
                    or ""
                ).strip().lower()

                if status in {
                    "completed",
                    "complete",
                    "done",
                    "success",
                }:
                    completed_steps.append(title)

                elif status in {
                    "failed",
                    "error",
                }:
                    failed_steps.append(title)

            if (
                not completed_steps
                and not failed_steps
            ):
                return

            if completed_steps == [
                "No saved execution plan found"
            ]:
                return

            archive_entry = {
                "status": str(
                    execution_state.get("status")
                    or ""
                ).strip(),

                "command": str(
                    command
                    or ""
                ).strip(),

                "completed_steps": completed_steps,

                "failed_steps": failed_steps,

                "last_action": str(
                    execution_state.get("last_action")
                    or ""
                ).strip(),

                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            sessions = (
                self.sessions._load_sessions()
            )

            index = self.sessions._find(
                sessions,
                session_id,
            )

            if index is None:
                return

            history = (
                sessions[index].get(
                    "execution_history"
                )
                or []
            )

            if not isinstance(history, list):
                history = []

            cleaned_history = []

            for item in history:

                if not isinstance(item, dict):
                    continue

                completed = (
                    item.get("completed_steps")
                    or []
                )

                failed = (
                    item.get("failed_steps")
                    or []
                )

                if completed == [
                    "No saved execution plan found"
                ]:
                    continue

                if (
                    not completed
                    and not failed
                ):
                    continue

                cleaned_history.append(item)

            cleaned_history.append(
                archive_entry
            )

            sessions[index][
                "execution_history"
            ] = cleaned_history[-25:]

            self.sessions._save_sessions(
                sessions,
                self.sessions.get_active_session_id(),
            )

        except Exception:
            return