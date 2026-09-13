from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from nova_backend.services.project_artifact_publisher_service import (
    ProjectArtifactPublisherService,
)


class ProjectExecutionController:

    def _normalize_step_action(
        self,
        action,
    ):
        """
        Normalize task and step actions into the canonical execution action.
        """
        normalized = str(action or "").strip().lower()

        action_map = {
            "implement": "implement",
            "build": "implement",
            "edit": "implement",
            "write": "implement",
            "modify": "implement",
            "patch": "implement",
            "fix": "implement",
            "execute": "execute",
            "run": "execute",
            "review": "review",
            "analyze": "review",
            "analysis": "review",
            "inspect": "review",
            "verify": "review",
            "test": "review",
        }

        return action_map.get(
            normalized,
            normalized,
        )

    def _normalize_task_action(
        self,
        action,
    ):
        """
        Normalize task-level actions through the same action mapping
        used by execution steps.
        """
        return self._normalize_step_action(action)

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

    def reset_execution_state(
        self,
        project_id,
    ):
        return (
            self.project_workspace_service
            .reset_execution_state(
                project_id
            )
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

        A task is runnable when:

        - it is not already terminal
        - all declared dependencies resolve to completed tasks

        Dependencies may reference tasks by:
        - UUID
        - exact title
        - normalized title
        - planner-generated slug
        """

        import re

        if not isinstance(
            tasks,
            list,
        ):
            return []

        terminal_statuses = {
            "completed",
            "complete",
            "done",
            "success",
        }

        non_runnable_statuses = {
            "completed",
            "complete",
            "done",
            "success",
            "cancelled",
            "canceled",
            "blocked",
            "failed",
        }

        def normalize_reference(
            value,
        ):
            value = str(
                value or ""
            ).strip().lower()

            if not value:
                return ""

            value = re.sub(
                r"[^a-z0-9]+",
                "_",
                value,
            )

            return value.strip("_")

        def dependency_variants(
            value,
        ):
            normalized = normalize_reference(
                value
            )

            if not normalized:
                return set()

            variants = {
                normalized,
            }

            # Planner slugs sometimes omit articles such as
            # "the" from task titles.
            without_articles = re.sub(
                r"(^|_)the(?=_|$)",
                "_",
                normalized,
            )

            without_articles = re.sub(
                r"_+",
                "_",
                without_articles,
            ).strip("_")

            if without_articles:
                variants.add(
                    without_articles
                )

            return variants

        completed_references = set()

        # Build all valid references for completed tasks.
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

            if status not in terminal_statuses:
                continue

            task_id = str(
                task.get(
                    "id",
                    "",
                )
            ).strip()

            title = str(
                task.get(
                    "title",
                    "",
                )
            ).strip()

            if task_id:
                completed_references.add(
                    task_id
                )
                completed_references.add(
                    task_id.lower()
                )

            if title:
                completed_references.update(
                    dependency_variants(
                        title
                    )
                )

        runnable = []

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

            nested_steps = task.get(
                "steps",
                [],
            )

            if not isinstance(
                nested_steps,
                list,
            ):
                nested_steps = []

            nested_terminal_statuses = {
                "completed",
                "complete",
                "done",
                "success",
                "cancelled",
                "canceled",
            }

            nested_unfinished = False
            nested_real_failure = False

            for nested_step in nested_steps:
                if not isinstance(nested_step, dict):
                    continue

                nested_status = str(
                    nested_step.get("status", "pending")
                ).strip().lower()

                nested_error = (
                    nested_step.get("error")
                    or nested_step.get("exception")
                    or nested_step.get("failure")
                )

                if nested_status == "failed" or nested_error:
                    nested_real_failure = True

                if nested_status not in nested_terminal_statuses:
                    nested_unfinished = True

            has_resumable_nested_work = (
                nested_unfinished
                and not nested_real_failure
            )

            # A terminal parent task must never be selected again.
            # Nested state cannot override a completed parent status.
            if status in {
                "completed",
                "complete",
                "done",
                "success",
                "succeeded",
                "failed",
                "cancelled",
                "canceled",
            }:
                continue

            task_status = str(
                task.get("status") or ""
            ).strip().lower()

            if task_status in {
                "failed",
                "failure",
                "error",
                "errored",
                "exception",
                "blocked",
            }:
                task_error = str(
                    task.get("error")
                    or "Task execution failed."
                )

                task_steps = (
                    task.get("steps")
                    or task.get("substeps")
                    or task.get("execution_steps")
                    or []
                )

                if isinstance(task_steps, list):
                    for task_step in task_steps:
                        if not isinstance(task_step, dict):
                            continue


                        task_step_status = str(
                            task_step.get("status")
                            or task_step.get("state")
                            or task_step.get("completion_status")
                            or ""
                        ).strip().lower()

                        if task_step_status in {
                            "failed",
                            "failure",
                            "error",
                            "errored",
                            "exception",
                            "blocked",
                        }:
                            task_step["status"] = "failed"
                            task_step["state"] = "failed"
                            task_step["completion_status"] = "failed"

                            task_step["error"] = str(
                                task_step.get("error")
                                or task_error
                            )

                            task_step["next_action"] = None
                            task_step["mutation_ready"] = False

            print(
                "[PROJECT RUNNABLE TASK DIAGNOSTIC]",
                {
                    "task_id": task.get("id"),
                    "task_title": task.get("title"),
                    "parent_status": status,
                    "task_keys": sorted(
                        str(key)
                        for key in task.keys()
                    ),
                    "steps_type": type(
                        task.get("steps")
                    ).__name__,
                    "steps_count": len(
                        task.get("steps") or []
                    )
                    if isinstance(
                        task.get("steps"),
                        list,
                    )
                    else None,
                    "nested_unfinished": nested_unfinished,
                    "nested_real_failure": nested_real_failure,
                    "has_resumable_nested_work": has_resumable_nested_work,
                },
                flush=True,
            )

            if (
                status in non_runnable_statuses
                and not has_resumable_nested_work
            ):
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

                dependency_lower = (
                    dependency_value.lower()
                )

                variants = dependency_variants(
                    dependency_value
                )

                resolved = (
                    dependency_value
                    in completed_references
                    or dependency_lower
                    in completed_references
                    or bool(
                        variants
                        & completed_references
                    )
                )

                if not resolved:
                    dependencies_satisfied = False

                    print(
                        "[PROJECT DEPENDENCY BLOCKED]",
                        {
                            "task_id": task.get(
                                "id"
                            ),
                            "task_title": task.get(
                                "title"
                            ),
                            "dependency": dependency_value,
                            "variants": sorted(
                                variants
                            ),
                        },
                        flush=True,
                    )

                    break

            if dependencies_satisfied:
                runnable.append(
                    task
                )

        print(
            "[PROJECT RUNNABLE TASKS]",
            {
                "total": len(tasks),
                "runnable": len(runnable),
                "runnable_ids": [
                    task.get("id")
                    for task in runnable
                    if isinstance(
                        task,
                        dict,
                    )
                    and task.get("id")
                ],
            },
            flush=True,
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
            "execution_file",
            "run_file",
            "script_file",
            "test_script",
            "test_file",
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

        execution = self._repair_execution_history(
            execution
        )

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
            "[PROJECT CONTINUE TASKS BEFORE FILTER]",
            [
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "status": task.get("status"),
                    "dependencies": task.get(
                        "dependencies",
                        [],
                    ),
                }
                for task in tasks
                if isinstance(
                    task,
                    dict,
                )
            ],
            flush=True,
        )

        runnable = self._runnable_tasks(
            tasks
        )

        # No currently runnable task does NOT automatically
        # mean the project is complete.
        #
        # First determine whether there are unfinished tasks.
        unfinished_tasks = [
            task
            for task in tasks
            if isinstance(
                task,
                dict,
            )
            and str(
                task.get(
                    "status",
                    "open",
                )
            ).strip().lower()
            not in {
                "completed",
                "complete",
                "done",
                "success",
                "cancelled",
                "canceled",
            }
        ]

        if not runnable:
            failed_tasks = [
                task
                for task in tasks
                if isinstance(
                    task,
                    dict,
                )
                and str(
                    task.get(
                        "status",
                        "",
                    )
                ).strip().lower()
                == "failed"
            ]

            unfinished_tasks = [
                task
                for task in tasks
                if isinstance(
                    task,
                    dict,
                )
                and str(
                    task.get(
                        "status",
                        "open",
                    )
                ).strip().lower()
                not in {
                    "completed",
                    "complete",
                    "done",
                    "success",
                    "cancelled",
                    "canceled",
                }
            ]

            if failed_tasks:
                final_status = "failed"
                message = (
                    "Project execution ended with "
                    "failed tasks."
                )

                queue = [
                    task.get("id")
                    for task in failed_tasks
                    if task.get("id")
                ]

                next_task = (
                    failed_tasks[0]
                    if failed_tasks
                    else None
                )

                print(
                    "[PROJECT CONTINUE FAILED]",
                    {
                        "project_id": project_id,
                        "failed": len(
                            failed_tasks
                        ),
                        "queue": queue,
                    },
                    flush=True,
                )

            elif unfinished_tasks:
                final_status = "blocked"
                message = (
                    "Project execution is blocked "
                    "because unfinished tasks remain."
                )

                queue = [
                    task.get("id")
                    for task in unfinished_tasks
                    if task.get("id")
                ]

                next_task = (
                    unfinished_tasks[0]
                    if unfinished_tasks
                    else None
                )

                print(
                    "[PROJECT CONTINUE BLOCKED]",
                    {
                        "project_id": project_id,
                        "unfinished": len(
                            unfinished_tasks
                        ),
                        "queue": queue,
                    },
                    flush=True,
                )

            else:
                final_status = "completed"
                message = (
                    "Project completed successfully."
                )

                queue = []
                next_task = None

            execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status=final_status,
                    current_task_id=None,
                    current_step=None,
                    queue=queue,
                    last_action="continue",
                )
            )

            return {
                "project_id": project_id,
                "action": "continue",
                "execution": execution,
                "status": final_status,
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
            if isinstance(
                task,
                dict,
            )
            and task.get("id")
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
            if isinstance(
                task,
                dict,
            )
            and task.get("id")
        ]

        self.project_workspace_service.update_execution_state(
            project_id,
            status="running",
            current_task_id=current_task_id,
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

        print(
            "[CONTINUE RAW ORCHESTRATOR RESULT]",
            repr(result),
            flush=True,
        )

        self._sync_project_execution(
            project_id,
            result,
            "continue",
        )

        # The orchestrator may legitimately pause on a task that
        # requires user input. Never leave that state persisted
        # as running.
        if isinstance(result, dict):
            execution_result = (
                result.get("execution")
                or result.get("execution_state")
                or result
            )

            execution_status = str(
                execution_result.get("status")
                if isinstance(
                    execution_result,
                    dict,
                )
                else ""
            ).strip().lower()

            if execution_status in {
                "waiting",
                "needs_input",
                "waiting_input",
            }:
                persisted_execution = (
                    self.project_workspace_service
                    .get_execution_state(
                        project_id
                    )
                    or {}
                )

                waiting_task_id = (
                    persisted_execution.get(
                        "current_task_id"
                    )
                    or current_task_id
                )

                waiting_queue = (
                    persisted_execution.get(
                        "queue"
                    )
                    or [waiting_task_id]
                )

                self.project_workspace_service.update_execution_state(
                    project_id,
                    status="waiting",
                    current_task_id=waiting_task_id,
                    current_step=current_task.get(
                        "title",
                        "Current task",
                    ),
                    queue=waiting_queue,
                    last_action="continue",
                )

                print(
                    "[CONTINUE WAITING STATE RESTORED]",
                    {
                        "project_id": project_id,
                        "task_id": waiting_task_id,
                        "queue": waiting_queue,
                        "status": "waiting",
                    },
                    flush=True,
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

    def _repair_execution_history(
        self,
        execution,
    ):
        if not isinstance(
            execution,
            dict,
        ):
            return execution

        steps = execution.get(
            "steps",
            [],
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        existing_history = execution.get(
            "history",
            [],
        )

        if not isinstance(
            existing_history,
            list,
        ):
            existing_history = []

        terminal_statuses = {
            "completed",
            "complete",
            "done",
            "success",
            "failed",
            "error",
            "blocked",
        }

        def get_step_key(item):
            if not isinstance(
                item,
                dict,
            ):
                return ""

            for field_name in (
                "step_id",
                "task_id",
                "id",
            ):
                value = str(
                    item.get(field_name) or ""
                ).strip()

                if value:
                    return value

            return ""

        def normalize_history_entry(item):
            if not isinstance(
                item,
                dict,
            ):
                return None

            step_id = (
                item.get("step_id")
                or item.get("id")
            )

            task_id = item.get(
                "task_id"
            )

            status = str(
                item.get("status") or ""
            ).strip().lower()

            normalized_status = {
                "complete": "completed",
                "done": "completed",
                "success": "completed",
                "error": "failed",
            }.get(
                status,
                status,
            )

            return {
                "step_id": step_id,
                "task_id": task_id,
                "status": normalized_status,
                "action": item.get(
                    "action"
                ),
                "result": item.get(
                    "result"
                ),
            }

        history_by_key = {}
        non_structured_history = []

        for item in existing_history:
            key = get_step_key(item)

            if key:
                normalized_entry = (
                    normalize_history_entry(item)
                )

                if normalized_entry is not None:
                    history_by_key[key] = (
                        normalized_entry
                    )
            else:
                non_structured_history.append(
                    item
                )

        repaired_history = []

        for step in steps:
            if not isinstance(
                step,
                dict,
            ):
                continue

            status = str(
                step.get("status") or ""
            ).strip().lower()

            normalized_status = {
                "complete": "completed",
                "done": "completed",
                "success": "completed",
                "error": "failed",
            }.get(
                status,
                status,
            )

            if normalized_status not in terminal_statuses:
                continue

            step_id = (
                step.get("id")
                or step.get("step_id")
            )

            task_id = step.get(
                "task_id"
            )

            key = str(
                step_id
                or task_id
                or ""
            ).strip()

            if not key:
                continue

            existing_entry = history_by_key.get(
                key,
                {},
            )

            result = step.get(
                "result"
            )

            if result in (
                None,
                "",
            ):
                result = step.get(
                    "output"
                )

            repaired_entry = {
                "step_id": (
                    step_id
                    or existing_entry.get(
                        "step_id"
                    )
                ),
                "task_id": (
                    task_id
                    or existing_entry.get(
                        "task_id"
                    )
                ),
                "status": normalized_status,
                "action": (
                    step.get("action")
                    or existing_entry.get(
                        "action"
                    )
                ),
                "result": (
                    result
                    if result not in (
                        None,
                        "",
                    )
                    else existing_entry.get(
                        "result"
                    )
                ),
            }

            repaired_history.append(
                repaired_entry
            )

        execution["history"] = (
            non_structured_history
            + repaired_history
        )

        return execution


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

            execution_state = (
                self.project_workspace_service.get_execution_state(project_id)
                or {}
            )

            execution_status = str(
                execution_state.get("status") or ""
            ).strip().lower()

            if execution_status in {"paused", "stopped"}:
                return {
                    "ok": False,
                    "project_id": project_id,
                    "action": "run_all",
                    "status": execution_status,
                    "execution": execution_state,
                    "artifacts": all_published_artifacts,
                    "debug_last_result": last_result,
                    "message": (
                        "Project execution is paused."
                        if execution_status == "paused"
                        else "Project execution was stopped."
                    ),
                }


            project = self._get_project(
                project_id
            )

            if not project:
                break

            tasks = self._get_tasks(
                project
            )

            if not isinstance(tasks, list):
                tasks = []

            runnable = self._runnable_tasks(
                tasks
            )

            if not isinstance(runnable, list):
                runnable = []

            print(
                "[PROJECT RUN-ALL LOOP]",
                loop_guard,
                "RUNNABLE:",
                len(runnable),
                flush=True,
            )

            if not runnable:
                try:
                    projects = (
                        self.project_workspace_service
                        ._load_projects()
                    )

                    failed_tasks = []
                    unfinished_tasks = []

                    if isinstance(projects, list):
                        for stored_project in projects:

                            if not isinstance(
                                stored_project,
                                dict,
                            ):
                                continue

                            if (
                                stored_project.get("id")
                                != project_id
                            ):
                                continue

                            stored_tasks = (
                                stored_project.get("tasks")
                                or []
                            )

                            for task in stored_tasks:
                                if not isinstance(
                                    task,
                                    dict,
                                ):
                                    continue

                                task_status = str(
                                    task.get("status")
                                    or "open"
                                ).strip().lower()

                                if task_status == "failed":
                                    failed_tasks.append(task)
                                    continue

                                if task_status not in {
                                    "completed",
                                    "complete",
                                    "done",
                                    "success",
                                    "cancelled",
                                    "canceled",
                                }:
                                    unfinished_tasks.append(task)

                            if failed_tasks:
                                final_status = "failed"
                            elif unfinished_tasks:
                                final_status = "blocked"
                            else:
                                final_status = "completed"

                            stored_project["status"] = (
                                final_status
                            )
                            stored_project["active"] = False
                            stored_project["updated_at"] = (
                                datetime.now(
                                    timezone.utc
                                ).isoformat()
                            )

                            self.project_workspace_service._save_projects(
                                projects
                            )

                            completed_task_ids = [
                                task.get("id")
                                for task in stored_tasks
                                if isinstance(task, dict)
                                and str(
                                    task.get("status") or ""
                                ).strip().lower()
                                in {
                                    "completed",
                                    "complete",
                                    "done",
                                    "success",
                                }
                                and task.get("id")
                            ]

                            completed_step_ids = [
                                step.get("id")
                                for task in stored_tasks
                                if isinstance(task, dict)
                                for step in task.get("steps", [])
                                if isinstance(step, dict)
                                and str(
                                    step.get("status")
                                    or step.get("state")
                                    or step.get("completion_status")
                                    or ""
                                ).strip().lower()
                                in {
                                    "completed",
                                    "complete",
                                    "done",
                                    "success",
                                }
                                and step.get("id")
                            ]

                            failed_task_ids = [
                                task.get("id")
                                for task in stored_tasks
                                if isinstance(task, dict)
                                and str(
                                    task.get("status") or ""
                                ).strip().lower()
                                in {
                                    "failed",
                                    "error",
                                }
                                and task.get("id")
                            ]

                            execution = (
                                self.project_workspace_service
                                .update_execution_state(
                                    project_id,
                                    status=final_status,
                                    current_task_id=None,
                                    current_step=None,
                                    queue=[],
                                    completed_steps=completed_step_ids,
                                    completed_tasks=completed_task_ids,
                                    failed_tasks=failed_task_ids,
                                    last_action="run_all",
                                )
                            )

                            return {
                                "ok": final_status == "completed",
                                "project_id": project_id,
                                "status": final_status,
                                "message": (
                                    "Project execution completed. "
                                    "No runnable tasks remain."
                                    if final_status == "completed"
                                    else (
                                        "Project execution stopped. "
                                        "Failed tasks remain."
                                        if final_status == "failed"
                                        else (
                                            "Project execution stopped. "
                                            "Unfinished tasks are blocked."
                                        )
                                    )
                                ),
                                "execution": execution,
                            }

                except Exception as exc:
                    print(
                        "[PROJECT RUN-ALL PROJECT STATUS SYNC ERROR]",
                        repr(exc),
                        flush=True,
                    )

                execution = (
                    self.project_workspace_service
                    .update_execution_state(
                        project_id,
                        status="blocked",
                        current_task_id=None,
                        current_step=None,
                        queue=[],
                        last_action="run_all",
                    )
                )

                return {
                    "ok": False,
                    "project_id": project_id,
                    "status": "blocked",
                    "message": (
                        "Project execution stopped. "
                        "No runnable tasks remain."
                    ),
                    "execution": execution,
                }

                return {
                    "ok": True,
                    "project_id": project_id,
                    "action": "run_all",
                    "status": "completed",
                    "artifacts": all_published_artifacts,
                    "execution": execution,
                    "debug_last_result": last_result,
                    "message": (
                        "Project execution completed. "
                        "No runnable tasks remain."
                    ),
                }

            current_task = runnable[0]

            if not isinstance(
                current_task,
                dict,
            ):
                print(
                    "[PROJECT RUN-ALL INVALID TASK]",
                    repr(current_task),
                    flush=True,
                )
                break

            current_task_id = (
                current_task.get("id")
            )

            queue = [
                task.get("id")
                for task in runnable
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
            ]

            self.project_workspace_service.update_execution_state(
                project_id,
                status="running",
                current_task_id=current_task_id,
                current_step=current_task.get(
                    "title",
                    "Current task",
                ),
                queue=queue,
                last_action="run_all",
            )

            try:
                self._materialize_task_files(
                    [current_task]
                )

                result = (
                    self._execute_with_existing_orchestrator(
                        project_id=project_id,
                        tasks=[current_task],
                        command="run_step",
                    )
                )

                result_execution = (
                    result.get("execution")
                    or result.get("execution_state")
                    or {}
                ) if isinstance(result, dict) else {}
                result_status = str(
                    (
                        result_execution.get("status")
                        if isinstance(result_execution, dict)
                        else None
                    )
                    or (
                        result.get("status")
                        if isinstance(result, dict)
                        else None
                    )
                    or ""
                ).strip().lower()
                result_ok = (
                    result.get("ok")
                    if isinstance(result, dict)
                    else None
                )
                failure_statuses = {
                    "failed",
                    "failure",
                    "error",
                    "errored",
                    "exception",
                    "blocked",
                }
                if (
                    result_ok is False
                    or result_status in failure_statuses
                ):
                    failure_error = (
                        (
                            result_execution.get("error")
                            if isinstance(result_execution, dict)
                            else None
                        )
                        or (
                            result.get("error")
                            if isinstance(result, dict)
                            else None
                        )
                        or (
                            result.get("message")
                            if isinstance(result, dict)
                            else None
                        )
                        or "Project task execution failed."
                    )
                    current_task["status"] = "failed"
                    current_task["error"] = str(
                        failure_error
                    )
                    current_task_steps = (
                        current_task.get("steps")
                        or current_task.get("substeps")
                        or current_task.get("execution_steps")
                        or []
                    )
                    if isinstance(current_task_steps, list):
                        for current_task_step in current_task_steps:
                            if not isinstance(current_task_step, dict):
                                continue
                            current_task_step["status"] = "failed"
                            current_task_step["state"] = "failed"
                            current_task_step["completion_status"] = "failed"
                            current_task_step["error"] = str(
                                failure_error
                            )
                            current_task_step["next_action"] = None
                            current_task_step["mutation_ready"] = False
                # Normalize the task result before synchronization.
                # The execution service may return ok=True even when the
                # nested execution is waiting for input or approval.
                result_execution = (
                    result.get("execution")
                    if isinstance(result, dict)
                    else {}
                )

                if not isinstance(result_execution, dict):
                    result_execution = {}

                execution_status = str(
                    result_execution.get("status")
                    or result_status
                    or ""
                ).strip().lower()

                execution_complete = (
                    result_execution.get("complete") is True
                    or execution_status in {
                        "completed",
                        "complete",
                        "done",
                        "success",
                    }
                )

                execution_waiting = (
                    result_execution.get("waiting") is True
                    or execution_status in {
                        "waiting",
                        "waiting_approval",
                        "needs_input",
                        "paused",
                    }
                    or str(
                        result_execution.get("completion_status")
                        or ""
                    ).strip().lower()
                    in {
                        "needs_input",
                        "waiting",
                        "waiting_approval",
                    }
                )

                execution_failed = (
                    result_ok is False
                    or result_status in failure_statuses
                    or execution_status in {
                        "failed",
                        "error",
                        "blocked",
                        "cancelled",
                        "canceled",
                    }
                )

                result_success = (
                    not execution_failed
                    and not execution_waiting
                    and execution_complete
                )

                print(
                    "[PROJECT RUN-ALL RESULT CLASSIFICATION]",
                    {
                        "project_id": project_id,
                        "task_id": current_task.get("id"),
                        "result_ok": result_ok,
                        "result_status": result_status,
                        "execution_status": execution_status,
                        "execution_complete": execution_complete,
                        "execution_waiting": execution_waiting,
                        "execution_failed": execution_failed,
                        "result_success": result_success,
                    },
                    flush=True,
                )

                if result_success:
                    current_task_id = str(
                        current_task.get("id") or ""
                    ).strip()

                    if current_task_id:
                        try:
                            task_update_result = (
                                self.project_workspace_service
                                .update_task_status(
                                    project_id,
                                    current_task_id,
                                    "completed",
                                )
                            )

                            current_task["status"] = "completed"

                            print(
                                "[PROJECT RUN-ALL TASK COMPLETED]",
                                {
                                    "project_id": project_id,
                                    "task_id": current_task_id,
                                    "result_status": result_status,
                                    "result_ok": result_ok,
                                    "update_result": task_update_result,
                                },
                                flush=True,
                            )

                        except Exception as exc:
                            print(
                                "[PROJECT RUN-ALL TASK COMPLETION ERROR]",
                                {
                                    "project_id": project_id,
                                    "task_id": current_task_id,
                                    "error": str(exc),
                                },
                                flush=True,
                            )

                            current_task["status"] = "failed"
                            current_task["error"] = (
                                "Execution succeeded, but the task status "
                                f"could not be persisted: {exc}"
                            )

                last_result = result

                print(
                    "[PROJECT RUN-ALL TASK RESULT]",
                    {
                        "task_id": current_task.get("id"),
                        "task_title": current_task.get("title"),
                        "result_type": type(result).__name__,
                        "result": result,
                    },
                    flush=True,
                )

                self._sync_project_execution(
                    project_id,
                    result,
                    "run_all",
                    tasks=[current_task],
                )

                published_artifacts = (
                    self._publish_completed_artifacts(
                        project_id,
                        [current_task],
                        result,
                    )
                )

                if isinstance(
                    published_artifacts,
                    list,
                ):
                    all_published_artifacts.extend(
                        published_artifacts
                    )

            except Exception as exc:
                error_message = str(
                    exc
                )

                print(
                    "[PROJECT RUN-ALL TASK ERROR]",
                    {
                        "task_id": current_task.get("id"),
                        "task_title": current_task.get("title"),
                        "error": error_message,
                    },
                    flush=True,
                )

                last_result = {
                    "ok": False,
                    "project_id": project_id,
                    "action": "run_all",
                    "status": "failed",
                    "task_id": current_task.get("id"),
                    "message": error_message,
                    "error": error_message,
                }

                try:
                    self._sync_project_execution(
                        project_id,
                        last_result,
                        "run_all",
                    )
                except Exception as sync_exc:
                    print(
                        "[PROJECT RUN-ALL FAILURE SYNC ERROR]",
                        repr(sync_exc),
                        flush=True,
                    )

                return last_result

            refreshed_project = (
                self._get_project(
                    project_id
                )
            )

            if not refreshed_project:
                break

            refreshed_tasks = self._get_tasks(
                refreshed_project
            )

            if not isinstance(
                refreshed_tasks,
                list,
            ):
                refreshed_tasks = []

            refreshed_runnable = (
                self._runnable_tasks(
                    refreshed_tasks
                )
            )

            if not isinstance(
                refreshed_runnable,
                list,
            ):
                refreshed_runnable = []

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

            if execution_status in {
                "failed",
                "blocked",
                "paused",
                "stopped",
                "cancelled",
                "canceled",
            }:
                return {
                    "ok": False,
                    "project_id": project_id,
                    "action": "run_all",
                    "status": execution_status,
                    "artifacts": all_published_artifacts,
                    "execution": execution,
                    "debug_last_result": last_result,
                    "message": (
                        "Project execution stopped with status "
                        f"'{execution_status}'."
                    ),
                }

        if not refreshed_runnable:
            terminal_success_statuses = {
                "completed",
                "complete",
                "done",
                "success",
            }

            unresolved_statuses = {
                "open",
                "pending",
                "queued",
                "active",
                "running",
                "waiting",
                "waiting_approval",
                "needs_input",
                "paused",
                "blocked",
                "failed",
                "error",
            }

            refreshed_task_statuses = [
                str(
                    task.get("status") or ""
                ).strip().lower()
                for task in refreshed_tasks
                if isinstance(task, dict)
            ]

            all_tasks_completed = bool(
                refreshed_task_statuses
            ) and all(
                status in terminal_success_statuses
                for status in refreshed_task_statuses
            )

            has_unresolved_tasks = any(
                status in unresolved_statuses
                for status in refreshed_task_statuses
            )

            if all_tasks_completed and not has_unresolved_tasks:
                final_status = "completed"
            else:
                final_status = "blocked"

            print(
                "[PROJECT RUN-ALL FINAL CLASSIFICATION]",
                {
                    "project_id": project_id,
                    "task_statuses": refreshed_task_statuses,
                    "all_tasks_completed": all_tasks_completed,
                    "has_unresolved_tasks": has_unresolved_tasks,
                    "final_status": final_status,
                },
                flush=True,
            )

            final_execution = (
                self.project_workspace_service.update_execution_state(
                    project_id,
                    status=final_status,
                    current_task_id=None,
                    current_step=None,
                    queue=[],
                    last_action="run_all",
                )
            )

            return {
                "ok": True,
                "project_id": project_id,
                "action": "run_all",
                "status": final_status,
                "artifacts": all_published_artifacts,
                "execution": final_execution,
                "debug_last_result": last_result,
                "message": (
                    "Project execution completed. "
                    f"Processed {loop_guard} task cycle(s)."
                    if final_status == "completed"
                    else (
                        "Project execution stopped with unresolved tasks. "
                        f"Processed {loop_guard} task cycle(s)."
                    )
                ),
            }

        execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        return {
            "ok": False,
            "project_id": project_id,
            "action": "run_all",
            "status": "running",
            "artifacts": all_published_artifacts,
            "execution": execution,
            "debug_last_result": last_result,
            "message": (
                "Project execution stopped after reaching "
                f"the {max_loops}-cycle safety limit."
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
            .update_execution_state(
                project_id,
                status="paused",
                last_action="pause",
            )
        )

        projects = (
            self.project_workspace_service
            ._load_projects()
        )

        for stored_project in projects:
            if not isinstance(
                stored_project,
                dict,
            ):
                continue

            if stored_project.get("id") != project_id:
                continue

            stored_project["status"] = "paused"
            stored_project["active"] = False
            stored_project["updated_at"] = (
                execution.get("updated_at")
                if isinstance(
                    execution,
                    dict,
                )
                else stored_project.get("updated_at")
            )
            break

        self.project_workspace_service._save_projects(
            projects
        )

        return {
            "ok": True,
            "project_id": project_id,
            "action": "pause",
            "status": "paused",
            "execution": execution,
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

        execution = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="stopped",
                last_action="stop",
            )
        )

        projects = (
            self.project_workspace_service
            ._load_projects()
        )

        for stored_project in projects:
            if not isinstance(
                stored_project,
                dict,
            ):
                continue

            if stored_project.get("id") != project_id:
                continue

            stored_project["status"] = "stopped"
            stored_project["active"] = False
            stored_project["updated_at"] = (
                execution.get("updated_at")
                if isinstance(
                    execution,
                    dict,
                )
                else stored_project.get("updated_at")
            )
            break

        self.project_workspace_service._save_projects(
            projects
        )

        return {
            "ok": True,
            "project_id": project_id,
            "action": "stop",
            "status": "stopped",
            "execution": execution,
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
            execution = result

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
                step.get("status")
                or step.get("state")
                or ""
            ).strip().lower()

            if step_status in {
                "completed",
                "complete",
                "done",
                "success",
            }:
                task["status"] = "completed"

            elif step_status in {
                "failed",
                "failure",
                "error",
                "errored",
                "exception",
            }:
                task["status"] = "failed"

                error_value = (
                    step.get("error")
                    or step.get("message")
                    or step.get("result")
                    or step.get("output")
                    or "Task execution failed."
                )

                task["error"] = str(
                    error_value
                )

            elif step_status in {
                "blocked",
                "cancelled",
                "canceled",
            }:
                task["status"] = "blocked"

                blocked_value = (
                    step.get("error")
                    or step.get("message")
                    or step.get("result")
                    or "Task is blocked."
                )

                task["error"] = str(
                    blocked_value
                )

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

        execution = (
            result.get(
                "execution"
            )
            or result.get(
                "execution_state"
            )
        )

        if not isinstance(
            execution,
            dict,
        ):
            if isinstance(
                result.get(
                    "steps"
                ),
                list,
            ):
                execution = result
            else:
                return

        steps = execution.get(
            "steps",
            [],
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        # The execution service may return completed task results
        # in history rather than in steps. Prefer explicit steps,
        # then use history as the synchronization source.
        history = execution.get(
            "history",
            [],
        )

        if not isinstance(
            history,
            list,
        ):
            history = []

        if not steps:
            steps = [
                item
                for item in history
                if isinstance(
                    item,
                    dict,
                )
                and (
                    item.get("task_id")
                    or item.get("step_id")
                    or item.get("id")
                )
            ]

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
                if isinstance(
                    task,
                    dict,
                )
                and str(
                    task.get("status") or ""
                ).strip().lower()
                in {
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

         # Sync execution-service task results back into
        # the persistent project task list.

        synced_task_ids = []

        for step in steps:
            if not isinstance(
                step,
                dict,
            ):
                continue

            task_id = (
                step.get(
                    "task_id"
                )
                or step.get(
                    "step_id"
                )
                or step.get(
                    "id"
                )
            )

            if not task_id:
                print(
                    "[PROJECT SYNC STEP SKIPPED]",
                    {
                        "reason": "missing_task_id",
                        "step": step,
                    },
                    flush=True,
                )
                continue

            task_id = str(
                task_id
            ).strip()

            status = str(
                step.get(
                    "status",
                    "",
                )
            ).strip().lower()

            normalized_status = {
                "complete": "completed",
                "done": "completed",
                "success": "completed",
                "error": "failed",
            }.get(
                status,
                status,
            )

            print(
                "[PROJECT SYNC STEP]",
                {
                    "task_id": task_id,
                    "status": status,
                    "normalized_status": normalized_status,
                    "step_id": step.get("id"),
                    "error": step.get("error"),
                    "result": step.get("result"),
                },
                flush=True,
            )

            if normalized_status not in {
                "completed",
                "failed",
                "blocked",
            }:
                print(
                    "[PROJECT SYNC STEP IGNORED]",
                    {
                        "task_id": task_id,
                        "status": normalized_status,
                    },
                    flush=True,
                )
                continue

            try:
                update_result = (
                    self.project_workspace_service.update_task_status(
                        project_id,
                        task_id,
                        normalized_status,
                    )
                )

                synced_task_ids.append(
                    task_id
                )

                print(
                    "[PROJECT SYNC TASK UPDATED]",
                    {
                        "project_id": project_id,
                        "task_id": task_id,
                        "status": normalized_status,
                        "result": update_result,
                    },
                    flush=True,
                )

            except Exception as exc:
                print(
                    "[PROJECT SYNC TASK UPDATE ERROR]",
                    {
                        "project_id": project_id,
                        "task_id": task_id,
                        "status": normalized_status,
                        "error": str(exc),
                    },
                    flush=True,
                )

        print(
            "[PROJECT SYNC TASK IDS]",
            synced_task_ids,
            flush=True,
        )

        # IMPORTANT:
        # Always reload the project AFTER task status changes.
        # The project-level state must be based on the actual
        # remaining project tasks, not on the execution-service
        # status of the single task that just ran.
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

        print(
            "[PROJECT SYNC DECISION]",
            {
                "project_id": project_id,
                "execution_status": execution_status,
                "remaining_tasks": len(remaining_tasks),
                "remaining_ids": [
                    task.get("id")
                    for task in remaining_tasks
                    if isinstance(
                        task,
                        dict,
                    )
                    and task.get("id")
                ],
                "action": action,
            },
            flush=True,
        )

        # A genuine failed/blocked execution stops the project.
        if execution_status in {
            "failed",
            "blocked",
        }:
            queue = [
                task.get("id")
                for task in remaining_tasks
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
            ]

            next_task = (
                remaining_tasks[0]
                if remaining_tasks
                else None
            )

            execution = (
                self.project_workspace_service.update_execution_state(
                    project_id,
                    status=execution_status,
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
            )

            projects = (
                self.project_workspace_service._load_projects()
            )

            for project in projects:
                if (
                    project.get("id") != project_id
                    or not self.project_workspace_service._same_project_owner(
                        project
                    )
                ):
                    continue

                project["status"] = execution_status
                project["active"] = False
                project["updated_at"] = (
                    execution.get(
                        "updated_at"
                    )
                    if isinstance(
                        execution,
                        dict,
                    )
                    else project.get(
                        "updated_at"
                    )
                )

                self.project_workspace_service._save_projects(
                    projects
                )
                break

            return
        # Approval is a project pause, not completion.
        if execution_status == "waiting_approval":
            queue = [
                task.get("id")
                for task in remaining_tasks
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
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

        # A task that is waiting for input must remain queued,
        # but the persisted execution state must be waiting,
        # not running.
        if execution_status in {
            "waiting",
            "needs_input",
            "waiting_input",
        }:
            next_task = (
                remaining_tasks[0]
                if remaining_tasks
                else None
            )

            queue = [
                task.get("id")
                for task in remaining_tasks
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
            ]

            print(
                "[PROJECT SYNC WAITING]",
                {
                    "project_id": project_id,
                    "task_id": (
                        next_task.get("id")
                        if next_task
                        else None
                    ),
                    "remaining": len(remaining_tasks),
                    "execution_status": execution_status,
                },
                flush=True,
            )

            self.project_workspace_service.update_execution_state(
                project_id,
                status="waiting",
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

        # CRITICAL RUN-ALL RULE:
        #
        # The execution service runs ONE project task at a time.
        # Therefore execution_status == "complete" only means
        # that the CURRENT execution finished.
        #
        # It does NOT mean the entire project is complete.
        #
        # Only zero runnable project tasks means the project
        # itself is complete.
        if remaining_tasks:
            next_task = remaining_tasks[0]

            queue = [
                task.get("id")
                for task in remaining_tasks
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
            ]

            result_status = str(
                result.get(
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            result_completion_status = str(
                result.get(
                    "completion_status",
                    "",
                )
                or ""
            ).strip().lower()

            result_next_action = str(
                result.get(
                    "next_action",
                    "",
                )
                or ""
            ).strip().lower()

            task_result = result.get(
                "result"
            )

            if not isinstance(
                task_result,
                dict,
            ):
                task_result = {}

            task_status = str(
                task_result.get(
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            task_completion_status = str(
                task_result.get(
                    "completion_status",
                    "",
                )
                or ""
            ).strip().lower()

            waiting_statuses = {
                "waiting",
                "needs_input",
                "waiting_input",
                "blocked",
                "paused",
            }

            is_waiting = (
                result_status in waiting_statuses
                or result_completion_status in waiting_statuses
                or task_status in waiting_statuses
                or task_completion_status in waiting_statuses
                or "needs_input" in result_next_action
                or "satisfy the completion criteria" in result_next_action
            )

            persisted_status = (
                "waiting"
                if is_waiting
                else "running"
            )

            print(
                "[PROJECT SYNC CONTINUE]",
                {
                    "project_id": project_id,
                    "next_task_id": next_task.get("id"),
                    "remaining": len(remaining_tasks),
                    "result_status": result_status,
                    "result_completion_status": result_completion_status,
                    "task_status": task_status,
                    "task_completion_status": task_completion_status,
                    "persisted_status": persisted_status,
                },
                flush=True,
            )

            self.project_workspace_service.update_execution_state(
                project_id,
                status=persisted_status,
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

            return

        # No runnable tasks remain.
        # Completion is valid only when every project task
        # has a terminal success status.
        terminal_success_statuses = {
            "completed",
            "complete",
            "done",
            "success",
        }

        task_statuses = [
            str(
                task.get(
                    "status",
                    "",
                )
            ).strip().lower()
            for task in latest_tasks
            if isinstance(
                task,
                dict,
            )
        ]

        all_tasks_completed = bool(
            task_statuses
        ) and all(
            status in terminal_success_statuses
            for status in task_statuses
        )

        print(
            "[PROJECT SYNC FINAL DECISION]",
            {
                "project_id": project_id,
                "remaining": 0,
                "task_statuses": task_statuses,
                "all_tasks_completed": all_tasks_completed,
            },
            flush=True,
        )

        completed_task_ids = [
            task.get("id")
            for task in latest_tasks
            if isinstance(task, dict)
            and str(
                task.get("status") or ""
            ).strip().lower()
            in terminal_success_statuses
            and task.get("id")
        ]

        completed_step_ids = [
            step.get("id")
            for task in latest_tasks
            if isinstance(task, dict)
            for step in task.get("steps", [])
            if isinstance(step, dict)
            and str(
                step.get("status")
                or step.get("state")
                or step.get("completion_status")
                or ""
            ).strip().lower()
            in {
                "completed",
                "complete",
                "done",
                "success",
            }
            and step.get("id")
        ]

        failed_task_ids = [
            task.get("id")
            for task in latest_tasks
            if isinstance(task, dict)
            and str(
                task.get("status") or ""
            ).strip().lower()
            in {
                "failed",
                "error",
            }
            and task.get("id")
        ]

        if all_tasks_completed:

            self.project_workspace_service.update_execution_state(
                project_id,
                status="completed",
                current_task_id=None,
                current_step="",
                queue=[],
                completed_tasks=completed_task_ids,
                completed_steps=completed_step_ids,
                failed_tasks=failed_task_ids,
                last_action=action,
            )

            projects = (
                self.project_workspace_service._load_projects()
            )

            for project in projects:
                if project.get("id") != project_id:
                    continue

                project["status"] = "completed"
                project["active"] = False
                project["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

            self.project_workspace_service._save_projects(
                projects
            )

        else:
            # No runnable tasks remain, but the project is not
            # successfully complete. Preserve the actual task
            # failure/block state instead of falsely completing.
            unresolved_statuses = [
                status
                for status in task_statuses
                if status not in terminal_success_statuses
            ]

            print(
                "[PROJECT SYNC NOT COMPLETE]",
                {
                    "project_id": project_id,
                    "unresolved_statuses": unresolved_statuses,
                },
                flush=True,
            )

            self.project_workspace_service.update_execution_state(
                project_id,
                status="paused",
                current_task_id=None,
                current_step="",
                queue=[],
                last_action=action,
            )

        # Persist the top-level project status consistently with the
        # execution-state decision. Never force completion here.
        projects = (
            self.project_workspace_service._load_projects()
        )

        for project in projects:
            if project.get("id") != project_id:
                continue

            execution_state = (
                self.project_workspace_service.get_execution_state(
                    project_id
                )
                or {}
            )

            persisted_execution_status = str(
                execution_state.get(
                    "status",
                    "",
                )
            ).strip().lower()

            if persisted_execution_status == "completed":
                project["status"] = "completed"
                project["active"] = False

            elif persisted_execution_status == "failed":
                project["status"] = "failed"
                project["active"] = False

            elif persisted_execution_status == "blocked":
                project["status"] = "blocked"
                project["active"] = False

            else:
                project["status"] = "active"
                project["active"] = True

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self.project_workspace_service._save_projects(
                projects
            )
            break
























