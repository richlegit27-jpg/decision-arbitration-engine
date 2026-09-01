from __future__ import annotations

from nova_backend.tools.base import NovaTool


class ProjectWorkspaceTool(NovaTool):
    name = "project_workspace_update"

    description = (
        "Updates Nova project workspace state."
    )

    def run(
        self,
        project_id="",
        field="",
        value="",
        **kwargs,
    ):
        from nova_backend.services.project_workspace_service import (
            ProjectWorkspaceService,
        )

        service = ProjectWorkspaceService()

        project_id = str(
            project_id or ""
        ).strip()

        field = str(
            field or ""
        ).strip().lower()

        if not project_id:
            return {
                "ok": False,
                "error": "project_id_required",
            }

        if field not in {
            "name",
            "description",
            "status",
        }:
            return {
                "ok": False,
                "error": "unsupported_field",
                "field": field,
            }

        # Never allow structured state objects to become
        # project field strings.
        if isinstance(value, (dict, list, tuple, set)):
            return {
                "ok": False,
                "error": "invalid_field_value",
                "field": field,
                "message": (
                    "Project field values must be plain text."
                ),
            }

        value = str(
            value if value is not None else ""
        ).strip()

        if field == "name":
            if not value:
                return {
                    "ok": False,
                    "error": "project_name_required",
                }

            return service.update_project(
                project_id,
                name=value,
            )

        if field == "description":
            return service.update_project(
                project_id,
                description=value,
            )

        if field == "status":
            return service.update_project(
                project_id,
                status=value,
            )

        return {
            "ok": False,
            "error": "unsupported_field",
            "field": field,
        }