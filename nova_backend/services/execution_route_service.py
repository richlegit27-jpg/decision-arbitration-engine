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
                    "error": (
                        "execution control is unavailable"
                    ),
                }
            ), 503

        try:

            if action in {
                "run_step",
                "next",
                "continue",
                "go",
            }:

                execution = (
                    self.execution_service.advance(
                        session_id
                    )
                )

            elif action in {
                "run_all",
                "execute",
                "execute_all",
            }:

                execution = (
                    self.execution_service.run_all(
                        session_id
                    )
                )

            elif action in {
                "state",
                "get_state",
                "status",
            }:

                execution = (
                    self.execution_service.get_state(
                        session_id
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

            if not isinstance(
                execution,
                dict,
            ):
                return jsonify(
                    {
                        "ok": False,
                        "error": (
                            "execution returned invalid state"
                        ),
                    }
                ), 500

            if self.working_state_service:

                self.working_state_service.update_working_state(
                    session_id,
                    {
                        "execution": execution,
                    },
                )

            return jsonify(
                {
                    "ok": True,
                    "action": action,
                    "session_id": session_id,
                    "execution_state": execution,
                }
            )

        except Exception as e:

            return jsonify(
                {
                    "ok": False,
                    "action": action,
                    "session_id": session_id,
                    "error": str(e),
                }
            ), 500