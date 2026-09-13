from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from nova_backend.services.project_artifact_publisher_service import (
    ProjectArtifactPublisherService,
)


class ProjectExecutionController:

    VALID_ACTIONS = {
        "continue",
        "next_step",
        "next_task",
        "run_all",
        "pause",
        "stop",
        "reset",
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

        print(
            "[PROJECT RUNNABLE INPUT]",
            {
                "tasks_type": type(tasks).__name__,
                "task_count": len(tasks),
                "tasks": [
                    {
                        "id": task.get("id"),
                        "title": task.get("title"),
                        "status": task.get("status"),
                        "dependencies": task.get("dependencies"),
                    }
                    for task in tasks
                    if isinstance(
                        task,
                        dict,
                    )
                ],
            },
            flush=True,
        )

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

    def _phase_records(self, project):
        """
        Return phases in deterministic execution order.

        Projects without phases retain the existing flat-task behavior.
        """
        if not isinstance(project, dict):
            return []

        phases = project.get("phases", [])

        if not isinstance(phases, list):
            return []

        indexed = []

        for index, phase in enumerate(phases):
            if not isinstance(phase, dict):
                continue

            phase_id = str(
                phase.get("id", "")
            ).strip()

            if not phase_id:
                continue

            raw_order = phase.get("order")

            try:
                order = int(raw_order)
            except (TypeError, ValueError):
                order = index

            indexed.append(
                (
                    order,
                    index,
                    phase,
                )
            )

        indexed.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        return [
            item[2]
            for item in indexed
        ]

    def _phase_task_status(self, task):
        if not isinstance(task, dict):
            return "open"

        return str(
            task.get(
                "status",
                "open",
            )
        ).strip().lower()

    def _phase_is_successfully_complete(self, phase_tasks):
        """
        A phase is complete only when it has at least one task and
        every assigned task has a successful terminal status.
        """
        if not phase_tasks:
            return False

        terminal_success_statuses = {
            "completed",
            "complete",
            "done",
            "success",
        }

        return all(
            self._phase_task_status(task)
            in terminal_success_statuses
            for task in phase_tasks
        )

    def _phase_schedule(self, project, tasks):
        """
        Return the current phase and its runnable tasks.

        Execution order:
        1. Ordered phases with incomplete assigned tasks.
        2. Unassigned tasks after all phase work is complete.

        Flat projects retain the existing task behavior.
        """
        phases = self._phase_records(project)

        if not phases:
            return {
                "phased": False,
                "phase": None,
                "phase_tasks": [],
                "runnable": self._runnable_tasks(tasks),
                "phase_queue": [],
                "unassigned_tasks": [],
                "blocked": False,
                "completed": False,
            }

        valid_tasks = [
            task
            for task in tasks
            if isinstance(task, dict)
        ]

        phase_queue = [
            {
                "id": phase.get("id"),
                "title": phase.get("title", ""),
                "status": phase.get("status", "planned"),
            }
            for phase in phases
        ]

        unassigned_tasks = [
            task
            for task in valid_tasks
            if not str(
                task.get("phase_id", "")
            ).strip()
        ]

        for phase in phases:
            phase_id = str(
                phase.get("id", "")
            ).strip()

            phase_tasks = [
                task
                for task in valid_tasks
                if str(
                    task.get("phase_id", "")
                ).strip() == phase_id
            ]

            if not phase_tasks:
                continue

            if self._phase_is_successfully_complete(
                phase_tasks
            ):
                continue

            phase_runnable = [
                task
                for task in self._runnable_tasks(
                    valid_tasks
                )
                if str(
                    task.get("phase_id", "")
                ).strip() == phase_id
            ]

            phase_statuses = {
                self._phase_task_status(task)
                for task in phase_tasks
            }

            blocked = (
                not phase_runnable
                and bool(
                    phase_statuses.intersection(
                        {
                            "failed",
                            "blocked",
                        }
                    )
                )
            )

            return {
                "phased": True,
                "phase": phase,
                "phase_tasks": phase_tasks,
                "runnable": phase_runnable,
                "phase_queue": phase_queue,
                "unassigned_tasks": unassigned_tasks,
                "blocked": blocked,
                "completed": False,
            }

        unassigned_runnable = self._runnable_tasks(
            unassigned_tasks
        )

        if unassigned_runnable:
            return {
                "phased": True,
                "phase": None,
                "phase_tasks": unassigned_tasks,
                "runnable": unassigned_runnable,
                "phase_queue": phase_queue,
                "unassigned_tasks": unassigned_tasks,
                "blocked": False,
                "completed": False,
            }

        all_tasks_complete = bool(
            valid_tasks
        ) and all(
            self._phase_task_status(task)
            in {
                "completed",
                "complete",
                "done",
                "success",
            }
            for task in valid_tasks
        )

        return {
            "phased": True,
            "phase": None,
            "phase_tasks": [],
            "runnable": [],
            "phase_queue": phase_queue,
            "unassigned_tasks": unassigned_tasks,
            "blocked": False,
            "completed": all_tasks_complete,
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

        phase_schedule = self._phase_schedule(
            project,
            tasks,
        )

        runnable = phase_schedule["runnable"]

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

            elif unfinished_tasks:
                # There is still project work remaining, but
                # none is currently runnable. Do NOT report
                # completion.
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
                    "[PROJECT CONTINUE WAITING]",
                    {
                        "project_id": project_id,
                        "unfinished": len(
                            unfinished_tasks
                        ),
                        "queue": queue,
                    },
                    flush=True,
                )

                execution = (
                    self.project_workspace_service
                    .update_execution_state(
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
                        current_phase_id=(
                            phase_schedule["phase"].get("id")
                            if phase_schedule.get("phase")
                            else None
                        ),
                        current_phase_title=(
                            phase_schedule["phase"].get("title", "")
                            if phase_schedule.get("phase")
                            else None
                        ),
                        phase_queue=phase_schedule.get(
                            "phase_queue",
                            [],
                        ),
                        last_action="continue",
                    )
                )

                return {
                    "project_id": project_id,
                    "action": "continue",
                    "execution": execution,
                    "message": (
                        "Project has unfinished tasks "
                        "that are currently waiting on "
                        "dependencies."
                    ),
                }

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
            current_phase_id=(
                phase_schedule["phase"].get("id")
                if phase_schedule.get("phase")
                else None
            ),
            current_phase_title=(
                phase_schedule["phase"].get("title", "")
                if phase_schedule.get("phase")
                else None
            ),
            phase_queue=phase_schedule.get(
                "phase_queue",
                [],
            ),
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

            phase_schedule = self._phase_schedule(
                project,
                tasks,
            )

            runnable = phase_schedule["runnable"]

            print(
                "[PROJECT RUN-ALL LOOP]",
                loop_guard,
                "RUNNABLE:",
                len(runnable),
                flush=True,
            )

            if not runnable:
                # No runnable tasks means the project is either fully
                # complete or blocked/waiting. Resolve the terminal state
                # here instead of bypassing final-status persistence.
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

                terminal_success_statuses = {
                    "completed",
                    "complete",
                    "done",
                    "success",
                }

                if task_statuses and task_statuses.issubset(
                    terminal_success_statuses
                ):
                    self.project_workspace_service.update_execution_state(
                        project_id,
                        status="completed",
                        current_task_id=None,
                        current_step="",
                        queue=[],
                        current_phase_id=None,
                        current_phase_title=None,
                        phase_queue=phase_schedule.get(
                            "phase_queue",
                            [],
                        ),
                        last_action="run_all",
                    )

                    projects = (
                        self.project_workspace_service._load_projects()
                    )

                    for project_record in projects:
                        if project_record.get("id") != project_id:
                            continue

                        project_record["status"] = "completed"
                        project_record["active"] = False
                        project_record["updated_at"] = datetime.now(
                            timezone.utc
                        ).isoformat()

                        self.project_workspace_service._save_projects(
                            projects
                        )
                        break

                    last_result = {
                        "status": "completed",
                        "message": "Project execution completed.",
                    }

                break

            queue = [
                task.get("id")
                for task in runnable
                if task.get("id")
            ]

            current_task = runnable[0]

            print(
                "[PROJECT RUN-ALL BEFORE STATE UPDATE]",
                flush=True,
            )

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
                current_phase_id=(
                    phase_schedule["phase"].get("id")
                    if phase_schedule.get("phase")
                    else None
                ),
                current_phase_title=(
                    phase_schedule["phase"].get("title", "")
                    if phase_schedule.get("phase")
                    else None
                ),
                phase_queue=phase_schedule.get(
                    "phase_queue",
                    [],
                ),
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

            print(
                "[PROJECT CONTINUE BEFORE EXECUTION]",
                {
                    "project_id": project_id,
                    "task_id": current_task.get("id"),
                    "task_title": current_task.get("title"),
                    "task_status": current_task.get("status"),
                    "action": current_task.get("action"),
                    "command": current_task.get("command"),
                    "payload": current_task.get("payload"),
                    "execution_mode": current_task.get("execution_mode"),
                },
                flush=True,
            )

            try:
                result = self._execute_with_existing_orchestrator(
                    project_id=project_id,
                    tasks=[current_task],
                    command="run_step",
                )

            except Exception as exc:
                error_text = (
                    f"{type(exc).__name__}: {exc}"
                )

                print(
                    "[PROJECT RUN-ALL EXECUTION ERROR]",
                    error_text,
                    flush=True,
                )

                current_task["status"] = "failed"
                current_task["error"] = error_text

                try:
                    self.project_workspace_service.update_task_status(
                        project_id,
                        current_task.get("id"),
                        "failed",
                    )
                except Exception as persist_exc:
                    print(
                        "[PROJECT RUN-ALL TASK FAILURE PERSIST ERROR]",
                        repr(persist_exc),
                        flush=True,
                    )

                try:
                    self.project_workspace_service.update_execution_state(
                        project_id,
                        status="failed",
                        current_task_id=current_task.get("id"),
                        current_step=current_task.get(
                            "title",
                            "Current task",
                        ),
                        queue=queue,
                        last_action="run_all",
                    )
                except Exception as state_exc:
                    print(
                        "[PROJECT RUN-ALL STATE FAILURE PERSIST ERROR]",
                        repr(state_exc),
                        flush=True,
                    )

                last_result = {
                    "ok": False,
                    "error": error_text,
                    "execution": {},
                    "steps": [
                        dict(current_task)
                    ],
                    "task_id": current_task.get("id"),
                    "task_title": current_task.get("title"),
                }

                break

            print(
                "[PROJECT CONTINUE AFTER EXECUTION]",
                {
                    "project_id": project_id,
                    "task_id": current_task.get("id"),
                    "task_title": current_task.get("title"),
                    "task_status": current_task.get("status"),
                    "execution": (
                        result.get("execution")
                        or result.get("execution_state")
                        or {}
                    )
                    if isinstance(result, dict)
                    else result,
                    "result": result,
                },
                flush=True,
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

            try:
                tasks = self._merge_execution_results_into_tasks(
                    refreshed_tasks_after_execution
                    or tasks,
                    result,
                )

                executed_task = next(
                    (
                        task
                        for task in tasks
                        if isinstance(task, dict)
                        and str(
                            task.get("id")
                            or ""
                        ).strip()
                        == str(
                            current_task.get("id")
                            or ""
                        ).strip()
                    ),
                    current_task,
                )

                executed_task_status = str(
                    executed_task.get(
                        "status",
                        "",
                    )
                    or ""
                ).strip().lower()

                if executed_task_status in {
                    "failed",
                    "error",
                }:
                    failed_task_id = str(
                        executed_task.get("id")
                        or ""
                    ).strip()

                    failed_task_title = str(
                        executed_task.get("title")
                        or "Previous task"
                    ).strip()

                    failure_reason = (
                        executed_task.get("error")
                        or executed_task.get("result")
                        or executed_task.get("content")
                        or "Task execution failed."
                    )

                    executed_task["status"] = "failed"
                    executed_task["error"] = str(
                        failure_reason
                    )

                    try:
                        self.project_workspace_service.update_task_status(
                            project_id,
                            executed_task.get("id"),
                            "failed",
                        )
                    except Exception as persist_exc:
                        print(
                            "[PROJECT RUN-ALL FAILED TASK PERSIST ERROR]",
                            repr(persist_exc),
                            flush=True,
                        )

                    refreshed_project_after_failure = (
                        self._get_project(
                            project_id
                        )
                    )

                    refreshed_tasks_after_failure = (
                        self._get_tasks(
                            refreshed_project_after_failure
                        )
                        if refreshed_project_after_failure
                        else tasks
                    )

                    failed_task_index = -1

                    for index, task in enumerate(
                        refreshed_tasks_after_failure
                    ):
                        if not isinstance(
                            task,
                            dict,
                        ):
                            continue

                        if str(
                            task.get("id")
                            or ""
                        ).strip() == failed_task_id:
                            failed_task_index = index
                            break

                    if failed_task_index >= 0:
                        for downstream_task in (
                            refreshed_tasks_after_failure[
                                failed_task_index + 1:
                            ]
                        ):
                            if not isinstance(
                                downstream_task,
                                dict,
                            ):
                                continue

                            downstream_status = str(
                                downstream_task.get(
                                    "status",
                                    "",
                                )
                                or ""
                            ).strip().lower()

                            if downstream_status in {
                                "completed",
                                "complete",
                                "done",
                                "success",
                                "failed",
                                "error",
                                "cancelled",
                                "canceled",
                                "blocked",
                            }:
                                continue

                            downstream_task_id = (
                                downstream_task.get("id")
                            )

                            downstream_task["status"] = "blocked"
                            downstream_task["blocked_by"] = failed_task_id
                            downstream_task["error"] = (
                                f"Blocked because prerequisite task "
                                f"'{failed_task_title}' "
                                f"({failed_task_id}) failed."
                            )

                            persisted_blocked_task = (
                                self.project_workspace_service.update_task_status(
                                    project_id,
                                    downstream_task_id,
                                    "blocked",
                                )
                            )

                            if persisted_blocked_task is None:
                                print(
                                    "[PROJECT RUN-ALL BLOCKED TASK PERSIST RETURNED NONE]",
                                    {
                                        "project_id": project_id,
                                        "task_id": downstream_task_id,
                                        "task_title": downstream_task.get(
                                            "title"
                                        ),
                                        "failed_task_id": failed_task_id,
                                    },
                                    flush=True,
                                )
                            else:
                                persisted_blocked_task["blocked_by"] = (
                                    failed_task_id
                                )
                                persisted_blocked_task["error"] = (
                                    downstream_task["error"]
                                )

                                print(
                                    "[PROJECT RUN-ALL BLOCKED TASK PERSISTED]",
                                    {
                                        "task_id": downstream_task_id,
                                        "blocked_by": failed_task_id,
                                    },
                                    flush=True,
                                )

                            try:
                                persisted_blocked_task = (
                                    self.project_workspace_service.update_task_status(
                                        project_id,
                                        downstream_task_id,
                                        "blocked",
                                    )
                                )

                                if persisted_blocked_task is None:
                                    print(
                                        "[PROJECT RUN-ALL BLOCKED TASK PERSIST RETURNED NONE]",
                                        {
                                            "project_id": project_id,
                                            "task_id": downstream_task_id,
                                            "task_title": downstream_task.get(
                                                "title"
                                            ),
                                            "failed_task_id": failed_task_id,
                                            "all_task_ids": [
                                                task.get("id")
                                                for task in refreshed_tasks_after_failure
                                                if isinstance(task, dict)
                                            ],
                                        },
                                        flush=True,
                                    )

                            except Exception as persist_exc:
                                print(
                                    "[PROJECT RUN-ALL BLOCKED TASK PERSIST ERROR]",
                                    {
                                        "project_id": project_id,
                                        "task_id": downstream_task_id,
                                        "task_title": downstream_task.get(
                                            "title"
                                        ),
                                        "failed_task_id": failed_task_id,
                                        "error": repr(
                                            persist_exc
                                        ),
                                    },
                                    flush=True,
                                )
                                print(
                                    "[PROJECT RUN-ALL BLOCKED TASK PERSIST ERROR]",
                                    {
                                        "task_id": downstream_task_id,
                                        "error": repr(
                                            persist_exc
                                        ),
                                    },
                                    flush=True,
                                )

                        tasks = refreshed_tasks_after_failure

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

            except Exception as exc:
                error_text = (
                    f"{type(exc).__name__}: {exc}"
                )

                print(
                    "[PROJECT RUN-ALL POST-EXECUTION ERROR]",
                    error_text,
                    flush=True,
                )

                last_result = {
                    "ok": False,
                    "error": error_text,
                    "execution": (
                        result.get("execution")
                        or result.get("execution_state")
                        or {}
                    )
                    if isinstance(result, dict)
                    else {},
                    "steps": (
                        result.get("steps", [])
                        if isinstance(result, dict)
                        else []
                    ),
                    "task_id": current_task.get("id"),
                    "task_title": current_task.get("title"),
                }

                current_task["status"] = "failed"
                current_task["error"] = error_text

                try:
                    self.project_workspace_service.update_task_status(
                        project_id,
                        current_task.get("id"),
                        "failed",
                    )
                except Exception as persist_exc:
                    print(
                        "[PROJECT RUN-ALL TASK FAILURE PERSIST ERROR]",
                        repr(persist_exc),
                        flush=True,
                    )

                try:
                    self.project_workspace_service.update_execution_state(
                        project_id,
                        status="failed",
                        current_task_id=current_task.get("id"),
                        current_step=current_task.get(
                            "title",
                            "Current task",
                        ),
                        queue=queue,
                        last_action="run_all",
                    )
                except Exception as state_exc:
                    print(
                        "[PROJECT RUN-ALL STATE FAILURE PERSIST ERROR]",
                        repr(state_exc),
                        flush=True,
                    )

                break

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

        terminal_success_statuses = {
            "completed",
            "complete",
            "done",
            "success",
        }

        all_tasks_completed = bool(
            final_task_statuses
        ) and all(
            status in terminal_success_statuses
            for status in final_task_statuses
        )

        if "failed" in final_task_statuses:
            final_status = "failed"

        elif "blocked" in final_task_statuses:
            final_status = "blocked"

        elif (
            "waiting_approval"
            in final_task_statuses
        ):
            final_status = "paused"

        elif all_tasks_completed:
            final_status = "completed"

        elif remaining:
            final_status = "running"

        else:
            final_status = "paused"

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

            # Persist the top-level project terminal state.
            projects = self.project_workspace_service._load_projects()

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
                break

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
            "status": final_status,
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
                    "id"
                )
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
                "completed",
                "complete",
                "done",
                "success",
            }:
                self.project_workspace_service.update_task_status(
                    project_id,
                    task_id,
                    "completed",
                )

            elif status == "failed":
                self.project_workspace_service.update_task_status(
                    project_id,
                    task_id,
                    "failed",
                )

            elif status == "blocked":
                self.project_workspace_service.update_task_status(
                    project_id,
                    task_id,
                    "blocked",
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

            print(
                "[PROJECT SYNC CONTINUE]",
                {
                    "project_id": project_id,
                    "next_task_id": next_task.get("id"),
                    "remaining": len(remaining_tasks),
                },
                flush=True,
            )

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

        if all_tasks_completed:
            self.project_workspace_service.update_execution_state(
                project_id,
                status="completed",
                current_task_id=None,
                current_step="",
                queue=[],
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

    def reset_project(
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

        if not isinstance(tasks, list):
            tasks = []

        now = self._now()

        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_status = str(
                task.get("status")
                or ""
            ).strip().lower()

            if task_status in {
                "completed",
                "failed",
                "running",
                "paused",
            }:
                task["status"] = "pending"

            task["error"] = None

            if "result" in task:
                task["result"] = None

            if "execution_metadata" in task:
                task["execution_metadata"] = None

            if "started_at" in task:
                task["started_at"] = None

            if "completed_at" in task:
                task["completed_at"] = None

        project["status"] = "active"

        execution = project.get(
            "execution"
        )

        if not isinstance(execution, dict):
            execution = {}

        execution.update(
            {
                "status": "idle",
                "current_step": "",
                "current_task_id": None,
                "queue": [],
                "last_action": "reset",
                "updated_at": now,
            }
        )

        project["execution"] = execution

        if hasattr(
            self.project_workspace_service,
            "save_project",
        ):
            self.project_workspace_service.save_project(
                project
            )
        else:
            self._sync_project_execution(
                project_id,
                execution,
                action="reset",
            )

        return {
            "ok": True,
            "project_id": project_id,
            "action": "reset",
            "status": "active",
            "message": "Project execution reset.",
            "execution": execution,
        }

    def _next_step(
        self,
        project_id,
    ):
        result = self.continue_project(
            project_id
        )

        if not isinstance(
            result,
            dict,
        ):
            return result

        if result.get("ok") is False:
            return result

        result["action"] = "next_step"
        result["message"] = (
            "Next execution step completed."
        )

        execution = result.get(
            "execution"
        )

        if isinstance(
            execution,
            dict,
        ):
            execution["last_action"] = (
                "next_step"
            )

        return result

    def _next_task(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return {
                "ok": False,
                "project_id": project_id,
                "action": "next_task",
                "message": "Project not found.",
            }

        tasks = self._get_tasks(
            project
        )

        phase_schedule = self._phase_schedule(
            project,
            tasks,
        )

        runnable = phase_schedule["runnable"]

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

        current_index = -1

        if current_task_id:
            for index, task in enumerate(
                runnable
            ):
                if not isinstance(
                    task,
                    dict,
                ):
                    continue

                if str(
                    task.get("id")
                ) == str(
                    current_task_id
                ):
                    current_index = index
                    break

        next_task = None

        if current_index >= 0:
            for task in runnable[
                current_index + 1:
            ]:
                if not isinstance(
                    task,
                    dict,
                ):
                    continue

                next_task = task
                break
        else:
            for task in runnable:
                if not isinstance(
                    task,
                    dict,
                ):
                    continue

                next_task = task
                break

        if next_task:
            queue = [
                task.get("id")
                for task in runnable
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
            ]

            execution = (
                self.project_workspace_service
                .update_execution_state(
                    project_id,
                    status="paused",
                    current_task_id=(
                        next_task.get("id")
                    ),
                    current_step=(
                        next_task.get(
                            "title",
                            "Next task",
                        )
                    ),
                    queue=queue,
                    current_phase_id=(
                        phase_schedule["phase"].get("id")
                        if phase_schedule.get("phase")
                        else None
                    ),
                    current_phase_title=(
                        phase_schedule["phase"].get("title", "")
                        if phase_schedule.get("phase")
                        else None
                    ),
                    phase_queue=phase_schedule.get(
                        "phase_queue",
                        [],
                    ),
                    last_action="next_task",
                )
            )

            return {
                "ok": True,
                "project_id": project_id,
                "action": "next_task",
                "message": (
                    "Advanced to the next runnable task. "
                    "Execution is paused."
                ),
                "execution": execution,
            }

        execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        execution["last_action"] = (
            "next_task"
        )

        return {
            "ok": True,
            "project_id": project_id,
            "action": "next_task",
            "message": (
                "No next runnable task remains."
            ),
            "execution": execution,
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

        if action == "next_step":
            return self._next_step(
                project_id
            )

        if action == "next_task":
            return self._next_task(
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

        if action == "reset":
            return self.reset_project(
                project_id
            )

        return None

