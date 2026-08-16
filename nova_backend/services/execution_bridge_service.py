from typing import Any

from nova_backend.services.project_brain_context_builder import (
    build_project_brain_context,
)


class ExecutionBridgeService:

    def __init__(
        self,
        chat_execution_service,
        logger,
    ):
        self.chat_execution_service = chat_execution_service
        self.logger = logger

    def try_execution_trigger(self, session_id, user_text):
        try:
            if not self.chat_execution_service.is_execution_trigger(user_text):
                return None

            state = self.chat_execution_service.advance(session_id)

            reply_text = (
                self._format_execution_response(state)
                if hasattr(self, "_format_execution_response")
                else self.chat_execution_service.format_reply(state)
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
            self.logger.exception("[NovaExecutionBridge] failed")

            reply_text = "Execution bridge failed: " + str(exc)

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
            }

    def try_execution_autoplan_start(self, session_id, user_text):
        try:
            clean = str(user_text or "").strip()
            lower = clean.lower()

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

            if not matched_prefix:
                return None

            goal = clean[len(matched_prefix):].strip()

            if not goal:
                goal = "Untitled mission"

            steps = [
                f"Understand the goal and define the best approach for: {goal}",
                "Work through the implementation or solution in the correct order",
                "Review the result, verify quality, and determine the next move",
            ]

            project_context = build_project_brain_context()

            brain_context = {
                "project_name": project_context.project_name,
                "active_checkpoint": project_context.active_checkpoint,
                "blocker": project_context.blocker,
                "next_move": project_context.next_move,
            }

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

            reply_text = (
                "Mission created.\n\n"
                f"Goal: {goal}\n\n"
                "Steps:\n"
                + "\n".join(
                    [
                        f"{index + 1}. {step}"
                        for index, step in enumerate(steps)
                    ]
                )
                + "\n\n"
                "Send `next` to run the first step."
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
                "what are we working on",
                "what are we working on now",
                "what are we working on right now",
                "what comes next",
            }

            if clean not in status_questions:
                return None

            state = self.chat_execution_service.get_state(
                session_id
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
                f"Next move: {project_brain.get('next_move', 'Mission completed')}\n"
                f"Next action: {next_action.get('step', 'No further action required')}\n"
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