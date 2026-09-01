from __future__ import annotations

from flask import Blueprint, jsonify, request

from nova_backend.services.project_workspace_service import (
    project_workspace_service,
)


project_bp = Blueprint(
    "project_bp",
    __name__,
)


def register_project_routes(
    app,
):

    @project_bp.route(
        "/api/projects/<project_id>/brain",
        methods=["GET"],
    )
    def get_project_brain(
        project_id,
    ):
        brain = project_workspace_service.get_project_brain_summary(
            project_id
        )

        if not brain:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "brain": brain,
            }
        )

    @project_bp.route(
        "/api/projects/<project_id>/decision",
        methods=["POST"],
    )
    def add_project_decision(
        project_id,
    ):
        data = request.get_json(
            silent=True
        ) or {}

        decision = data.get(
            "decision",
            "",
        )

        if not decision:
            return jsonify(
                {
                    "ok": False,
                    "error": "Decision required",
                }
            ), 400

        result = project_workspace_service.add_project_decision(
            project_id,
            decision,
        )

        return jsonify(
            {
                "ok": True,
                "decision": result,
            }
        )

    @project_bp.route(
        "/api/projects/<project_id>/next-action",
        methods=["POST"],
    )
    def add_next_action(
        project_id,
    ):
        data = request.get_json(
            silent=True
        ) or {}

        action = data.get(
            "action",
            "",
        )

        if not action:
            return jsonify(
                {
                    "ok": False,
                    "error": "Action required",
                }
            ), 400

        result = project_workspace_service.add_next_action(
            project_id,
            action,
        )

        return jsonify(
            {
                "ok": True,
                "action": result,
            }
        )

    @project_bp.route(
        "/api/projects/<project_id>",
        methods=["DELETE"],
    )
    def delete_project(
        project_id,
    ):
        result = project_workspace_service.delete_project(
            project_id
        )

        if not result:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "project": result,
            }
        )

    @project_bp.route(
        "/api/projects/<project_id>/activate",
        methods=["POST"],
    )
    def activate_project(
        project_id,
    ):
        result = project_workspace_service.set_active_project(
            project_id
        )

        if not result:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "project": result,
            }
        )

    app.register_blueprint(
        project_bp
    )