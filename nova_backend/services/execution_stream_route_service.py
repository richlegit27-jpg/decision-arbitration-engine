from __future__ import annotations


class ExecutionStreamRouteService:

    def __init__(
        self,
        session_service,
        execution_service,
        execution_stream_service,
        execution_fix_service,
    ):
        self.session_service = session_service
        self.execution_service = execution_service
        self.execution_stream_service = execution_stream_service
        self.execution_fix_service = execution_fix_service

    def _normalize_execution(self, execution):
        if isinstance(execution, dict):
            normalized = dict(execution)
        else:
            normalized = {}

        normalized.setdefault(
            "id",
            "",
        )
        normalized.setdefault(
            "type",
            "execution_run",
        )
        normalized.setdefault(
            "title",
            "Execution Run",
        )
        normalized.setdefault(
            "goal",
            "",
        )
        normalized.setdefault(
            "status",
            "idle",
        )
        normalized.setdefault(
            "current_step",
            "",
        )
        normalized.setdefault(
            "result",
            "",
        )
        normalized.setdefault(
            "error",
            "",
        )
        normalized.setdefault(
            "history",
            [],
        )
        normalized.setdefault(
            "steps",
            [],
        )
        normalized.setdefault(
            "meta",
            {},
        )

        if not isinstance(
            normalized["history"],
            list,
        ):
            normalized["history"] = []

        if not isinstance(
            normalized["steps"],
            list,
        ):
            normalized["steps"] = []

        if not isinstance(
            normalized["meta"],
            dict,
        ):
            normalized["meta"] = {}

        return normalized

    def _apply_control_action(
        self,
        execution,
        action,
    ):
        execution = self._normalize_execution(
            execution
        )

        action = str(
            action or ""
        ).strip().lower()

        if action == "run_step":
            step_number = (
                len(
                    execution["steps"]
                )
                + 1
            )

            step_id = (
                f"step_{step_number}"
            )

            step = {
                "id": step_id,
                "title": (
                    f"Step {step_number}"
                ),
                "text": (
                    f"Step {step_number}"
                ),
                "status": "completed",
                "started_at": "",
                "completed_at": "",
                "failed_at": "",
                "blocked_at": "",
                "output": "Step completed.",
                "notes": "",
                "meta": {},
            }

            from datetime import datetime, timezone

            now = datetime.now(
                timezone.utc
            ).isoformat()

            step["started_at"] = now
            step["completed_at"] = now

            execution["steps"].append(
                step
            )

            execution["history"].append(
                f"run_step: Step {step_number}"
            )

            execution["current_step"] = ""

            execution["status"] = (
                "completed"
            )

            execution["updated_at"] = now

            counts = {
                "blocked": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "running": 0,
                "total": len(
                    execution["steps"]
                ),
            }

            for item in execution["steps"]:
                status = str(
                    item.get("status")
                    or ""
                ).lower()

                if status == "completed":
                    counts["completed"] += 1
                elif status == "failed":
                    counts["failed"] += 1
                elif status == "blocked":
                    counts["blocked"] += 1
                elif status == "running":
                    counts["running"] += 1
                else:
                    counts["pending"] += 1

            execution["meta"][
                "step_counts"
            ] = counts

            return execution

        return execution

    def stream(self, data):

        if not isinstance(
            data,
            dict,
        ):
            data = {}

        session_id = str(
            data.get("session_id") or ""
        ).strip()

        action = str(
            data.get("action") or ""
        ).strip().lower()

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

            if not isinstance(
                session,
                dict,
            ):
                session = {}

            working_state = session.get(
                "working_state",
                {},
            )

            if not isinstance(
                working_state,
                dict,
            ):
                working_state = {}

            execution = (
                working_state.get(
                    "execution"
                )
                or {}
            )

            execution = self._normalize_execution(
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

                result = (
                    self.execution_fix_service.apply_fix(
                        session_id,
                        session,
                        execution,
                        action,
                    )
                )

                execution = (
                    result.get(
                        "execution"
                    )
                    or execution
                )

                step = result.get(
                    "step"
                )

                ok = bool(
                    result.get(
                        "ok"
                    )
                )

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

            execution = self._apply_control_action(
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