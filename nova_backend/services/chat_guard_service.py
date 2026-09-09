from __future__ import annotations

import traceback


class ChatGuardService:

    def handle_casual_chat_guard(
        self,
        payload,
        execution_bridge_service,
    ):
        try:
            print(
                "[CHAT GUARD ENTERED]",
                repr(payload),
                flush=True,
            )
            user_text = str(
                payload.get("user_text")
                or payload.get("text")
                or payload.get("message")
                or ""
            ).strip()

            if not user_text:
                return None

            session_id = str(
                payload.get("session_id") or ""
            ).strip()

            clean = (
                " ".join(
                    user_text.lower().split()
                )
                .rstrip("?!.")
            )

            print(
                "[CHAT GUARD ENTER]",
                {
                    "session_id": session_id,
                    "user_text": user_text,
                    "clean": clean,
                },
                flush=True,
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

            print(
                "[CHAT GUARD STATUS RESULT]",
                repr(execution_status_result),
                flush=True,
            )

            if execution_status_result is not None:
                return execution_status_result

            target_capture_result = (
                execution_bridge_service
                .try_execution_target_capture(
                    session_id,
                    user_text,
                )
            )

            print(
                "[CHAT GUARD TARGET RESULT]",
                repr(target_capture_result),
                flush=True,
            )

            if target_capture_result is not None:
                return target_capture_result

            autoplan_result = (
                execution_bridge_service
                .try_execution_autoplan_start(
                    session_id,
                    user_text,
                )
            )

            print(
                "[CHAT GUARD AUTOPLAN RESULT]",
                repr(autoplan_result),
                flush=True,
            )

            if autoplan_result is not None:
                return autoplan_result

            execution_result = (
                execution_bridge_service
                .try_execution_trigger(
                    session_id,
                    user_text,
                )
            )

            print(
                "[CHAT GUARD EXECUTION RESULT]",
                repr(execution_result),
                flush=True,
            )

            if execution_result is not None:
                return execution_result

            return None

        except Exception as exc:
            print(
                "[CHAT GUARD FAILED]",
                repr(exc),
                flush=True,
            )

            traceback.print_exc()

            return None