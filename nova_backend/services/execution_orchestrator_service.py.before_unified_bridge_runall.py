from __future__ import annotations


class ExecutionOrchestratorService:

    def __init__(
        self,
        execution_state_service=None,
        working_state_service=None,
        execution_mutation_service=None,
        safe_str=None,
        execution_step_service=None,
        approval_service=None,
        execution_bridge=None,
    ):

        self.execution_state_service = (
            execution_state_service
        )

        self.working_state_service = (
            working_state_service
        )

        self.execution_mutation_service = (
            execution_mutation_service
        )

        self._safe_str = safe_str

        self.execution_step_service = (
            execution_step_service
        )

        self.approval_service = (
            approval_service
        )

        self.execution_bridge = (
            execution_bridge
        )

    def _step_is_complete(self, step):
        """
        Return True only when an actual execution step is terminally
        completed.
        """
        if not isinstance(step, dict):
            return False

        status = self._safe_str(
            step.get("status")
        ).strip().lower()

        return status in {
            "complete",
            "completed",
            "done",
        }

    def _all_steps_complete(self, steps):
        """
        NOVA_EXECUTION_STEP_TRUTH_V1

        The step list is authoritative. A stale current_index, status,
        or complete flag must never complete an execution while any
        real step remains unfinished.
        """
        if not isinstance(steps, list) or not steps:
            return False

        return all(
            self._step_is_complete(step)
            for step in steps
        )

    def _first_unfinished_step_index(self, steps):
        """
        Derive execution position from actual step statuses instead of
        trusting persisted current_index.
        """
        if not isinstance(steps, list):
            return 0

        for index, step in enumerate(steps):
            if not self._step_is_complete(step):
                return index

        return len(steps)

    def process_execution(
        self,
        session_id="",
        state=None,
        command="",
    ):
        if command in {
            "next",
            "continue",
            "keep going",
            "run next",
        }:
            command = "run_step"

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

        print(
            "ORCH COMMAND DEBUG:",
            {
                "command_arg": command,
                "state_command": execution_state.get("command"),
                "selected_command": selected_command,
                "continue_request": execution_state.get(
                    "continue_request"
                ),
                "status": execution_state.get(
                    "status"
                ),
            },
            flush=True,
        )

        return self._process_execution_command(
            command=selected_command,
            session_id=session_id,
            execution_state=execution_state,
        )

    def _build_execution_context(
        self,
        execution_state,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        steps = execution_state.get("steps") or []

        context = {
            "goal": self._safe_str(
                execution_state.get("goal")
            ),
            "completed_steps": [],
            "failed_steps": [],
            "tool_results": [],
        }

        for index, step in enumerate(steps):

            if not isinstance(step, dict):
                continue

            status = self._safe_str(
                step.get("status")
            ).strip().lower()

            entry = {
                "index": index,
                "title": self._safe_str(
                    step.get("title")
                    or step.get("name")
                    or step.get("action")
                ),
                "action": self._safe_str(
                    step.get("action")
                ),
                "result": step.get("result"),
                "error": step.get("error"),
            }

            if status == "completed":
                context["completed_steps"].append(entry)

            elif status == "failed":
                context["failed_steps"].append(entry)

            metadata = step.get("execution_metadata")

            if (
                isinstance(metadata, dict)
                and metadata.get("tool_name")
            ):
                context["tool_results"].append(
                    {
                        "tool_name": metadata.get(
                            "tool_name"
                        ),
                        "success": metadata.get(
                            "success"
                        ),
                        "result": step.get("result"),
                        "error": step.get("error"),
                    }
                )

        return context

    def _should_retry_step(
        self,
        execution_state,
        step,
    ):
        recovery_strategy = (
            execution_state.get(
                "recovery_strategy"
            )
            or {}
        )

        if not isinstance(
            recovery_strategy,
            dict,
        ):
            return False

        if not recovery_strategy.get(
            "needs_recovery"
        ):
            return False

        retry_count = int(
            step.get(
                "recovery_retry_count",
                0,
            )
            or 0
        )

        return retry_count < 1

    def _build_recovery_strategy(
        self,
        execution_state,
    ):
        execution_context = (
            self._build_execution_context(
                execution_state
            )
        )

        failed_steps = (
            execution_context.get(
                "failed_steps",
                [],
            )
        )

        if not failed_steps:
            return {
                "needs_recovery": False,
                "strategy": None,
                "failed_steps": [],
            }

        latest_failure = failed_steps[-1]

        return {
            "needs_recovery": True,
            "strategy": "repair_or_retry",
            "failed_steps": failed_steps,
            "latest_failure": latest_failure,
            "goal": execution_context.get(
                "goal",
                "",
            ),
        }

    def _append_execution_event(
        self,
        execution_state,
        event,
        max_events=100,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        event = (
            event
            if isinstance(event, dict)
            else {}
        )

        events = execution_state.get("events")

        if not isinstance(events, list):
            events = []

        events.append(event)

        try:
            max_events = int(max_events)
        except Exception:
            max_events = 100

        if max_events > 0 and len(events) > max_events:
            events = events[-max_events:]

        execution_state["events"] = events

        return event

    def _build_execution_event(
        self,
        event_type,
        execution_state,
        step=None,
        message="",
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        step = (
            step
            if isinstance(step, dict)
            else {}
        )

        return {
            "type": self._safe_str(event_type),
            "message": self._safe_str(message),
            "session_id": self._safe_str(
                execution_state.get("session_id")
            ),
            "status": self._safe_str(
                execution_state.get("status")
            ),
            "current_index": (
                execution_state.get("current_index")
            ),
            "progress": execution_state.get(
                "progress"
            ),
            "step": {
                "title": self._safe_str(
                    step.get("title")
                    or step.get("name")
                ),
                "action": self._safe_str(
                    step.get("action")
                ),
                "tool_name": self._safe_str(
                    step.get("tool_name")
                ),
                "status": self._safe_str(
                    step.get("status")
                ),
            },
        }

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

        print(
            "EXECUTION INPUT DEBUG",
            {
                "session_id": session_id,
                "command": command,
                "incoming_goal": execution_state.get("goal"),
                "incoming_steps": execution_state.get("steps"),
            },
        )

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

        elif intelligence_intent == "approve_execution":
            command = "approve"

        elif intelligence_intent == "deny_execution":
            command = "deny"

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

        persisted_state_available = (
            isinstance(
                persisted_execution_state,
                dict,
            )
            and bool(persisted_execution_state)
        )

        incoming_has_state = bool(
            execution_state.get("steps")
        )

        if incoming_has_state:
            execution_state = execution_state

        elif persisted_state_available:
            execution_state = persisted_execution_state

        else:
            execution_state = {}

        print(
            "ORCH STATE BEFORE STEPS =",
            execution_state,
        )

        steps = execution_state.get("steps") or []

        if (
            not steps
            and command not in {
                "run_step",
                "run step",
            }
        ):
            return None

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
        # APPROVAL CONTROL
        # =========================
        if command in {
            "approve",
            "deny",
        }:
            state_status = self._safe_str(
                execution_state.get("status")
            ).lower().strip()

            if state_status != "waiting_approval":
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No execution step is "
                            "waiting for approval."
                        ),
                    },
                    "execution": execution_state,
                }

            if (
                current_index >= len(steps)
                or not isinstance(
                    steps[current_index],
                    dict,
                )
            ):
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "The pending approval step "
                            "could not be found."
                        ),
                    },
                    "execution": execution_state,
                }

            if self.approval_service is None:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "Execution approval service "
                            "is unavailable."
                        ),
                    },
                    "execution": execution_state,
                }

            pending_step = steps[
                current_index
            ]

            if command == "approve":
                approved_step = (
                    self.approval_service.approve_step(
                        pending_step
                    )
                )

                execution_state["steps"][
                    current_index
                ] = approved_step

                execution_state = (
                    self.execution_mutation_service.mark_approved_for_execution(
                        execution_state,
                        step_index=current_index,
                        current_step=approved_step,
                    )
                )
                execution_state["command"] = (
                    "run_step"
                )

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return (
                    self._process_execution_command(
                        command="run_step",
                        session_id=session_id,
                        execution_state=(
                            execution_state
                        ),
                    )
                )

            denied_step = (
                self.approval_service.deny_step(
                    pending_step
                )
            )

            execution_state["steps"][
                current_index
            ] = denied_step

            execution_state = (
                self.execution_mutation_service.mark_approval_denied(
                    execution_state,
                    error="Execution approval denied.",
                )
            )

            execution_state = (
                self.execution_mutation_service.append_history(
                    execution_state,
                    "approval denied",
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
                    "text": (
                        "Execution approval denied. "
                        "The protected step was not run."
                    ),
                },
                "execution": execution_state,
            }


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

            # Derive the current position from the actual step list.
            # Never trust a stale persisted current_index.
            current_index = (
                self._first_unfinished_step_index(
                    steps
                )
            )

            execution_state["current_index"] = current_index

            if self._all_steps_complete(steps):

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


            print(
                "AFTER RELOAD DEBUG =",
                {
                    "current_index": refreshed_execution.get(
                        "current_index"
                    ),
                    "current_step": refreshed_execution.get(
                        "current_step"
                    ),
                    "step0_status": (
                        refreshed_execution.get("steps", [{}])[0].get(
                            "status"
                        )
                        if refreshed_execution.get("steps")
                        else None
                    ),
                    "step1_status": (
                        refreshed_execution.get("steps", [{}, {}])[1].get(
                            "status"
                        )
                        if len(
                            refreshed_execution.get("steps", [])
                        ) > 1
                        else None
                    ),
                },
                flush=True,
            )

            refreshed_steps = (
                refreshed_execution.get("steps")
                or []
            )

            if not isinstance(
                refreshed_steps,
                list,
            ) or current_index >= len(refreshed_steps):
                refreshed_steps = steps

            # Re-derive from refreshed step truth before deciding
            # whether the execution is actually complete.
            current_index = (
                self._first_unfinished_step_index(
                    refreshed_steps
                )
            )

            execution_state["current_index"] = current_index

            if self._all_steps_complete(refreshed_steps):
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

            step = refreshed_steps[current_index]

            execution_state = refreshed_execution
            steps = refreshed_steps
            execution_state["current_index"] = current_index            
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

            print(
                "CONTINUE REQUEST DEBUG =",
                execution_state.get("continue_request"),
                execution_state.get("command"),
                execution_state.get("current_index"),
            )

            if (
                execution_state.get("continue_request")
                or command == "continue"
            ):
                execution_state = (
                    self.execution_mutation_service.clear_continue_request(
                        execution_state
                    )
                )

                execution_state = (
                    self.execution_mutation_service.mark_running(
                        execution_state,
                        step_index=current_index,
                        current_step=(
                            step.get("title")
                            if isinstance(step, dict)
                            else None
                        ),
                        waiting=False,
                    )
                )

                if step:
                    execution_state = (
                        self.execution_mutation_service.mark_step_running(
                            execution_state,
                            step_index=current_index,
                            step=step,
                        )
                    )

                    step = dict(
                        execution_state["steps"][current_index]
                    )

                execution_event = (
                    self._build_execution_event(
                        "step_started",
                        execution_state,
                        step=step,
                        message=(
                            f"Starting step: "
                            f"{step.get('title') or step.get('action')}"
                        ),
                    )
                )

                self._append_execution_event(
                    execution_state,
                    execution_event,
                )

            self._save_execution_state(
                session_id,
                execution_state,
            )



            execution_state = (
                self.execution_mutation_service.mark_step_running(
                    execution_state,
                    step_index=current_index,
                    step=step,
                )
            )

            step = dict(
                execution_state["steps"][current_index]
            )

            execution_state = (
                self.execution_mutation_service.mark_running(
                    execution_state,
                    step_index=current_index,
                    current_step=step.get("title") or "",
                    waiting=False,
                )
            )

            print(
                "DEBUG BEFORE EXECUTE_STEP_LOGIC",
                {
                    "has_execution_step_service": self.execution_step_service is not None,
                    "step": step,
                },
                flush=True,
            )

            print(
                "DEBUG STEP BEFORE EXECUTE_STEP_LOGIC =",
                {
                    "title": step.get("title"),
                    "action": step.get("action"),
                    "target_file": step.get("target_file"),
                    "keys": list(step.keys()),
                    "full": step,
                },
                flush=True,
            )

            result = self.execution_step_service.execute_step_logic(
                session_id=session_id,
                step=step,
            )

            print(
                "DEBUG AFTER EXECUTE_STEP_LOGIC",
                result,
                flush=True,
            )

            step_status = self._safe_str(
                step.get("status")
            ).lower().strip()

            if step_status == "waiting_approval":
                approval_reason = self._safe_str(
                    step.get("error")
                    or (
                        "Approval required "
                        "before execution."
                    )
                )

                step_title = self._safe_str(
                    step.get("title")
                    or "current step"
                )

                execution_state["steps"][
                    current_index
                ] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_waiting_approval(
                        execution_state,
                        step_index=current_index,
                        reason=approval_reason,
                    )
                )

                execution_state = (
                    self.execution_mutation_service.append_history(
                        execution_state,
                        (
                            "waiting approval: "
                            f"{step_title}"
                        ),
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
                        "text": (
                            "Approval required: "
                            f"{step_title}. "
                            f"{approval_reason}"
                        ),
                    },
                    "execution": execution_state,
                    "step_output": "",
                }

            if step_status in {
                "failed",
                "blocked",
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

            normalized_result = (
                result.get("result")
                if isinstance(result, dict)
                else result
            )

            execution_state = (
                self.execution_mutation_service.mark_step_completed(
                    execution_state,
                    step_index=current_index,
                    step=step,
                    result=normalized_result,
                )
            )

            step = dict(
                execution_state["steps"][current_index]
            )

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

            execution_state = (
                self.execution_mutation_service.advance_after_step_completion(
                    execution_state,
                    completed_index=current_index,
                )
            )

            steps = execution_state.get("steps") or []

            next_index = int(
                execution_state.get(
                    "current_index",
                    len(steps),
                )
                or 0
            )

            if next_index >= len(steps):
                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state
                    )
                )

            else:
                next_step = steps[next_index]

                execution_state = (
                    self.execution_mutation_service.mark_step_pending(
                        execution_state,
                        step_index=next_index,
                        step=next_step,
                    )
                )

                next_step = dict(
                    execution_state["steps"][next_index]
                )

                execution_state = (
                    self.execution_mutation_service.mark_running(
                        execution_state,
                        step_index=next_index,
                        current_step=(
                            next_step.get("title")
                            or next_step.get("action")
                            or ""
                        ),
                        waiting=True,
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
                    "text": (
                        f"Completed step: "
                        f"{step.get('title')}"
                    ),
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
                            "text": (
                                "Execution stopped because "
                                "the run_all loop guard was reached."
                            ),
                        },
                        "execution": execution_state,
                    }

                step_result = (
                    self._process_execution_command(
                        command="run_step",
                        session_id=session_id,
                        execution_state=execution_state,
                    )
                )

                if not isinstance(step_result, dict):

                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                "Execution stopped because "
                                "run_step returned no execution result."
                            ),
                        },
                        "execution": execution_state,
                    }

                execution_state = (
                    step_result.get("execution")
                    or execution_state
                )

                assistant_message = (
                    step_result.get("assistant_message")
                    or {}
                )

                message_text = self._safe_str(
                    assistant_message.get("text")
                )

                if message_text:
                    outputs.append(message_text)

                if not step_result.get("ok"):

                    status = self._safe_str(
                        execution_state.get("status")
                    ).lower().strip()

                    print(
                        "RUN_ALL FAILURE DEBUG =",
                        {
                            "status": status,
                            "current_index": execution_state.get(
                                "current_index"
                            ),
                            "step_result_ok": step_result.get("ok"),
                            "step_result": step_result,
                            "steps": [
                                {
                                    "index": index,
                                    "title": item.get("title"),
                                    "status": item.get("status"),
                                }
                                for index, item in enumerate(
                                    execution_state.get("steps") or []
                                )
                                if isinstance(item, dict)
                            ],
                        },
                        flush=True,
                    )

                    if status in {
                        "failed",
                        "blocked",
                    }:

                        steps = (
                            execution_state.get("steps")
                            or []
                        )

                        next_index = (
                            self._first_unfinished_step_index(
                                steps
                            )
                        )

                        if next_index is not None:

                            execution_state["current_index"] = (
                                next_index
                            )

                            execution_state["status"] = (
                                "running"
                            )

                            self._save_execution_state(
                                session_id,
                                execution_state,
                            )

                            continue

                    self._save_execution_state(
                        session_id,
                        execution_state,
                    )

                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": "\n".join(outputs),
                        },
                        "execution": execution_state,
                    }


                status = self._safe_str(
                    execution_state.get("status")
                ).lower().strip()

                if status == "waiting_approval":

                    self._save_execution_state(
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

                if status in {
                    "complete",
                    "completed",
                }:

                    self._save_execution_state(
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

                if status in {
                    "failed",
                    "cancelled",
                    "canceled",
                }:

                    self._save_execution_state(
                        session_id,
                        execution_state,
                    )

                    return {
                        "ok": False,
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

            execution_state = (
                self.execution_mutation_service.reset(
                    execution_state
                )
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            try:
                from nova_backend.services.chat_execution_service import (
                    chat_execution_service,
                )

                if hasattr(
                    chat_execution_service,
                    "cancel",
                ):
                    execution_state = (
                        chat_execution_service.cancel(
                            session_id
                        )
                    )

                else:
                    chat_execution_service.reset(
                        session_id
                    )

            except Exception as legacy_reset_error:
                print(
                    "LEGACY EXECUTION RESET FAILED:",
                    legacy_reset_error,
                )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Execution cancelled.",
                },
                "execution": execution_state,
                "execution_state": execution_state,
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



