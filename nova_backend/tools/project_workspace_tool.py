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

        if field == "name":
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