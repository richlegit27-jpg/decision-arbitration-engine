from __future__ import annotations


class ExecutionOrchestratorService:

    def __init__(
        self,
        execution_state_service=None,
        working_state_service=None,
        execution_mutation_service=None,
        safe_str=None,
        execution_step_service=None,
    ):
        self.execution_state_service = execution_state_service
        self.working_state_service = working_state_service
        self.execution_mutation_service = (
            execution_mutation_service
        )
        self._safe_str = safe_str
        self.execution_step_service = execution_step_service

    def process_execution(
        self,
        session_id="",
        state=None,
        command="",
    ):
        execution_state = (
            state
            if isinstance(state, dict)
            else {}
        )

        selected_command = (
            command
            or execution_state.get("command")
            or execution_state.get("intent")
            or execution_state.get("mode")
            or ""
        )

        return self._process_execution_command(
            command=selected_command,
            session_id=session_id,
            execution_state=execution_state,
        )

    def _save_execution_state(
        self,
        session_id="",
        execution_state=None,
    ):
        if not self.execution_state_service:
            return {}

        return self.execution_state_service.save_execution_state(
            session_id,
            execution_state,
        )

    def _save_active_execution(
        self,
        session_id="",
        execution_state=None,
    ):
        return self._save_execution_state(
            session_id=session_id,
            execution_state=execution_state,
        )

    def _process_execution_command(
        self,
        command="",
        session_id="",
        execution_state=None,
    ):

        persisted_execution_state = {}

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        command = self._safe_str(command).strip().lower()

        intelligence_intent = (
            self._safe_str(
                execution_state.get("intent") or execution_state.get("mode") or ""
            )
            .strip()
            .lower()
        )

        if intelligence_intent in {
            "resume_execution",
            "continue_waiting_execution",
        }:
            command = "run_step"

        elif intelligence_intent == "run_all_steps":
            command = "run_all"

        elif intelligence_intent == "retry_failed_step":
            command = "retry_failed"

        elif intelligence_intent == "cancel_execution":
            command = "cancel"

        working_state = {}

        if self.working_state_service:
            working_state = (
                self.working_state_service.get_working_state(
                    session_id
                )
                or {}
            )
        persisted_execution_state = (
            self.execution_state_service.get_execution_state(
                session_id
            )
            or {}
        )

        persisted_has_state = bool(persisted_execution_state.get("steps"))

        incoming_has_state = bool(execution_state.get("steps"))

        if persisted_has_state:

            execution_state = persisted_execution_state

        elif incoming_has_state:

            execution_state = execution_state

        else:

            execution_state = {}

        steps = execution_state.get("steps") or []

        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        if current_index < 0:
            current_index = 0

        if current_index >= len(steps):
            current_index = len(steps)


        # =========================
        # NEXT AFTER COMPLETION
        # =========================

        if command in {
            "next",
            "continue",
            "keep going",
            "run next",
        }:

            command = "run_step"

            current_index = int(
                execution_state.get(
                    "current_index",
                    0,
                )
                or 0
            )

            execution_state = (
                self.execution_mutation_service.mark_running(
                    execution_state,
                    step_index=current_index,
                    current_step=execution_state.get("current_step") or "",
                    waiting=False,
                )
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

        # =========================
        # RUN STEP
        # =========================
        if command in {
            "run_step",
            "run step",
        }:

            if not steps:

                persisted_execution = (
                    self.execution_state_service.get_execution_state(
                        session_id
                    )
                    or {}
                )

                if isinstance(
                    persisted_execution,
                    dict,
                ) and persisted_execution.get("steps"):
                    execution_state = persisted_execution

                    current_index = int(
                        execution_state.get(
                            "current_index",
                            0,
                        )
                        or 0
                    )

                    steps = execution_state.get(
                        "steps",
                        [],
                    )

                    current_index = int(
                        execution_state.get(
                            "current_index",
                            0,
                        )
                    )

            if not steps:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No active execution plan. "
                            "Start one with: auto-plan <goal>"
                        ),
                    },
                    "execution": execution_state,
                }

            while current_index < len(steps) and self._safe_str(
                steps[current_index].get("status")
            ).lower().strip() in {
                "completed",
                "done",
            }:
                current_index += 1

            execution_state["current_index"] = current_index

            if current_index >= len(steps):

                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state,
                    )
                )
                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": ("All execution steps completed."),
                    },
                    "execution": execution_state,
                }

            refreshed_execution = (
                self.execution_state_service.get_execution_state(
                    session_id
                )
                or execution_state
            )
            refreshed_steps = refreshed_execution.get("steps") or []

            if not isinstance(
                refreshed_steps,
                list,
            ) or current_index >= len(refreshed_steps):
                refreshed_steps = steps

            step = refreshed_steps[current_index]

            execution_state = refreshed_execution

            steps = refreshed_steps
            execution_state["current_index"] = current_index

            if current_index >= len(steps):
                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state,
                    )
                )

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "All execution steps completed.",
                    },
                    "execution": execution_state,
                }

            refreshed_execution = (
                self.execution_state_service.get_execution_state(
                    session_id
                )
                or execution_state
            )
            
            refreshed_steps = refreshed_execution.get("steps") or []

            if not isinstance(
                refreshed_steps,
                list,
            ) or current_index >= len(refreshed_steps):
                refreshed_steps = steps

            original_step = (
                steps[current_index]
                if current_index < len(steps) and isinstance(steps[current_index], dict)
                else {}
            )

            refreshed_step = (
                refreshed_steps[current_index]
                if current_index < len(refreshed_steps)
                and isinstance(refreshed_steps[current_index], dict)
                else {}
            )

            step = {
                **original_step,
                **refreshed_step,
            }

            execution_state = refreshed_execution
            steps = refreshed_steps

            step["status"] = "running"

            execution_state = (
                self.execution_mutation_service.mark_running(
                    execution_state,
                    step_index=current_index,
                    current_step=step.get("title") or "",
                    waiting=False,
                )
            )

            result = self.execution_step_service.execute_step_logic(
                session_id=session_id,
                step=step,
            )

            step_status = self._safe_str(
                step.get("status")
            ).lower().strip()

            if step_status in {
                "failed",
                "blocked",
                "waiting_approval",
            }:
                step_error = self._safe_str(
                    step.get("error")
                    or "Execution step failed."
                )
                step_title = self._safe_str(
                    step.get("title")
                    or "current step"
                )

                execution_state["steps"][
                    current_index
                ] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_failed(
                        execution_state,
                        step_index=current_index,
                        error=step_error,
                    )
                )

                execution_state = (
                    self.execution_mutation_service.append_history(
                        execution_state,
                        f"failed: {step_title}: {step_error}",
                    )
                )

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            f"Step failed: {step_title}. "
                            f"{step_error}"
                        ),
                    },
                    "execution": execution_state,
                    "step_output": step.get(
                        "result",
                        "",
                    ),
                }

            step["status"] = "completed"

            if result:
                step["result"] = result

            execution_state["steps"][current_index] = dict(step)

            steps = execution_state["steps"]

            result = step.get(
                "result",
                "",
            )

            execution_state = (
                self.execution_mutation_service.append_history(
                    execution_state,
                    f"completed: {step.get('title')}",
                )
            )

            execution_state["current_index"] = current_index + 1

            execution_state["current_step_index"] = current_index + 1

            execution_state["progress"] = current_index + 1

            execution_state["waiting"] = True

            execution_state["_execution_processing"] = False

            next_index = execution_state.get(
                "current_index",
                current_index + 1,
            )

            if next_index < len(steps):
                next_step = steps[next_index]

                execution_state["current_step"] = next_step.get("title") or ""

                execution_state["current_step_title"] = next_step.get("title") or ""
            execution_state["_execution_processing"] = False

            next_index = execution_state["current_index"]

            if next_index < len(steps):
                next_step = steps[next_index]

                execution_state["current_step"] = next_step.get("title") or ""

                execution_state["current_step_title"] = next_step.get("title") or ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": (f"Completed step: " f"{step.get('title')}"),
                },
                "execution": execution_state,
                "step_output": result,
            }

        # =========================
        # RUN ALL
        # =========================
        if command == "run_all":

            outputs = []
            loop_guard = 0

            while True:

                loop_guard += 1
                if loop_guard > 100:
                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": "Execution stopped because the run_all loop guard was reached.",
                        },
                        "execution": execution_state,
                    }

                current_index = int(execution_state.get("current_index", 0) or 0)

                if current_index >= len(steps):
                    execution_state = (
                        self.execution_mutation_service.mark_complete(
                            execution_state,
                        )
                    )
                    break

                step = steps[current_index]

                step["status"] = "running"

                execution_state["steps"][current_index] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_running(
                        execution_state,
                        step_index=current_index,
                        current_step=step.get("title") or "",
                        waiting=False,
                    )
                )
                execution_state["_execution_processing"] = False

                self._save_active_execution(
                    session_id,
                    execution_state,
                )

                result = self.execution_step_service.execute_step_logic(
                    session_id=session_id,
                    step=step,
                )

                step_status = self._safe_str(
                    step.get("status")
                ).lower().strip()

                if step_status in {
                    "failed",
                    "blocked",
                    "waiting_approval",
                }:
                    step_error = self._safe_str(
                        step.get("error")
                        or "Execution step failed."
                    )
                    step_title = self._safe_str(
                        step.get("title")
                        or "current step"
                    )

                    execution_state["steps"][
                        current_index
                    ] = dict(step)

                    execution_state = (
                        self.execution_mutation_service.mark_failed(
                            execution_state,
                            step_index=current_index,
                            error=step_error,
                        )
                    )

                    execution_state = (
                        self.execution_mutation_service.append_history(
                            execution_state,
                            (
                                f"failed: {step_title}: "
                                f"{step_error}"
                            ),
                        )
                    )

                    self._save_active_execution(
                        session_id,
                        execution_state,
                    )

                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                f"Step failed: {step_title}. "
                                f"{step_error}"
                            ),
                        },
                        "execution": execution_state,
                        "step_output": step.get(
                            "result",
                            "",
                        ),
                    }

                step["status"] = "completed"

                if result:
                    step["result"] = result

                execution_state["steps"][current_index] = dict(step)

                steps = execution_state["steps"]

                step_title = self._safe_str(step.get("title"))

                execution_state = (
                    self.execution_mutation_service.append_history(
                        execution_state,
                        f"completed: {step_title}",
                    )
                )
                execution_state["current_index"] = current_index + 1

                execution_state["progress"] = current_index + 1

                outputs.append(f"Completed step: {step_title}")

                if execution_state["current_index"] >= len(steps):
                    execution_state = (
                        self.execution_mutation_service.mark_complete(
                            execution_state,
                        )
                    )
                    break

            self._save_active_execution(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "\n".join(outputs),
                },
                "execution": execution_state,
            }

        # =========================
        # CANCEL
        # =========================
        if command == "cancel":
            execution_state = (
                self.execution_mutation_service.cancel(
                    execution_state
                )
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Execution cancelled.",
                },
                "execution": execution_state,
            }

        # =========================
        # RETRY FAILED
        # =========================
        if command == "retry_failed":
            (
                execution_state,
                failed_index,
            ) = (
                self.execution_mutation_service.prepare_failed_retry(
                    execution_state,
                )
            )

            if failed_index is None:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "No failed execution step found to retry.",
                    },
                    "execution": execution_state,
                }

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return self._process_execution_command(
                command="run_step",
                session_id=session_id,
                execution_state=execution_state,
            )