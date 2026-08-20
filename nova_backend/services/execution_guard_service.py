
class ExecutionGuardService:

    def __init__(
        self,
        chat_execution_service,
        chat_service=None,
    ):
        self.chat_execution_service = chat_execution_service
        self.chat_service = chat_service

    def handle(self, payload):
        if not isinstance(payload, dict):
            return None

        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        clean = " ".join(
            user_text.lower().split()
        )

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        if clean in {
            "status",
            "execution status",
            "mission status",
        }:
            state = self.chat_execution_service.get_state(
                session_id
            )

            reply = self.chat_execution_service.format_reply(
                state
            )

            return {
                "ok": True,
                "text": reply,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply,
                    "content": reply,
                    "execution_state": state,
                    "attachments": [],
                },
                "execution_state": state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            }

        if clean.startswith("auto-plan "):
            goal = user_text.split(
                "auto-plan",
                1,
            )[1].strip()

            steps = [
                "Inspect the mission and identify the likely target files",
                "Make the smallest safe implementation change",
                "Verify the result and report the next move",
            ]

            goal_lower = goal.lower()

            if (
                "web" in goal_lower
                or "fetch" in goal_lower
                or "search" in goal_lower
            ):
                steps = [
                    "Inspect the web fetch route, ranking path, and displayed source output",
                    "Patch the smallest mismatch between backend fetch results and UI/session output",
                    "Verify fresh search results, source ordering, and displayed cards",
                ]

            elif (
                "memory" in goal_lower
                or "recall" in goal_lower
            ):
                steps = [
                    "Inspect memory write, ranking, and recall injection path",
                    "Patch the smallest issue blocking correct memory recall",
                    "Verify recall with a direct follow-up prompt",
                ]

            elif (
                "execution" in goal_lower
                or "plan" in goal_lower
            ):
                steps = [
                    "Inspect execution state, trigger routing, and durable save file",
                    "Patch the smallest issue in mission start or step advancement",
                    "Verify auto-plan, k, next, continue, and completion behavior",
                ]

            project_context = build_project_brain_context()

            brain_context = {
                "project_name": project_context.project_name,
                "active_checkpoint": project_context.active_checkpoint,
                "blocker": project_context.blocker,
                "next_move": project_context.next_move,
            }

            state = self.chat_execution_service.start(
                session_id,
                goal,
                steps,
                context={
                    "source": "execution_guard",
                    "task_goal": goal,
                    "project": "Nova",
                    "project_brain": brain_context,
                },
            )

            reply = (
                "I'll get started on that.\n\n"
                "I'll keep track of the progress and let you know what I find."
            )

            return {
                "ok": True,
                "text": reply,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply,
                    "content": reply,
                    "execution_state": state,
                    "attachments": [],
                },
                "execution_state": state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            }

        if clean in {
            "k",
            "ok",
            "okay",
            "next",
            "continue",
            "run it",
            "run step",
            "execute",
            "go",
            "advance",
        }:

            if (
                self.chat_service
                and hasattr(
                    self.chat_service,
                    "execution_orchestrator_service",
                )
            ):
                return None

            current_state = self.chat_execution_service.get_state(
                session_id
            )

            print(
                "[EXEC_DEBUG_STATE]",
                current_state,
            )

            if isinstance(current_state, dict):
                current_status = str(
                    current_state.get("status")
                    or ""
                ).lower()

                if current_status in {
                    "idle",
                    "stopped",
                    "complete",
                    "completed",
                }:
                    reply = self.chat_execution_service.format_reply(
                        current_state
                    )

                    return {
                        "ok": True,
                        "text": reply,
                        "assistant_message": {
                            "role": "assistant",
                            "text": reply,
                            "content": reply,
                            "execution_state": current_state,
                            "attachments": [],
                        },
                        "execution_state": current_state,
                        "skip_cleanup": True,
                        "skip_post_processing": True,
                        "skip_rewrite": True,
                    }

            state = self.chat_execution_service.advance(
                session_id
            )

            try:
                if (
                    hasattr(
                        self,
                        "chat_service",
                    )
                    and self.chat_service
                ):
                    self.chat_service._save_execution_state(
                        session_id,
                        state,
                    )

            except Exception as e:
                print(
                    "EXECUTION STATE SAVE FAILED:",
                    e,
                )

            reply = self.format_execution_response(
                state
            ).get(
                "text",
                "I'm continuing with the next part.",
            )

            return {
                "ok": True,
                "text": reply,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply,
                    "content": reply,
                    "execution_state": state,
                    "attachments": [],
                },
                "execution_state": state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            }

    def handle_execution_action(self, clean, session_id):
        commands = {
            "next": "next",
            "nex": "next",
            "continue": "next",
            "continue on": "next",
            "keep going": "next",
            "go": "next",
            "run next": "next",
            "next step": "next",
            "run step": "next",
            "run_step": "next",
            "run all": "run_all",
            "run_all": "run_all",
            "run it": "run_all",
            "execute": "run_all",
            "execute all": "run_all",
            "auto": "run_all",
            "auto mode": "run_all",
            "autopilot": "run_all",
            "retry": "retry",
            "retry failed": "retry",
            "retry_failed": "retry",
            "try again": "retry",
            "rerun failed": "retry",
            "stop": "cancel",
            "cancel": "cancel",
        }

        if clean not in commands:
            return None

        action = commands[clean]

        if action == "run_all":
            state = self.chat_execution_service.run_all(
                session_id
            )

        elif action == "cancel":
            state = self.chat_execution_service.reset(
                session_id
            )

        else:
            if (
                self.chat_service
                and hasattr(
                    self.chat_service,
                    "execution_orchestrator_service",
                )
            ):
                return None

            state = self.chat_execution_service.advance(
                session_id
            )
        return {
            "state": state,
            "action": action,
        }

    def format_execution_response(self, state, command="", action=""):
        status = str(
            state.get("status") or ""
        ).strip().lower()

        goal = str(
            state.get("goal") or ""
        ).strip()

        error = str(
            state.get("error") or ""
        ).strip()

        steps = state.get("steps") or []

        current = str(
            state.get("current_step") or ""
        ).strip()

        index = int(
            state.get("current_index") or 0
        )

        if status in {"idle", "none", ""}:
            reply = error or (
                "I don't have an active task right now. "
                "Tell me what you'd like to work on."
            )

        elif status in {"complete", "completed"}:
            reply = (
                "Done. I finished working on "
                + goal
                + "."
                if goal
                else "Done. I finished the task."
            )

        elif status in {"failed", "error"}:
            reply = error or (
                "I ran into a problem while working on this."
            )

        else:
            total = len(steps)

            if not current and steps:
                current = str(
                    steps[index]
                    if index < len(steps)
                    else steps[-1]
                )

            reply = (
                "I'm continuing with the next part.\n\n"
                + (current or "Continuing the work.")
            )

        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply,
                "content": reply,
            },
            "text": reply,
            "execution_state": state,
            "debug": {
                "route": "execution_command_top_guard",
                "command": command,
                "action": action,
            },
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
        }