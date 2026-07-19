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

            return None

        except Exception:
            return None