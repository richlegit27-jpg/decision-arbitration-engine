"""
Nova Chat Execution Module

Owns:

- auto-plan execution
- next/continue flows
- execution state handling
- mission lifecycle
"""


class ChatExecutionHandler:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def auto_advance(self, session_id):
        return self._run_auto_advance_execution(
            session_id
        )

    def execute_current_step(
        self,
        execution,
        user_text,
        session_id="",
        attachments=None,
    ):
        return self.chat_service._execute_current_step(
            execution=execution,
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

    def _run_auto_advance_execution(self, session_id):
        try:
            execution_state = self.chat_service._load_execution_state(
                session_id
            ) or {}

            if not isinstance(
                execution_state,
                dict,
            ):
                execution_state = {}

            if not execution_state.get("steps"):
                return None

            result = self.chat_service._execute_current_step(
                execution=execution_state,
                user_text="next",
                session_id=session_id,
                attachments=None,
            )

            if isinstance(result, dict):
                return result

        except Exception as exc:
            try:
                print(
                    "[NOVA AUTO ADVANCE ERROR]",
                    exc,
                )
            except Exception:
                pass

        return None