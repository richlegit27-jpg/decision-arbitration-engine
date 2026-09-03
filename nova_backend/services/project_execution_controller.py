from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from nova_backend.services.project_artifact_publisher_service import (
    ProjectArtifactPublisherService,
)


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
        chat_execution_service=None,
    ):
        self.project_workspace_service = (
            project_workspace_service
        )

        self.chat_execution_service = (
            chat_execution_service
        )

        self.artifact_publisher = (
            ProjectArtifactPublisherService(
                project_workspace_service=(
                    project_workspace_service
                )
            )
        )

    def _now(self):
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _sandbox_dir(self):
        sandbox_dir = (
            Path(__file__).resolve().parents[1]
            / "sandbox"
        ).resolve()

        sandbox_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return sandbox_dir

    def _resolve_sandbox_target(
        self,
        target_file,
    ):
        target = str(
            target_file or ""
        ).strip()

        if not target:
            return None

        sandbox_dir = self._sandbox_dir()

        candidate = (
            sandbox_dir / target
        ).resolve()

        try:
            candidate.relative_to(
                sandbox_dir
            )
        except ValueError:
            return None

        return candidate

    def _write_task_file(
        self,
        task,
    ):
        if not isinstance(
            task,
            dict,
        ):
            return None

        target_file = str(
            task.get(
                "target_file",
                "",
            )
            or ""
        ).strip()

        content = task.get(
            "content",
            None,
        )

        if not target_file:
            return None

        if content is None:
            return None

        target = self._resolve_sandbox_target(
            target_file
        )

        if target is None:
            return None

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            str(content),
            encoding="utf-8",
        )

        return str(target)

    def _materialize_task_files(
        self,
        tasks,
    ):
        written_files = []

        if not isinstance(
            tasks,
            list,
        ):
            return written_files

        for task in tasks:
            try:
                written_file = (
                    self._write_task_file(
                        task
                    )
                )

                if written_file:
                    written_files.append(
                        written_file
                    )

            except Exception as exc:
                print(
                    "[PROJECT FILE WRITE FAILED]",
                    exc,
                    flush=True,
                )

        return written_files

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
                "failed",
                "blocked",
            }
        ]

    def _get_execution_service(self):
        return self.chat_execution_service

    def _build_execution_steps(
        self,
        tasks,
    ):
        steps = []

        for task in tasks:
            task_id = task.get("id")

            if not task_id:
                continue

            title = str(
                task.get(
                    "title",
                    "Project task",
                )
            ).strip()

            description = str(
                task.get(
                    "description",
                    "",
                )
            ).strip()

            step = {
                "id": f"project_task_{task_id}",
                "task_id": task_id,
                "title": title or "Project task",
                "description": description,
                "action": task.get(
                    "action",
                    "analysis",
                ),
                "status": "pending",
            }

            if task.get("target_file"):
                step["target_file"] = task.get(
                    "target_file"
                )

            if task.get("content"):
                step["content"] = task.get(
                    "content"
                )

            if task.get("command"):
                step["command"] = task.get(
                    "command"
                )

            steps.append(step)

        return steps

    def _execute_with_existing_orchestrator(
        self,
        project_id,
        tasks,
        command,
    ):
        execution_service = (
            self._get_execution_service()
        )

        if execution_service is None:
            return {
                "ok": False,
                "error": (
                    "The existing execution service "
                    "is unavailable."
                ),
            }

        steps = self._build_execution_steps(
            tasks
        )

        if not steps:
            return {
                "ok": True,
                "execution": {},
                "message": "No runnable project tasks remain.",
            }

        task_ids = [
            str(
                task.get(
                    "id"
                )
            )
            for task in tasks
            if isinstance(
                task,
                dict,
            )
            and task.get(
                "id"
            )
        ]

        task_key = (
            task_ids[0]
            if task_ids
            else command
        )

        session_id = (
            f"project:{project_id}:{task_key}"
        )

        project = self._get_project(
            project_id
        ) or {}

        goal = project.get(
            "name",
            "Project execution",
        )

        context = {
            "project_id": project_id,
            "task_type": "project_execution",
            "command": command,
        }

        try:
            print(
                "[PROJECT EXECUTION] starting",
                {
                    "session_id": session_id,
                    "command": command,
                    "goal": goal,
                    "step_count": len(steps),
                },
                flush=True,
            )

            execution_service.start(
                session_id=session_id,
                goal=goal,
                steps=steps,
                context=context,
            )

            print(
                "[PROJECT EXECUTION] start completed",
                session_id,
                flush=True,
            )

            if command == "run_all":
                print(
                    "[PROJECT EXECUTION] calling run_all",
                    session_id,
                    flush=True,
                )

                execution = execution_service.run_all(
                    session_id=session_id
                )

                print(
                    "[PROJECT EXECUTION] run_all returned",
                    type(execution),
                    flush=True,
                )
            else:
                print(
                    "[PROJECT EXECUTION] calling advance",
                    session_id,
                    flush=True,
                )

                execution = execution_service.advance(
                    session_id=session_id
                )

                print(
                    "[PROJECT EXECUTION] advance returned",
                    type(execution),
                    flush=True,
                )

        except Exception as exc:
            print(
                "[PROJECT EXECUTION ERROR]",
                repr(exc),
                flush=True,
            )

            return {
                "ok": False,
                "error": (
                    "Project execution failed: "
                    f"{exc}"
                ),
            }

        if not isinstance(
            execution,
            dict,
        ):
            return {
                "ok": False,
                "error": (
                    "The execution service "
                    "returned no result."
                ),
            }

        return {
            "ok": True,
            "execution": execution,
            "assistant_message": {
                "role": "assistant",
                "text": (
                    execution_service.format_reply(
                        execution
                    )
                ),
            },
        }

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
            task_statuses = {
                str(
                    task.get(
                        "status",
                        "",
                    )
                ).strip().lower()
                for task in tasks
                if isinstance(
                    task,
                    dict,
                )
            }

            if "failed" in task_statuses:
                final_status = "failed"
                message = (
                    "Project execution ended with "
                    "failed tasks."
                )

            elif "blocked" in task_statuses:
                final_status = "blocked"
                message = (
                    "Project execution is blocked."
                )

            else:
                final_status = "completed"
                message = (
                    "Project completed successfully."
                )

            execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status=final_status,
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
                "message": message,
            }

        project_execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        current_task_id = (
            project_execution.get(
                "current_task_id"
            )
        )

        runnable_by_id = {
            task.get("id"): task
            for task in runnable
            if task.get("id")
        }

        current_task = runnable_by_id.get(
            current_task_id
        )

        if current_task is None:
            current_task = runnable[0]

        current_task_id = (
            current_task.get("id")
        )

        queue = [
            task.get("id")
            for task in runnable
            if task.get("id")
        ]

        self.project_workspace_service.update_execution_state(
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

        self._materialize_task_files(
            [current_task]
        )

        result = self._execute_with_existing_orchestrator(
            project_id=project_id,
            tasks=[current_task],
            command="run_step",
        )
        self._sync_project_execution(
            project_id,
            result,
            "continue",
        )

        published_artifacts = (
            self._publish_completed_artifacts(
                project_id,
                [current_task],
                result,
            )
        )

        return {
            "project_id": project_id,
            "action": "continue",           
            "artifacts": published_artifacts,
            "execution": (
                self.project_workspace_service
                .get_execution_state(
                    project_id
                )
            ),
            "message": (
                result.get(
                    "assistant_message",
                    {},
                ).get(
                    "text",
                    "Project execution continued.",
                )
                if isinstance(
                    result,
                    dict,
                )
                else "Project execution continued."
            ),
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


        if not runnable:
            execution = (
                self.project_workspace_service
                .get_execution_state(
                    project_id
                )
            )

            return {
                "ok": True,
                "project_id": project_id,
                "action": "run_all",
                "artifacts": [],
                "execution": execution,
                "message": "Project has no remaining runnable tasks.",
            }
        queue = [
            task.get("id")
            for task in runnable
            if task.get("id")
        ]

        current_task = runnable[0]

        self.project_workspace_service.update_execution_state(
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

        print(
            "[PROJECT RUN-ALL MATERIALIZE INPUT]",
            [
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "target_file": task.get("target_file"),
                    "content": task.get("content"),
                }
                for task in runnable
            ],
            flush=True,
        )

        print(
            "[PROJECT RUN-ALL BEFORE MATERIALIZE]",
            flush=True,
        )

        self._materialize_task_files(
            runnable
        )

        print(
            "[PROJECT RUN-ALL AFTER MATERIALIZE]",
            flush=True,
        )

        print(
            "[PROJECT RUN-ALL BEFORE ORCHESTRATOR]",
            flush=True,
        )

        result = self._execute_with_existing_orchestrator(
            project_id=project_id,
            tasks=runnable,
            command="run_all",
        )

        print(
            "[PROJECT RUN-ALL AFTER ORCHESTRATOR]",
            type(result),
            flush=True,
        )

        print(
            "[PROJECT RUN-ALL BEFORE PUBLISH]",
            flush=True,
        )

        published_artifacts = (
            self._publish_completed_artifacts(
                project_id,
                runnable,
                result,
            )
        )

        print(
            "[PROJECT RUN-ALL AFTER PUBLISH]",
            len(published_artifacts),
            flush=True,
        )

        print(
            "[PROJECT RUN-ALL BEFORE SYNC]",
            flush=True,
        )

        self._sync_project_execution(
            project_id,
            result,
            "run_all",
        )

        print(
            "[PROJECT RUN-ALL AFTER SYNC]",
            flush=True,
        )

        execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
        )

        message = (
            result.get(
                "assistant_message",
                {},
            ).get(
                "text",
                "Project execution completed.",
            )
            if isinstance(
                result,
                dict,
            )
            else "Project execution completed."
        )

        return {
            "project_id": project_id,
            "action": "run_all",
            "artifacts": published_artifacts,
            "execution": execution,
            "message": message,
        }

    def _publish_completed_artifacts(
        self,
        project_id,
        tasks,
        result,
    ):
        if not isinstance(
            result,
            dict,
        ):
            return []

        execution = result.get(
            "execution"
        )

        if not isinstance(
            execution,
            dict,
        ):
            return []

        steps = execution.get(
            "steps",
            []
        )

        if not isinstance(
            steps,
            list,
        ):
            return []

        task_by_id = {
            str(task.get("id")): task
            for task in tasks
            if isinstance(
                task,
                dict,
            )
            and task.get("id")
        }

        published = []

        for step in steps:
            if not isinstance(
                step,
                dict,
            ):
                continue

            status = str(
                step.get(
                    "status",
                    "",
                )
            ).strip().lower()

            if status not in {
                "completed",
                "done",
            }:
                continue

            task_id = step.get(
                "task_id"
            )

            if not task_id:
                continue

            task = task_by_id.get(
                str(task_id)
            )

            if not task:
                continue

            artifact = (
                self.artifact_publisher
                .publish_task_artifact(
                    project_id,
                    task,
                    result=step.get("result"),
                )
            )
            if artifact:
                published.append(
                    artifact
                )

        return published

    def _sync_project_execution(
        self,
        project_id,
        result,
        action,
    ):
        if not isinstance(
            result,
            dict,
        ):
            return

        execution = result.get(
            "execution"
        )

        if not isinstance(
            execution,
            dict,
        ):
            return

        steps = execution.get(
            "steps",
            []
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        project = self._get_project(
            project_id
        )

        if not project:
            return

        # First synchronize task statuses from the execution
        # service back into the project task list.
        for step in steps:
            if not isinstance(
                step,
                dict,
            ):
                continue

            task_id = step.get(
                "task_id"
            )

            if not task_id:
                continue

            status = str(
                step.get(
                    "status",
                    "",
                )
            ).strip().lower()

            if status in {
                "completed",
                "done",
            }:
                self.project_workspace_service.update_task_status(
                    project_id,
                    task_id,
                    "completed",
                )

            elif status in {
                "failed",
                "blocked",
            }:
                self.project_workspace_service.update_task_status(
                    project_id,
                    task_id,
                    "failed",
                )

        # Reload the project after task status updates.
        project = self._get_project(
            project_id
        ) or {}

        latest_tasks = self._get_tasks(
            project
        )

        remaining_tasks = self._runnable_tasks(
            latest_tasks
        )

        execution_status = str(
            execution.get(
                "status",
                "",
            )
        ).strip().lower()

        # A failed or blocked execution stops the project.
        if execution_status in {
            "failed",
            "blocked",
        }:
            queue = [
                task.get("id")
                for task in remaining_tasks
                if task.get("id")
            ]

            self.project_workspace_service.update_execution_state(
                project_id,
                status=execution_status,
                current_task_id=(
                    queue[0]
                    if queue
                    else None
                ),
                current_step=(
                    next(
                        (
                            task.get(
                                "title",
                                "",
                            )
                            for task in remaining_tasks
                            if task.get("id")
                            == queue[0]
                        ),
                        "",
                    )
                    if queue
                    else ""
                ),
                queue=queue,
                last_action=action,
            )

            return

        # Waiting for approval pauses the project.
        if execution_status == "waiting_approval":
            queue = [
                task.get("id")
                for task in remaining_tasks
                if task.get("id")
            ]

            next_task = (
                remaining_tasks[0]
                if remaining_tasks
                else None
            )

            self.project_workspace_service.update_execution_state(
                project_id,
                status="paused",
                current_task_id=(
                    next_task.get("id")
                    if next_task
                    else None
                ),
                current_step=(
                    next_task.get(
                        "title",
                        "",
                    )
                    if next_task
                    else ""
                ),
                queue=queue,
                last_action=action,
            )

            return

        # If no runnable tasks remain, the project is complete.
        if not remaining_tasks:
            self.project_workspace_service.update_execution_state(
                project_id,
                status="completed",
                current_task_id=None,
                current_step="",
                queue=[],
                last_action=action,
            )

            return

        # The current execution finished successfully, so advance
        # the project to the next remaining task.
        next_task = remaining_tasks[0]

        queue = [
            task.get("id")
            for task in remaining_tasks
            if task.get("id")
        ]

        self.project_workspace_service.update_execution_state(
            project_id,
            status="running",
            current_task_id=next_task.get(
                "id"
            ),
            current_step=next_task.get(
                "title",
                "",
            ),
            queue=queue,
            last_action=action,
        )

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





