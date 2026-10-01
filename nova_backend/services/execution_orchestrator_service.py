from __future__ import annotations

import mimetypes
from pathlib import Path


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
        project_workspace_service=None,
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
        self.project_workspace_service = (
            project_workspace_service
        )

    def _register_project_file(
        self,
        execution_state,
        step,
    ):
        print(
            "[PROJECT FILE REGISTRATION CHECK]",
            {
                "project_id": (
                    execution_state.get("project_id")
                    if isinstance(execution_state, dict)
                    else None
                ),
                "action": (
                    step.get("action")
                    if isinstance(step, dict)
                    else None
                ),
                "next_action": (
                    step.get("next_action")
                    if isinstance(step, dict)
                    else None
                ),
                "target_file": (
                    step.get("target_file")
                    if isinstance(step, dict)
                    else None
                ),
            },
            flush=True,
        )

        if self.project_workspace_service is None:
            return None

        if not isinstance(execution_state, dict):
            return None

        project_id = execution_state.get("project_id")
        if not project_id:
            return None

        if not isinstance(step, dict):
            return None

        action = str(
            step.get("action")
            or ""
        ).strip().lower()

        if action not in {
            "create",
            "create_file",
            "write",
            "write_file",
            "modify",
            "modify_file",
            "update",
            "patch",
            "replace",
            "implement",
            "build",
            "generate",
        }:
            return None

        target_file = (
            step.get("target_file")
            or step.get("file_path")
            or step.get("path")
        )

        if not target_file:
            return None

        source = Path(
            str(target_file)
        ).expanduser()

        if not source.is_file():
            return None

        original_name = source.name
        size = source.stat().st_size
        mime_type = (
            mimetypes.guess_type(
                original_name
            )[0]
            or "application/octet-stream"
        )

        return self.project_workspace_service.add_file(
            project_id,
            original_name,
            str(source),
            size,
            mime_type,
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

    def _unfinished_project_tasks(self, execution_state):
        if (
            isinstance(execution_state, dict)
            and not execution_state.get("project_id")
            and self.project_workspace_service is not None
        ):
            active_project = (
                self.project_workspace_service.get_active_project()
            )

            if (
                isinstance(active_project, dict)
                and active_project.get("id")
            ):
                execution_state["project_id"] = (
                    active_project["id"]
                )

        if self.project_workspace_service is None:
            return ["Project workspace service unavailable"]

        project_id = (
            execution_state.get("project_id")
            if isinstance(execution_state, dict)
            else None
        )

        if not project_id:
            active_project = (
                self.project_workspace_service.get_active_project()
        )

            if isinstance(active_project, dict):
                project_id = active_project.get("id")

        if not project_id:
            return ["Active project could not be resolved"]

        project = self.project_workspace_service.get_project(
            project_id
        )

        if not isinstance(project, dict):
            return [
                f"Project could not be loaded: {project_id}"
            ]

        if hasattr(
            self.project_workspace_service,
            "refresh_project",
        ):
            project = self.project_workspace_service.refresh_project(
                project_id
            )
        else:
            project = self.project_workspace_service.get_project(
                project_id
            )

        print(
            "[ORCHESTRATOR FRESH PROJECT TASKS]",
            [
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "status": task.get("status"),
                }
                for task in project.get("tasks", [])
                if isinstance(task, dict)
            ],
            flush=True,
        )

        completed_statuses = {
            "completed",
            "complete",
            "done",
            "success",
            "succeeded",
            "finished",
        }

        unfinished = []

        for task in project.get("tasks", []):

            if not isinstance(task, dict):
                continue

            status = str(
                task.get("status") or ""
            ).strip().lower()

            print(
                "[ORCHESTRATOR TASK STATUS CHECK]",
                {
                    "title": task.get("title"),
                    "status": status,
                },
                flush=True,
            )

            if status in completed_statuses:
                continue

            title = str(
                task.get("title")
                or task.get("id")
                or "Untitled task"
            ).strip()

            action = str(
                task.get("action") or ""
            ).strip().lower()

            execution_mode = str(
                task.get("execution_mode") or ""
            ).strip().lower()

            has_execution_payload = bool(
                task.get("steps")
                or task.get("content")
                or task.get("code")
                or task.get("replacement")
                or task.get("command")
                or task.get("target_file")
                or task.get("target_files")
            )

            if not has_execution_payload:
                print(
                    "[IGNORING NON-EXECUTABLE PROJECT TASK]",
                    {
                        "title": title,
                        "status": status,
                    },
                    flush=True,
                )
                continue

            unfinished.append(title)

        return unfinished

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

        if (
            not execution_state.get("project_id")
            and self.project_workspace_service is not None
        ):
            active_project = (
                self.project_workspace_service.get_active_project()
            )

            if (
                isinstance(active_project, dict)
                and active_project.get("id")
            ):
                execution_state["project_id"] = (
                    active_project["id"]
                )

        if (
            not execution_state.get("project_id")
            and self.project_workspace_service is not None
        ):
            active_project = (
                self.project_workspace_service.get_active_project()
            )

            if (
                isinstance(active_project, dict)
                and active_project.get("id")
            ):
                execution_state["project_id"] = (
                    active_project["id"]
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


        if command in {
            "yes",
            "y",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "go ahead",
            "do it",
            "approve",
            "approved",
        }:
            command = "approve"

        elif command in {
            "no",
            "n",
            "nope",
            "deny",
            "denied",
            "stop",
        }:
            command = "deny"

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

        steps = (
            execution_state.get("steps")
            or []
        )

        if incoming_has_state:
            if (
                persisted_state_available
                and command in {
                    "run_step",
                    "run step",
                    "approve",
                }
                and str(
                    persisted_execution_state.get(
                        "status",
                        "",
                    )
                ).strip().lower()
                == "waiting_approval"
            ):
                preserved_index = int(
                    persisted_execution_state.get(
                        "current_index",
                        execution_state.get(
                            "current_index",
                            0,
                        ),
                    )
                    or 0
                )

                persisted_steps = (
                    persisted_execution_state.get(
                        "steps"
                    )
                    or []
                )

                if (
                    isinstance(
                        persisted_steps,
                        list,
                    )
                    and 0 <= preserved_index < len(
                        persisted_steps
                    )
                    and isinstance(
                        steps,
                        list,
                    )
                    and 0 <= preserved_index < len(
                        steps
                    )
                    and isinstance(
                        persisted_steps[
                            preserved_index
                        ],
                        dict,
                    )
                    and isinstance(
                        steps[
                            preserved_index
                        ],
                        dict,
                    )
                ):
                    incoming_step = steps[
                        preserved_index
                    ]

                    persisted_step = persisted_steps[
                        preserved_index
                    ]

                    persisted_status = str(
                        persisted_step.get("status", "")
                    ).strip().lower()

                    persisted_complete = (
                        persisted_status in {
                            "completed",
                            "complete",
                            "success",
                        }
                        or persisted_step.get("complete") is True
                    )

                    if persisted_complete:
                        # Preserve completed work; never restore
                        # stale approval state over it.
                        for key in (
                            "status",
                            "waiting",
                            "next_action",
                            "result",
                            "complete",
                            "execution_metadata",
                            "content",
                            "code",
                        ):
                            if key in persisted_step:
                                incoming_step[key] = (
                                    persisted_step[key]
                                )

                        incoming_step["status"] = "completed"
                        incoming_step["complete"] = True
                        incoming_step["waiting"] = False
                        incoming_step["approved"] = True
                        incoming_step["approval_required"] = False
                        incoming_step["approval_status"] = None
                        incoming_step["requires_approval"] = False
                        incoming_step.pop("error", None)

                    else:
                        for key in (
                            "status",
                            "waiting",
                            "approved",
                            "approval_required",
                            "approval_status",
                            "next_action",
                            "result",
                            "complete",
                            "execution_metadata",
                            "content",
                            "code",
                        ):
                            if key in persisted_step:
                                incoming_step[key] = (
                                    persisted_step[key]
                                )

                execution_state["status"] = (
                    persisted_execution_state.get(
                        "status"
                    )
                )
                execution_state["waiting"] = (
                    persisted_execution_state.get(
                        "waiting",
                        True,
                    )
                )
                execution_state[
                    "approval_status"
                ] = persisted_execution_state.get(
                    "approval_status",
                    "pending",
                )
                execution_state["current_index"] = (
                    preserved_index
                )

                print(
                    "[CONTINUE APPROVAL STATE PRESERVED]",
                    {
                        "status": execution_state.get(
                            "status"
                        ),
                        "waiting": execution_state.get(
                            "waiting"
                        ),
                        "approval_status": execution_state.get(
                            "approval_status"
                        ),
                        "current_index": preserved_index,
                    },
                    flush=True,
                )

            else:
                execution_state = execution_state

            if (
                execution_state.get(
                    "continue_request"
                )
                is True
            ):
                print(
                    "[CONTINUE REQUEST STATE PRESERVED]",
                    {
                        "status": execution_state.get("status"),
                        "waiting": execution_state.get("waiting"),
                        "approval_status": execution_state.get(
                            "approval_status"
                        ),
                    },
                    flush=True,
                )

        elif persisted_state_available:
            execution_state = persisted_execution_state

        else:
            execution_state = {}

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

        # NORMALIZE APPROVAL STATE FROM STEP TRUTH
        if isinstance(steps, list) and current_index < len(steps):
            current_step = steps[current_index]



            if isinstance(current_step, dict):
                if (
                    current_step.get("approved") is True
                    and current_step.get("approval_required") is False
                ):
                    execution_state["status"] = "ready"
                    execution_state["waiting"] = False
                    execution_state["approval_status"] = "approved"

            if (
                current_step.get("approved") is True
                and current_step.get("approval_required") is False
                and current_step.get("result")
            ):
                current_step["status"] = "completed"
                current_step["waiting"] = False
                current_step["complete"] = True

                if isinstance(current_step.get("execution_metadata"), dict):
                    current_step["execution_metadata"]["success"] = True
                    current_step["execution_metadata"]["waiting"] = False
                    current_step["execution_metadata"]["waiting_approval"] = False





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

            if (
                command == "approve"
                and current_index >= len(steps)
            ):
                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "Execution is already complete."
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
                or (
                    state_status != "waiting_approval"
                    and not (
                        command == "approve"
                        and (
                            steps[current_index].get("approved")
                            is True
                            or steps[current_index].get(
                                "approval_required"
                            )
                            is True
                            or steps[current_index].get(
                                "requires_approval"
                            )
                            is True
                            or self._safe_str(
                                steps[current_index].get(
                                    "approval_status"
                                )
                            ).lower().strip()
                            in {
                                "pending",
                                "waiting_approval",
                                "awaiting_approval",
                                "approval_required",
                            }
                        )
                    )
                )
            ):
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

                # Approval releases the SAME step.
                # Do not advance past the approved mutation step.
                execution_state["current_index"] = (
                    current_index
                )
                execution_state["current_step_index"] = (
                    current_index
                )
                execution_state["command"] = "run_step"

                print(
                    "[APPROVAL RELEASE SAME STEP]",
                    {
                        "approved_index": current_index,
                        "current_index": execution_state.get(
                            "current_index"
                        ),
                        "step_count": len(
                            execution_state.get("steps") or []
                        ),
                        "step_status": approved_step.get(
                            "status"
                        ),
                        "approval_status": approved_step.get(
                            "approval_status"
                        ),
                        "approval_required": approved_step.get(
                            "approval_required"
                        ),
                    },
                    flush=True,
                )

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return (
                    self._process_execution_command(
                        command="run_step",
                        session_id=session_id,
                        execution_state=execution_state,
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

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": (
                        "Execution step denied."
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

            # Preserve explicit resume position.
            # Only recover index when persisted position is invalid.

            persisted_index = int(
                execution_state.get(
                    "current_index",
                    0,
                )
                or 0
            )

            if (
                0 <= persisted_index < len(steps)
                and isinstance(
                    steps[persisted_index],
                    dict,
                )
                and steps[persisted_index].get("status")
                not in {
                    "completed",
                    "complete",
                    "done",
                }
            ):
                current_index = persisted_index

            else:
                current_index = (
                    self._first_unfinished_step_index(
                        steps
                    )
                )

            execution_state["current_index"] = current_index
            if self._all_steps_complete(steps):
                unfinished_tasks = self._unfinished_project_tasks(
                    execution_state
                )

                if unfinished_tasks:
                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                "Execution steps are complete, but "
                                "project tasks remain unfinished: "
                                + ", ".join(unfinished_tasks)
                                + ". Add executable steps or complete "
                                "the tasks before finishing."
                            ),
                        },
                        "execution": execution_state,
                    }

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
            # Preserve the execution state supplied by the caller.
            # Persisted state is only a fallback when the incoming
            # state does not contain a usable step list.
            refreshed_execution = execution_state

            incoming_steps = (
                execution_state.get("steps")
                or []
            )

            refreshed_steps = incoming_steps

            if not isinstance(
                refreshed_steps,
                list,
            ) or current_index >= len(
                refreshed_steps
            ):
                persisted_refresh = (
                    self.execution_state_service.get_execution_state(
                        session_id
                    )
                    or {}
                )

                persisted_refresh_steps = (
                    persisted_refresh.get("steps")
                    or []
                    if isinstance(persisted_refresh, dict)
                    else []
                )

                if isinstance(
                    persisted_refresh_steps,
                    list,
                 ) and current_index < len(
                    persisted_refresh_steps
                ):
                    refreshed_execution = persisted_refresh
                    refreshed_steps = persisted_refresh_steps

            execution_state["current_index"] = current_index

            if self._all_steps_complete(refreshed_steps):
                unfinished_tasks = self._unfinished_project_tasks(
                    execution_state
                )

                if unfinished_tasks:
                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                "Execution steps are complete, but "
                                "project tasks remain unfinished: "
                                + ", ".join(unfinished_tasks)
                                + ". Add executable steps or complete "
                                "the tasks before finishing."
                            ),
                        },
                        "execution": execution_state,
                    }

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

            original_step = (
                steps[current_index]
                if current_index < len(steps)
                and isinstance(steps[current_index], dict)
                else {}
            )

            refreshed_step = (
                refreshed_steps[current_index]
                if (
                    current_index < len(refreshed_steps)
                    and isinstance(
                        refreshed_steps[current_index],
                        dict,
                    )
                )
                else {}
            )

            step = {
                **refreshed_step,
                **original_step,
            }

            # Preserve caller-supplied execution context
            # when the refreshed/persisted step does not have it.
            for preserved_key in (
                "project_context",
                "goal",
                "content",
                "target_file",
                "target_files",
                "code",
                "replacement",
                "command",
                "execution_file",
            ):
                original_value = (
                    original_step.get(preserved_key)
                    if isinstance(original_step, dict)
                    else None
                )
                refreshed_value = (
                    refreshed_step.get(preserved_key)
                    if isinstance(refreshed_step, dict)
                    else None
                )

                if original_value and not refreshed_value:
                    step[preserved_key] = original_value

                    if (
                        isinstance(refreshed_steps, list)
                        and current_index < len(refreshed_steps)
                        and isinstance(
                            refreshed_steps[current_index],
                            dict,
                        )
                    ):
                        refreshed_steps[current_index][
                            preserved_key
                        ] = original_value

            if isinstance(execution_state.get("steps"), list):
                execution_state["steps"][current_index] = dict(
                    step
                )



            steps = refreshed_steps

            execution_state["current_index"] = current_index

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

            step_action = str(
                step.get("action") or ""
            ).strip()

            step_target = str(
                step.get("target_file")
                or step.get("execution_file")
                or ""
            ).strip()

            step_command = str(
                step.get("command") or ""
            ).strip()

            if not (
                step_action
                or step_target
                or step_command
            ):
                print(
                    "[ORCHESTRATOR SKIP INVALID STEP]",
                    {
                        "id": step.get("id"),
                        "title": step.get("title"),
                        "action": step_action,
                    },
                    flush=True,
                )

                current_index += 1
                execution_state["current_index"] = current_index

                return {
                    "ok": False,
                    "status": "blocked",
                    "message": (
                        "Step blocked: missing execution contract."
                    ),
                    "execution": execution_state,
                }

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

            # =========================
            # MUTATION PAYLOAD VALIDATION GATE
            # =========================
            # Do not send incomplete implementation steps
            # into approval/execution flow.
            # Missing target/content means clarification,
            # not approval.

            if (
                self._safe_str(
                    step.get("action")
                ).lower().strip()
                == "implement"
                and step.get("next_action")
                != "execute_general_task"
                and (
                    not self._safe_str(
                        step.get("target_file")
                    ).strip()
                    or not (
                        self._safe_str(
                            step.get("content")
                        ).strip()
                        or self._safe_str(
                            step.get("file_content")
                        ).strip()
                        or self._safe_str(
                            step.get("generated_content")
                        ).strip()
                        or self._safe_str(
                            (
                                step.get("payload")
                                or {}
                            ).get("content")
                        ).strip()
                    )
                )
                and not (
                    step.get("text")
                    or step.get("description")
                    or step.get("goal")
                )
            ):

                step["status"] = "waiting"
                step["waiting"] = True
                step["needs_clarification"] = True
                step["clarification"] = (
                    "Please provide the target file path "
                    "and the content to create or modify."
                )

                execution_state["steps"][current_index] = dict(step)

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": step["clarification"],
                    },
                    "execution": execution_state,
                    "step_output": "",
                }

            # =========================
            # NORMALIZE CREATE MUTATION
            # =========================
            if (
                self._safe_str(
                    step.get("action")
                ).lower().strip()
                == "create"
                and self._safe_str(
                    step.get("target_file")
                ).strip()
                and self._safe_str(
                    step.get("content")
                    or step.get("generated_content")
                    or step.get("file_content")
                ).strip()
            ):
                content = (
                    step.get("content")
                    or step.get("generated_content")
                    or step.get("file_content")
                )

                step["file_content"] = content
                step["mutation_mode"] = "create"
                step["execution_mode"] = "mutation"
                step["mutation_ready"] = True
                step["payload_required"] = False
                step["next_action"] = "execute"

                if not step.get("payload"):
                    step["payload"] = {
                        "action": "create",
                        "target_file": step.get(
                            "target_file"
                        ),
                        "content": content,
                    }

                execution_state["steps"][current_index] = dict(step)

            # =========================
            # PRE-EXECUTION APPROVAL GATE
            # =========================

            step_action = self._safe_str(
                step.get("action")
            ).lower().strip()

            # Explicit file mutations with a concrete target and
            # content do not inherit stale approval flags.
            explicit_file_mutation_ready = bool(
                step_action in {
                    "implement",
                    "create",
                    "write",
                    "create_file",
                    "write_file",
                }
                and self._safe_str(
                    step.get("target_file")
                ).strip()
                and self._safe_str(
                    step.get("content")
                    or step.get("generated_content")
                    or step.get("file_content")
                ).strip()
                and (
                    step.get("mutation_ready") is True
                    or step.get("mutation_mode") == "create"
                    or step.get("payload_required") is False
                    or (
                        step.get("target_file")
                        and (
                            step.get("content")
                            or step.get("generated_content")
                            or step.get("file_content")
                        )
                    )
                )
            )

            step_status = self._safe_str(
                step.get("status")
            ).lower().strip()

            if explicit_file_mutation_ready:
                step["requires_approval"] = False
                step["approval_required"] = False
                step["approval_status"] = None
                if step_status in {
                    "waiting_approval",
                    "awaiting_approval",
                    "approval_required",
                }:
                    step["status"] = "pending"
                    step_status = "pending"

            mutation_actions = {
                "implement",
                "create",
                "write",
                "modify",
                "update",
                "patch",
                "replace",
                "delete",
                "remove",
                "execute",
            }

            approval_required = (
                step_action in mutation_actions
                and (
                    step.get("requires_approval") is True
                    or step.get("approval_required") is True
                    or step_status in {
                        "waiting_approval",
                        "awaiting_approval",
                        "approval_required",
                    }
                )
            )

            if step_action not in mutation_actions:
                step["requires_approval"] = False
                step["approval_required"] = False
                step["approval_status"] = None

            if (
                str(
                    execution_state.get("command")
                    or ""
                ).strip().lower()
                == "approve"
            ):
                approval_required = False

                step["requires_approval"] = False
                step["approval_required"] = False
                step["approval_status"] = "approved"

            print(
                "[APPROVAL GATE FINAL CHECK]",
                {
                    "command": execution_state.get("command"),
                    "step_action": step_action,
                    "step_status": step_status,
                    "requires_approval": step.get("requires_approval"),
                    "approval_required_field": step.get("approval_required"),
                    "approval_status": step.get("approval_status"),
                    "approval_required_computed": approval_required,
                },
                flush=True,
            )


            if approval_required:
                approval_reason = self._safe_str(
                    step.get("error")
                    or "Approval required before execution."
                )

                execution_state["steps"][current_index] = dict(step)

                execution_state = (
                    self.execution_mutation_service.mark_waiting_approval(
                        execution_state,
                        step_index=current_index,
                        reason=approval_reason,
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
                            f"Approval required: "
                            f"{step.get('title')}. "
                            f"{approval_reason}"
                        ),
                    },
                    "execution": execution_state,
                    "step_output": "",
                }

            result = self.execution_step_service.execute_step_logic(
                session_id=session_id,
                step=step,
            )

            # A successful executor result takes precedence over
            # stale approval state left on the original step.
            if (
                isinstance(result, dict)
                and str(
                    result.get("status") or ""
                ).lower().strip() == "completed"
            ):
                completed_step = dict(step)
                completed_step.update(result)

                for preserved_key in (
                    "action",
                    "description",
                    "execution_file",
                    "target_file",
                    "target_files",
                    "command",
                    "content",
                    "code",
                    "replacement",
                    "tool_name",
                ):
                    original_value = step.get(preserved_key)
                    result_value = result.get(preserved_key)

                    if original_value and not result_value:
                        completed_step[preserved_key] = original_value

                completed_step["status"] = "completed"
                completed_step["complete"] = True
                completed_step["waiting"] = False
                completed_step["requires_approval"] = False
                completed_step["approval_required"] = False
                completed_step["approval_status"] = None
                completed_step.pop("error", None)

                step = completed_step

            # ---------------------------------
            # WAITING / CLARIFICATION STOP GATE
            # ---------------------------------
            # Executor waiting states are not
            # completed steps. Preserve themand
            # return control to the user.


            if (
                isinstance(result, dict)
                and (
                    result.get("waiting")
                    or result.get("status") == "waiting"
                )
                and result.get("status") != "waiting_approval"
                and not (
                    isinstance(step, dict)
                    and str(
                        step.get("action") or ""
                    ).lower() in {
                        "implement",
                        "modify",
                        "create_file",
                        "write_file",
                    }
                    and (
                        step.get("target_file")
                        or step.get("target_files")
                        or step.get("goal")
                        or execution_state.get("goal")
                    )
                )
            ):
                waiting_step = dict(result)

                waiting_step["status"] = "waiting"
                waiting_step["waiting"] = True
                waiting_step["complete"] = False

                execution_state["steps"][current_index] = (
                    waiting_step
                )

                execution_state["status"] = "waiting"
                execution_state["waiting"] = True
                execution_state["complete"] = False
                execution_state["current_step"] = waiting_step

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            waiting_step.get("clarification")
                            or waiting_step.get("result")
                            or "Waiting for additional information."
                        ),
                    },
                    "execution": execution_state,
                    "step_output": waiting_step.get(
                        "result",
                        "",
                    ),
                }

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

            # ---------------------------------
            # PRESERVE WAITING / CLARIFICATION STATE
            # ---------------------------------
            # Executor waiting is not completion.
            # Do not advance the pipeline until the
            # required input is supplied.

            if (
                isinstance(result, dict)
                and str(result.get("status") or "").lower().strip() != "completed"
                and (
                    result.get("waiting") is True
                    or result.get("status") == "waiting"
                    or result.get("needs_clarification") is True
                )
                and not (
                    isinstance(step, dict)
                    and str(
                        step.get("action") or ""
                    ).lower() in {
                        "implement",
                        "modify",
                        "create_file",
                        "write_file",
                    }
                    and (
                        step.get("target_file")
                        or step.get("target_files")
                        or step.get("goal")
                        or execution_state.get("goal")
                    )
                )
            ):
                execution_state["steps"][current_index] = dict(result)

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            result.get("clarification")
                            or result.get("error")
                            or "Waiting for additional information."
                        ),
                    },
                    "execution": execution_state,
                    "step_output": result.get(
                        "result",
                        "",
                    ),
                }

            # ---------------------------------
            # WAITING STATE HANDOFF
            # ---------------------------------
            # AI clarification / missing context is
            # not a completed step. Persist waiting
            # state and stop execution here.
            if (
                isinstance(result, dict)
                and result.get("waiting")
                and str(result.get("status") or "").lower().strip() != "completed"
            ):
                waiting_step = dict(step)

                waiting_step["status"] = "waiting"
                waiting_step["waiting"] = True
                waiting_step["result"] = result.get(
                    "result",
                    "",
                )
                waiting_step["clarification"] = result.get(
                    "clarification",
                    "",
                )

                execution_state["steps"][current_index] = (
                    waiting_step
                )

                execution_state["status"] = "waiting"
                execution_state["waiting"] = True
                execution_state["complete"] = False
                execution_state["current_step"] = waiting_step

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            waiting_step.get("clarification")
                            or waiting_step.get("result")
                            or "Waiting for additional information."
                        ),
                    },
                    "execution": execution_state,
                    "step_output": waiting_step.get(
                        "result",
                        "",
                    ),
                }

            if (
                isinstance(result, dict)
                and str(result.get("status") or "").lower().strip()
                == "completed"
            ):
                completed_step = dict(step)
                completed_step.update(result)

                for preserved_key in (
                    "action",
                    "description",
                    "execution_file",
                    "target_file",
                    "target_files",
                    "command",
                    "content",
                    "code",
                    "replacement",
                    "tool_name",
                ):
                    original_value = step.get(preserved_key)
                    result_value = result.get(preserved_key)

                    if original_value and not result_value:
                        completed_step[preserved_key] = original_value

                completed_step["status"] = "completed"
                completed_step["complete"] = True
                completed_step["waiting"] = False
                completed_step["requires_approval"] = False
                completed_step["approval_required"] = False
                completed_step["approval_status"] = None
                completed_step.pop("error", None)

                step = completed_step

            normalized_result = (
                result.get("result")
                if isinstance(result, dict)
                else result
            )


            # ---------------------------------
            # BLOCK TASKS WITH NO EXECUTABLE INSTRUCTIONS
            # ---------------------------------
            if isinstance(step, dict):
                executable_fields = (
                    "action",
                    "execution_file",
                    "target_file",
                    "target_files",
                    "command",
                    "content",
                    "code",
                    "replacement",
                    "tool_name",
                )

                has_executable_instructions = any(
                    step.get(field)
                    for field in executable_fields
                )

                if not has_executable_instructions:
                    waiting_step = dict(step)
                    waiting_step["status"] = "waiting"
                    waiting_step["waiting"] = True
                    waiting_step["complete"] = False
                    waiting_step["needs_clarification"] = True
                    waiting_step["clarification"] = (
                        "I’m ready to continue, but I need a few more "
                        "details before I can complete this task.\n\n"
                        f"Current task: {step.get('title') or 'Untitled task'}\n\n"
                        "Please tell me what action you want me to take "
                        "and include any required details "
                        "(files, content, or expected result)."
                    )

                    execution_state["steps"][current_index] = (
                        waiting_step
                    )
                    execution_state["status"] = "waiting"
                    execution_state["waiting"] = True
                    execution_state["complete"] = False
                    execution_state["current_step"] = waiting_step

                    self._save_execution_state(
                        session_id,
                        execution_state,
                    )

                    return {
                        "ok": True,
                        "assistant_message": {
                            "role": "assistant",
                            "text": waiting_step["clarification"],
                        },
                        "execution": execution_state,
                        "step_output": "",
                    }

            # ---------------------------------
            # PREVENT STATE DOWNGRADE
            # ---------------------------------
            # Do not allow stale pending template steps
            # to overwrite a live running/waiting step.

            existing_step = None

            try:
                existing_steps = execution_state.get("steps") or []

                if (
                    isinstance(existing_steps, list)
                    and 0 <= current_index < len(existing_steps)
                    and isinstance(existing_steps[current_index], dict)
                ):
                    existing_step = existing_steps[current_index]

            except Exception:
                existing_step = None

            if isinstance(existing_step, dict):
                existing_status = str(
                    existing_step.get("status") or ""
                ).lower().strip()

                incoming_status = str(
                    step.get("status") or ""
                ).lower().strip()

                if (
                    existing_status in {
                        "running",
                        "waiting",
                    }
                    and incoming_status == "pending"
                ):
                    print(
                        "BLOCKED STATE DOWNGRADE =",
                        {
                            "existing": existing_status,
                            "incoming": incoming_status,
                            "step": existing_step.get("title"),
                        },
                        flush=True,
                    )

                    step = dict(existing_step)

            try:
                self._register_project_file(
                    execution_state,
                    step,
                )
            except Exception as exc:
                print(
                    "PROJECT FILE REGISTRATION FAILED:",
                    exc,
                    flush=True,
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

            print(
                "DEBUG BEFORE ADVANCE AFTER STEP COMPLETION",
                {
                    "current_index": current_index,
                    "step_status": step.get("status"),
                    "step_complete": step.get("complete"),
                    "step_result": step.get("result"),
                },
                flush=True,
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
                if (
                    isinstance(
                        execution_state,
                        dict,
                    )
                    and self.project_workspace_service is not None
                ):
                    project_id = execution_state.get(
                        "project_id"
                    )

                    if project_id:
                        self.project_workspace_service.get_project(
                            project_id
                        )

                unfinished_tasks = self._unfinished_project_tasks(
                    execution_state
                )
                if unfinished_tasks:
                    execution_state["status"] = "in_progress"
                    execution_state["complete"] = False

                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": (
                                "Execution steps are exhausted, but "
                                "project tasks remain unfinished: "
                                + ", ".join(unfinished_tasks)
                                + ". Add executable steps or complete "
                                "the remaining tasks."
                            ),
                        },
                        "execution": execution_state,
                    }

                execution_state = (
                    self.execution_mutation_service.mark_complete(
                        execution_state
                    )
                )

            else:
                next_step = dict(
                    steps[next_index]
                )

                # Carry only mutation context that verification actually
                # needs. Do NOT overwrite the verification target.
                #
                # A verify step has its own target_file / verification_file.
                # The previous mutation step must never replace those with
                # the implementation artifact.

                if (
                    isinstance(step, dict)
                    and isinstance(next_step, dict)
                    and next_step.get("action") == "verify"
                ):
                    if (
                        step.get("content")
                        and not next_step.get("expected_output")
                        and not next_step.get("verification_file")
                    ):
                        next_step["expected_output"] = step.get(
                            "content"
                        )

                    if (
                        step.get("mutation_mode")
                        and not next_step.get("mutation_mode")
                    ):
                        next_step["mutation_mode"] = step.get(
                            "mutation_mode"
                        )

                    steps[next_index] = next_step
                    execution_state["steps"] = steps

                    print(
                        "DEBUG NEXT STEP AFTER CONTEXT COPY =",
                        next_step,
                        flush=True,
                    )

                    if (
                        step.get("content")
                        and not next_step.get("expected_output")
                        and not next_step.get("verification_file")
                    ):
                        next_step["expected_output"] = step.get(
                            "content"
                        )

                    steps[next_index] = next_step
                    execution_state["steps"] = steps

                    print(
                        "DEBUG NEXT STEP AFTER CONTEXT COPY =",
                        next_step,
                        flush=True,
                    )

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
            # Reuse the approval-aware single-step pipeline and continue
            # until execution reaches a terminal state, an approval gate,
            # or there are no remaining pending steps.
            result = None
            current_state = execution_state

            for _ in range(100):
                result = self._process_execution_command(
                    command="run_step",
                    session_id=session_id,
                    execution_state=current_state,
                )

                if not isinstance(result, dict):
                    break

                next_state = result.get("execution")

                if isinstance(next_state, dict):
                    current_state = next_state

                status = self._safe_str(
                    current_state.get("status")
                ).strip().lower()

                if (
                    current_state.get("complete") is True
                    or current_state.get("cancelled") is True
                    or status in {
                        "complete",
                        "completed",
                        "failed",
                        "error",
                        "cancelled",
                    }
                ):
                    break

                steps = current_state.get("steps")

                if not isinstance(steps, list):
                    break

                current_index = int(
                    current_state.get("current_index", 0) or 0
                )

                if current_index >= len(steps):
                    break

                current_step = steps[current_index]

                if not isinstance(current_step, dict):
                    break

                step_status = self._safe_str(
                    current_step.get("status")
                ).strip().lower()

                execution_metadata = (
                    current_step.get("execution_metadata")
                    if isinstance(
                        current_step.get("execution_metadata"),
                        dict,
                    )
                    else {}
                )

                waiting_for_approval = (
                    current_state.get("waiting_for_approval") is True
                    or current_state.get("awaiting_approval") is True
                    or current_state.get("approval_required") is True
                    or current_step.get("waiting_for_approval") is True
                    or current_step.get("awaiting_approval") is True
                    or current_step.get("approval_required") is True
                    or execution_metadata.get("waiting_approval") is True
                    or step_status in {
                        "waiting_approval",
                        "awaiting_approval",
                        "approval_required",
                    }
                )

                if waiting_for_approval:
                    break

                if (
                    current_state.get("waiting") is True
                    or current_state.get("needs_clarification") is True
                    or step_status == "waiting"
                    or current_step.get("needs_clarification") is True
                ):
                    break

                if step_status in {
                    "failed",
                    "error",
                    "cancelled",
                }:
                    break

                if not any(
                    isinstance(step, dict)
                    and self._safe_str(step.get("status")).strip().lower()
                    not in {
                        "completed",
                        "complete",
                        "failed",
                        "error",
                        "cancelled",
                    }
                    for step in steps
                ):
                    break

            return result

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






