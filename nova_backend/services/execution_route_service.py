from __future__ import annotations

from flask import jsonify, request


class ExecutionRouteService:

    def __init__(
        self,
        working_state_service=None,
        execution_service=None,
    ):
        self.working_state_service = working_state_service
        self.execution_service = execution_service

    def execution_control(self):
        data = request.get_json(silent=True) or {}

        session_id = str(data.get("session_id") or "").strip()
        action = str(data.get("action") or "").strip()

        if not session_id:
            return jsonify({
                "ok": False,
                "error": "missing session_id",
            }), 400

        if not action:
            return jsonify({
                "ok": False,
                "error": "missing action",
            }), 400

        if not self.working_state_service or not self.execution_service:
            return jsonify({
                "ok": False,
                "error": "execution control is unavailable",
            }), 503

        working = (
            self.working_state_service.get_working_state(
                session_id
            )
            or {}
        )

        execution = working.get("execution")

        execution = self.execution_service.normalize_execution(
            execution
        )

        execution = self.execution_service.apply_control_action(
            execution,
            action,
        )

        self.working_state_service.update_working_state(
            session_id,
            {
                "execution": execution,
            },
        )

        return jsonify({
            "ok": True,
            "action": action,
            "session_id": session_id,
            "execution_state": execution,
        })
