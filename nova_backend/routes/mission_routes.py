from flask import jsonify, request

from nova_backend.services.mission_service import (
    mission_service,
)


def register_mission_routes(
    app,
    execution_state_service=None,
    mission_orchestrator=None,
):

    def persist_mission_state(session_id, mission):
        if execution_state_service and session_id:
            execution_state_service.persist_working_state(
                session_id,
                {
                    "active_execution": {
                        "id": mission.get("id"),
                        "goal": mission.get("goal"),
                        "status": mission.get("status"),
                        "steps": mission.get("steps", []),
                        "current_step_index": mission.get(
                            "current_step",
                            0,
                        ),
                    }
                },
            )

    @app.get("/api/missions")
    def list_missions():

        return jsonify(
            {
                "ok": True,
                "missions": mission_service.list_missions(),
            }
        )


    @app.get("/api/missions/<mission_id>")
    def get_mission(mission_id):

        mission = mission_service.get_mission(
            mission_id
        )

        if not mission:
            return jsonify(
                {
                    "ok": False,
                    "error": "mission_not_found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "mission": mission,
            }
        )


    @app.post("/api/missions/<mission_id>/start")
    def start_mission(mission_id):

        data = request.get_json(
            silent=True
        ) or {}

        session_id = str(
            data.get("session_id")
            or data.get("active_session_id")
            or ""
        ).strip()

        mission = mission_service.start_mission(
            mission_id
        )

    orchestration_result = None

    if mission_orchestrator:

        orchestration_result = (
            mission_orchestrator.run_mission(
                {
                    "mission_id": mission.get("id"),
                    "goal": mission.get("goal"),
                    "steps": mission.get("steps", []),
                }
            )
        )

        mission["orchestration"] = (
            orchestration_result
        )

        if not mission:
            return jsonify(
                {
                    "ok": False,
                    "error": "mission_not_found",
                }
            ), 404

        persist_mission_state(
            session_id,
            mission,
        )

        return jsonify(
            {
                "ok": True,
                "mission": mission,
            }
        )


    @app.post("/api/missions/<mission_id>/advance")
    def advance_mission(mission_id):

        data = request.get_json(
            silent=True
        ) or {}

        session_id = str(
            data.get("session_id")
            or data.get("active_session_id")
            or ""
        ).strip()

        mission = mission_service.advance_step(
            mission_id
        )

        if not mission:
            return jsonify(
                {
                    "ok": False,
                    "error": "mission_not_found",
                }
            ), 404

        persist_mission_state(
            session_id,
            mission,
        )

        return jsonify(
            {
                "ok": True,
                "mission": mission,
            }
        )


    @app.post("/api/missions/<mission_id>/status")
    def update_mission_status(mission_id):

        data = request.get_json(
            silent=True
        ) or {}

        status = str(
            data.get("status", "")
        ).strip()

        if not status:
            return jsonify(
                {
                    "ok": False,
                    "error": "missing_status",
                }
            ), 400

        mission = mission_service.update_status(
            mission_id,
            status,
        )

        if not mission:
            return jsonify(
                {
                    "ok": False,
                    "error": "mission_not_found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "mission": mission,
            }
        )