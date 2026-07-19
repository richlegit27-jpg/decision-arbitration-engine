from __future__ import annotations


class ExecutionStreamRouteService:

    def __init__(
        self,
        session_service,
        execution_service,
        execution_stream_service,
        execution_fix_service,
        execution_loop_service,
    ):
        self.session_service = session_service
        self.execution_service = execution_service
        self.execution_stream_service = execution_stream_service
        self.execution_fix_service = execution_fix_service
        self.execution_loop_service = execution_loop_service

    def stream(self, data):

        session_id = str(
            data.get("session_id") or ""
        ).strip()

        action = str(
            data.get("action") or ""
        ).strip()

        action = self.execution_loop_service.command_alias(
            action
        )

        def generate():

            if not session_id:
                yield self.execution_stream_service.send_event(
                    "error",
                    {
                        "ok": False,
                        "error": "missing session_id",
                        "done": True,
                    },
                )
                return

            if not action:
                yield self.execution_stream_service.send_event(
                    "error",
                    {
                        "ok": False,
                        "error": "missing action",
                        "done": True,
                    },
                )
                return

            session = self.session_service.get_session(
                session_id
            )

            if not isinstance(session, dict):
                session = {}

            execution = (
                session.get("working_state", {})
                .get("execution")
                or {}
            )

            execution = self.execution_service.normalize_execution(
                execution
            )

            yield self.execution_stream_service.send_event(
                "start",
                {
                    "ok": True,
                    "action": action,
                    "session_id": session_id,
                    "execution_state": execution,
                    "done": False,
                },
            )

            if action == "fix_file":

                result = self.execution_fix_service.apply_fix(
                    session_id,
                    session,
                    execution,
                    action,
                )

                execution = result["execution"]
                step = result["step"]
                ok = result["ok"]

                self.execution_stream_service.save_execution(
                    session_id,
                    execution,
                )

                yield self.execution_stream_service.send_event(
                    "step_start",
                    {
                        "step": step,
                        "execution_state": execution,
                        "done": False,
                    },
                )

                yield self.execution_stream_service.send_event(
                    "step_done",
                    {
                        "step": step,
                        "execution_state": execution,
                        "done": False,
                    },
                )

                yield self.execution_stream_service.send_event(
                    "done",
                    {
                        "ok": ok,
                        "execution_state": execution,
                        "done": True,
                    },
                )

                return

            execution = self.execution_service.apply_control_action(
                execution,
                action,
            )

            self.execution_stream_service.save_execution(
                session_id,
                execution,
            )

            yield self.execution_stream_service.send_event(
                "done",
                {
                    "ok": True,
                    "execution_state": execution,
                    "done": True,
                },
            )

        return generate()