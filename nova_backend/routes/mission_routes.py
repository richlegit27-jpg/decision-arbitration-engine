from flask import jsonify


def register_mission_routes(app, execution_state_service=None, mission_orchestrator=None):
    """Retire the unauthenticated legacy Mission API.

    Project execution is the supported user-facing workflow. These legacy
    endpoints operated on a process-wide mission store and bypassed its
    authenticated project execution and approval boundaries.
    """

    def disabled(*args, **kwargs):
        return jsonify({
            "ok": False,
            "error": "legacy_missions_disabled",
            "message": "Use Nova Projects for authenticated task execution.",
        }), 410

    app.add_url_rule("/api/missions", "list_missions", disabled, methods=["GET"])
    app.add_url_rule("/api/missions/<mission_id>", "get_mission", disabled, methods=["GET"])
    app.add_url_rule("/api/missions/<mission_id>/start", "start_mission", disabled, methods=["POST"])
    app.add_url_rule("/api/missions/<mission_id>/advance", "advance_mission", disabled, methods=["POST"])
    app.add_url_rule("/api/missions/<mission_id>/status", "update_mission_status", disabled, methods=["POST"])
