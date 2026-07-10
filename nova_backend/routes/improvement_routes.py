from flask import jsonify

from nova_backend.services.nova_improvement_report_service import (
    create_improvement_report,
)


def register_improvement_routes(app):

    @app.get("/api/improvements")
    def nova_improvements_api():

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

        return jsonify(
            {
                "ok": True,
                "reports": [
                    report
                ],
            }
        )