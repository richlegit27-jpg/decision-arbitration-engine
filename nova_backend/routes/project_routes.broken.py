from __future__ import annotations

from flask import Blueprint, jsonify, request

from nova_backend.services.project_builder_service import (
    ProjectBuilderService,
)
from nova_backend.services.project_workspace_service import (
    ProjectWorkspaceService,
)
from nova_backend.services.project_execution_controller import (
    ProjectExecutionController,
)


project_bp = Blueprint(
    "project_bp",
    __name__,
)


project_workspace_service = ProjectWorkspaceService()


project_builder_service = ProjectBuilderService(
    project_workspace_service
)


def register_project_routes(
app,
chat_execution_service=None,
):
project_execution_controller = (
ProjectExecutionController(
project_workspace_service=(
project_workspace_service
),
chat_execution_service=(
chat_execution_service
),
)
)

```
@project_bp.route(
    "/api/projects/build",
    methods=["POST"],
)
def build_project():
    data = request.get_json(
        silent=True
    ) or {}

    project_request = str(
        data.get(
            "request",
            "",
        )
    ).strip()

    owner_id = str(
        data.get(
            "owner_id",
            "default",
        )
    ).strip() or "default"

    project_id = data.get(
        "project_id"
    )

    if not project_request:
        return jsonify(
            {
                "ok": False,
                "error": "Project request required",
            }
        ), 400

    try:
        result = (
            project_builder_service
            .build_project_from_request(
                user_text=project_request,
                owner_id=owner_id,
                project_id=project_id,
            )
        )

        return jsonify(
            result
        )

    except ValueError as exc:
        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 400

    except Exception as exc:
        return jsonify(
            {
                "ok": False,
                "error": (
                    "Project build failed: "
                    f"{exc}"
                ),
            }
        ), 500

@project_bp.route(
    "/api/projects/<project_id>/brain",
    methods=["GET"],
)
def get_project_brain(
    project_id,
):
    brain = (
        project_workspace_service
        .get_project_brain_summary(
            project_id
        )
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

    decision = str(
        data.get(
            "decision",
            "",
        )
    ).strip()

    if not decision:
        return jsonify(
            {
                "ok": False,
                "error": "Decision required",
            }
        ), 400

    result = (
        project_workspace_service
        .add_project_decision(
            project_id,
            decision,
        )
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

    action = str(
        data.get(
            "action",
            "",
        )
    ).strip()

    if not action:
        return jsonify(
            {
                "ok": False,
                "error": "Action required",
            }
        ), 400

    result = (
        project_workspace_service
        .add_next_action(
            project_id,
            action,
        )
    )

    return jsonify(
        {
            "ok": True,
            "action": result,
        }
    )

@project_bp.route(
    "/api/projects/<project_id>/tasks/<task_id>",
    methods=["PATCH"],
)
def update_project_task(
    project_id,
    task_id,
):
    data = request.get_json(
        silent=True
    ) or {}

    status = str(
        data.get(
            "status",
            "",
        )
    ).strip().lower()

    allowed_statuses = {
        "open",
        "running",
        "completed",
        "blocked",
    }

    if status not in allowed_statuses:
        return jsonify(
            {
                "ok": False,
                "error": "Invalid task status",
            }
        ), 400

    task = (
        project_workspace_service
        .update_task_status(
            project_id,
            task_id,
            status,
        )
    )

    if not task:
        return jsonify(
            {
                "ok": False,
                "error": "Task not found",
            }
        ), 404

    return jsonify(
        {
            "ok": True,
            "task": task,
        }
    )

@project_bp.route(
    "/api/projects/<project_id>",
    methods=["DELETE"],
)
def delete_project(
    project_id,
):
    result = (
        project_workspace_service
        .delete_project(
            project_id
        )
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
    result = (
        project_workspace_service
        .set_active_project(
            project_id
        )
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
    "/api/projects/<project_id>/execution",
    methods=["GET"],
)
def get_project_execution(
    project_id,
):
    result = (
        project_execution_controller.get_state(
            project_id
        )
    )

    if result is None:
        return jsonify(
            {
                "ok": False,
                "error": "Project not found",
            }
        ), 404

    return jsonify(
        {
            "ok": True,
            **result,
        }
    )

@project_bp.route(
    "/api/projects/<project_id>/continue",
    methods=["POST"],
)
def continue_project_execution(
    project_id,
):
    result = (
        project_execution_controller.continue_project(
            project_id
        )
    )

    if result is None:
        return jsonify(
            {
                "ok": False,
                "error": "Project not found",
            }
        ), 404

    return jsonify(
        {
            "ok": True,
            **result,
        }
    )

@project_bp.route(
    "/api/projects/<project_id>/run-all",
    methods=["POST"],
)
def run_all_project_execution(
    project_id,
):
    print(
        "[PROJECT RUN-ALL ROUTE ENTERED]",
        project_id,
        flush=True,
    )

    result = (
        project_execution_controller.run_all(
            project_id
        )
    )

    if result is None:
        return jsonify(
            {
                "ok": False,
                "error": "Project not found",
            }
        ), 404

    return jsonify(
        {
            "ok": True,
            **result,
        }
    )

@project_bp.route(
    "/api/projects/<project_id>/pause",
    methods=["POST"],
)
def pause_project_execution(
    project_id,
):
    result = (
        project_execution_controller.pause_project(
            project_id
        )
    )

    if result is None:
        return jsonify(
            {
                "ok": False,
                "error": "Project not found",
            }
        ), 404

    return jsonify(
        {
            "ok": True,
            **result,
        }
    )

@project_bp.route(
    "/api/projects/<project_id>/stop",
    methods=["POST"],
)
def stop_project_execution(
    project_id,
):
    result = (
        project_execution_controller.stop_project(
            project_id
        )
    )

    if result is None:
        return jsonify(
            {
                "ok": False,
                "error": "Project not found",
            }
        ), 404

    return jsonify(
        {
            "ok": True,
            **result,
        }
    )

app.register_blueprint(
    project_bp
)
```
