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

    def _normalize_task_action(
        self,
        action,
    ):
        action = str(
            action or "analysis"
        ).strip().lower()

        action_aliases = {
            # Implementation actions.
            "write": "implement",
            "create": "implement",
            "modify": "implement",
            "update": "implement",
            "build": "implement",
            "code": "implement",
            "edit": "implement",

            # Documentation actions.
            "document": "implement",
            "documentation": "implement",

            # Analysis actions.
            "analyse": "analysis",
            "analyze": "analysis",
            "research": "analysis",

            # Design/planning actions.
            "plan": "design",
            "planning": "design",
            "architect": "design",

            # Verification actions.
            "verify": "test",
            "validate": "test",
            "validation": "test",
            "check": "test",
        }

        return action_aliases.get(
            action,
            action,
        )

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
        """
        Return tasks that are eligible for execution.

        A task is runnable only when:

        - it is not already finished or blocked
        - all declared dependencies are completed
        """

        if not isinstance(
            tasks,
            list,
        ):
            return []

        completed_ids = set()
        completed_titles = set()

        terminal_statuses = {
            "completed",
            "done",
        }

        for task in tasks:

            if not isinstance(
                task,
                dict,
            ):
                continue

            status = str(
                task.get(
                    "status",
                    "open",
                )
            ).strip().lower()

            if status in terminal_statuses:

                task_id = str(
                    task.get(
                        "id",
                        "",
                    )
                ).strip()

                task_title = str(
                    task.get(
                        "title",
                        "",
                    )
                ).strip().lower()

                if task_id:
                    completed_ids.add(
                        task_id
                    )

                if task_title:
                    completed_titles.add(
                        task_title
                    )

        runnable = []

        non_runnable_statuses = {
            "completed",
            "done",
            "cancelled",
            "canceled",
            "blocked",
            "failed",
        }

        for task in tasks:

            if not isinstance(
                task,
                dict,
            ):
                continue

            status = str(
                task.get(
                    "status",
                    "open",
                )
            ).strip().lower()

            if status in non_runnable_statuses:
                continue

            dependencies = task.get(
                "dependencies",
                [],
            )

            if not isinstance(
                dependencies,
                list,
            ):
                dependencies = []

            dependencies_satisfied = True

            for dependency in dependencies:

                dependency_value = str(
                    dependency or ""
                ).strip()

                if not dependency_value:
                    continue

                if (
                    dependency_value not in completed_ids
                    and dependency_value.lower()
                    not in completed_titles
                ):
                    dependencies_satisfied = False
                    break

            if dependencies_satisfied:

                runnable.append(
                    task
                )

        return runnable

    def _get_execution_service(self):
        return self.chat_execution_service

    def _build_execution_steps(
        self,
        tasks,
    ):
        steps = []

        if not isinstance(
            tasks,
            list,
        ):
            return steps

        execution_fields = (
            "execution_mode",
            "dependencies",
            "expected_output",
            "completion_criteria",
            "target_file",
            "target_files",
            "target_function",
            "content",
            "code",
            "replacement",
            "command",
        )

        for task in tasks:
            if not isinstance(
                task,
                dict,
            ):
                continue

            task_id = task.get(
                "id"
            )

            if not task_id:
                continue

            title = str(
                task.get(
                    "title",
                    "Project task",
                )
                or "Project task"
            ).strip()

            description = str(
                task.get(
                    "description",
                    "",
                )
                or ""
            ).strip()

            action = self._normalize_task_action(
                task.get(
                    "action",
                    "analysis",
                )
            )

            step = {
                "id": (
                    f"project_task_{task_id}"
                ),
                "task_id": str(
                    task_id
                ),
                "title": (
                    title
                    or "Project task"
                ),
                "description": description,
                "action": action,
                "status": "pending",
            }

            for field_name in execution_fields:
                value = task.get(
                    field_name
                )

                if value not in (
                    None,
                    "",
                    [],
                ):
                    step[field_name] = value

            steps.append(
                step
            )

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

            print(
                "[PROJECT EXECUTION RAW RESULT]",
                execution,
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

        print(
            "[PROJECT RUN-ALL TASKS BEFORE FILTER]",
            [
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "status": task.get("status"),
                }
                for task in tasks
                if isinstance(task, dict)
            ],
            flush=True,
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

        all_published_artifacts = []
        last_result = None
        loop_guard = 0
        max_loops = 100

        while loop_guard < max_loops:
            loop_guard += 1

            project = self._get_project(
                project_id
            )

            if not project:
                break

            tasks = self._get_tasks(
                project
            )

            runnable = self._runnable_tasks(
                tasks
            )

            print(
                "[PROJECT RUN-ALL LOOP]",
                loop_guard,
                "RUNNABLE:",
                len(runnable),
                flush=True,
            )

            if not runnable:
                break

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
                "[PROJECT RUN-ALL EXECUTING TASK]",
                current_task.get("id"),
                current_task.get("title"),
                flush=True,
            )

            self._materialize_task_files(
                [current_task]
            )

            result = self._execute_with_existing_orchestrator(
                project_id=project_id,
                tasks=[current_task],
                command="run_step",
            )

            print(
                "[PROJECT RUN-ALL TASK RESULT]",
                current_task.get("id"),
                type(result),
                repr(result),
                flush=True,
            )

            refreshed_after_execution = self._get_project(
                project_id
            )

            refreshed_tasks_after_execution = (
                self._get_tasks(
                    refreshed_after_execution
                )
                if refreshed_after_execution
                else []
            )

            executed_task = next(
                (
                    task
                    for task in refreshed_tasks_after_execution
                    if isinstance(task, dict)
                    and str(task.get("id"))
                    == str(current_task.get("id"))
                ),
                None,
            )

            if executed_task:
                current_task = executed_task

            if result is None and executed_task:
                result = {
                    "execution": {
                        "steps": [
                            dict(executed_task)
                        ]
                    }
                }

            last_result = result

            print(
                "[PROJECT RUN-ALL RESULT DATA]",
                result,
                flush=True,
            )

            print(
                "[PROJECT RUN-ALL EXECUTED TASK STATE]",
                executed_task,
                flush=True,
            )

            tasks = self._merge_execution_results_into_tasks(
                refreshed_tasks_after_execution
                or tasks,
                result,
            )

            published_artifacts = (
                self._publish_completed_artifacts(
                    project_id,
                    [current_task],
                    result,
                )
            )

            if published_artifacts:
                all_published_artifacts.extend(
                    published_artifacts
                )

            self._sync_project_execution(
                project_id,
                result,
                "run_all",
                tasks=tasks,
            )

            refreshed_project = self._get_project(
                project_id
            )

            if not refreshed_project:
                break

            refreshed_tasks = self._get_tasks(
                refreshed_project
            )

            refreshed_runnable = self._runnable_tasks(
                refreshed_tasks
            )

            execution = (
                self.project_workspace_service
                .get_execution_state(
                    project_id
                )
                or {}
            )

            execution_status = str(
                execution.get(
                    "status",
                    "",
                )
            ).strip().lower()

            print(
                "[PROJECT RUN-ALL AFTER TASK]",
                "STATUS:",
                execution_status,
                "REMAINING:",
                len(refreshed_runnable),
                flush=True,
            )

            if execution_status in {
                "failed",
                "blocked",
                "paused",
                "stopped",
            }:
                break

            if not refreshed_runnable:
                break

            current_task_id = current_task.get(
                "id"
            )

            next_task_ids = {
                task.get("id")
                for task in refreshed_runnable
                if task.get("id")
            }

            if current_task_id in next_task_ids:
                print(
                    "[PROJECT RUN-ALL NO PROGRESS]",
                    current_task_id,
                    flush=True,
                )

                break

        final_project = self._get_project(
            project_id
        )

        final_tasks = (
            self._get_tasks(final_project)
            if final_project
            else []
        )

        remaining = self._runnable_tasks(
            final_tasks
        )

        final_task_statuses = {
            str(
                task.get(
                    "status",
                    "",
                )
            ).strip().lower()
            for task in final_tasks
            if isinstance(
                task,
                dict,
            )
        }

        if "failed" in final_task_statuses:
            final_status = "failed"

        elif "blocked" in final_task_statuses:
            final_status = "blocked"

        elif (
            "waiting_approval"
            in final_task_statuses
        ):
            final_status = "paused"

        elif not remaining:
            final_status = "completed"

        else:
            final_status = "running"

        if final_status == "completed":
            final_execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status="completed",
                    current_task_id=None,
                    current_step="",
                    queue=[],
                    last_action="run_all",
                )
            )

        elif final_status in {
            "failed",
            "blocked",
            "paused",
        }:
            final_execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status=final_status,
                    current_task_id=None,
                    current_step="",
                    queue=[],
                    last_action="run_all",
                )
            )

        else:
            next_task = remaining[0]

            final_execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status="running",
                    current_task_id=next_task.get(
                        "id"
                    ),
                    current_step=next_task.get(
                        "title",
                        "",
                    ),
                    queue=[
                        task.get("id")
                        for task in remaining
                        if task.get("id")
                    ],
                    last_action="run_all",
                )
            )

        message = (
            last_result.get(
                "assistant_message",
                {},
            ).get(
                "text",
                "Project execution completed.",
            )
            if isinstance(
                last_result,
                dict,
            )
            else "Project execution completed."
        )

        if not remaining:
            message = (
                "Project execution completed. "
                f"Processed {loop_guard} task cycle(s)."
            )

        return {
            "ok": True,
            "project_id": project_id,
            "action": "run_all",
            "artifacts": all_published_artifacts,
            "execution": final_execution,
            "debug_last_result": last_result,
            "message": message,
        }

    def _merge_execution_results_into_tasks(
        self,
        tasks,
        result,
    ):
        if not isinstance(tasks, list):
            return tasks

        if not isinstance(result, dict):
            return tasks

        execution = (
            result.get("execution")
            or result.get("execution_state")
            or {}
        )

        if not isinstance(execution, dict):
            return tasks

        steps = execution.get("steps") or []

        if not isinstance(steps, list):
            return tasks

        steps_by_task_id = {}

        for step in steps:
            if not isinstance(step, dict):
                continue

            task_id = (
                step.get("task_id")
                or step.get("id")
            )

            if not task_id:
                continue

            steps_by_task_id[
                str(task_id)
            ] = step

        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_id = task.get("id")

            if not task_id:
                continue

            step = steps_by_task_id.get(
                str(task_id)
            )

            if not isinstance(step, dict):
                continue

            step_status = str(
                step.get("status") or ""
            ).strip().lower()

            if step_status in {
                "completed",
                "complete",
                "done",
                "success",
            }:
                task["status"] = "completed"

            execution_output = (
                step.get("result")
                or step.get("output")
                or step.get("content")
                or step.get("text")
                or ""
            )

            if execution_output:
                task["result"] = execution_output
                task["content"] = execution_output

        return tasks

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

        execution = (
            result.get("execution")
            or result.get("execution_state")
        )

        # ChatExecutionService.run_all() returns the
        # execution state directly. Support both shapes:
        #
        # 1. {"execution": {"steps": [...]}}
        # 2. {"steps": [...]}
        #
        if not isinstance(
            execution,
            dict,
        ):
            execution = result

        steps = execution.get(
            "steps",
            []
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

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
        published_task_ids = set()

        print(
            "[PROJECT ARTIFACT PUBLISH START]",
            {
                "project_id": project_id,
                "task_count": len(tasks),
                "step_count": len(steps),
                "result_keys": list(result.keys()),
                "execution_keys": (
                    list(execution.keys())
                    if isinstance(execution, dict)
                    else []
                ),
            },
            flush=True,
        )

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
                or ""
            ).strip().lower()

            if status not in {
                "completed",
                "done",
                "success",
            }:
                continue

            task_id = (
                step.get("task_id")
                or step.get("id")
            )

            if not task_id:
                print(
                    "[PROJECT ARTIFACT NO TASK ID]",
                    step,
                    flush=True,
                )
                continue

            task_id = str(task_id)

            if task_id in published_task_ids:
                continue

            task = task_by_id.get(
                task_id
            )

            if not task:
                print(
                    "[PROJECT ARTIFACT TASK NOT FOUND]",
                    {
                        "task_id": task_id,
                        "available_task_ids": (
                            list(task_by_id.keys())
                        ),
                    },
                    flush=True,
                )
                continue

            print(
                "[PROJECT ARTIFACT STEP DATA]",
                {
                    "task_id": task_id,
                    "step_keys": list(step.keys()),
                    "step": step,
                    "top_level_result_keys": list(result.keys()),
                    "top_level_result": result,
                },
                flush=True,
            )

            artifact_result = (
                step.get("result")
                or step.get("output")
                or step.get("content")
                or step.get("text")
                or result.get("result")
                or result.get("output")
                or result.get("content")
                or ""
            )

            print(
                "[PROJECT ARTIFACT EXTRACTED RESULT]",
                {
                    "task_id": task_id,
                    "artifact_result_type": type(
                        artifact_result
                    ).__name__,
                    "artifact_result": artifact_result,
                    "has_result": bool(artifact_result),
                },
                flush=True,
            )

            artifact = (
                self.artifact_publisher
                .publish_task_artifact(
                    project_id,
                    task,
                    result=artifact_result,
                )
            )

            if artifact:
                published.append(
                    artifact
                )

                published_task_ids.add(
                    task_id
                )

                print(
                    "[PROJECT ARTIFACT PUBLISHED]",
                    {
                        "task_id": task_id,
                        "artifact": artifact.get("name")
                        or artifact.get("original_name")
                        or artifact.get("id"),
                    },
                    flush=True,
                )
            else:
                print(
                    "[PROJECT ARTIFACT NOT CREATED]",
                    {
                        "task_id": task_id,
                        "target_file": task.get(
                            "target_file"
                        ),
                        "has_result": bool(
                            artifact_result
                        ),
                    },
                    flush=True,
                )

        return published

    def _sync_project_execution(
        self,
        project_id,
        result,
        action,
        tasks=None,
    ):
        if not isinstance(
            result,
            dict,
        ):
            return
        tasks = tasks or []


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

        # Project execution can complete tasks without returning the
        # ChatExecutionService step list. Build synthetic completed
        # steps from the project tasks so artifact publication follows
        # the actual project execution state.
        if not steps:
            steps = [
                {
                    "task_id": task.get("id"),
                    "id": task.get("id"),
                    "status": task.get("status"),
                    "result": (
                        task.get("result")
                        or task.get("output")
                        or task.get("content")
                        or task.get("response")
                        or ""
                    ),
                }
                for task in tasks
                if isinstance(task, dict)
                and str(
                    task.get("status") or ""
                ).strip().lower() in {
                    "completed",
                    "complete",
                    "done",
                    "success",
                }
            ]

            print(
                "[PROJECT ARTIFACT FALLBACK STEPS]",
                {
                    "project_id": project_id,
                    "step_count": len(steps),
                },
                flush=True,
            )

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

            print(
                "[PROJECT SYNC STEP]",
                {
                    "task_id": task_id,
                    "status": status,
                    "step_id": step.get("id"),
                    "error": step.get("error"),
                    "result": step.get("result"),
                },
                flush=True,
            )

            if status in {
                "complete",
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








