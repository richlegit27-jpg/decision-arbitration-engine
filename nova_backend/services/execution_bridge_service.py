from typing import Any


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
            reply_text = self.chat_execution_service.format_reply(state)

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



    # NOVA_AUTO_PLAN_EXECUTION_START_20260607
    def try_auto_plan_execution_start(self, session_id, user_text):
        try:
            raw_text = str(user_text or "").strip()
            clean_text = " ".join(raw_text.lower().split())

            if not clean_text.startswith("auto-plan "):
                return None

            goal = (
                raw_text[len("auto-plan "):].strip()
                or "Untitled execution mission"
            )

            steps = [
                "Understand the mission and identify the target files",
                "Make the smallest safe implementation change",
                "Verify the result and report the next move",
            ]

            state = self.chat_execution_service.start(
                session_id,
                goal,
                steps,
            )

            if not isinstance(state, dict):
                state = self.chat_execution_service.get_state(session_id)

            current_step = (
                state.get("current_step")
                if isinstance(state, dict)
                else None
            )

            reply_text = (
                "Execution mission started: "
                + goal
                + "\n\n"
                + "Step 1/3: "
                + str(current_step or "Understand the mission and identify the target files")
                + "\n\n"
                + "Send k, next, continue, or run it to advance."
            )

            return {
                "ok": True,
            }

        except Exception as exc:
            self.logger.exception(
                "[NovaAutoPlanExecutionStart] failed"
            )
        reply_text = "Auto-plan execution start failed: " + str(exc)
        return {
            "ok": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
            "assistant_message": {
                "role": "assistant",
                "text": reply_text,
                "content": reply_text,
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
        }


    # NOVA_EXECUTION_AUTOPLAN_START_20260607
    # NOVA_EXECUTION_AUTOPLAN_START_20260607
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
                "Inspect the current target and identify the smallest safe change",
                "Apply the implementation without disturbing working systems",
                "Verify the result and report the next move",
            ]

            state = self.chat_execution_service.start(
                session_id=session_id,
                goal=goal,
                steps=steps,
            )

            reply_text = (
                "Mission started: "
                + goal
                + "\n\n"
                + "Step 1/"
                + str(len(steps))
                + ": "
                + str(state.get("current_step"))
                + "\n\n"
                + "Send k, next, continue, or run it to advance."
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

    # NOVA_EXECUTION_STATUS_BRIDGE_20260607
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

            refresh_states = getattr(
                self.chat_execution_service,
                "_load_states",
                None,
            )

            if callable(refresh_states):
                try:
                    refresh_states()
                except Exception:
                    pass

            state = (
                self.chat_execution_service.get_state(
                    session_id
                )
            )

            if (
                not isinstance(state, dict)
                or state.get("status") == "idle"
                or state.get("complete") is True
            ):
                return None

            goal = str(
                state.get("goal")
                or "Untitled mission"
            ).strip()

            status = str(
                state.get("status")
                or "ready"
            ).strip()

            steps = state.get("steps") or []

            current_index = int(
                state.get("current_index")
                or 0
            )

            current_step = str(
                state.get("current_step")
                or ""
            ).strip()

            lines = [
                f"Active mission: {goal}",
                f"Status: {status}",
            ]

            if current_step and steps:
                lines.append(
                    f"Step {current_index + 1}/{len(steps)}: "
                    f"{current_step}"
                )

            if state.get("waiting"):
                lines.append(
                    "Next: send next, k, continue, "
                    "or run it to advance."
                )

            reply_text = "\n".join(lines)

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
                    "attachments": [],
                    "meta": {
                        "route": "active_execution_status",
                    },
                },
                "execution_state": state,
                "session_id": session_id,
                "active_session_id": session_id,
                "debug": {
                    "route": "active_execution_status",
                    "route_taken": "active_execution_status",
                    "suppressed_project_state_recall": True,
                },
            }

        except Exception as exc:
            if self.logger is not None:
                self.logger.exception(
                    "[NovaExecutionStatus] failed"
                )

            return None