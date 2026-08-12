from flask import jsonify, request

from nova_backend.services.planner_service import (
    planner_service,
)


def register_planner_routes(app):

    @app.get("/api/planner/modules")
    def planner_modules():

        return jsonify(
            {
                "ok": True,
                "modules": planner_service.list_modules(),
            }
        )


    @app.post("/api/planner/plan")
    def planner_build_plan():

        data = request.get_json() or {}

        goal = str(
            data.get("goal", "")
        ).strip()

        if not goal:
            return jsonify(
                {
                    "ok": False,
                    "error": "missing_goal",
                }
            ), 400

        plan = planner_service.build_plan(
            goal
        )

        return jsonify(
            {
                "ok": True,
                "plan": plan,
            }
        )


    @app.post("/api/planner/mission")
    def planner_create_mission():

        data = request.get_json() or {}

        goal = str(
            data.get("goal", "")
        ).strip()

        if not goal:
            return jsonify(
                {
                    "ok": False,
                    "error": "missing_goal",
                }
            ), 400

        mission = planner_service.create_mission(
            goal
        )

        return jsonify(
            {
                "ok": True,
                "mission": mission,
            }
        )


    @app.post("/api/planner/mission/<mission_name>/advance")
    def planner_advance_mission(mission_name):

        result = planner_service.advance_step(
            mission_name
        )

        return jsonify(
            {
                "ok": True,
                "result": result,
            }
        )