from flask import request, jsonify

from nova_backend.services.project_brain_decision_log_route_contract import (
    build_decision_log_api_payload,
    extract_user_text,
    is_decision_log_question,
)


def install_project_brain_decision_log_route(app):

    @app.post("/api/project-brain/decision-log")
    def project_brain_decision_log_route():

        try:
            data = request.get_json(silent=True) or {}

            user_text = extract_user_text(data)

            if not is_decision_log_question(user_text):
                return jsonify(
                    {
                        "ok": False,
                        "error": "not_decision_log_question",
                    }
                ), 400

            payload = build_decision_log_api_payload(
                user_text
            )

            return jsonify(payload)

        except Exception as exc:
            return jsonify(
                {
                    "ok": False,
                    "error": str(exc),
                }
            ), 500


    print(
        "[NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_SERVICE] installed"
    )