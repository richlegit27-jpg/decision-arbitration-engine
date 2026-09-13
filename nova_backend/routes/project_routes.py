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
    project_execution_controller=None,
):
    if project_execution_controller is None:
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

    @project_bp.route(
        "/api/projects/<project_id>/reset",
        methods=["POST"],
    )
    def reset_project_execution(project_id):
        result = (
            project_execution_controller
            .reset_execution_state(project_id)
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

        project_id = data.get("project_id")

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
                )
            )

            return jsonify(result)

        except ValueError as exc:
            return jsonify(
                {
                    "ok": False,
                    "error": str(exc),
                }
            ), 400

        except Exception as exc:
            import traceback

            traceback.print_exc()

            return jsonify(
                {
                    "ok": False,
                    "error": f"Project build failed: {exc}",
                }
            ), 500

    @project_bp.route(
        "/api/projects/<project_id>/brain",
        methods=["GET"],
    )
    def get_project_brain(project_id):
        brain = (
            project_workspace_service
            .get_project_brain_summary(project_id)
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
        "/api/projects/<project_id>/phases",
        methods=["GET"],
    )
    def list_project_phases(
        project_id,
    ):
        phases = (
            project_workspace_service
            .list_phases(
                project_id
            )
        )

        if phases is None:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "phases": phases,
            }
        )


    @project_bp.route(
        "/api/projects/<project_id>/phases",
        methods=["POST"],
    )
    def add_project_phase(
        project_id,
    ):
        data = request.get_json(
            silent=True
        ) or {}

        title = str(
            data.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            return jsonify(
                {
                    "ok": False,
                    "error": "Phase title is required",
                }
            ), 400

        phase = (
            project_workspace_service
            .add_phase(
                project_id,
                title,
                data.get(
                    "description",
                    "",
                ),
                data.get(
                    "status",
                    "planned",
                ),
                data.get(
                    "order",
                ),
                data.get(
                    "goal",
                    "",
                ),
                data.get(
                    "milestone",
                    "",
                ),
            )
        )

        if not phase:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "phase": phase,
            }
        ), 201


    @project_bp.route(
        "/api/projects/<project_id>/phases/<phase_id>",
        methods=["GET"],
    )
    def get_project_phase(
        project_id,
        phase_id,
    ):
        phase = (
            project_workspace_service
            .get_phase(
                project_id,
                phase_id,
            )
        )

        if not phase:
            return jsonify(
                {
                    "ok": False,
                    "error": "Phase not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "phase": phase,
            }
        )


    @project_bp.route(
        "/api/projects/<project_id>/phases/<phase_id>",
        methods=["PATCH"],
    )
    def update_project_phase(
        project_id,
        phase_id,
    ):
        data = request.get_json(
            silent=True
        ) or {}

        allowed_fields = {
            "title",
            "description",
            "status",
            "order",
            "goal",
            "milestone",
        }

        updates = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }

        if not updates:
            return jsonify(
                {
                    "ok": False,
                    "error": "No valid phase updates supplied",
                }
            ), 400

        phase = (
            project_workspace_service
            .update_phase(
                project_id,
                phase_id,
                updates,
            )
        )

        if not phase:
            return jsonify(
                {
                    "ok": False,
                    "error": "Phase not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "phase": phase,
            }
        )


    @project_bp.route(
        "/api/projects/<project_id>/phases/<phase_id>",
        methods=["DELETE"],
    )
    def delete_project_phase(
        project_id,
        phase_id,
    ):
        deleted = (
            project_workspace_service
            .delete_phase(
                project_id,
                phase_id,
            )
        )

        if not deleted:
            return jsonify(
                {
                    "ok": False,
                    "error": "Phase not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "deleted": True,
                "phase_id": phase_id,
            }
        )


    @project_bp.route(
        "/api/projects/<project_id>/tasks/intelligence",
        methods=["GET"],
    )
    def get_project_task_intelligence(
        project_id,
    ):
        intelligence = (
            project_workspace_service
            .get_task_intelligence(
                project_id
            )
        )

        if intelligence is None:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "intelligence": intelligence,
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
            data.get("status", "")
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
        "/api/projects/<project_id>/tasks",
        methods=["POST"],
    )
    def add_project_task(
        project_id,
    ):
        data = request.get_json(
            silent=True
        ) or {}

        task = (
            project_workspace_service
            .add_task(
                project_id=project_id,
                title=data.get(
                    "title",
                    "New Task",
                ),
                priority=data.get(
                    "priority",
                    "medium",
                ),
                description=data.get(
                    "description",
                    "",
                ),
                action=data.get(
                    "action",
                    "",
                ),
                execution_mode=data.get(
                    "execution_mode",
                    "",
                ),
                target_file=data.get(
                    "target_file",
                    "",
                ),
                target_files=data.get(
                    "target_files",
                    [],
                ),
                target_function=data.get(
                    "target_function",
                    "",
                ),
                dependencies=data.get(
                    "dependencies",
                    [],
                ),
                expected_output=data.get(
                    "expected_output",
                    "",
                ),
                completion_criteria=data.get(
                    "completion_criteria",
                    [],
                ),
                phase_id=data.get(
                    "phase_id",
                    "",
                ),
                steps=data.get(
                    "steps",
                    [],
                ),
                content=data.get(
                    "content",
                    "",
                ),
                code=data.get(
                    "code",
                    "",
                ),
                replacement=data.get(
                    "replacement",
                    "",
                ),
                command=data.get(
                    "command",
                    "",
                ),
            )
        )

        if not task:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        return jsonify(
            {
                "ok": True,
                "task": task,
            }
        )
    @project_bp.route(
        "/api/projects/<project_id>/tasks/<task_id>",
        methods=["DELETE"],
    )
    def delete_project_task(
        project_id,
        task_id,
    ):
        deleted = (
            project_workspace_service
            .delete_task(
                project_id,
                task_id,
            )
        )

        if not deleted:
            return jsonify(
                {
                    "ok": False,
                    "error": "Task not found",
                }
            ), 404

        project_workspace_service.add_activity(
            project_id,
            "Task deleted",
            task_id,
        )

        return jsonify(
            {
                "ok": True,
                "deleted": True,
                "task_id": task_id,
            }
        )

    @project_bp.route(
        "/api/projects/<project_id>/activate",
        methods=["POST"],
    )


    def activate_project(project_id):
        result = (
            project_workspace_service
            .set_active_project(project_id)
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
    def get_project_execution(project_id):
        result = (
            project_execution_controller
            .get_state(project_id)
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
    def continue_project_execution(project_id):
        result = (
            project_execution_controller
            .continue_project(project_id)
        )

        if result is None:
            return jsonify(
                {
                    "ok": False,
                    "error": "Project not found",
                }
            ), 404

        execution = (
            result.get("execution")
            or result.get("execution_state")
            or {}
        )

        execution_status = str(
            execution.get("status")
            or ""
        ).strip().lower()

        ok = (
            execution_status
            not in {
                "failed",
                "error",
                "blocked",
            }
        )

        return jsonify(
            {
                "ok": ok,
                **result,
            }
        )

    @project_bp.route(
        "/api/projects/<project_id>/run-all",
        methods=["POST"],
    )
    def run_all_project_execution(project_id):
        print(
            "[PROJECT RUN-ALL ROUTE ENTERED]",
            project_id,
            flush=True,
        )

        result = (
            project_execution_controller
            .run_all(project_id)
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
    def pause_project_execution(project_id):
        result = (
            project_execution_controller
            .pause_project(project_id)
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

    app.register_blueprint(project_bp)










