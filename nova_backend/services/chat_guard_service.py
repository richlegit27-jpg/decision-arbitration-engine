from __future__ import annotations


class ChatGuardService:

    def handle_casual_chat_guard(
        self,
        payload,
        execution_bridge_service,
    ):
        try:
            user_text = str(
                payload.get("user_text")
                or payload.get("text")
                or payload.get("message")
                or ""
            ).strip()

            session_id = str(
                payload.get("session_id") or ""
            ).strip()

            clean = (
                " ".join(
                    user_text.lower().split()
                )
                .rstrip("?!.")
            )

            project_state_questions = {
                "what are we working on",
                "what are we working on now",
                "what are we working on right now",
                "where are we at",
                "where are we at with nova",
                "what is nova working on",
                "what is nova working on now",
            }

            if clean in project_state_questions:
                return None

            execution_status_result = (
                execution_bridge_service
                .try_execution_status(
                    session_id,
                    user_text,
                )
            )

            if execution_status_result is not None:
                return execution_status_result

            execution_result = (
                execution_bridge_service
                .try_execution_trigger(
                    session_id,
                    user_text,
                )
            )

            if execution_result is not None:
                return execution_result

            autoplan_result = (
                execution_bridge_service
                .try_execution_autoplan_start(
                    session_id,
                    user_text,
                )
            )

            if autoplan_result is not None:
                return autoplan_result

            return None

        except Exception:
            return None