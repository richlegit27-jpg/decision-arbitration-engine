from __future__ import annotations

from copy import deepcopy

from flask import jsonify, request


class ExecutionRouteService:
    def __init__(
        self,
        working_state_service=None,
        execution_service=None,
    ):
        self.working_state_service = working_state_service
        self.execution_service = execution_service

    def _load_execution(self, session_id):
        if not self.working_state_service:
            return None

        state = self.working_state_service.get_working_state(
            session_id
        )

        if not isinstance(state, dict):
            return None

        execution = state.get("execution")

        if not isinstance(execution, dict):
            return None

        return deepcopy(execution)

    def _save_execution(self, session_id, execution):
        if not self.working_state_service:
            return

        self.working_state_service.update_working_state(
            session_id,
            {
                "execution": execution,
            },
        )

    def _new_execution(self, session_id, data):
        title = str(
            data.get("title") or "Execution Run"
        ).strip()

        goal = str(
            data.get("goal") or "Complete the requested execution."
        ).strip()

        steps = data.get("steps")

        if not isinstance(steps, list) or not steps:
            steps = [
                "Execute the requested step",
            ]

        return self.execution_service.new_execution(
            title=title,
            goal=goal,
            steps=steps,
            status="planned",
            meta={
                "session_id": session_id,
                "source": "execution_control",
            },
            auto_start=True,
        )

    def execution_control(self):
        data = request.get_json(
            silent=True
        ) or {}

        session_id = str(
            data.get("session_id") or ""
        ).strip()

        action = str(
            data.get("action") or ""
        ).strip().lower()

        if not session_id:
            return jsonify(
                {
                    "ok": False,
                    "error": "missing session_id",
                }
            ), 400

        if not action:
            return jsonify(
                {
                    "ok": False,
                    "error": "missing action",
                }
            ), 400

        if not self.execution_service:
            return jsonify(
                {
                    "ok": False,
                    "error": "execution control is unavailable",
                }
            ), 503

        try:
            execution = self._load_execution(
                session_id
            )

            if execution is None:
                execution = self._new_execution(
                    session_id,
                    data,
                )

            if action in {
                "run_step",
                "next",
                "continue",
                "go",
            }:
                execution = (
                    self.execution_service.advance_execution_step(
                        execution
                    )
                )

            elif action in {
                "run_all",
                "execute",
                "execute_all",
            }:
                execution = (
                    self.execution_service.apply_control_action(
                        execution,
                        "run_all",
                    )
                )

            elif action in {
                "state",
                "get_state",
                "status",
            }:
                execution = (
                    self.execution_service.normalize_execution(
                        execution
                    )
                )

            elif action in {
                "start",
                "resume",
                "unblock",
            }:
                execution = (
                    self.execution_service.start_execution(
                        execution
                    )
                )

            elif action in {
                "stop",
                "block",
            }:
                execution = (
                    self.execution_service.apply_control_action(
                        execution,
                        "stop",
                    )
                )

            elif action in {
                "retry",
                "retry_failed",
            }:
                execution = (
                    self.execution_service.apply_control_action(
                        execution,
                        "retry_failed",
                    )
                )

            elif action == "test_fail":
                execution = (
                    self.execution_service.apply_control_action(
                        execution,
                        "test_fail",
                    )
                )

            else:
                return jsonify(
                    {
                        "ok": False,
                        "error": (
                            f"unknown execution action: "
                            f"{action}"
                        ),
                    }
                ), 400

            if not isinstance(execution, dict):
                return jsonify(
                    {
                        "ok": False,
                        "error": "execution returned invalid state",
                    }
                ), 500

            self._save_execution(
                session_id,
                execution,
            )

            return jsonify(
                {
                    "ok": True,
                    "action": action,
                    "session_id": session_id,
                    "execution_state": execution,
                }
            )

        except Exception as exc:
            return jsonify(
                {
                    "ok": False,
                    "action": action,
                    "session_id": session_id,
                    "error": str(exc),
                }
            ), 500