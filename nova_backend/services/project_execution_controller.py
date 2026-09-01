from __future__ import annotations

from datetime import datetime, timezone


class ProjectExecutionController:

    VALID_ACTIONS = {
        "continue",
        "run_all",
        "pause",
        "stop",
    }

    def __init__(
        self,
        project_workspace_service,
    ):
        self.project_workspace_service = (
            project_workspace_service
        )

    def _now(self):
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _get_project(
        self,
        project_id,
    ):
        return self.project_workspace_service.get_project(
            project_id
        )

    def _get_tasks(
        self,
        project,
    ):
        tasks = project.get(
            "tasks",
            []
        )

        if not isinstance(
            tasks,
            list,
        ):
            return []

        return [
            task
            for task in tasks
            if isinstance(
                task,
                dict,
            )
        ]

    def _runnable_tasks(
        self,
        tasks,
    ):
        return [
            task
            for task in tasks
            if str(
                task.get(
                    "status",
                    "open",
                )
            ).strip().lower()
            not in {
                "completed",
                "done",
                "cancelled",
            }
        ]

    def get_state(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return None

        execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
        )

        return {
            "project_id": project_id,
            "execution": execution,
            "tasks": self._get_tasks(
                project
            ),
        }

    def continue_project(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return None

        tasks = self._get_tasks(
            project
        )

        runnable = self._runnable_tasks(
            tasks
        )

        if not runnable:
            execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status="completed",
                    current_task_id=None,
                    current_step=None,
                    queue=[],
                    last_action="continue",
                )
            )

            return {
                "project_id": project_id,
                "action": "continue",
                "execution": execution,
                "message": "No runnable tasks remain.",
            }

        execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        current_task_id = execution.get(
            "current_task_id"
        )

        current_task = next(
            (
                task
                for task in runnable
                if task.get("id")
                == current_task_id
            ),
            None,
        )

        if current_task is None:
            current_task = runnable[0]

        queue = [
            task.get("id")
            for task in runnable
            if task.get("id")
        ]

        updated = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="running",
                current_task_id=current_task.get(
                    "id"
                ),
                current_step=current_task.get(
                    "title",
                    "Current task",
                ),
                queue=queue,
                last_action="continue",
            )
        )

        self.project_workspace_service.add_activity(
            project_id,
            "Project execution continued",
            current_task.get(
                "title",
                "Current task",
            ),
        )

        return {
            "project_id": project_id,
            "action": "continue",
            "execution": updated,
            "message": "Project execution continued.",
        }

    def run_all(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return None

        tasks = self._get_tasks(
            project
        )

        runnable = self._runnable_tasks(
            tasks
        )

        queue = [
            task.get("id")
            for task in runnable
            if task.get("id")
        ]

        if not runnable:
            updated = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status="completed",
                    current_task_id=None,
                    current_step=None,
                    queue=[],
                    last_action="run_all",
                )
            )

            return {
                "project_id": project_id,
                "action": "run_all",
                "execution": updated,
                "message": "No runnable tasks remain.",
            }

        current_task = runnable[0]

        updated = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="running",
                current_task_id=current_task.get(
                    "id"
                ),
                current_step=current_task.get(
                    "title",
                    "Current task",
                ),
                queue=queue,
                last_action="run_all",
            )
        )

        self.project_workspace_service.add_activity(
            project_id,
            "Project execution started",
            (
                f"Run All queued "
                f"{len(queue)} task(s)."
            ),
        )

        return {
            "project_id": project_id,
            "action": "run_all",
            "execution": updated,
            "message": (
                f"Queued {len(queue)} task(s) "
                "for project execution."
            ),
        }

    def pause_project(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return None

        execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        updated = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="paused",
                current_task_id=execution.get(
                    "current_task_id"
                ),
                current_step=execution.get(
                    "current_step"
                ),
                queue=execution.get(
                    "queue",
                    [],
                ),
                last_action="pause",
            )
        )

        self.project_workspace_service.add_activity(
            project_id,
            "Project execution paused",
            execution.get(
                "current_step",
                "",
            ),
        )

        return {
            "project_id": project_id,
            "action": "pause",
            "execution": updated,
            "message": "Project execution paused.",
        }

    def stop_project(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return None

        updated = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="stopped",
                current_task_id=None,
                current_step="Stopped",
                queue=[],
                last_action="stop",
            )
        )

        self.project_workspace_service.add_activity(
            project_id,
            "Project execution stopped",
            "",
        )

        return {
            "project_id": project_id,
            "action": "stop",
            "execution": updated,
            "message": "Project execution stopped.",
        }

    def control(
        self,
        project_id,
        action,
    ):
        action = str(
            action or ""
        ).strip().lower()

        if action not in self.VALID_ACTIONS:
            return None

        if action == "continue":
            return self.continue_project(
                project_id
            )

        if action == "run_all":
            return self.run_all(
                project_id
            )

        if action == "pause":
            return self.pause_project(
                project_id
            )

        if action == "stop":
            return self.stop_project(
                project_id
            )

        return None