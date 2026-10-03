from __future__ import annotations

import builtins
from datetime import datetime, timezone
from functools import wraps
import logging
import os
import threading
from nova_backend.services.project_artifact_publisher_service import (
    ProjectArtifactPublisherService,
)
from nova_backend.services.execution_approval_service import (
    ExecutionApprovalService,
)


_PROJECT_EXECUTION_LOCKS = {}
_PROJECT_EXECUTION_ACTIONS = {}
_PROJECT_EXECUTION_LOCKS_GUARD = threading.Lock()
_LOGGER = logging.getLogger(__name__)


def _execution_debug(*args, **kwargs):
    """Emit verbose execution diagnostics only when explicitly enabled."""

    enabled = str(os.environ.get("NOVA_EXECUTION_DEBUG") or "").lower()
    if enabled in {"1", "true", "yes", "on"}:
        builtins.print(*args, **kwargs)


def _exclusive_project_execution(action_name):
    """Allow only one advancing execution action per project at a time."""

    def decorate(method):
        @wraps(method)
        def guarded(self, project_id, *args, **kwargs):
            project_key = str(project_id or "").strip()

            with _PROJECT_EXECUTION_LOCKS_GUARD:
                execution_lock = _PROJECT_EXECUTION_LOCKS.setdefault(
                    project_key,
                    threading.Lock(),
                )

            if not execution_lock.acquire(blocking=False):
                with _PROJECT_EXECUTION_LOCKS_GUARD:
                    active_action = _PROJECT_EXECUTION_ACTIONS.get(
                        project_key,
                        "execution",
                    )

                _LOGGER.warning(
                    "Project execution busy project=%s requested=%s active=%s",
                    project_key,
                    action_name,
                    active_action,
                )
                return {
                    "ok": False,
                    "project_id": project_id,
                    "action": action_name,
                    "status": "busy",
                    "execution_status": "running",
                    "message": (
                        "Project execution is already processing "
                        f"'{active_action}'."
                    ),
                }

            with _PROJECT_EXECUTION_LOCKS_GUARD:
                _PROJECT_EXECUTION_ACTIONS[project_key] = action_name

            _LOGGER.info(
                "Project execution start project=%s action=%s",
                project_key,
                action_name,
            )
            try:
                result = method(self, project_id, *args, **kwargs)
                result_status = (
                    str(result.get("status") or "")
                    if isinstance(result, dict)
                    else "unknown"
                )
                log_method = (
                    _LOGGER.warning
                    if result_status.lower()
                    in {"failed", "blocked", "cancelled", "canceled"}
                    else _LOGGER.info
                )
                log_method(
                    "Project execution finish project=%s action=%s status=%s",
                    project_key,
                    action_name,
                    result_status,
                )
                return result
            except Exception:
                _LOGGER.exception(
                    "Project execution exception project=%s action=%s",
                    project_key,
                    action_name,
                )
                raise
            finally:
                with _PROJECT_EXECUTION_LOCKS_GUARD:
                    _PROJECT_EXECUTION_ACTIONS.pop(project_key, None)
                execution_lock.release()

        return guarded

    return decorate

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
            "create": "implement",
            "edit": "implement",
            "write": "write",
            "modify": "implement",
            "patch": "implement",
            "fix": "implement",
            "refactor": "implement",
            "execute": "execute",
            "run": "execute",
            "run_file": "execute",
            "run_script": "execute",
            "python_run": "execute",
            "command": "command",
            "shell": "command",
            "run_command": "command",
            "review": "review",
            "analyze": "review",
            "analysis": "review",
            "inspect": "review",
            "verify": "verify",
            "validation": "verify",
            "validate": "verify",
            "test": "verify",
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
        "next",
        "next_task",
        "next_step",
        "run_all",
        "pause",
        "stop",
        "approve",
        "reset",
        "state",
        "get_state",
        "status",
    }

    def __init__(
        self,
        project_workspace_service,
        chat_execution_service=None,
        execution_orchestrator_service=None,
    ):
        self.project_workspace_service = (
            project_workspace_service
        )

        self.chat_execution_service = (
            chat_execution_service
        )

        self.execution_orchestrator_service = (
            execution_orchestrator_service
        )
        self.execution_approval_service = (
            ExecutionApprovalService()
        )

        self.artifact_publisher = (
            ProjectArtifactPublisherService(
                project_workspace_service=(
                    project_workspace_service
                )
            )
        )

    @_exclusive_project_execution("reset")
    def reset_execution_state(
        self,
        project_id,
    ):
        execution = (
            self.project_workspace_service
            .reset_execution_state(
                project_id
            )
        )

        if execution is None:
            return None

        orchestrator = self.execution_orchestrator_service
        state_service = getattr(
            orchestrator,
            "execution_state_service",
            None,
        )

        if state_service is not None and hasattr(
            state_service,
            "save_execution_state",
        ):
            state_service.save_execution_state(
                f"project:{project_id}",
                {
                    "steps": [],
                    "current_index": 0,
                    "status": "ready",
                    "waiting": False,
                    "complete": False,
                    "project_id": project_id,
                    "project_controller_managed": True,
                },
            )

        return {
            "ok": True,
            "project_id": project_id,
            "action": "reset",
            "status": "ready",
            "execution": execution,
            "message": "Project execution was reset and is ready.",
        }

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
            "succeeded",
            "finished",
        }

        non_runnable_statuses = {
            "completed",
            "complete",
            "done",
            "success",
            "succeeded",
            "finished",
            "cancelled",
            "canceled",
            "blocked",
            "failed",
            "failure",
            "error",
            "errored",
            "exception",
            "waiting",
            "waiting_input",
            "needs_input",
            "waiting_approval",
            "awaiting_approval",
            "paused",
            "stopped",
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

            owner = str(task.get("owner") or "NOVA").strip().upper()
            if owner in {"USER", "COLLABORATIVE"}:
                continue

            nested_steps = (
                task.get("steps")
                or task.get("substeps")
                or task.get("execution_steps")
                or []
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
                "succeeded",
                "finished",
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

                if nested_status in {
                    "failed",
                    "failure",
                    "error",
                    "errored",
                    "exception",
                    "blocked",
                } or nested_error:
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
                "finished",
                "failed",
                "failure",
                "error",
                "errored",
                "exception",
                "blocked",
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

            _execution_debug(
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

            if status in non_runnable_statuses:
                continue

            # A failed child is authoritative. Do not automatically retry a
            # parent that still says open because of stale or legacy state.
            if nested_real_failure:
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

                    _execution_debug(
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
                nested_steps = (
                    task.get("steps")
                    or task.get("substeps")
                    or task.get("execution_steps")
                    or []
                )

                execution_fields = (
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

                has_task_instructions = any(
                    task.get(field_name)
                    for field_name in execution_fields
                )

                has_executable_nested_step = (
                    isinstance(nested_steps, list)
                    and any(
                        isinstance(step, dict)
                        and (
                            any(
                                step.get(field_name)
                                for field_name in execution_fields
                            )
                            or str(
                                step.get("action") or ""
                            ).strip().lower()
                            in {
                                "implement",
                                "create",
                                "write",
                                "edit",
                                "modify",
                                "refactor",
                                "delete",
                                "test",
                                "verify",
                                "validate",
                                "analysis",
                                "analyze",
                                "research",
                                "review",
                                "plan",
                                "planning",
                                "design",
                                "document",
                                "run",
                                "execute",
                            }
                        )
                        for step in nested_steps
                    )
                )

                has_executable_task_action = (
                    str(
                        task.get("action") or ""
                    ).strip().lower()
                    in {
                        "implement",
                        "create",
                        "write",
                        "edit",
                        "modify",
                        "refactor",
                        "delete",
                        "test",
                        "verify",
                        "validate",
                        "analysis",
                        "analyze",
                        "research",
                        "review",
                        "plan",
                        "planning",
                        "design",
                        "document",
                        "run",
                        "execute",
                    }
                )

                if (
                    has_task_instructions
                    or has_executable_nested_step
                    or has_executable_task_action
                ):
                    runnable.append(task)

                else:
                    _execution_debug(
                        "[PROJECT TASK SKIPPED: NO EXECUTABLE INSTRUCTIONS]",
                        {
                            "task_id": task.get("id"),
                            "title": task.get("title"),
                        },
                        flush=True,
                    )

        _execution_debug(
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

    @staticmethod
    def _find_execution_failure(execution_state):
        """Return the first failed execution node, including nested steps."""
        failure_statuses = {
            "failed",
            "failure",
            "error",
            "errored",
            "exception",
            "blocked",
            "cancelled",
            "canceled",
        }
        waiting_statuses = {
            "waiting",
            "waiting_input",
            "waiting_approval",
            "awaiting_approval",
            "needs_input",
            "paused",
        }

        pending = [execution_state]
        visited = set()

        while pending:
            node = pending.pop()
            if not isinstance(node, dict) or id(node) in visited:
                continue
            visited.add(id(node))

            statuses = [
                str(node.get(key) or "").strip().lower()
                for key in (
                    "status",
                    "state",
                    "completion_status",
                    "execution_status",
                )
            ]
            status = next((value for value in statuses if value), "")
            metadata = node.get("execution_metadata")
            runtime_result = node.get("runtime_result")

            failed = (
                any(value in failure_statuses for value in statuses)
                or (
                    isinstance(metadata, dict)
                    and metadata.get("success") is False
                    and status not in waiting_statuses
                    and node.get("waiting") is not True
                )
                or (
                    isinstance(runtime_result, dict)
                    and runtime_result.get("ok") is False
                )
                or (
                    bool(node.get("error"))
                    and status not in waiting_statuses
                )
            )

            if failed:
                return {
                    "status": status or "failed",
                    "error": (
                        node.get("error")
                        or (
                            metadata.get("error")
                            if isinstance(metadata, dict)
                            else None
                        )
                        or "Project task execution failed."
                    ),
                    "node": node,
                }

            for key in (
                "execution",
                "execution_state",
                "steps",
                "substeps",
                "execution_steps",
            ):
                child = node.get(key)
                if isinstance(child, dict):
                    pending.append(child)
                elif isinstance(child, list):
                    pending.extend(child)

        return None

    @staticmethod
    def _preflight_execution_steps(steps):
        """Normalize inherited inputs and block malformed executable steps."""
        implementation_actions = {
            "implement",
            "create",
            "write",
            "edit",
            "modify",
            "patch",
            "fix",
            "delete",
        }
        run_actions = {
            "execute",
            "run",
            "run_file",
            "run_script",
            "python_run",
        }
        command_actions = {
            "command",
            "shell",
            "run_command",
        }

        normalized_steps = []
        first_blocker = None

        for raw_step in steps or []:
            if not isinstance(raw_step, dict):
                continue

            step = dict(raw_step)
            action = str(step.get("action") or "").strip().lower()
            target_file = str(step.get("target_file") or "").strip()
            target_files = step.get("target_files") or []

            if isinstance(target_files, str):
                target_files = [target_files]

            if not target_file and isinstance(target_files, list):
                target_file = next(
                    (
                        str(candidate).strip()
                        for candidate in target_files
                        if str(candidate or "").strip()
                    ),
                    "",
                )

            if target_file:
                step["target_file"] = target_file

            execution_file = str(
                step.get("execution_file")
                or step.get("run_file")
                or step.get("script_file")
                or step.get("test_script")
                or step.get("test_file")
                or ""
            ).strip()
            command = str(step.get("command") or "").strip()

            if action in run_actions and not execution_file and target_file:
                execution_file = target_file
                step["execution_file"] = execution_file

            blocker = ""
            if action in implementation_actions and not target_file:
                blocker = (
                    "Execution is blocked because the file operation has no "
                    "target file. Add target_file or a non-empty target_files "
                    "entry to the planned step."
                )
            elif action in run_actions and not (execution_file or command):
                blocker = (
                    "Execution is blocked because the run step has no "
                    "execution_file, command, or runnable target file."
                )
            elif action in command_actions and not command:
                blocker = (
                    "Execution is blocked because the command step has no "
                    "command to run."
                )

            if blocker:
                step["status"] = "blocked"
                step["state"] = "blocked"
                step["completion_status"] = "blocked"
                step["complete"] = False
                step["waiting"] = False
                step["error"] = blocker
                first_blocker = first_blocker or step

            normalized_steps.append(step)

        return normalized_steps, first_blocker

    @staticmethod
    def _project_progress_signature(project):
        """Return the persisted task/step state used for no-progress checks."""
        tasks = project.get("tasks") if isinstance(project, dict) else []
        if not isinstance(tasks, list):
            tasks = []

        signature = []
        for task in tasks:
            if not isinstance(task, dict):
                continue

            child_steps = (
                task.get("steps")
                or task.get("substeps")
                or task.get("execution_steps")
                or []
            )
            if not isinstance(child_steps, list):
                child_steps = []

            signature.append(
                (
                    str(task.get("id") or ""),
                    str(task.get("status") or "").strip().lower(),
                    tuple(
                        (
                            str(step.get("id") or step.get("step_id") or ""),
                            str(
                                step.get("status")
                                or step.get("state")
                                or ""
                            ).strip().lower(),
                        )
                        for step in child_steps
                        if isinstance(step, dict)
                    ),
                )
            )

        return tuple(signature)

    def _finalize_no_runnable_work(self, project_id, action):
        """Persist a truthful terminal or blocked state when nothing can run."""
        import re

        project = self._get_project(project_id)
        if not project:
            return None

        tasks = self._get_tasks(project)
        success_statuses = {
            "completed",
            "complete",
            "done",
            "success",
            "succeeded",
            "finished",
        }
        failure_statuses = {
            "failed",
            "failure",
            "error",
            "errored",
            "exception",
        }
        cancelled_statuses = {"cancelled", "canceled"}
        stopped_statuses = {"stopped"}
        waiting_approval_statuses = {
            "waiting_approval",
            "awaiting_approval",
        }
        waiting_statuses = {
            "waiting",
            "waiting_input",
            "needs_input",
        }
        paused_statuses = {"paused"}

        statuses = [
            str(task.get("status") or "open").strip().lower()
            for task in tasks
        ]
        failed_tasks = [
            task
            for task in tasks
            if str(task.get("status") or "").strip().lower()
            in failure_statuses
        ]
        unfinished_tasks = [
            task
            for task in tasks
            if str(task.get("status") or "open").strip().lower()
            not in (
                success_statuses
                | failure_statuses
                | cancelled_statuses
                | stopped_statuses
                | waiting_approval_statuses
                | waiting_statuses
                | paused_statuses
            )
        ]

        def normalize(value):
            return re.sub(
                r"[^a-z0-9]+",
                "_",
                str(value or "").strip().lower(),
            ).strip("_")

        completed_references = set()
        for task in tasks:
            if str(task.get("status") or "").strip().lower() not in success_statuses:
                continue
            for reference in (task.get("id"), task.get("title")):
                if reference:
                    completed_references.add(str(reference).strip().lower())
                    completed_references.add(normalize(reference))

        blocked_ids = []
        for task in unfinished_tasks:
            dependencies = task.get("dependencies") or []
            if not isinstance(dependencies, list):
                dependencies = []
            unresolved = [
                str(dependency).strip()
                for dependency in dependencies
                if str(dependency or "").strip()
                and str(dependency).strip().lower() not in completed_references
                and normalize(dependency) not in completed_references
            ]

            existing_blocker = str(
                task.get("error")
                or task.get("failure_reason")
                or task.get("blocked_reason")
                or ""
            ).strip()

            if existing_blocker:
                blocker = existing_blocker
            elif unresolved:
                blocker = (
                    "Unresolved dependencies: "
                    + ", ".join(unresolved)
                    + ". The dependency may be missing or cyclic."
                )
            else:
                blocker = ""
                if not blocker:
                    nested_steps = (
                        task.get("steps")
                        or task.get("substeps")
                        or task.get("execution_steps")
                        or []
                    )
                    if isinstance(nested_steps, list):
                        failed_child = next(
                            (
                                step
                                for step in nested_steps
                                if isinstance(step, dict)
                                and (
                                    str(step.get("status") or "").strip().lower()
                                    in {
                                        "failed",
                                        "failure",
                                        "error",
                                        "errored",
                                        "exception",
                                    }
                                    or step.get("error")
                                )
                            ),
                            None,
                        )
                    else:
                        failed_child = None
                    if failed_child is not None:
                        blocker = str(
                            failed_child.get("error")
                            or failed_child.get("failure_reason")
                            or "Nested execution step failed."
                        )
                        task_id = task.get("id")
                        if task_id:
                            self.project_workspace_service.update_task_status(
                                project_id,
                                task_id,
                                "failed",
                                error=blocker,
                            )
                            failed_tasks.append(task)
                        continue
                    blocker = (
                        "No executable input is available for this task. Add the "
                        "required target file, command, execution file, or step input."
                    )

            task_id = task.get("id")
            if task_id:
                self.project_workspace_service.update_task_status(
                    project_id,
                    task_id,
                    "blocked",
                    error=blocker,
                )
                blocked_ids.append(task_id)

        if failed_tasks:
            final_status = "failed"
            queue = [task.get("id") for task in failed_tasks if task.get("id")]
            message = "Project execution ended with failed tasks."
        elif blocked_ids:
            final_status = "blocked"
            queue = blocked_ids
            message = (
                "Project execution is blocked because no remaining task is "
                "runnable. See each blocked task for its blocker."
            )
        elif statuses and all(
            status in success_statuses for status in statuses
        ):
            final_status = "completed"
            queue = []
            message = "Project execution is complete; no work remains."
        elif any(status in waiting_approval_statuses for status in statuses):
            final_status = "waiting_approval"
            queue = [
                task.get("id")
                for task in tasks
                if str(task.get("status") or "").strip().lower()
                in waiting_approval_statuses
                and task.get("id")
            ]
            message = "Project execution is waiting for approval."
        elif any(status in waiting_statuses for status in statuses):
            final_status = "waiting"
            queue = [
                task.get("id")
                for task in tasks
                if str(task.get("status") or "").strip().lower()
                in waiting_statuses
                and task.get("id")
            ]
            message = "Project execution is waiting for required input."
        elif any(status in paused_statuses for status in statuses):
            final_status = "paused"
            queue = [
                task.get("id")
                for task in tasks
                if str(task.get("status") or "").strip().lower()
                in paused_statuses
                and task.get("id")
            ]
            message = "Project execution is paused."
        elif any(status in stopped_statuses for status in statuses):
            final_status = "stopped"
            queue = []
            message = "Project execution was stopped."
        elif statuses and all(
            status in success_statuses | cancelled_statuses for status in statuses
        ):
            final_status = "cancelled"
            queue = []
            message = "Project execution was cancelled before all work completed."
        elif not tasks:
            final_status = "completed"
            queue = []
            message = "Project has no executable work."
        else:
            final_status = "blocked"
            queue = []
            message = "Project execution is blocked because no work can advance."

        execution = self.project_workspace_service.update_execution_state(
            project_id,
            status=final_status,
            current_task_id=queue[0] if queue else None,
            current_step=None,
            queue=queue,
            failed_tasks=[
                task.get("id")
                for task in failed_tasks
                if task.get("id")
            ],
            last_action=action,
        )

        return {
            "ok": final_status in {"completed", "waiting", "waiting_approval"},
            "project_id": project_id,
            "action": action,
            "status": final_status,
            "execution_status": final_status,
            "execution": execution,
            "message": message,
        }

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
            "file_content",
            "code",
            "replacement",
            "command",
            "payload",
            "tool_name",
            "tool",
            "tool_action",
            "verification_file",
            "approval_required",
            "requires_approval",
            "approval_status",
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

            task_title = str(
                task.get(
                    "title",
                    "Project task",
                )
                or "Project task"
            ).strip()

            task_description = str(
                task.get(
                    "description",
                    "",
                )
                or ""
            ).strip()

            task_action = self._normalize_task_action(
                task.get(
                    "action",
                    "analysis",
                )
            )

            nested_steps = (
                task.get("steps")
                or task.get("substeps")
                or task.get("execution_steps")
            )

            # New planner format: execute the real nested steps.
            # Legacy format: preserve the task itself as one runtime step.
            if not isinstance(
                nested_steps,
                list,
            ) or not nested_steps:
                nested_steps = [None]

            for step_index, task_step in enumerate(
                nested_steps
            ):
                if not isinstance(
                    task_step,
                    dict,
                ):
                    task_step = {}

                nested_step_id = (
                    task_step.get("id")
                    or f"{task_id}_step_{step_index + 1}"
                )

                nested_title = str(
                    task_step.get(
                        "title",
                        "",
                    )
                    or ""
                ).strip()

                nested_description = str(
                    task_step.get(
                        "description",
                        "",
                    )
                    or ""
                ).strip()

                nested_action = task_step.get(
                    "action"
                )

                step_action = self._normalize_step_action(
                    nested_action
                    if nested_action
                    else task_action
                )

                # Start with the complete task so task-level execution
                # metadata remains available to the executor.
                step = dict(task)

                # The runtime step represents ONE concrete nested step,
                # not the planner's entire nested step list.
                step.pop(
                    "steps",
                    None,
                )
                step.pop("substeps", None)
                step.pop("execution_steps", None)

                step.update(
                    {
                        "id": (
                            f"project_step_{task_id}_"
                            f"{nested_step_id}"
                        ),
                        "task_id": str(
                            task_id
                        ),
                        "step_id": str(
                            nested_step_id
                        ),
                        "task_title": (
                            task_title
                        ),
                        "title": (
                            nested_title
                            or task_title
                            or "Project step"
                        ),
                        "description": (
                            nested_description
                            or task_description
                        ),
                        "action": step_action,
                        "status": (
                            task_step.get(
                                "status",
                                "pending",
                            )
                            or "pending"
                        ),
                    }
                )

                # Inherit task-level execution metadata first.
                for field_name in execution_fields:
                    if field_name in task:
                        step[field_name] = task.get(
                            field_name
                        )

                # Nested step metadata overrides inherited task metadata.
                for field_name in execution_fields:
                    if field_name in task_step:
                        nested_value = task_step.get(field_name)
                        if (
                            nested_value not in (None, "", [], {})
                            or isinstance(nested_value, bool)
                        ):
                            step[field_name] = nested_value

                # Preserve project context for downstream execution.
                if "project_context" in task_step:
                    step["project_context"] = task_step.get(
                        "project_context"
                    )

                # Preserve the planner's step-specific fields even
                # though they are not execution fields.
                for field_name in (
                    "expected_output",
                    "completion_criteria",
                ):
                    if field_name in task_step:
                        step[field_name] = task_step.get(
                            field_name
                        )

                _execution_debug(
                    "[DEBUG BUILT EXECUTION STEP]",
                    {
                        "id": step.get("id"),
                        "task_id": step.get("task_id"),
                        "step_id": step.get("step_id"),
                        "task_title": step.get("task_title"),
                        "title": step.get("title"),
                        "action": step.get("action"),
                        "execution_mode": step.get(
                            "execution_mode"
                        ),
                        "execution_file": step.get(
                            "execution_file"
                        ),
                        "target_file": step.get(
                            "target_file"
                        ),
                        "command": step.get(
                            "command"
                        ),
                    },
                    flush=True,
                )

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

        _execution_debug(
            "[DEBUG TASKS BEFORE BUILD STEPS]",
            tasks,
            flush=True,
        )

        steps = self._build_execution_steps(
            tasks
        )

        steps, blocked_step = self._preflight_execution_steps(
            steps
        )

        _execution_debug(
            "[DEBUG FINAL STEPS SENT TO EXECUTOR]",
            steps,
            flush=True,
        )

        if not steps:
            return {
                "ok": False,
                "status": "failed",
                "error": (
                    "A runnable task was selected, but no executable "
                    "steps could be built for it."
                ),
                "message": (
                    "Execution cannot continue because the selected "
                    "task produced no executable steps."
                ),
            }

        if blocked_step is not None:
            blocker = str(
                blocked_step.get("error")
                or "Execution is blocked by missing required input."
            )
            return {
                "ok": False,
                "status": "blocked",
                "error": blocker,
                "execution": {
                    "status": "blocked",
                    "complete": False,
                    "waiting": False,
                    "current_index": next(
                        (
                            index
                            for index, candidate in enumerate(steps)
                            if candidate is blocked_step
                            or candidate.get("id") == blocked_step.get("id")
                        ),
                        0,
                    ),
                    "current_step": blocked_step,
                    "steps": steps,
                    "error": blocker,
                    "project_id": project_id,
                    "project_controller_managed": True,
                },
                "message": blocker,
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

        # One canonical execution session per project.
        # Do not key execution state to the first runnable task because
        # the task queue changes as execution progresses.
        session_id = (
            f"project:{project_id}"
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
            _execution_debug(
                "[PROJECT EXECUTION] starting",
                {
                    "session_id": session_id,
                    "command": command,
                    "goal": goal,
                    "step_count": len(steps),
                },
                flush=True,
            )

            _execution_debug(
                "[DEBUG CONTROLLER STEPS BEFORE START]",
                steps,
                flush=True,
            )

            orchestrator = (
                self.execution_orchestrator_service
            )

            if orchestrator is None:
                _execution_debug(
                    "[PROJECT EXECUTION] canonical orchestrator unavailable; "
                    "falling back to legacy execution service",
                    flush=True,
                )

                if command == "run_all":
                    execution = execution_service.run_all(
                        session_id=session_id
                    )
                else:
                    execution = execution_service.advance(
                        session_id=session_id
                    )

                _execution_debug(
                    "[PROJECT EXECUTION] legacy executor returned",
                    type(execution),
                    flush=True,
                )

            else:
                _execution_debug(
                    "[PROJECT EXECUTION] routing through canonical orchestrator",
                    {
                        "session_id": session_id,
                        "command": command,
                    },
                    flush=True,
                )

                execution_state_service = (
                    getattr(
                        orchestrator,
                        "execution_state_service",
                        None,
                    )
                )

                if execution_state_service is None:
                    raise RuntimeError(
                        "Canonical execution state service is unavailable."
                    )

                persisted_state = (
                    execution_state_service.get_execution_state(
                        session_id
                    )
                )

                if not isinstance(
                    persisted_state,
                    dict,
                ):
                    persisted_state = {}

                persisted_task_id = str(
                    persisted_state.get("current_task_id")
                    or ""
                ).strip()

                incoming_task_ids = [
                    str(task.get("id"))
                    for task in tasks
                    if isinstance(task, dict)
                    and task.get("id")
                ]

                same_task = (
                    persisted_task_id
                    and persisted_task_id in incoming_task_ids
                )

                _execution_debug(
                    "[PROJECT EXECUTION PERSISTED STATE]",
                    {
                        "status": persisted_state.get(
                            "status"
                        ),
                        "current_index": persisted_state.get(
                            "current_index"
                        ),
                        "step_count": len(
                            persisted_state.get(
                                "steps",
                                []
                            )
                            if isinstance(
                                persisted_state.get(
                                    "steps",
                                    []
                                ),
                                list,
                            )
                            else []
                        ),
                        "waiting": persisted_state.get(
                            "waiting"
                        ),
                        "mission_id": persisted_state.get(
                            "mission_id"
                        ),
                    },
                    flush=True,
                )

                if command == "approve" and persisted_state.get("steps"):
                    # Approval must continue the exact persisted
                    # execution state. Do not replace its steps
                    # with freshly reconstructed project-task steps,
                    # because those project tasks may still be open
                    # while the canonical execution already has
                    # completed/running/pending step state.
                    execution_state = dict(
                        persisted_state
                    )

                elif command == "approve":
                    workspace_execution = (
                        self.project_workspace_service.get_execution_state(
                            project_id
                        )
                        or {}
                    )
                    approval_index = workspace_execution.get(
                        "current_index",
                        workspace_execution.get("current_step_index", 0),
                    )
                    try:
                        approval_index = int(approval_index)
                    except (TypeError, ValueError):
                        approval_index = 0
                    if approval_index < 0 or approval_index >= len(steps):
                        approval_index = 0

                    # The project workspace can contain the authoritative
                    # approval state before the orchestrator state store has
                    # been initialized. Seed the canonical state from the
                    # approved project task so the same step is released.
                    execution_state = {
                        "steps": steps,
                        "current_index": approval_index,
                        "current_step_index": approval_index,
                        "status": "waiting_approval",
                        "waiting": True,
                        "complete": False,
                        "project_id": project_id,
                    }

                else:
                    # Continue an existing canonical execution when
                    # one is already persisted. Only create a fresh
                    # execution state when no persisted execution exists.

                    if (
                        isinstance(
                            persisted_state,
                            dict,
                        )
                        and persisted_state.get("steps")
                        and same_task
                        and not (
                            command == "run_step"
                            and str(
                                persisted_state.get("status") or ""
                            ).strip().lower() in {
                                "complete",
                                "completed",
                            }
                            and steps
                        )
                    ):
                        execution_state = dict(
                            persisted_state
                        )

                        if steps and not persisted_state.get("steps"):
                            execution_state["steps"] = steps
                            execution_state["current_index"] = 0
                            execution_state["status"] = "pending"
                            execution_state["complete"] = False
                            execution_state["waiting"] = False
                    else:
                        execution_state = {
                            "steps": steps,
                            "current_index": 0,
                            "status": "pending",
                            "waiting": False,
                            "complete": False,
                            "project_id": project_id,
                            "command": command,
                        }

                        # Preserve an existing mission identifier
                        # when one already exists.


                if (
                    isinstance(
                        persisted_state,
                        dict,
                    )
                    and persisted_state.get(
                        "mission_id"
                    )
                ):
                    execution_state[
                        "mission_id"
                    ] = persisted_state.get(
                        "mission_id"
                    )
                execution_state["project_id"] = (
                    project_id
                )

                execution_state["project_controller_managed"] = True

                execution_state["command"] = (
                    command
                )

                if command == "run_step":
                    execution_state[
                        "continue_request"
                    ] = True

                if command == "run_all":
                    execution_state[
                        "continue_request"
                    ] = True
                    execution_state[
                        "run_all"
                    ] = True

                execution = (
                    orchestrator.process_execution(
                        session_id=session_id,
                        state=execution_state,
                        command=command,
                    )
                )

                _execution_debug(
                    "[POST ORCHESTRATOR TASK REFRESH BEFORE]",
                    tasks,
                    flush=True,
                )

                project = (
                    self.project_workspace_service
                    .get_project(
                        project_id
                    )
                )

                tasks = (
                    project.get("tasks", [])
                    if isinstance(
                        project,
                        dict,
                    )
                    else []
                )

                _execution_debug(
                    "[POST ORCHESTRATOR TASK REFRESH AFTER]",
                    tasks,
                    flush=True,
                )

                _execution_debug(
                    "[EXECUTOR RETURN DEBUG]",
                    execution,
                    flush=True,
                )

                _execution_debug(
                    "[PROJECT EXECUTION] canonical orchestrator returned",
                    type(execution),
                    flush=True,
                )

        except Exception as exc:
            _execution_debug(
                "[PROJECT EXECUTION ERROR]",
                repr(exc),
                flush=True,
            )

            return {
                "ok": False,
                "status": "failed",
                "task_id": task_ids[0] if task_ids else None,
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
                "status": "failed",
                "task_id": task_ids[0] if task_ids else None,
                "error": (
                    "The execution service "
                    "returned no result."
                ),
            }

        execution = self._repair_execution_history(
            execution
        )

        assistant_message = (
            execution.get("assistant_message")
            if isinstance(
                execution,
                dict,
            )
            else None
        )

        if not isinstance(
            assistant_message,
            dict,
        ):
            assistant_message = {
                "role": "assistant",
                "text": (
                    execution_service.format_reply(
                        execution
                    )
                ),
            }

        return {
            "ok": bool(
                execution.get(
                    "ok",
                    True,
                )
            ),
            "execution": execution,
            "assistant_message": assistant_message,
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

    def _pending_approval_step(
        self,
        task,
    ):
        if not isinstance(task, dict):
            return None

        nested_steps = (
            task.get("steps")
            or task.get("substeps")
            or task.get("execution_steps")
            or []
        )

        if not isinstance(nested_steps, list):
            return None

        for step in nested_steps:
            if not isinstance(step, dict):
                continue

            evaluation = (
                self.execution_approval_service.evaluate(
                    step
                )
            )

            if evaluation.get("waiting"):
                return step

        return None

    @_exclusive_project_execution("approve")
    def approve_project(
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

        execution_state = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        current_task_id = (
            execution_state.get(
                "current_task_id"
            )
        )

        current_task = None

        for task in tasks:
            if not isinstance(
                task,
                dict,
            ):
                continue

            if task.get("id") == current_task_id:
                current_task = task
                break

        if current_task is None:
            return {
                "ok": False,
                "project_id": project_id,
                "action": "approve",
                "status": "error",
                "message": (
                    "No current execution task "
                    "is available for approval."
                ),
            }

        orchestrator_state = {}
        orchestrator = self.execution_orchestrator_service
        state_service = getattr(orchestrator, "execution_state_service", None)
        if state_service is not None and hasattr(
            state_service,
            "get_execution_state",
        ):
            candidate_state = state_service.get_execution_state(
                f"project:{project_id}"
            )
            if isinstance(candidate_state, dict):
                orchestrator_state = candidate_state

        canonical_steps = (
            orchestrator_state.get("steps")
            or execution_state.get("steps")
            or []
        )
        canonical_index = orchestrator_state.get(
            "current_index",
            orchestrator_state.get(
                "current_step_index",
                execution_state.get(
                    "current_index",
                    execution_state.get("current_step_index", 0),
                ),
            ),
        )

        try:
            canonical_index = int(canonical_index)
        except (TypeError, ValueError):
            canonical_index = 0

        pending_approval_step = None

        if (
            isinstance(canonical_steps, list)
            and 0 <= canonical_index < len(canonical_steps)
            and isinstance(canonical_steps[canonical_index], dict)
        ):
            candidate_step = canonical_steps[canonical_index]

            evaluation = self.execution_approval_service.evaluate(
                candidate_step
            )

            if (
                evaluation.get("waiting")
                or candidate_step.get("approval_required") is True
                or candidate_step.get("requires_approval") is True
                or str(
                    candidate_step.get("approval_status") or ""
                ).strip().lower()
                in {
                    "pending",
                    "waiting_approval",
                    "awaiting_approval",
                    "approval_required",
                }
            ):
                pending_approval_step = candidate_step

        if pending_approval_step is None:
            pending_approval_step = self._pending_approval_step(
                current_task
            )

        if pending_approval_step is None:
            return {
                "ok": False,
                "project_id": project_id,
                "action": "approve",
                "status": "error",
                "message": (
                    "No pending approval is available "
                    "for the current execution task."
                ),
            }

        approved_step = (
            self.execution_approval_service.approve_step(
                pending_approval_step
            )
        )

        updated_tasks = []

        for task in tasks:
            if (
                isinstance(task, dict)
                and task.get("id") == current_task_id
            ):
                task = dict(task)
                pending_step_id = str(
                    pending_approval_step.get("id")
                    or pending_approval_step.get("step_id")
                    or ""
                ).strip()
                nested_step_key = next(
                    (
                        key
                        for key in (
                            "steps",
                            "substeps",
                            "execution_steps",
                        )
                        if isinstance(task.get(key), list)
                        and any(
                            isinstance(step, dict)
                            and (
                                step is pending_approval_step
                                or str(
                                    step.get("id")
                                    or step.get("step_id")
                                    or ""
                                ).strip()
                                == pending_step_id
                            )
                            for step in task.get(key)
                        )
                    ),
                    None,
                )
                if nested_step_key is None:
                    nested_step_key = next(
                        (
                            key
                            for key in (
                                "steps",
                                "substeps",
                                "execution_steps",
                            )
                            if isinstance(task.get(key), list)
                            and task.get(key)
                        ),
                        None,
                    )
                nested_steps = (
                    task.get(nested_step_key) or []
                    if nested_step_key
                    else []
                )
                matched_nested_step = False

                if isinstance(nested_steps, list):
                    updated_steps = []

                    for step in nested_steps:
                        if (
                            isinstance(step, dict)
                            and str(
                                step.get("id")
                                or step.get("step_id")
                                or ""
                            ).strip()
                            == str(
                                pending_approval_step.get("id")
                                or pending_approval_step.get("step_id")
                                or ""
                            ).strip()
                        ):
                            updated_steps.append(
                                approved_step
                            )
                            matched_nested_step = True
                        else:
                            updated_steps.append(step)

                    if nested_step_key:
                        task[nested_step_key] = updated_steps

                if not matched_nested_step:
                    # A task-level approval is represented as a synthesized
                    # runtime step. Persist the grant on the task itself so
                    # rebuilding the canonical step preserves the decision.
                    task["approved"] = True
                    task["approval_required"] = False
                    task["requires_approval"] = False
                    task["approval_status"] = "approved"
                    task["approval_was_required"] = True
                    task.pop("error", None)

            updated_tasks.append(task)

        persisted_tasks = (
            self.project_workspace_service.update_project_tasks(
                project_id,
                updated_tasks,
            )
        )

        if persisted_tasks is None:
            return {
                "ok": False,
                "project_id": project_id,
                "action": "approve",
                "status": "error",
                "message": (
                    "Failed to persist execution approval."
                ),
            }

        current_task = next(
            (
                task
                for task in persisted_tasks
                if isinstance(task, dict)
                and task.get("id") == current_task_id
            ),
            current_task,
        )


        result = (
            self._execute_with_existing_orchestrator(
                project_id=project_id,
                tasks=[current_task],
                command="approve",
            )
        )

        _execution_debug(
            "[APPROVE RAW ORCHESTRATOR RESULT]",
            repr(result),
            flush=True,
        )

        self._sync_project_execution(
            project_id,
            result,
            "approve",
        )

        persisted_execution = (
            self.project_workspace_service.get_execution_state(project_id)
            or {}
        )

        persisted_status = str(
            persisted_execution.get("status") or ""
        ).strip().lower()
        unsuccessful_statuses = {
            "failed",
            "failure",
            "error",
            "errored",
            "exception",
            "blocked",
            "cancelled",
            "canceled",
        }
        approval_ok = (
            isinstance(result, dict)
            and result.get("ok", False) is not False
            and persisted_status not in unsuccessful_statuses
        )

        published_artifacts = []
        if approval_ok:
            published_artifacts = self._publish_completed_artifacts(
                project_id,
                [current_task],
                result,
            )

        response_message = (
            result.get("assistant_message", {}).get("text")
            if isinstance(result, dict)
            and isinstance(result.get("assistant_message"), dict)
            else ""
        )
        response_error = str(
            persisted_execution.get("error")
            or (result.get("error") if isinstance(result, dict) else "")
            or ""
        )

        return {
            "ok": approval_ok,
            "project_id": project_id,
            "action": "approve",
            "status": persisted_status or (
                "running" if approval_ok else "failed"
            ),
            "artifacts": published_artifacts,
            "execution": persisted_execution,
            "error": response_error or None,
            "message": response_message or response_error or "Execution approved.",
        }


    @_exclusive_project_execution("next_step")
    def continue_project(
        self,
        project_id,
    ):
        project = self._get_project(
            project_id
        )

        if not project:
            return None

        existing_execution = (
            self.project_workspace_service
            .get_execution_state(
                project_id
            )
            or {}
        )

        existing_steps = (
            existing_execution.get("steps")
            or []
        )

        existing_index = (
            existing_execution.get(
                "current_index",
                existing_execution.get("current_step_index", 0),
            )
        )
        if not isinstance(existing_index, int) or existing_index < 0:
            existing_index = 0

        if (
            existing_execution.get("status") == "running"
            and isinstance(existing_steps, list)
            and existing_index < len(existing_steps)
        ):
            _execution_debug(
                "[PROJECT CONTINUE RESUME EXISTING EXECUTION]",
                {
                    "current_index": existing_index,
                    "step_count": len(existing_steps),
                },
                flush=True,
            )

        tasks = self._get_tasks(
            project
        )

        _execution_debug(
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

        executable_tasks = [
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
                "succeeded",
                "finished",
                "cancelled",
                "canceled",
            }
            and (
                task.get("steps")
                or task.get("substeps")
                or task.get("execution_steps")
                or task.get("command")
                or task.get("target_file")
                or task.get("target_files")
                or task.get("content")
                or task.get("code")
                or task.get("replacement")
                or task.get("execution_file")
            )
        ]

        # No currently runnable task does NOT automatically
        # mean the project is complete.
        #
        # First determine whether there are unfinished tasks.

        ignored_tasks = [
            task
            for task in tasks
            if isinstance(task, dict)
            and task not in executable_tasks
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

        unfinished_tasks = [
            task
            for task in executable_tasks
            if str(
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
            for task in executable_tasks
            if str(
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
            queue = [
                task.get("id")
                for task in failed_tasks
                if task.get("id")
            ]
            execution = self.project_workspace_service.update_execution_state(
                project_id,
                status="failed",
                current_task_id=None,
                current_step=None,
                queue=queue,
                failed_tasks=queue,
                last_action="continue",
            )
            return {
                "ok": False,
                "project_id": project_id,
                "action": "continue",
                "execution": execution,
                "status": "failed",
                "message": "Project execution ended with failed tasks.",
            }

        if not runnable:
            return self._finalize_no_runnable_work(
                project_id,
                "continue",
            )

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

        progress_before = self._project_progress_signature(project)

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
            control_request=None,
            current_task_id=current_task_id,
            current_step=(
                current_task.get("steps", [{}])[0].get(
                    "title",
                    current_task.get("title", "Current task"),
                )
                if isinstance(current_task.get("steps"), list)
                and current_task.get("steps")
                and isinstance(current_task.get("steps")[0], dict)
                else current_task.get("title", "Current task")
            ),
            queue=queue,
            last_action="continue",
        )

        result = self._execute_with_existing_orchestrator(
            project_id=project_id,
            tasks=[current_task],
            command="run_step",
        )

        _execution_debug(
            "[CONTINUE RAW ORCHESTRATOR RESULT]",
            repr(result),
            flush=True,
        )

        self._sync_project_execution(
            project_id,
            result,
            "continue",
            tasks=[current_task],
        )

        persisted_control = (
            self.project_workspace_service.get_execution_state(project_id)
            or {}
        )
        persisted_status = str(
            persisted_control.get("status") or ""
        ).strip().lower()
        control_request = str(
            persisted_control.get("control_request") or ""
        ).strip().lower()
        if persisted_status in {
            "failed",
            "blocked",
            "cancelled",
            "canceled",
        }:
            self.project_workspace_service.update_execution_state(
                project_id,
                status=(
                    "cancelled"
                    if persisted_status in {"cancelled", "canceled"}
                    else persisted_status
                ),
                control_request=None,
                last_action="continue",
            )
            control_request = ""

        if control_request in {"pause", "stop"}:
            latest_project = self._get_project(project_id) or {}
            latest_tasks = self._get_tasks(latest_project)
            all_tasks_completed = bool(latest_tasks) and all(
                str(task.get("status") or "").strip().lower()
                in {"completed", "complete", "done", "success", "succeeded"}
                for task in latest_tasks
                if isinstance(task, dict)
            )

            if all_tasks_completed:
                self.project_workspace_service.update_execution_state(
                    project_id,
                    status="completed",
                    current_task_id=None,
                    current_step=None,
                    queue=[],
                    control_request=None,
                    last_action="continue",
                )
                completed_project = self._get_project(project_id) or {}
                return {
                    "ok": True,
                    "project_id": project_id,
                    "action": "continue",
                    "status": "completed",
                    "execution_status": "completed",
                    "execution": completed_project.get("execution") or {},
                    "message": "Project execution is complete; no work remains.",
                }

            control_status = (
                "paused" if control_request == "pause" else "stopped"
            )
            return {
                "ok": False,
                "project_id": project_id,
                "action": "continue",
                "status": control_status,
                "execution_status": control_status,
                "execution": persisted_control,
                "message": f"Project execution is {control_status}.",
            }

        execution_result = result if isinstance(result, dict) else {}
        for _ in range(3):
            nested = (
                execution_result.get("execution")
                or execution_result.get("execution_state")
            )
            if not isinstance(nested, dict):
                break
            execution_result = nested

        execution_status = str(
            execution_result.get("status") or ""
        ).strip().lower()
        execution_failure = self._find_execution_failure(execution_result)

        if execution_failure is not None:
            failure_status = str(
                execution_failure.get("status") or "failed"
            ).strip().lower()
            final_status = (
                "blocked"
                if failure_status == "blocked"
                else (
                    "cancelled"
                    if failure_status in {"cancelled", "canceled"}
                    else "failed"
                )
            )
            message = str(
                execution_failure.get("error")
                or (
                    "Project execution was cancelled."
                    if final_status == "cancelled"
                    else "Project execution failed."
                )
            )
        elif execution_status in {
            "waiting",
            "waiting_approval",
            "awaiting_approval",
            "needs_input",
            "waiting_input",
            "paused",
        }:
            final_status = (
                "paused"
                if execution_status == "paused"
                else (
                    "waiting_approval"
                    if execution_status in {
                        "waiting_approval",
                        "awaiting_approval",
                    }
                    else "waiting"
                )
            )
            message = "Project execution is waiting before it can advance."
        else:
            refreshed_project = self._get_project(project_id) or {}
            refreshed_tasks = self._get_tasks(refreshed_project)
            remaining_runnable = self._runnable_tasks(refreshed_tasks)
            failed_after = [
                task
                for task in refreshed_tasks
                if str(task.get("status") or "").strip().lower()
                in {"failed", "error"}
            ]
            unfinished_after = [
                task
                for task in refreshed_tasks
                if str(task.get("status") or "").strip().lower()
                not in {
                    "completed",
                    "complete",
                    "done",
                    "success",
                    "cancelled",
                    "canceled",
                }
            ]

            if failed_after:
                final_status = "failed"
                message = "Project execution ended with a failed task."
            elif remaining_runnable:
                final_status = "ready"
                message = "One execution step advanced; more work is ready."
            elif unfinished_after:
                final_status = "blocked"
                message = (
                    "Project execution is blocked by unresolved dependencies "
                    "or missing executable input."
                )
            else:
                final_status = "completed"
                message = "Project execution is complete; no work remains."

            if (
                final_status == "ready"
                and self._project_progress_signature(refreshed_project)
                == progress_before
            ):
                final_status = "blocked"
                message = (
                    "Execution stopped because no progress was possible for "
                    f"task '{current_task.get('title') or current_task_id}'."
                )

        active_task_id = (
            current_task_id
            if final_status in {
                "waiting",
                "waiting_approval",
                "paused",
                "blocked",
            }
            else None
        )
        queue = [active_task_id] if active_task_id else []
        if final_status in {"failed", "blocked", "cancelled"} and current_task_id:
            self.project_workspace_service.update_task_status(
                project_id,
                current_task_id,
                final_status,
                error=message,
            )
        persisted_execution = (
            self.project_workspace_service.update_execution_state(
                project_id,
                status=final_status,
                current_task_id=active_task_id,
                current_step=(
                    current_task.get("title")
                    if active_task_id
                    else None
                ),
                queue=queue,
                last_action="continue",
            )
        )

        published_artifacts = []
        if final_status in {"ready", "completed"}:
            published_artifacts = self._publish_completed_artifacts(
                project_id,
                [current_task],
                result,
            )

        return {
            "ok": final_status not in {"failed", "blocked", "cancelled"},
            "project_id": project_id,
            "action": "continue",
            "status": final_status,
            "execution_status": final_status,
            "artifacts": published_artifacts,
            "execution": persisted_execution,
            "message": message,
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

            # The canonical execution can mark the overall
            # execution complete while the embedded step remains
            # pending. When the execution itself is explicitly
            # complete, promote the corresponding project task.
            execution_status = str(
                execution.get(
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            execution_complete = (
                execution_status
                in {
                    "complete",
                    "completed",
                    "done",
                    "success",
                }
                or execution.get(
                    "complete",
                    False,
                ) is True
            )

            if (
                execution_complete
                and normalized_status
                not in {
                    "failed",
                    "blocked",
                }
            ):
                normalized_status = "completed"

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


    @_exclusive_project_execution("run_all")
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

            if execution_status in {
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
                    "execution": execution_state,
                    "artifacts": all_published_artifacts,
                    "debug_last_result": last_result,
                    "message": (
                        "Project execution is paused."
                        if execution_status == "paused"
                        else "Project execution was stopped."
                    ),
                }

            if execution_state.get("control_request"):
                return {
                    "ok": False,
                    "project_id": project_id,
                    "action": "run_all",
                    "status": execution_status or "paused",
                    "execution": execution_state,
                    "artifacts": all_published_artifacts,
                    "message": "Project execution is awaiting a control action.",
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

            _execution_debug(
                "[PROJECT RUN-ALL LOOP]",
                loop_guard,
                "RUNNABLE:",
                len(runnable),
                flush=True,
            )

            projects = (
                self.project_workspace_service
                ._load_projects()
            )

            _execution_debug(
                "[RUN_ALL PROJECT LOAD DEBUG]",
                {
                    "type": type(projects).__name__,
                    "count": len(projects) if isinstance(projects, list) else None,
                    "project_ids": [
                        p.get("id")
                        for p in projects
                        if isinstance(p, dict)
                    ] if isinstance(projects, list) else None,
                },
                flush=True,
            )
            if not runnable:
                return self._finalize_no_runnable_work(
                    project_id,
                    "run_all",
                )

            current_task = runnable[0]

            # Refresh task from persistent storage before execution.
            # Previous task syncs may have changed dependency/status state.
            fresh_project = self._get_project(
                project_id
            )

            if isinstance(fresh_project, dict):
                fresh_tasks = fresh_project.get(
                    "tasks",
                    [],
                )

                if isinstance(fresh_tasks, list):
                    fresh_task = next(
                        (
                            task
                            for task in fresh_tasks
                            if isinstance(task, dict)
                            and task.get("id") == current_task.get("id")
                        ),
                        None,
                    )

                    if isinstance(fresh_task, dict):
                        current_task = fresh_task

            if not isinstance(
                current_task,
                dict,
            ):
                _execution_debug(
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

            progress_before = self._project_progress_signature(
                fresh_project
                if isinstance(fresh_project, dict)
                else project
            )

            # FINAL DEPENDENCY EXECUTION GATE
            dependencies = current_task.get("dependencies", [])

            if isinstance(dependencies, list) and dependencies:
                dependency_context_tasks = (
                    fresh_tasks
                    if "fresh_tasks" in locals()
                    and isinstance(fresh_tasks, list)
                    else tasks
                )
                runnable_check = self._runnable_tasks(
                    dependency_context_tasks
                )
                current_task_is_runnable = any(
                    isinstance(candidate, dict)
                    and candidate.get("id") == current_task.get("id")
                    for candidate in runnable_check
                )

                if not current_task_is_runnable:
                    _execution_debug(
                        "[PROJECT RUN-ALL FINAL DEPENDENCY BLOCK]",
                        {
                            "task": current_task.get("title"),
                            "dependencies": dependencies,
                        },
                        flush=True,
                    )

                    current_task["status"] = "blocked"
                    current_task["error"] = (
                        "Dependencies unresolved"
                    )

                    self._sync_project_execution(
                        project_id,
                        {
                            "status": "blocked",
                            "task_id": current_task.get("id"),
                            "error": "Dependencies unresolved",
                        },
                        "run_all",
                        tasks=[current_task],
                    )

                    continue

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
                result = (
                    self._execute_with_existing_orchestrator(
                        project_id=project_id,
                        tasks=[current_task],
                        command="run_all",
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
                # Normalize the task result before synchronization.
                # The execution service may return ok=True even when the
                # nested execution is waiting for input or approval.

                if not isinstance(result_execution, dict):
                    result_execution = {}

                nested_execution = result_execution.get("execution")

                if isinstance(nested_execution, dict):
                    result_execution = nested_execution

                execution_failure = self._find_execution_failure(
                    result_execution
                )

                execution_status = str(
                    result_execution.get("status")
                    or result_status
                    or ""
                ).strip().lower()

                _execution_debug(
                    "[EXECUTION STATUS DETAILS]",
                    {
                        "result_ok": result_ok,
                        "result_status": result_status,
                        "execution_status": execution_status,
                        "complete": result_execution.get("complete"),
                        "completed": result_execution.get("completed"),
                        "steps": result_execution.get("steps"),
                    },
                    flush=True,
                )

                execution_complete = (
                    result_execution.get("complete") is True
                    or execution_status in {
                        "completed",
                        "complete",
                        "done",
                    }
                )

                execution_waiting = (
                    result_execution.get("waiting") is True
                    or execution_status in {
                        "waiting",
                        "waiting_input",
                        "waiting_approval",
                        "awaiting_approval",
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
                        "waiting_input",
                        "waiting_approval",
                        "awaiting_approval",
                    }
                )

                execution_failed = (
                    (result_ok is False and not execution_waiting)
                    or execution_failure is not None
                    or result_status in {
                        "failed",
                        "failure",
                        "error",
                        "errored",
                        "exception",
                        "blocked",
                        "cancelled",
                        "canceled",
                    }
                    or execution_status in {
                        "failed",
                        "failure",
                        "error",
                        "errored",
                        "exception",
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

                _execution_debug(
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

                if execution_failed:
                    failure_status = str(
                        (
                            execution_failure.get("status")
                            if isinstance(execution_failure, dict)
                            else ""
                        )
                        or execution_status
                        or result_status
                        or "failed"
                    ).strip().lower()
                    terminal_status = (
                        "blocked"
                        if failure_status == "blocked"
                        else (
                            "cancelled"
                            if failure_status in {"cancelled", "canceled"}
                            else "failed"
                        )
                    )
                    failure_error = (
                        execution_failure.get("error")
                        if execution_failure
                        else None
                    )
                    if not failure_error and isinstance(result, dict):
                        failure_error = (
                            result_execution.get("error")
                            or result.get("error")
                            or result.get("message")
                        )
                    failure_error = (
                        failure_error or "Project task execution failed."
                    )
                    current_task_id = str(
                        current_task.get("id") or ""
                    ).strip()

                    current_task["status"] = terminal_status
                    current_task["error"] = str(failure_error)

                    if current_task_id:
                        failed_node = (
                            execution_failure.get("node")
                            if isinstance(execution_failure, dict)
                            else None
                        )
                        failed_node_task_id = str(
                            failed_node.get("task_id") or ""
                        ).strip() if isinstance(failed_node, dict) else ""
                        failed_step_id = str(
                            (
                                failed_node.get("step_id")
                                or failed_node.get("id")
                            )
                            or ""
                        ).strip() if isinstance(failed_node, dict) else ""

                        step_update = None
                        if (
                            failed_step_id
                            and failed_node_task_id == current_task_id
                        ):
                            step_update = (
                                self.project_workspace_service
                                .update_nested_step_status(
                                    project_id,
                                    current_task_id,
                                    failed_step_id,
                                    terminal_status,
                                    result=str(failure_error),
                                    error=str(failure_error),
                                )
                            )

                        if not isinstance(step_update, dict):
                            self.project_workspace_service.update_task_status(
                                project_id,
                                current_task_id,
                                terminal_status,
                                error=str(failure_error),
                            )

                    execution = (
                        self.project_workspace_service.update_execution_state(
                            project_id,
                            status=terminal_status,
                            current_task_id=None,
                            current_step=None,
                            queue=[],
                            last_action="run_all",
                        )
                    )

                    return {
                        "ok": False,
                        "project_id": project_id,
                        "action": "run_all",
                        "status": terminal_status,
                        "execution": execution,
                        "debug_last_result": result,
                        "message": (
                            "Project execution is blocked by missing or "
                            "unresolved task input."
                            if terminal_status == "blocked"
                            else (
                                "Project execution failed while processing "
                                "a task."
                            )
                        ),
                    }

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

                            if not isinstance(
                                task_update_result,
                                dict,
                            ):
                                raise RuntimeError(
                                    "Task completion was not persisted: "
                                    "update_task_status returned no task"
                                )

                            persisted_task_id = str(
                                task_update_result.get("id") or ""
                            ).strip()

                            if persisted_task_id != current_task_id:
                                raise RuntimeError(
                                    "Task completion persistence returned "
                                    "the wrong task"
                                )

                            persisted_status = str(
                                task_update_result.get("status") or ""
                            ).strip().lower()

                            if persisted_status not in {
                                "completed",
                                "complete",
                                "done",
                                "success",
                            }:
                                raise RuntimeError(
                                    "Task completion was not persisted: "
                                    f"returned status={persisted_status!r}"
                                )

                            current_task["status"] = "completed"

                            try:
                                self.project_workspace_service.add_activity(
                                    project_id,
                                    "Task completed",
                                    str(
                                        current_task.get("title")
                                        or current_task.get("name")
                                        or current_task_id
                                    ),
                                )
                            except Exception as activity_error:
                                _execution_debug(
                                    "[PROJECT ACTIVITY LOG ERROR]",
                                    str(activity_error),
                                    flush=True,
                                )

                            _execution_debug(
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
                            error_message = (
                                "Execution succeeded, but the task status "
                                f"could not be persisted: {exc}"
                            )

                            _execution_debug(
                                "[PROJECT RUN-ALL TASK COMPLETION ERROR]",
                                {
                                    "project_id": project_id,
                                    "task_id": current_task_id,
                                    "error": error_message,
                                },
                                flush=True,
                            )

                            current_task["status"] = "failed"
                            current_task["error"] = error_message


                            try:
                                failed_task_update_result = (
                                    self.project_workspace_service
                                    .update_task_status(
                                        project_id,
                                        current_task_id,
                                        "failed",
                                        error=error_message,
                                    )
                                )

                                if not isinstance(
                                    failed_task_update_result,
                                    dict,
                                ):
                                    raise RuntimeError(
                                        "update_task_status returned no "
                                        "persisted failed task"
                                    )

                                failed_task_id = str(
                                    failed_task_update_result.get("id") or ""
                                ).strip()

                                failed_task_status = str(
                                    failed_task_update_result.get("status")
                                    or ""
                                ).strip().lower()

                                if failed_task_id != current_task_id:
                                    raise RuntimeError(
                                        "Failure persistence returned the "
                                        "wrong task"
                                    )

                                if failed_task_status != "failed":
                                    raise RuntimeError(
                                        "Failure persistence returned "
                                        f"status={failed_task_status!r}"
                                    )

                                try:
                                    self.project_workspace_service.add_activity(
                                        project_id,
                                        "Task failed",
                                        str(
                                            current_task.get("title")
                                            or current_task.get("name")
                                            or current_task_id
                                        ),
                                    )
                                except Exception as activity_error:
                                    _execution_debug(
                                        "[PROJECT ACTIVITY LOG ERROR]",
                                        str(activity_error),
                                        flush=True,
                                    )

                                _execution_debug(
                                    "[PROJECT RUN-ALL TASK FAILURE PERSISTED]",
                                    {
                                        "project_id": project_id,
                                        "task_id": current_task_id,
                                        "update_result": (
                                            failed_task_update_result
                                        ),
                                    },
                                    flush=True,
                                )

                            except Exception as failure_exc:
                                _execution_debug(
                                    "[PROJECT RUN-ALL TASK FAILURE "
                                    "PERSISTENCE ERROR]",
                                    {
                                        "project_id": project_id,
                                        "task_id": current_task_id,
                                        "error": str(failure_exc),
                                    },
                                    flush=True,
                                )
                                _execution_debug(
                                    "[PROJECT RUN-ALL TASK FAILURE "
                                    "PERSISTENCE ERROR]",
                                    {
                                        "project_id": project_id,
                                        "task_id": current_task_id,
                                        "error": str(failure_exc),
                                    },
                                    flush=True,
                                )

                            current_task["status"] = "failed"
                            current_task["error"] = (
                                "Execution succeeded, but the task status "
                                f"could not be persisted: {exc}"
                            )

                last_result = result

                _execution_debug(
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

                if (
                    execution_waiting
                    and not execution_failed
                    and not result_success
                ):
                    return {
                        "ok": True,
                        "project_id": project_id,
                        "action": "run_all",
                        "status": execution_status,
                        "artifacts": all_published_artifacts,
                        "execution": result_execution,
                        "debug_last_result": last_result,
                        "message": (
                            "Project execution is waiting for approval."
                            if execution_status == "waiting_approval"
                            else "Project execution is waiting."
                        ),
                    }

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

                _execution_debug(
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
                    _execution_debug(
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

            progress_after = self._project_progress_signature(
                refreshed_project
            )

            if progress_after == progress_before:
                no_progress_error = (
                    "Execution stopped because no progress was possible for "
                    f"task '{current_task.get('title') or current_task_id}'."
                )
                current_task["status"] = "blocked"
                current_task["error"] = no_progress_error
                self.project_workspace_service.update_task_status(
                    project_id,
                    current_task_id,
                    "blocked",
                    error=no_progress_error,
                )
                execution = (
                    self.project_workspace_service.update_execution_state(
                        project_id,
                        status="blocked",
                        current_task_id=current_task_id,
                        current_step=current_task.get("title") or current_task_id,
                        queue=[current_task_id] if current_task_id else [],
                        last_action="run_all",
                    )
                )
                return {
                    "ok": False,
                    "project_id": project_id,
                    "action": "run_all",
                    "status": "blocked",
                    "execution": execution,
                    "debug_last_result": last_result,
                    "message": no_progress_error,
                }

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
                "succeeded",
                "finished",
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

            _execution_debug(
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
                "ok": final_status == "completed",
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

        remaining_task = (
            refreshed_runnable[0]
            if refreshed_runnable
            and isinstance(refreshed_runnable[0], dict)
            else {}
        )
        remaining_task_id = str(
            remaining_task.get("id") or ""
        ).strip()
        safety_error = (
            "Project execution stopped after reaching "
            f"the {max_loops}-cycle safety limit."
        )
        if remaining_task_id:
            self.project_workspace_service.update_task_status(
                project_id,
                remaining_task_id,
                "blocked",
                error=safety_error,
            )
        execution = self.project_workspace_service.update_execution_state(
            project_id,
            status="blocked",
            current_task_id=remaining_task_id or None,
            current_step=(
                remaining_task.get("title") or remaining_task_id
            ),
            queue=[
                task.get("id")
                for task in refreshed_runnable
                if isinstance(task, dict) and task.get("id")
            ],
            last_action="run_all",
        )

        return {
            "ok": False,
            "project_id": project_id,
            "action": "run_all",
            "status": "blocked",
            "artifacts": all_published_artifacts,
            "execution": execution,
            "debug_last_result": last_result,
            "message": safety_error,
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

        current_execution = (
            self.project_workspace_service.get_execution_state(project_id)
            or {}
        )
        current_status = str(
            current_execution.get("status") or ""
        ).strip().lower()
        if current_status in {
            "completed",
            "complete",
            "done",
            "success",
            "succeeded",
            "finished",
            "failed",
            "failure",
            "error",
            "blocked",
            "cancelled",
            "canceled",
            "stopped",
        }:
            return {
                "ok": False,
                "project_id": project_id,
                "action": "pause",
                "status": current_status,
                "execution": current_execution,
                "message": (
                    "Project execution is already in terminal state "
                    f"'{current_status}'."
                ),
            }

        execution = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="paused",
                control_request="pause",
                last_action="pause",
            )
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

        current_execution = (
            self.project_workspace_service.get_execution_state(project_id)
            or {}
        )
        current_status = str(
            current_execution.get("status") or ""
        ).strip().lower()
        if current_status in {
            "completed",
            "complete",
            "done",
            "success",
            "succeeded",
            "finished",
            "failed",
            "failure",
            "error",
            "blocked",
            "cancelled",
            "canceled",
        }:
            return {
                "ok": False,
                "project_id": project_id,
                "action": "stop",
                "status": current_status,
                "execution": current_execution,
                "message": (
                    "Project execution is already in terminal state "
                    f"'{current_status}'."
                ),
            }

        execution = (
            self.project_workspace_service
            .update_execution_state(
                project_id,
                status="stopped",
                control_request="stop",
                last_action="stop",
            )
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
        requested_action = str(
            action or ""
        ).strip().lower()

        action = {
            "next": "next_step",
            "next_task": "next_step",
            "run_next": "next_step",
            "resume": "continue",
        }.get(
            requested_action,
            requested_action,
        )

        if action not in self.VALID_ACTIONS:
            return {
                "ok": False,
                "project_id": project_id,
                "action": requested_action,
                "status": "invalid_action",
                "message": (
                    f"Unsupported project execution action: "
                    f"{requested_action or '<empty>'}."
                ),
            }

        if action == "continue":
            return self.continue_project(
                project_id
            )

        if action == "next_step":
            return self.continue_project(
                project_id
            )

        if action == "approve":
            return self.approve_project(project_id)

        if action == "reset":
            return self.reset_execution_state(project_id)

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
        if action in {
            "state",
            "get_state",
            "status",
        }:
            return self.get_state(
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
                step.get("generated_content")
                or step.get("file_content")
                or step.get("content")
                or step.get("text")
                or step.get("output")
                or step.get("result")
                or ""
            )

            if execution_output:
                task["result"] = execution_output
                task["content"] = execution_output

        return tasks

    def publish_execution_artifacts(
        self,
        project_id,
        result,
        tasks=None,
    ):
        """
        Publish artifacts from an already-completed execution result.

        This does not execute or advance anything. It only synchronizes
        the existing execution result and publishes completed artifacts.
        """
        if not isinstance(result, dict):
            return []

        if tasks is None:
            project = self._get_project(project_id) or {}
            tasks = self._get_tasks(project)

        if not isinstance(tasks, list):
            tasks = []

        self._sync_project_execution(
            project_id,
            result,
            "approve",
            tasks=tasks,
        )

        return self._publish_completed_artifacts(
            project_id,
            tasks,
            result,
        )

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

        # Support all execution result shapes:
        #
        # 1. {"execution": {"steps": [...]}}
        # 2. {"steps": [...]}
        # 3. {"execution": {"execution": {"steps": [...]}}}
        #
        if not isinstance(
            execution,
            dict,
        ):
            execution = result

        nested_execution = (
            execution.get("execution")
            if isinstance(
                execution,
                dict,
            )
            else None
        )

        if (
            isinstance(
                nested_execution,
                dict,
            )
            and isinstance(
                nested_execution.get("steps"),
                list,
            )
        ):
            execution = nested_execution

        steps = execution.get(
            "steps",
            []
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        executable_tasks = [
            task
            for task in tasks
            if isinstance(
                task,
                dict,
            )
        ]

        task_by_id = {
            str(task.get("id")): task
            for task in executable_tasks
            if isinstance(
                task,
                dict,
            )
            and task.get("id")
        }

        published = []
        published_task_ids = set()

        _execution_debug(
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
                _execution_debug(
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
                for candidate_task in tasks:
                    if not isinstance(
                        candidate_task,
                        dict,
                    ):
                        continue

                    dependencies = candidate_task.get(
                        "dependencies",
                        [],
                    )

                    if not isinstance(
                        dependencies,
                        list,
                    ):
                        continue

                    dependency_ids = {
                        str(dependency).strip()
                        for dependency in dependencies
                        if str(dependency).strip()
                    }

                    if task_id in dependency_ids:
                        task = candidate_task
                        task_id = str(
                            candidate_task.get(
                                "id"
                            )
                        )
                        break

            if not task:
                _execution_debug(
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

            _execution_debug(
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

            artifact_result = {
                "result": step.get("result"),
                "output": step.get("output"),
                "content": step.get("content"),
                "text": step.get("text"),
                "file_content": step.get("file_content"),
                "target_file": step.get("target_file"),
                "action": step.get("action"),
                "execution_metadata": (
                    step.get("execution_metadata")
                    if isinstance(
                        step.get("execution_metadata"),
                        dict,
                    )
                    else {}
                ),
            }

            _execution_debug(
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

                _execution_debug(
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
                _execution_debug(
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

        _execution_debug(
            "[PROJECT SYNC ENTRY]",
            {
                "project_id": project_id,
                "action": action,
                "result_keys": (
                    list(result.keys())
                    if isinstance(result, dict)
                    else None
                ),
                "result_execution_type": type(
                    result.get("execution")
                ).__name__
                if isinstance(result, dict)
                else None,
            },
            flush=True,
        )

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

        if (
            isinstance(execution, dict)
            and isinstance(
                execution.get("execution"),
                dict,
            )
        ):
            execution = execution.get(
                "execution"
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
            elif any(
                key in result
                for key in ("status", "error", "task_id", "completion_status")
            ):
                execution = result
            else:
                return

        # NOVA_STALE_EXECUTION_POINTER_GUARD_20260930
        # If continue/run-next has fresh runnable tasks but the persisted
        # execution pointer references a different task, discard the stale
        # pointer and force rebuild from current runnable steps.
        if isinstance(
            execution,
            dict,
        ):
            current_step = execution.get(
                "current_step",
                {},
            )

            current_task_id = ""
            if isinstance(
                current_step,
                dict,
            ):
                current_task_id = str(
                    current_step.get(
                        "task_id",
                    )
                    or ""
                ).strip()

            runnable_task_ids = {
                str(
                    task.get("id")
                    or ""
                ).strip()
                for task in tasks
                if isinstance(
                    task,
                    dict,
                )
                and task.get("id")
            }

            if (
                current_task_id
                and current_task_id not in runnable_task_ids
            ):
                _execution_debug(
                    "[PROJECT STALE EXECUTION POINTER RESET]",
                    {
                        "stale_task_id": current_task_id,
                        "valid_task_ids": list(
                            runnable_task_ids
                        ),
                    },
                    flush=True,
                )

                execution["current_step"] = None
                execution["current_step_title"] = None
                execution["current_index"] = 0
                execution["steps"] = []

        steps = execution.get(
            "steps",
            [],
        )
        if not isinstance(
            steps,
            list,
        ):
            steps = []

        _execution_debug(
            "[PROJECT SYNC RAW STEPS]",
            {
                "count": len(steps),
                "steps": steps,
            },
            flush=True,
        )

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

        completed_steps = execution.get(
            "completed_steps",
            [],
        )

        if (
            not steps
            and isinstance(completed_steps, list)
            and completed_steps
        ):
            completed_step_ids = {
                str(completed_step_id).strip()
                for completed_step_id in completed_steps
                if str(completed_step_id or "").strip()
            }
            steps = []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                task_id = str(task.get("id") or "").strip()
                nested_steps = task.get("steps") or []
                matched_nested_step = False
                if isinstance(nested_steps, list):
                    for nested_step in nested_steps:
                        if not isinstance(nested_step, dict):
                            continue
                        nested_id = str(
                            nested_step.get("id")
                            or nested_step.get("step_id")
                            or ""
                        ).strip()
                        if nested_id in completed_step_ids:
                            steps.append(
                                {
                                    "task_id": task_id,
                                    "step_id": nested_id,
                                    "id": nested_id,
                                    "status": "completed",
                                }
                            )
                            matched_nested_step = True

                if task_id in completed_step_ids and not matched_nested_step:
                    steps.append(
                        {
                            "task_id": task_id,
                            "id": task_id,
                            "status": "completed",
                        }
                    )

            _execution_debug(
                "[PROJECT SYNC COMPLETED STEP FALLBACK]",
                {
                    "project_id": project_id,
                    "steps": steps,
                },
                flush=True,
            )

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

            _execution_debug(
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
                _execution_debug(
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

            _execution_debug(
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
                _execution_debug(
                    "[PROJECT SYNC STEP IGNORED]",
                    {
                        "task_id": task_id,
                        "status": normalized_status,
                    },
                    flush=True,
                )
                continue

            try:
                step_id = str(
                    step.get("step_id")
                    or step.get("id")
                    or ""
                ).strip()

                update_result = None

                _execution_debug(
                    "[NESTED STEP ID MATCH DEBUG]",
                    {
                        "task_id": task_id,
                        "incoming_step_id": step_id,
                        "available_nested_steps": [],
                    },
                    flush=True,
                )

                if (
                    step_id
                    and hasattr(
                        self.project_workspace_service,
                        "update_nested_step_status",
                    )
                ):

                    update_result = (
                        self.project_workspace_service
                        .update_nested_step_status(
                            project_id,
                            task_id,
                            step_id,
                            normalized_status,
                            result=step.get("result"),
                            error=step.get("error"),
                        )
                    )

                if not isinstance(
                    update_result,
                    dict,
                ):
                    update_result = (
                        self.project_workspace_service
                        .update_task_status(
                            project_id,
                            task_id,
                            normalized_status,
                            result=step.get("result"),
                            error=step.get("error"),
                        )
                    )

                synced_task_ids.append(
                    task_id
                )

                _execution_debug(
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
                _execution_debug(
                    "[PROJECT SYNC TASK UPDATE ERROR]",
                    {
                        "project_id": project_id,
                        "task_id": task_id,
                        "status": normalized_status,
                        "error": str(exc),
                    },
                    flush=True,
                )

        _execution_debug(
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

        persisted_control_state = (
            self.project_workspace_service.get_execution_state(project_id)
            or {}
        )
        control_request = str(
            persisted_control_state.get("control_request") or ""
        ).strip().lower()
        raw_execution_status = str(
            execution.get("status") or ""
        ).strip().lower()

        if (
            control_request in {"pause", "stop"}
            and raw_execution_status
            not in {
                "failed",
                "failure",
                "error",
                "errored",
                "exception",
                "blocked",
                "cancelled",
                "canceled",
            }
        ):
            all_tasks_completed = bool(latest_tasks) and all(
                str(task.get("status") or "").strip().lower()
                in {"completed", "complete", "done", "success", "succeeded"}
                for task in latest_tasks
                if isinstance(task, dict)
            )

            if all_tasks_completed:
                self.project_workspace_service.update_execution_state(
                    project_id,
                    status="completed",
                    current_task_id=None,
                    current_step=None,
                    queue=[],
                    control_request=None,
                    last_action=action,
                )
                self._get_project(project_id)
                return

            control_status = (
                "paused" if control_request == "pause" else "stopped"
            )
            self.project_workspace_service.update_execution_state(
                project_id,
                status=control_status,
                control_request=control_request,
                last_action=control_request,
            )
            return

        execution_status = raw_execution_status
        execution_status = {
            "failure": "failed",
            "error": "failed",
            "errored": "failed",
            "exception": "failed",
        }.get(execution_status, execution_status)

        _execution_debug(
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
            "cancelled",
            "canceled",
        }:
            terminal_execution_status = (
                "cancelled"
                if execution_status in {"cancelled", "canceled"}
                else execution_status
            )
            if not synced_task_ids:
                candidate_task_id = str(
                    execution.get("task_id")
                    or result.get("task_id")
                    or (
                        tasks[0].get("id")
                        if tasks and isinstance(tasks[0], dict)
                        else ""
                    )
                    or persisted_control_state.get("current_task_id")
                    or ""
                ).strip()
                failure_error = str(
                    execution.get("error")
                    or result.get("error")
                    or result.get("message")
                    or (
                        "Project execution is blocked."
                        if terminal_execution_status == "blocked"
                        else (
                            "Project execution was cancelled."
                            if terminal_execution_status == "cancelled"
                            else "Project execution failed."
                        )
                    )
                )
                if candidate_task_id:
                    self.project_workspace_service.update_task_status(
                        project_id,
                        candidate_task_id,
                        terminal_execution_status,
                        error=failure_error,
                    )
                    synced_task_ids.append(candidate_task_id)
                    project = self._get_project(project_id) or {}
                    latest_tasks = self._get_tasks(project)
                    remaining_tasks = self._runnable_tasks(latest_tasks)

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

            failed_task_ids = [
                task.get("id")
                for task in latest_tasks
                if isinstance(task, dict)
                and str(
                    task.get("status") or ""
                ).strip().lower()
                in {"failed", "error"}
                and task.get("id")
            ]

            execution = (
                self.project_workspace_service.update_execution_state(
                    project_id,
                    status=terminal_execution_status,
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
                    failed_tasks=failed_task_ids,
                    control_request=None,
                    last_action=action,
                )
            )

            self._get_project(project_id)
            return


        # Approval must remain explicitly waiting for approval.
        if execution_status in {
            "waiting_approval",
            "awaiting_approval",
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

            self.project_workspace_service.update_execution_state(
                project_id,
                status="waiting_approval",

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

            _execution_debug(
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

            failure_statuses = {
                "failed",
                "failure",
                "error",
            }

            is_failed = (
                result_status in failure_statuses
                or result_completion_status in failure_statuses
                or task_status in failure_statuses
                or task_completion_status in failure_statuses
            )

            if is_failed:
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

                _execution_debug(
                    "[PROJECT FAILURE PERSIST DEBUG]",
                    {
                        "failed_task_ids": failed_task_ids,
                        "latest_task_statuses": [
                            (
                                task.get("id"),
                                task.get("status"),
                            )
                            for task in latest_tasks
                            if isinstance(task, dict)
                        ],
                    },
                    flush=True,
                )

                self.project_workspace_service.update_execution_state(
                    project_id,
                    status="failed",
                    current_task_id=(
                        current_task.get("id")
                        if remaining_tasks
                        else None
                    ),
                    current_step=(
                        current_task.get(
                            "title",
                            "",
                        )
                        if remaining_tasks
                        else ""
                    ),
                    queue=queue,
                    failed_tasks=failed_task_ids,
                    last_action=action,
                )
                return

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
                if is_waiting and remaining_tasks
                else "running"
            )

            _execution_debug(
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

            completed_task_ids = [
                task.get("id")
                for task in latest_tasks
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
                for task in latest_tasks
                if isinstance(task, dict)
                for step in (
                    task.get("steps")
                    or task.get("substeps")
                    or task.get("execution_steps")
                    or []
                )
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
                }
                and step.get("id")
            ]

            next_steps = self._build_execution_steps(
                [next_task]
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
                steps=next_steps,
                current_step_index=0,
                queue=queue,
                completed_tasks=completed_task_ids,
                completed_steps=completed_step_ids,
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
            "succeeded",
            "finished",
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

        _execution_debug(
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
            for step in (
                task.get("steps")
                or task.get("substeps")
                or task.get("execution_steps")
                or []
            )
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

        _execution_debug(
            "[PROJECT FAILED TASK DEBUG]",
            {
                "latest_tasks": [
                    {
                        "id": task.get("id"),
                        "status": task.get("status"),
                    }
                    for task in latest_tasks
                    if isinstance(task, dict)
                ],
            },
            flush=True,
        )

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
                control_request=None,
                last_action=action,
            )
            self._get_project(project_id)
            return
        else:
            # No runnable tasks remain, but the project is not
            # successfully complete. Preserve the actual task
            # failure/block state instead of falsely completing.
            unresolved_statuses = [
                status
                for status in task_statuses
                if status not in terminal_success_statuses
            ]

            final_status = (
                "failed"
                if failed_task_ids
                else "blocked"
            )

            _execution_debug(
                "[PROJECT SYNC NOT COMPLETE]",
                {
                    "project_id": project_id,
                    "unresolved_statuses": unresolved_statuses,
                    "failed_task_ids": failed_task_ids,
                    "final_status": final_status,
                },
                flush=True,
            )

            self.project_workspace_service.update_execution_state(
                project_id,
                status=final_status,
                current_task_id=None,
                current_step=None,
                queue=[],
                completed_tasks=completed_task_ids,
                completed_steps=completed_step_ids,
                failed_tasks=failed_task_ids,
                control_request=None,
                last_action=action,
            )
            self._get_project(project_id)
            return





























