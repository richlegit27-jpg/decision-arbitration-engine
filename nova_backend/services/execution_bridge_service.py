

from typing import Any

from nova_backend.services.project_brain_context_builder import (
    build_project_brain_context,
)
from nova_backend.services.project_planning_ai_service import (
    ProjectPlanningAIService,
)

class ExecutionBridgeService:

    def __init__(
        self,
        chat_execution_service,
        logger,
        chat_service=None,
        project_planning_ai_service=None,
    ):
        self.chat_execution_service = chat_execution_service
        self.logger = logger
        self.chat_service = chat_service

        self.project_planning_ai_service = (
            project_planning_ai_service
            or ProjectPlanningAIService()
        )

    def try_execution_trigger(
        self,
        session_id,
        user_text,
    ):
        try:
            target_result = self.try_execution_target_capture(
                session_id,
                user_text,
            )

            if target_result is not None:
                return target_result

            if not self.chat_execution_service.is_execution_trigger(
                user_text
            ):
                return None

            if hasattr(
                self.chat_execution_service,
                "execution_orchestrator_service",
            ):
                return None

            state = self.chat_execution_service.get_state(
                session_id
            )

            status = str(
                state.get("status")
                or ""
            ).lower().strip()

            has_active_execution = (
                status in {
                    "ready",
                    "running",
                    "paused",
                    "waiting_approval",
                }
                or bool(state.get("steps"))
                or bool(state.get("current_step"))
            )

            if not has_active_execution:
                return None

            state = self.chat_execution_service.advance(
                session_id,
                user_text,
            )

            reply_text = (
                self._format_execution_response(state)
                if hasattr(
                    self,
                    "_format_execution_response",
                )
                else self.chat_execution_service.format_reply(
                    state
                )
            )

            return {
                "ok": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": state,
                },
                "execution_state": state,
            }

        except Exception as exc:
            if self.logger:
                self.logger.exception(
                    "[NovaExecutionBridge] failed"
                )

            reply_text = (
                "Execution bridge failed: "
                + str(exc)
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
            }

    def try_execution_autoplan_start(
        self,
        session_id,
        user_text,
    ):
        print(
            "DEBUG NEW AUTOPLAN BRIDGE LOADED",
            flush=True,
        )

        try:
            clean = str(user_text or "").strip()
            lower = clean.lower()

            continuation_commands = {
                "k",
                "kk",
                "next",
                "nex",
                "continue",
                "resume",
            }

            if lower in continuation_commands:
                print(
                    "[AUTOPLAN CONTINUATION BYPASS]",
                    clean,
                    flush=True,
                )
                return None

            prefixes = [
                "auto-plan ",
                "autoplan ",
                "auto plan ",
            ]


            if lower in continuation_commands:
                return {
                    "ok": True,
                    "skip_cleanup": True,
                    "skip_post_processing": True,
                    "skip_rewrite": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No active execution mission. "
                            "Start one with: auto-plan <goal>"
                        ),
                        "content": (
                            "No active execution mission. "
                            "Start one with: auto-plan <goal>"
                        ),
                    },
                    "execution_state": {},
                    "debug": {
                        "route_taken": "no_active_execution_guard",
                    },
                }

            prefixes = [
                "auto-plan ",
                "autoplan ",
                "auto plan ",
            ]

            matched_prefix = None

            for prefix in prefixes:
                if lower.startswith(prefix):
                    matched_prefix = prefix
                    break

            is_natural_execution_request = (
                self.chat_execution_service.is_execution_trigger(
                    clean
                )
            )

            if matched_prefix:
                goal = clean[
                    len(matched_prefix):
                ].strip()

            elif is_natural_execution_request:
                goal = clean

                execution_phrases = (
                    "and run all steps",
                    "run all steps",
                    "and execute all steps",
                    "execute all steps",
                    "and run all",
                    "run all",
                    "and execute all",
                    "execute all",
                    "start execution",
                )

                goal_lower_clean = goal.lower()

                for phrase in execution_phrases:
                    if phrase in goal_lower_clean:
                        position = goal_lower_clean.find(
                            phrase
                        )

                        goal = goal[:position].strip(
                            " .,:;-"
                        )

                        break

            else:
                print(
                    "[AUTOPLAN BYPASS]",
                    clean,
                    flush=True,
                )
                return None

            if not goal:
                goal = "Untitled mission"
            goal_lower = goal.lower()

            steps = []

            project_context = build_project_brain_context()

            brain_context = {
                "project_name": project_context.project_name,
                "active_checkpoint": project_context.active_checkpoint,
                "blocker": project_context.blocker,
                "next_move": project_context.next_move,
            }

            try:
                plan = self.project_planning_ai_service.build_plan(
                    request=goal,
                    project_context={
                        "project_name": project_context.project_name,
                        "active_checkpoint": (
                            project_context.active_checkpoint
                        ),
                        "blocker": project_context.blocker,
                        "next_move": project_context.next_move,
                    },
                )

                steps = plan.get("tasks", [])

                if not isinstance(steps, list):
                    steps = []

                steps = [
                    step
                    for step in steps
                    if isinstance(step, dict)
                    and str(
                        step.get("title") or ""
                    ).strip()
                ]

                print(
                    "[AI AUTOPLAN RESULT]",
                    {
                        "goal": goal,
                        "plan_name": plan.get("name"),
                        "task_count": len(steps),
                    },
                    flush=True,
                )

            except Exception as exc:

                self.logger.exception(
                    "[AI AUTOPLAN FAILED]"
                )

                print(
                    "[AI AUTOPLAN FALLBACK]",
                    repr(exc),
                    flush=True,
                )

                steps = []

            if not steps:

                steps = [
                    {
                        "title": f"Analyze the goal: {goal}",
                        "action": "analyze",
                        "execution_mode": "ai",
                    },
                    {
                        "title": (
                            "Determine the required work "
                            "and implementation approach"
                        ),
                        "action": "plan",
                        "execution_mode": "ai",
                    },
                    {
                        "title": (
                            "Review the result and "
                            "determine next actions"
                        ),
                        "action": "review",
                        "execution_mode": "ai",
                    },
                ]

            print(
                "DEBUG AUTOPLAN STEPS BEFORE START:",
                steps,
            )

            for step in steps:
                if step.get("action") != "implement":
                    continue

                target_file = str(
                    step.get("target_file") or ""
                ).strip()

                target_files = (
                    step.get("target_files") or []
                )

                has_real_target = bool(
                    target_file
                    or target_files
                )

                if has_real_target:
                    step.setdefault(
                        "target_function",
                        "",
                    )

                    step["mutation_mode"] = "file"
                    step["next_action"] = (
                        "generate_file_replacement"
                    )
                    step["mutation_ready"] = True
                    step["payload_required"] = True

                else:
                    # Generic implementation/research step.
                    # Do not pretend the user's natural-language
                    # request is a file path.
                    step["mutation_mode"] = "general"
                    step["next_action"] = (
                        "execute_task"
                    )
                    step["mutation_ready"] = True
                    step["payload_required"] = False
                    step["status"] = "ready"

            session_id = str(
                session_id or ""
            ).strip()

            if not session_id:
                import uuid

                session_id = (
                    "execution_"
                    + uuid.uuid4().hex
                )

            print(
                "AUTOPLAN BEFORE START",

                {
                    "has_chat_execution_service": hasattr(
                        self,
                        "chat_execution_service",
                    ),
                    "has_chat_service": hasattr(
                        self,
                        "chat_service",
                    ),
                    "session_id": session_id,
                    "goal": goal,
                    "steps": len(steps),
                },
                flush=True,
            )

            print(
                "DEBUG STEPS RIGHT BEFORE START =",
                steps,
                flush=True,
            )

            state = self.chat_execution_service.start(
                session_id=session_id,
                goal=goal,
                steps=steps,
                context={
                    "source": "auto_plan",
                    "task_goal": goal,
                    "step_count": len(steps),
                    "steps": steps,
                    "project": "Nova",
                    "execution_reason": (
                        "Complete the user's requested task "
                        "through a guided execution workflow."
                    ),
                    "project_brain": brain_context,
                },
            )

            print(
                "DEBUG STATE AFTER EXECUTION START =",
                state,
                flush=True,
            )

            if state:
                if self.chat_service and hasattr(
                    self.chat_service,
                    "_save_execution_state",
                ):
                    self.chat_service._save_execution_state(
                        session_id,
                        state,
                    )
            step_lines = []

            for index, step in enumerate(steps):
                if isinstance(step, dict):
                    step_lines.append(
                        f"{index + 1}. {step.get('title', 'Execution step')}"
                    )
                else:
                    step_lines.append(
                        f"{index + 1}. {step}"
                    )

            target = {
                "target_file": "",
                "target_files": [],
                "target_function": "",
            }




            for step in steps:
                if not isinstance(step, dict):
                    continue

                if step.get("target_file"):
                    target["target_file"] = step.get("target_file")

                if step.get("target_files"):
                    target["target_files"] = step.get("target_files")

                if step.get("target_function"):
                    target["target_function"] = step.get("target_function")

            print(
                "[EXECUTION TARGET HANDOFF]",
                {
                    "session_id": session_id,
                    "target": target,
                    "status": state.get("status"),
                    "current_index": state.get("current_index"),
                },
                flush=True,
            )

            print(
                "[EXECUTION TARGET CONTINUE]",
                {
                    "session_id": session_id,
                    "current_index": state.get(
                        "current_index"
                    ),
                    "status": state.get("status"),
                    "handler": type(
                        self.chat_execution_service.execution_handler
                    ).__name__
                    if getattr(
                        self.chat_execution_service,
                        "execution_handler",
                        None,
                    ) is not None
                    else None,
                },
                flush=True,
            )

            execution_result = (
                self.chat_execution_service.advance(
                    session_id=session_id,
                )
            )

            print(
                "[EXECUTION TARGET CONTINUE RESULT]",
                repr(execution_result),
                flush=True,
            )

            if execution_result is None:
                raise RuntimeError(
                    "Chat execution service returned None "
                    "after target capture."
                )

            if isinstance(
                execution_result,
                dict,
            ):
                return execution_result

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": str(execution_result),
                    "content": str(execution_result),
                },
                "session_id": session_id,
                "execution": execution_result,
            }

        except Exception as exc:
            self.logger.exception(
                "[NovaExecutionAutoPlanStart] failed"
            )

            reply_text = (
                "Execution auto-plan start failed: "
                + str(exc)
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
            }

    def try_execution_status(
        self,
        session_id,
        user_text,
    ):
        try:
            clean = (
                " ".join(
                    str(user_text or "")
                    .strip()
                    .lower()
                    .split()
                )
                .rstrip("?!.")
            )

            status_questions = {
                "status",
                "execution status",
                "mission status",
                "what comes next",
            }

            if clean not in status_questions:
                return None

            state = self.chat_execution_service.get_state(
                session_id
            )
            print(
                "DEBUG TARGET CAPTURE CHECK",
                {
                    "session_id": session_id,
                    "current_index": state.get("current_index")
                    if isinstance(state, dict)
                    else None,
                    "steps": state.get("steps")
                    if isinstance(state, dict)
                    else None,
                },
                flush=True,
            )

            if (
                not isinstance(state, dict)
                or state.get("status") == "idle"
            ):
                return None

            goal = str(
                state.get("goal")
                or "Untitled mission"
            )

            status = str(
                state.get("status")
                or "ready"
            )

            task_type = str(
                state.get("task_type")
                or "general"
            )

            project_brain = (
                state.get("context", {})
                .get("project_brain", {})
                if isinstance(state, dict)
                else {}
            )

            next_action = state.get(
                "next_action",
                {},
            )

            reply_text = (
                f"Active mission: {goal}\n"
                f"Type: {task_type}\n"
                f"Status: {status}\n"
                f"Checkpoint: {project_brain.get('active_checkpoint', 'Not available')}\n"
                f"Blocker: {project_brain.get('blocker', 'None')}\n"
                f"Next move: {project_brain.get('next_move') or 'No next move available'}\n"
                f"Next action: {next_action.get('step') or 'Waiting for instruction'}\n"
            )

            return {
                "ok": True,
                "text": reply_text,
                "content": reply_text,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": state,
                },
                "execution_state": state,
            }

        except Exception:
            return None

    def try_execution_target_capture(
        self,
        session_id,
        user_text,
    ):
        try:
            state = self.chat_execution_service.get_state(
                session_id
            )

            if not isinstance(state, dict):
                return None

            steps = state.get("steps") or []

            current_index = int(
                state.get("current_index") or 0
            )

            if current_index >= len(steps):
                return None

            step = steps[current_index]

            if not isinstance(step, dict):
                return None

            if step.get("next_action") != "request_target":
                return None

            target = str(
                user_text or ""
            ).strip()

            ignored_commands = {
                "next",
                "continue",
                "go",
                "run",
                "advance",
            }

            if (
                not target
                or target.lower() in ignored_commands
                or target.lower().startswith("auto-plan")
                or target.lower().startswith("autoplan")
                or target.lower().startswith("auto plan")
            ):
                return None

            print(
                "[EXECUTION TARGET CAPTURED]",
                {
                    "session_id": session_id,
                    "current_index": current_index,
                    "target": target,
                },
                flush=True,
            )

            step["target_file"] = target
            step["target_files"] = [target]

            step["next_action"] = (
                "generate_file_replacement"
            )

            step["mutation_ready"] = True
            step["payload_required"] = True
            step["status"] = "ready"
            step["waiting_for_target"] = False

            state["steps"][current_index] = step
            state["current_step"] = step

            # Target capture is complete.
            # The mission must now be executable.
            state["status"] = "ready"
            state["waiting"] = False
            state["complete"] = False

            self.chat_execution_service._states[
                session_id
            ] = state

            self.chat_execution_service._sync_state_to_session(
                session_id,
                state,
            )

            self.chat_execution_service._save_states()

            reply_text = (
                "Target captured:\n"
                f"{target}\n\n"
                "Proceeding with implementation."
            )

            print(
                "[EXECUTION TARGET HANDOFF]",
                {
                    "session_id": session_id,
                    "target": target,
                    "current_index": current_index,
                    "next_action": step.get(
                        "next_action"
                    ),
                    "status": state.get("status"),
                },
                flush=True,
            )

            if (
                self.chat_service is not None
                and getattr(
                    self.chat_service,
                    "execution_orchestrator_service",
                    None,
                ) is not None
            ):
                return (
                    self.chat_service
                    .execution_orchestrator_service
                    .process_execution(
                        session_id=session_id,
                        state=state,
                        command="run_step",
                    )
                )

            return {
                "ok": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "target_captured": True,
                "continue_execution": False,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": state,
                },
                "execution_state": state,
            }

        except Exception:
            self.logger.exception(
                "[ExecutionTargetCapture] failed"
            )
            return None

