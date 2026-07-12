from flask import jsonify, request

from nova_backend.services.nova_improvement_report_service import (
    create_improvement_report,
)

from nova_backend.services.self_improvement_mission_adapter import (
    build_self_improvement_mission_request,
)

from nova_backend.services.planner_service import (
    planner_service,
)

_improvement_state = {
    "reports": [],
}


def register_improvement_routes(app):

    @app.get("/api/improvements")
    def nova_improvements_api():

        if not _improvement_state["reports"]:

            report = create_improvement_report(
                {
                    "problem":
                        "continuity",

                    "recommended_upgrade":
                        "Improve conversation recall",

                    "mission_state":
                        "proposal",
                }
            )

            report["id"] = (
                "improvement_001"
            )

            report["status"] = (
                "pending_review"
            )

            _improvement_state["reports"].append(
                report
            )

        return jsonify(
            {
                "ok": True,
                "reports":
                    _improvement_state["reports"],
            }
        )

    @app.post("/api/improvements/<improvement_id>/create-mission")
    def create_improvement_mission(improvement_id):

        for report in _improvement_state["reports"]:

            if report.get("id") == improvement_id:

                if report.get("status") != "approved":

                    return jsonify(
                        {
                            "ok": False,
                            "error":
                                "approval_required",
                        }
                    ), 403


                mission_proposal = {

                    "goal":
                        report.get(
                            "recommended_upgrade",
                            "Self improvement task",
                        ),

                    "type":
                        report.get(
                            "type",
                            "improvement_report",
                        ),

                    "approval_required":
                        report.get(
                            "approval_required",
                            True,
                        ),

                    "risk":
                        report.get(
                            "risk",
                            "unknown",
                        ),
                }


                mission_request = (
                    build_self_improvement_mission_request(
                        mission_proposal
                    )
                )


                mission = (
                    planner_service.create_mission(
                        mission_request["goal"]
                    )
                )


                report["mission_status"] = (
                    "created"
                )

                report["mission_id"] = (
                    mission.get("id")
                )


                return jsonify(
                    {
                        "ok": True,
                        "mission": mission,
                        "report": report,
                    }
                )


        return jsonify(
            {
                "ok": False,
                "error":
                    "improvement_not_found",
            }
        ), 404

    @app.post("/api/improvements/<improvement_id>/approve")
    def approve_improvement(improvement_id):

        for report in _improvement_state["reports"]:

            if report.get("id") == improvement_id:

                report["status"] = (
                    "approved"
                )

                return jsonify(
                    {
                        "ok": True,
                        "report": report,
                    }
                )


        return jsonify(
            {
                "ok": False,
                "error": "improvement_not_found",
            }
        ), 404



    @app.post("/api/improvements/<improvement_id>/reject")
    def reject_improvement(improvement_id):

        for report in _improvement_state["reports"]:

            if report.get("id") == improvement_id:

                report["status"] = (
                    "rejected"
                )

                return jsonify(
                    {
                        "ok": True,
                        "report": report,
                    }
                )


        return jsonify(
            {
                "ok": False,
                "error": "improvement_not_found",
            }
        ), 404