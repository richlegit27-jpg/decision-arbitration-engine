from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pathlib import Path
import re

from nova_backend.services.project_planning_ai_service import (
    project_planning_ai_service,
)


class ProjectBuilderService:
    """
    Nova's authoritative Project Builder.

    Responsibilities:
    - Turn a natural-language project request into a persistent project.
    - Create real persistent project tasks.
    - Keep project planning separate from execution.
    - Use ProjectWorkspaceService as the single source of project state.
    """

    def __init__(self, project_workspace_service):
        self.project_workspace_service = project_workspace_service

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def should_use_phases(self, plan):
        """
        Decide whether a project needs phase structure.

        Small projects stay task-only.
        Larger projects get phases + tasks.
        """

        if not isinstance(plan, dict):
            return False

        phases = (
            plan.get("phases")
            or []
        )

        tasks = (
            plan.get("tasks")
            or []
        )

        task_count = len(tasks)
        phase_count = len(phases)

        if task_count <= 5:
            return False

        if phase_count >= 3:
            return True

        return False

    def _normalize_task_reference(
        self,
        reference,
    ):
        """
        Normalize planner task IDs, titles, and dependency references
        into a stable lookup key.
        """
        normalized_reference = str(
            reference or ""
        ).strip().lower()

        normalized_reference = re.sub(
            r"[^a-z0-9]+",
            " ",
            normalized_reference,
        )

        normalized_reference = re.sub(
            r"\s+",
            " ",
            normalized_reference,
        ).strip()

        return normalized_reference

    def build_project_from_request(
        self,
        user_text,
        user_id=None,
        workspace_id=None,
        owner_id=None,
    ):
        """
        Build a project from a natural-language request.

        Responsibilities:
        1. Generate a planner structure.
        2. Create the project if necessary.
        3. Persist phases before tasks.
        4. Assign every task to a persistent phase.
        5. Convert planner task references into persistent task UUIDs.
        6. Persist remapped dependencies.
        """

        if owner_id is not None and user_id is None:
            user_id = owner_id

        if not user_text or not str(user_text).strip():
            raise ValueError("Project request required")

        clean_request = str(user_text).strip()

        project_id = None

        existing_project = None

        if project_id:
            existing_project = self.project_workspace_service.get_project(
                project_id
            )

        context = {
            "project_id": project_id,
            "owner_id": owner_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "request_text": clean_request,
        }

        plan = self._build_project_plan(
            request=clean_request,
            project_context=context,
        )

        if not isinstance(plan, dict):
            raise ValueError("Planner returned an invalid project plan")

        planned_phases = plan.get("phases")

        if not isinstance(planned_phases, list):
            planned_phases = plan.get("milestones")

        if not isinstance(planned_phases, list):
            planned_phases = []

        planned_tasks = plan.get("tasks")

        if not isinstance(planned_tasks, list):
            planned_tasks = []

        if not planned_tasks:
            raise ValueError("Planner returned no tasks")

        if existing_project:
            project = existing_project
        else:
            project_title = (
                plan.get("title")
                or plan.get("name")
                or clean_request[:120]
            )

            project_description = (
                plan.get("description")
                or clean_request
            )

            created_project = (
                self.project_workspace_service.create_project(
                    title=project_title,
                    request_text=clean_request,
                    owner_id=owner_id,
                    name=project_title,
                    description=project_description,
                )
            )

            if not isinstance(created_project, dict):
                raise RuntimeError(
                    "Project workspace failed to create project"
                )

            project = created_project

            project_id = project.get(
                "id"
            )

            if not project_id:
                raise RuntimeError(
                    "Created project did not contain an id"
                )

        if not project_id:
            project_id = project.get("id")

        if not project_id:
            raise ValueError("Project ID could not be determined")

        # ---------------------------------------------------------
        # Normalize planner phases.
        # ---------------------------------------------------------

        normalized_phases = []

        for phase_index, phase_spec in enumerate(planned_phases, start=1):
            if not isinstance(phase_spec, dict):
                continue

            phase_key = (
                phase_spec.get("id")
                or phase_spec.get("phase_id")
                or phase_spec.get("key")
                or f"phase_{phase_index}"
            )

            phase_title = (
                phase_spec.get("title")
                or phase_spec.get("name")
                or phase_spec.get("phase")
                or f"Phase {phase_index}"
            )

            phase_description = (
                phase_spec.get("description")
                or phase_spec.get("goal")
                or ""
            )

            normalized_phases.append(
                {
                    "planner_id": str(phase_key),
                    "title": str(phase_title),
                    "description": str(phase_description),
                    "goal": str(phase_spec.get("goal") or ""),
                    "milestone": str(
                        phase_spec.get("milestone") or ""
                    ),
                    "order": phase_spec.get("order")
                        or phase_index,
                }
            )

        # ---------------------------------------------------------
        # Fallback: derive phases from task metadata when the AI
        # planner returns tasks but no structural phases.
        # ---------------------------------------------------------

        if not normalized_phases:
            derived_phase_groups = {}

            for task_index, task_spec in enumerate(planned_tasks, start=1):
                if not isinstance(task_spec, dict):
                    continue

                searchable_text = " ".join(
                    [
                        str(task_spec.get("title") or ""),
                        str(task_spec.get("name") or ""),
                        str(task_spec.get("description") or ""),
                        str(task_spec.get("action") or ""),
                        str(task_spec.get("phase") or ""),
                        str(task_spec.get("phase_title") or ""),
                        str(task_spec.get("phase_name") or ""),
                        str(task_spec.get("phase_id") or ""),
                    ]
                ).lower()

                explicit_phase = (
                    task_spec.get("phase_id")
                    or task_spec.get("phase")
                    or task_spec.get("phase_title")
                    or task_spec.get("phase_name")
                )

                if explicit_phase:
                    phase_key = str(explicit_phase).strip()
                    phase_title = phase_key.replace("_", " ").strip()
                    phase_title = phase_title.title()
                elif "foundation" in searchable_text:
                    phase_key = "phase_foundation"
                    phase_title = "Foundation"
                elif "delivery" in searchable_text:
                    phase_key = "phase_delivery"
                    phase_title = "Delivery"
                elif "deployment" in searchable_text:
                    phase_key = "phase_deployment"
                    phase_title = "Deployment"
                elif "testing" in searchable_text or "test" in searchable_text:
                    phase_key = "phase_testing"
                    phase_title = "Testing"
                elif "documentation" in searchable_text or "document" in searchable_text:
                    phase_key = "phase_documentation"
                    phase_title = "Documentation"
                else:
                    phase_key = "phase_1"
                    phase_title = "Foundation"

                if phase_key not in derived_phase_groups:
                    derived_phase_groups[phase_key] = {
                        "planner_id": phase_key,
                        "title": phase_title,
                        "description": "",
                        "goal": "",
                        "milestone": "",
                        "order": len(derived_phase_groups) + 1,
                    }

            normalized_phases = list(
                derived_phase_groups.values()
            )

        # Ensure there is always at least one phase when phases are enabled.
        if not normalized_phases and use_phases:
            normalized_phases = [
                {
                    "planner_id": "phase_1",
                    "title": "Foundation",
                    "description": "",
                    "goal": "",
                    "milestone": "",
                    "order": 1,
                }
            ]

        # ---------------------------------------------------------
        # Persist phases and map planner phase IDs to real UUIDs.
        # ---------------------------------------------------------

        phase_id_map = {}


        def _phase_lookup_key(value):
            if isinstance(value, dict):
                value = (
                    value.get("id")
                    or value.get("phase_id")
                    or value.get("planner_id")
                    or value.get("title")
                    or value.get("name")
                    or ""
                )

            value = str(value or "").strip().lower()

            if not value:
                return ""

            return (
                value
                .replace("_", " ")
                .replace("-", " ")
                .replace(".", " ")
            ).strip()

        created_phases = []

        use_phases = self.should_use_phases(plan)

        if not use_phases:
            normalized_phases = []

        for phase_spec in normalized_phases:
            created_phase = (
                self.project_workspace_service.add_phase(
                    project_id=project_id,
                    title=phase_spec["title"],
                    description=phase_spec["description"],
                    status="planned",
                    order=phase_spec["order"],
                    goal=phase_spec["goal"],
                    milestone=phase_spec["milestone"],
                )
            )

            if isinstance(created_phase, dict):
                created_phase_id = (
                    created_phase.get("id")
                    or created_phase.get("phase_id")
                    or ""
                )
            else:
                created_phase_id = created_phase

            while isinstance(created_phase_id, dict):
                created_phase_id = (
                    created_phase_id.get("id")
                    or created_phase_id.get("phase_id")
                    or ""
                )

            created_phase_id = str(
                created_phase_id or ""
            ).strip()

            if not created_phase_id:
                raise RuntimeError(
                    "Created phase did not contain an id"
                )

            planner_phase_id = str(
                phase_spec.get("planner_id")
                or phase_spec.get("id")
                or phase_spec.get("title")
                or ""
            ).strip()

            phase_title_key = str(
                phase_spec.get("title") or ""
            ).strip().lower()

            if planner_phase_id:
                phase_id_map[
                    planner_phase_id
                ] = created_phase_id

            if phase_title_key:
                phase_id_map[
                    phase_title_key
                ] = created_phase_id

            created_phases.append(
                {
                    "id": created_phase_id,
                    "planner_id": (
                        phase_spec.get("planner_id")
                        or phase_spec.get("id")
                        or planner_phase_id
                    ),
                    "title": phase_spec["title"],
                    "description": phase_spec["description"],
                    "status": "planned",
                    "order": phase_spec["order"],
                    "goal": phase_spec["goal"],
                    "milestone": phase_spec["milestone"],
                }
            )




        # ---------------------------------------------------------
        # Normalize task execution metadata before persistence.
        # ---------------------------------------------------------

        normalized_tasks = []

        for task in planned_tasks:
            if not isinstance(task, dict):
                continue

            task_title = str(
                task.get("title")
                or task.get("name")
                or ""
            ).strip()

            task_title_lower = task_title.lower()

            task_text = " ".join(
                [
                    task_title,
                    str(task.get("description") or ""),
                    str(task.get("content") or ""),
                    str(task.get("expected_output") or ""),
                    str(task.get("completion_criteria") or ""),
                ]
            )
            task_text_lower = task_text.lower()

            task_command = str(
                task.get("command")
                or task.get("shell_command")
                or task.get("run_command")
                or task.get("execution_command")
                or task.get("cmd")
                or ""
            ).strip()

            if not task_command:
                command_match = re.search(
                    r"(?:run|execute|command(?:\s+is)?|shell(?:\s+command)?)\s*:\s*(.+)",
                    task_text,
                    flags=re.IGNORECASE,
                )

                if command_match:
                    task_command = command_match.group(1).strip()

            task["command"] = task_command

            is_contract_task = (
                "specify the exact" in task_title_lower
                or "execution contract" in task_title_lower
                or "define the execution contract" in task_title_lower
                or "exact file content" in task_title_lower
            )

            is_output_persistence_task = (
                "write captured output" in task_title_lower
                or "persist captured output" in task_title_lower
                or "save captured output" in task_title_lower
                or "output to " in task_title_lower
                or "write stdout" in task_title_lower
                or "persist stdout" in task_title_lower
            )

            is_execution_task = (
                not is_contract_task
                and (
                    task_title_lower.startswith("execute")
                    or task_title_lower.startswith("run ")
                    or "execute" in task_title_lower
                    or "run " in task_title_lower
                    or "subprocess" in task_text_lower
                    or "standard output" in task_text_lower
                    or "capture its output" in task_text_lower
                    or "real python" in task_text_lower
                    or "script execution" in task_text_lower
                )
            )

            if is_contract_task:
                task["action"] = "execute"
                task["execution_mode"] = "hybrid"
                task["execution_file"] = ""

            elif is_output_persistence_task:
                task["action"] = "implement"
                task["execution_mode"] = "hybrid"
                task["execution_file"] = ""

            elif is_execution_task:
                execution_file = str(
                    task.get("execution_file")
                    or task.get("run_file")
                    or task.get("script_file")
                    or task.get("test_script")
                    or task.get("test_file")
                    or ""
                ).strip()

                if not execution_file:
                    execution_match = re.search(
                        r"\b([A-Za-z0-9_.-]+\.py)\b",
                        task_text,
                        flags=re.IGNORECASE,
                    )

                    if execution_match:
                        execution_file = (
                            execution_match.group(1).strip()
                        )

                if not execution_file:
                    candidate_target_file = str(
                        task.get("target_file")
                        or ""
                    ).strip()

                    if candidate_target_file.lower().endswith(".py"):
                        execution_file = candidate_target_file

                if not execution_file:
                    candidate_target_files = (
                        task.get("target_files") or []
                    )

                    if isinstance(candidate_target_files, list):
                        for candidate_file in candidate_target_files:
                            candidate_file = str(
                                candidate_file or ""
                            ).strip()

                            if candidate_file.lower().endswith(".py"):
                                execution_file = candidate_file
                                break

                if not execution_file:
                    candidate_target_file = str(
                        task.get("target_file") or ""
                    ).strip()

                    if candidate_target_file.lower().endswith(".py"):
                        execution_file = candidate_target_file

                if not execution_file:
                    candidate_target_files = (
                        task.get("target_files") or []
                    )

                    if isinstance(candidate_target_files, list):
                        for candidate_file in candidate_target_files:
                            candidate_file = str(
                                candidate_file or ""
                            ).strip()

                            if candidate_file.lower().endswith(".py"):
                                execution_file = candidate_file
                                break

                if execution_file:
                    task["action"] = "execute"
                    task["execution_file"] = execution_file
                else:
                    task["action"] = "planning"
                    task["execution_mode"] = "blocked"
                    task["execution_file"] = ""
                    task["notes"] = (
                        "Execution requested but no runnable Python file was found."
                    )

            else:
                task["action"] = str(
                    task.get("action") or ""
                ).strip()

                task["execution_file"] = str(
                    task.get("execution_file")
                    or ""
                ).strip()

            target_file = str(
                task.get("target_file")
                or ""
            ).strip()

            target_files = task.get("target_files") or []

            if (
                is_execution_task
                and task.get("execution_file")
            ):
                output_matches = re.findall(
                    r"\b([A-Za-z0-9_.-]+\.(?:txt|json|csv|md|log|out|xml|yaml|yml))\b",
                    task_text,
                    flags=re.IGNORECASE,
                )

                output_matches = [
                    value
                    for value in output_matches
                    if value.lower()
                    != str(task["execution_file"]).lower()
                ]

                if output_matches:
                    target_file = output_matches[-1]
                    target_files = [target_file]

            task["target_file"] = target_file
            task["target_files"] = target_files

            normalized_tasks.append(task)

        # ---------------------------------------------------------
        # Final canonicalization after all planner tasks are built.
        # ---------------------------------------------------------

        for canonical_task in normalized_tasks:
            if not isinstance(canonical_task, dict):
                continue

            canonical_title = str(
                canonical_task.get("title")
                or canonical_task.get("name")
                or ""
            ).strip()

            canonical_description = str(
                canonical_task.get("description")
                or ""
            ).strip()

            canonical_expected_output = str(
                canonical_task.get("expected_output")
                or ""
            ).strip()

            canonical_content = str(
                canonical_task.get("content")
                or ""
            ).strip()

            canonical_completion_criteria = str(
                canonical_task.get("completion_criteria")
                or ""
            ).strip()

            canonical_target_file = str(
                canonical_task.get("target_file")
                or ""
            ).strip()

            canonical_target_files = (
                canonical_task.get("target_files")
                or []
            )

            if not isinstance(canonical_target_files, list):
                canonical_target_files = []

            canonical_text = " ".join(
                [
                    canonical_title,
                    canonical_description,
                    canonical_content,
                    canonical_expected_output,
                    canonical_completion_criteria,
                    canonical_target_file,
                    " ".join(
                        str(value or "").strip()
                        for value in canonical_target_files
                    ),
                ]
            )

            canonical_title_lower = canonical_title.lower()
            canonical_text_lower = canonical_text.lower()

            canonical_execution_file = str(
                canonical_task.get("execution_file")
                or canonical_task.get("run_file")
                or canonical_task.get("script_file")
                or canonical_task.get("test_script")
                or canonical_task.get("test_file")
                or ""
            ).strip()

            # Promote a Python target file into the execution file
            # when the planner placed it in target_file.
            if not canonical_execution_file:
                if canonical_target_file.lower().endswith(".py"):
                    canonical_execution_file = (
                        canonical_target_file
                    )

            # Also inspect target_files for a Python script.
            if not canonical_execution_file:
                for candidate_file in canonical_target_files:
                    candidate_file = str(
                        candidate_file or ""
                    ).strip()

                    if candidate_file.lower().endswith(".py"):
                        canonical_execution_file = candidate_file
                        break

            # Last fallback: extract a Python filename from the
            # complete canonical task text.
            if not canonical_execution_file:
                execution_match = re.search(
                    r"\b([A-Za-z0-9_.-]+\.py)\b",
                    canonical_text,
                    flags=re.IGNORECASE,
                )

                if execution_match:
                    canonical_execution_file = (
                        execution_match.group(1).strip()
                    )

            is_execution_task = bool(
                canonical_execution_file
                and (
                    canonical_title_lower.startswith("execute ")
                    or canonical_title_lower.startswith("run ")
                    or "execute" in canonical_title_lower
                    or "subprocess" in canonical_text_lower
                    or "capture output" in canonical_title_lower
                    or "captured stdout" in canonical_text_lower
                    or "standard output" in canonical_text_lower
                    or "script execution" in canonical_text_lower
                    or "real python" in canonical_text_lower
                    or "real execution" in canonical_text_lower
                )
            )

            is_output_persistence_task = (
                "write captured output" in canonical_title_lower
                or "write the captured output" in canonical_title_lower
                or "persist captured output" in canonical_title_lower
                or "persist the captured output" in canonical_title_lower
                or "save captured output" in canonical_title_lower
                or "save the captured output" in canonical_title_lower
                or "write stdout" in canonical_text_lower
                or "persist stdout" in canonical_text_lower
                or "save stdout" in canonical_text_lower
                or "write the stdout" in canonical_text_lower
                or "capture and write stdout" in canonical_title_lower
                or "capture and write stdout" in canonical_text_lower
                or "capture and write" in canonical_title_lower
                or "output artifact" in canonical_text_lower
                or "output to " in canonical_title_lower
            )

            if is_execution_task:
                canonical_task["action"] = "execute"
                canonical_task["execution_mode"] = "hybrid"
                canonical_task["execution_file"] = (
                    canonical_execution_file
                )

                canonical_task["command"] = str(
                    canonical_task.get("command")
                    or task.get("command")
                    or ""
                ).strip()

                # The execution task captures output but does not
                # itself persist the output artifact.
                canonical_task["target_file"] = ""
                canonical_task["target_files"] = []

            elif is_output_persistence_task:
                canonical_task["action"] = "implement"
                canonical_task["execution_mode"] = "hybrid"
                canonical_task["execution_file"] = ""

                output_matches = re.findall(
                    r"\b([A-Za-z0-9_.-]+\.(?:txt|json|csv|md|log|out|xml|yaml|yml))\b",
                    canonical_text,
                    flags=re.IGNORECASE,
                )

                if output_matches:
                    canonical_output_file = output_matches[-1]

                    canonical_task["target_file"] = (
                        canonical_output_file
                    )
                    canonical_task["target_files"] = [
                        canonical_output_file
                    ]

            canonical_steps = canonical_task.get("steps")

            if not isinstance(canonical_steps, list):
                continue

            for canonical_step in canonical_steps:
                if not isinstance(canonical_step, dict):
                    continue

                if is_execution_task:
                    canonical_step["action"] = "execute"
                    canonical_step["execution_mode"] = "hybrid"
                    canonical_step["execution_file"] = (
                        canonical_execution_file
                    )

                    canonical_step["command"] = str(
                        canonical_step.get("command")
                        or task.get("command")
                        or ""
                    ).strip()
                    canonical_step["target_file"] = ""
                    canonical_step["target_files"] = []

                elif is_output_persistence_task:
                    canonical_step["action"] = "implement"
                    canonical_step["execution_mode"] = "hybrid"
                    canonical_step["execution_file"] = ""

                    step_text = " ".join(
                        [
                            str(
                                canonical_step.get("title")
                                or canonical_step.get("name")
                                or ""
                            ),
                            str(
                                canonical_step.get("description")
                                or ""
                            ),
                            str(
                                canonical_step.get("content")
                                or ""
                            ),
                            str(
                                canonical_step.get("expected_output")
                                or ""
                            ),
                            str(
                                canonical_step.get("target_file")
                                or ""
                            ),
                            " ".join(
                                str(value or "").strip()
                                for value in (
                                    canonical_step.get(
                                        "target_files"
                                    )
                                    or []
                                )
                            ),
                        ]
                    )

                    step_output_matches = re.findall(
                        r"\b([A-Za-z0-9_.-]+\.(?:txt|json|csv|md|log|out|xml|yaml|yml))\b",
                        step_text,
                        flags=re.IGNORECASE,
                    )

                    if step_output_matches:
                        canonical_step["target_file"] = (
                            step_output_matches[-1]
                        )
                        canonical_step["target_files"] = [
                            step_output_matches[-1]
                        ]

            canonical_title_lower = canonical_title.lower()
            canonical_text_lower = canonical_text.lower()

            canonical_execution_file = str(
                canonical_task.get("execution_file")
                or canonical_task.get("run_file")
                or canonical_task.get("script_file")
                or canonical_task.get("test_script")
                or canonical_task.get("test_file")
                or ""
            ).strip()

            if not canonical_execution_file:
                if canonical_target_file.lower().endswith(".py"):
                    canonical_execution_file = (
                        canonical_target_file
                    )

            if not canonical_execution_file:
                if isinstance(canonical_target_files, list):
                    for candidate_file in canonical_target_files:
                        candidate_file = str(
                            candidate_file or ""
                        ).strip()

                        if candidate_file.lower().endswith(".py"):
                            canonical_execution_file = candidate_file
                            break

            if not canonical_execution_file:
                execution_match = re.search(
                    r"\b([A-Za-z0-9_.-]+\.py)\b",
                    canonical_text,
                    flags=re.IGNORECASE,
                )

                if execution_match:
                    canonical_execution_file = (
                        execution_match.group(1).strip()
                    )

            is_contract_task = (
                "specify the exact" in canonical_title_lower
                or "execution contract" in canonical_title_lower
                or "define the execution contract" in canonical_title_lower
                or "exact file content" in canonical_title_lower
            )

            is_non_executable_planning_task = (
                canonical_title_lower.startswith("clarify ")
                or canonical_title_lower.startswith("define ")
                or canonical_title_lower.startswith("specify ")
                or canonical_title_lower.startswith("design ")
                or canonical_title_lower.startswith("plan ")
                or canonical_title_lower.startswith("analyze ")
                or canonical_title_lower.startswith("validate ")
                or canonical_title_lower.startswith("verify ")
                or canonical_title_lower.startswith("confirm ")
                or is_contract_task
            )

            explicit_subprocess_task = (
                "subprocess" in canonical_title_lower
                or "subprocess" in canonical_text_lower
                or "launches" in canonical_text_lower
                or "launch " in canonical_text_lower
                or "runs the script" in canonical_text_lower
                or "run the script" in canonical_text_lower
                or "execute the script" in canonical_text_lower
                or "executes the script" in canonical_text_lower
                or "invoke python" in canonical_text_lower
                or "invokes python" in canonical_text_lower
                or "real python subprocess" in canonical_text_lower
            )

            explicit_execution_title = (
                canonical_title_lower.startswith("execute ")
                or canonical_title_lower.startswith("run ")
            )

            actual_execution_task = (
                explicit_subprocess_task
                or (
                    explicit_execution_title
                    and (
                        "script" in canonical_text_lower
                        or "subprocess" in canonical_text_lower
                        or "python" in canonical_text_lower
                    )
                )
            )

            output_persistence_task = (
                "write captured output" in canonical_title_lower
                or "write the captured output" in canonical_title_lower
                or "persist captured output" in canonical_title_lower
                or "persist the captured output" in canonical_title_lower
                or "save captured output" in canonical_title_lower
                or "save the captured output" in canonical_title_lower
                or "write stdout" in canonical_text_lower
                or "persist stdout" in canonical_text_lower
                or "save stdout" in canonical_text_lower
                or "output to " in canonical_title_lower
                or "output persistence" in canonical_title_lower
                or "output persistence" in canonical_text_lower
                or (
                    "persist" in canonical_text_lower
                    and "output" in canonical_text_lower
                )
                or (
                    "write" in canonical_title_lower
                    and "output" in canonical_title_lower
                )
                or (
                    "persist" in canonical_title_lower
                    and "output" in canonical_title_lower
                )
                or (
                    "save" in canonical_title_lower
                    and "output" in canonical_title_lower
                )
            )

            is_execution_task = bool(
                canonical_execution_file
                and not is_non_executable_planning_task
                and actual_execution_task
                and not output_persistence_task
            )

            is_output_persistence_task = bool(
                output_persistence_task
                and not is_execution_task
            )

            if is_execution_task:
                canonical_task["action"] = "execute"
                canonical_task["execution_mode"] = "hybrid"
                canonical_task["execution_file"] = (
                    canonical_execution_file
                )

                canonical_task["target_file"] = ""
                canonical_task["target_files"] = []

            elif is_output_persistence_task:
                canonical_task["action"] = "implement"
                canonical_task["execution_mode"] = "hybrid"
                canonical_task["execution_file"] = ""

                output_matches = re.findall(
                    r"\b([A-Za-z0-9_.-]+\.txt)\b",
                    canonical_text,
                    flags=re.IGNORECASE,
                )

                if output_matches:
                    canonical_output_file = output_matches[-1]

                    canonical_task["target_file"] = (
                        canonical_output_file
                    )
                    canonical_task["target_files"] = [
                        canonical_output_file
                    ]

            else:
                canonical_task["action"] = str(
                    canonical_task.get("action")
                    or "analyze"
                ).strip().lower()

                canonical_task["execution_mode"] = (
                    canonical_task.get("execution_mode")
                    or "ai"
                )

                canonical_task["execution_file"] = (
                    canonical_task.get("execution_file")
                    or ""
                )

            canonical_steps = canonical_task.get("steps")

            if not isinstance(canonical_steps, list):
                continue

            for canonical_step in canonical_steps:
                if not isinstance(canonical_step, dict):
                    continue

                if is_execution_task:
                    canonical_step["action"] = "execute"
                    canonical_step["execution_mode"] = "hybrid"
                    canonical_step["execution_file"] = (
                        canonical_execution_file
                    )
                    canonical_step["target_file"] = ""
                    canonical_step["target_files"] = []

                elif is_output_persistence_task:
                    canonical_step["action"] = "implement"
                    canonical_step["execution_mode"] = "hybrid"
                    canonical_step["execution_file"] = ""

                else:
                    canonical_step["action"] = "execute"
                    canonical_step["execution_mode"] = "hybrid"
                    canonical_step["execution_file"] = ""

        planned_tasks = normalized_tasks

        # Persist the normalized task collection.
        planned_tasks = normalized_tasks

        task_id_map = {}
        normalized_task_title_map = {}
        pending_dependency_records = []
        created_tasks = []

        for task_index, task_spec in enumerate(
            planned_tasks,
            start=1,
        ):
            if not isinstance(task_spec, dict):
                continue

            task_title = (
                task_spec.get("title")
                or task_spec.get("name")
                or f"Task {task_index}"
            )

            task_title = str(
                task_title
            ).strip()

            planner_task_id = (
                task_spec.get("id")
                or task_spec.get("task_id")
                or task_spec.get("key")
                or task_title
            )

            planner_task_id = str(
                planner_task_id
            ).strip()

            task_phase_key = (
                task_spec.get("phase_id")
                or task_spec.get("phase")
                or task_spec.get("phase_title")
                or task_spec.get("phase_name")
            )

            if isinstance(task_phase_key, dict):
                task_phase_key = (
                    task_phase_key.get("id")
                    or task_phase_key.get("phase_id")
                    or task_phase_key.get("title")
                    or task_phase_key.get("name")
                )

            task_phase_key = str(task_phase_key or "").strip()

            persistent_phase_id = None

            # 1. Resolve an explicit planner phase ID or phase title.
            if task_phase_key:
                persistent_phase_id = phase_id_map.get(
                    task_phase_key
                )

            if use_phases and not persistent_phase_id:
                raise RuntimeError(
                    "Task did not contain a valid phase_id"
                )

            # 2. Resolve by task title and metadata.
            searchable_task_text = " ".join(
                [
                    str(task_spec.get("title") or ""),
                    str(task_spec.get("description") or ""),
                    str(task_spec.get("name") or ""),
                    str(task_spec.get("phase") or ""),
                    str(task_spec.get("phase_title") or ""),
                    str(task_spec.get("phase_name") or ""),
                ]
            ).strip().lower()

            # Match explicit phase numbering in task text.
            # Example:
            #   "Design Phase One tasks" -> first phase
            #   "Implement Phase Two tasks" -> second phase
            if not persistent_phase_id and created_phases:
                phase_number_words = {
                    "one": 0,
                    "two": 1,
                    "three": 2,
                    "four": 3,
                    "five": 4,
                    "six": 5,
                    "seven": 6,
                    "eight": 7,
                    "nine": 8,
                    "ten": 9,
                }

                for phase_word, phase_index in phase_number_words.items():
                    if (
                        f"phase {phase_word}" in searchable_task_text
                        and phase_index < len(created_phases)
                    ):
                        persistent_phase_id = (
                            created_phases[phase_index].get("id")
                        )
                        break

            # 3. Match task text against persisted phase titles.
            if not persistent_phase_id:
                for created_phase in created_phases:
                    created_phase_id = created_phase.get("id")

                    created_phase_title = str(
                        created_phase.get("title") or ""
                    ).strip().lower()

                    if not created_phase_id or not created_phase_title:
                        continue

                    phase_title_words = [
                        word
                        for word in created_phase_title.replace(
                            "-", " "
                        ).split()
                        if len(word) >= 4
                    ]

                    if phase_title_words and all(
                        word in searchable_task_text
                        for word in phase_title_words
                    ):
                        persistent_phase_id = created_phase_id
                        break

            # 4. Existing semantic keyword matching.
            if not persistent_phase_id:
                if "foundation" in searchable_task_text:
                    persistent_phase_id = phase_id_map.get(
                        "phase_foundation"
                    )

                elif "delivery" in searchable_task_text:
                    persistent_phase_id = phase_id_map.get(
                        "phase_delivery"
                    )

                elif "deployment" in searchable_task_text:
                    persistent_phase_id = phase_id_map.get(
                        "phase_deployment"
                    )

                elif "testing" in searchable_task_text:
                    persistent_phase_id = phase_id_map.get(
                        "phase_testing"
                    )

                elif "documentation" in searchable_task_text:
                    persistent_phase_id = phase_id_map.get(
                        "phase_documentation"
                    )

            # Final fallback: assign unresolved tasks to a phase
            # deterministically instead of placing every task in
            # the first phase.
            if not persistent_phase_id and created_phases:
                phase_count = len(created_phases)

                if phase_count == 1:
                    fallback_phase_index = 0
                else:
                    tasks_per_phase = max(
                        1,
                        len(planned_tasks) // phase_count,
                    )

                    fallback_phase_index = min(
                        (task_index - 1) // tasks_per_phase,
                        phase_count - 1,
                    )

                persistent_phase_id = (
                    created_phases[fallback_phase_index].get("id")
                )

            # Unwrap nested phase objects until only the actual
            # persistent phase ID remains.
            while isinstance(
                persistent_phase_id,
                dict,
            ):
                persistent_phase_id = (
                    persistent_phase_id.get("id")
                    or persistent_phase_id.get("phase_id")
                    or persistent_phase_id.get("title")
                    or persistent_phase_id.get("name")
                    or ""
                )

            persistent_phase_id = str(
                persistent_phase_id or ""
            ).strip()

            dependencies = (
                task_spec.get("dependencies")
                or task_spec.get("depends_on")
                or []
            )

            if isinstance(
                dependencies,
                str,
            ):
                dependencies = [
                    dependencies
                ]

            if not isinstance(
                dependencies,
                list,
            ):
                dependencies = []

            if use_phases and not persistent_phase_id:
                raise RuntimeError(
                    "Task did not contain a valid phase_id"
                )

            print(
                "NOVA DEBUG persistent_phase_id:",
                repr(persistent_phase_id),
                type(persistent_phase_id).__name__,
            )

            # -----------------------------------------------------
            # Normalize task steps before persistence.
            # -----------------------------------------------------

            task_steps = (
                task_spec.get(
                    "steps"
                )
                or []
            )

            if isinstance(
                task_steps,
                dict,
            ):
                task_steps = [
                    task_steps
                ]

            if not isinstance(
                task_steps,
                list,
            ):
                task_steps = []

            normalized_steps = []

            for step_index, step_spec in enumerate(
                task_steps,
                start=1,
            ):
                if not isinstance(
                    step_spec,
                    dict,
                ):
                    continue

                step = dict(
                    step_spec
                )

                step_id = (
                    step.get("id")
                    or step.get("step_id")
                    or f"{planner_task_id}-step-{step_index}"
                )

                step["id"] = str(
                    step_id
                ).strip()

                step["task_id"] = str(
                    planner_task_id
                ).strip()

                step["action"] = str(
                    step.get("action")
                    or task_spec.get("action")
                    or "analyze"
                ).strip().lower()

                step["status"] = (
                    step.get("status")
                    or "pending"
                )

                normalized_steps.append(
                    step
                )

            # If the planner supplied no executable steps, create
            # one normalized step from the task metadata.
            if not normalized_steps:
                fallback_action = str(
                    task_spec.get(
                        "action"
                    )
                    or "analyze"
                ).strip().lower()

                fallback_step = {
                    "id": (
                        f"{planner_task_id}-step-1"
                    ),
                    "task_id": str(
                        planner_task_id
                    ).strip(),
                    "title": task_title,
                    "description": str(
                        task_spec.get(
                            "description"
                        )
                        or task_title
                    ).strip(),
                    "action": fallback_action,
                    "status": "pending",

                    "execution_file": (
                        task_spec.get(
                            "execution_file"
                        )
                        or task_spec.get(
                            "run_file"
                        )
                        or task_spec.get(
                            "script_file"
                        )
                        or task_spec.get(
                            "test_script"
                        )
                        or task_spec.get(
                            "test_file"
                        )
                        or ""
                    ),

                    "target_file": (
                        task_spec.get(
                            "target_file"
                        )
                        or ""
                    ),
                    "target_files": (
                        task_spec.get(
                            "target_files"
                        )
                        or []
                    ),

                    "target_function": (
                        task_spec.get(
                            "target_function"
                        )
                        or ""
                    ),
                    "expected_output": (
                        task_spec.get(
                            "expected_output"
                        )
                        or []
                    ),
                    "replacement": (
                        task_spec.get(
                            "replacement"
                        )
                        or ""
                    ),
                    "command": (
                        task_spec.get(
                            "command"
                        )
                        or ""
                    ),
                }

                normalized_steps.append(
                    fallback_step
                )

            task_steps = normalized_steps

            # -----------------------------------------------------
            # -----------------------------------------------------
            # Normalize execution and output metadata.
            # -----------------------------------------------------

            task_title_text = str(
                task_spec.get("title")
                or task_title
                or ""
            )

            task_description_text = str(
                task_spec.get("description")
                or ""
            )

            task_expected_output_text = str(
                task_spec.get("expected_output")
                or ""
            )

            task_completion_text = str(
                task_spec.get("completion_criteria")
                or ""
            )

            task_text = " ".join(
                [
                    task_title_text,
                    task_description_text,
                    task_expected_output_text,
                    task_completion_text,
                ]
            )

            execution_file = (
                task_spec.get("execution_file")
                or task_spec.get("run_file")
                or task_spec.get("script_file")
                or task_spec.get("test_script")
                or task_spec.get("test_file")
                or ""
            )

            # Recover execution metadata from normalized task steps
            # when the planner placed it on a step instead of the task.
            if not execution_file and isinstance(task_steps, list):
                for normalized_step in task_steps:
                    if not isinstance(normalized_step, dict):
                        continue

                    execution_file = (
                        normalized_step.get("execution_file")
                        or normalized_step.get("run_file")
                        or normalized_step.get("script_file")
                        or normalized_step.get("test_script")
                        or normalized_step.get("test_file")
                        or ""
                    )

                    if execution_file:
                        break

            task_text_lower = task_text.lower()

            task_title_lower = task_title_text.lower()

            is_create_and_execute_task = (
                "create" in task_title_lower
                and "execute" in task_title_lower
            )

            is_execution_task = (
                not is_create_and_execute_task
                and (
                    task_title_lower.startswith("execute ")
                    or task_title_lower.startswith("run ")
                    or task_title_lower.startswith("implement script execution")
                    or "execute " in task_title_lower
                    or "run " in task_title_lower
                    or "script execution" in task_text_lower
                    or "execution metadata" in task_text_lower
                    or "capture output" in task_text_lower
                    or "standard output" in task_text_lower
                )
            )

            is_output_persistence_task = (
                "write captured output" in task_title_lower
                or "persist captured output" in task_title_lower
                or "save captured output" in task_title_lower
                or "output to " in task_title_lower
            )

            if is_output_persistence_task:
                is_execution_task = False
                execution_file = ""

            if is_execution_task:
                execution_match = re.search(

                    r"\b([A-Za-z0-9_.-]+\.py)\b",
                    task_title_text,
                    flags=re.IGNORECASE,
                )

                if not execution_match:
                    execution_match = re.search(
                        r"\b([A-Za-z0-9_.-]+\.py)\b",
                        task_text,
                        flags=re.IGNORECASE,
                    )

                if execution_match:
                    execution_file = (
                        execution_match.group(1).strip()
                    )

            target_file = (
                task_spec.get("target_file")
                or ""
            )

            target_files = (
                task_spec.get("target_files")
                or []
            )

            # -----------------------------------------------------
            # Final execution/output metadata normalization.
            # -----------------------------------------------------

            normalized_action = str(
                task_spec.get("action") or ""
            ).strip().lower()

            normalized_execution_mode = str(
                task_spec.get("execution_mode") or ""
            ).strip().lower()

            final_task_title = str(
                task_title
                or task_spec.get("title")
                or ""
            ).strip()

            final_task_text = " ".join(
                [
                    final_task_title,
                    task_text,
                    str(task_spec.get("description") or ""),
                    str(task_spec.get("expected_output") or ""),
                    str(task_spec.get("completion_criteria") or ""),
                ]
            )

            final_task_title_lower = final_task_title.lower()
            final_task_text_lower = final_task_text.lower()

            if (
                normalized_action == "create"
                and target_file
                and not task_spec.get("content")
            ):
                task_spec["content"] = ""

            final_is_execution_task = bool(
                execution_file
                and (
                    final_task_title_lower.startswith("execute ")
                    or final_task_title_lower.startswith("run ")
                    or "script execution" in final_task_title_lower
                    or "capture output" in final_task_title_lower
                    or "standard output" in final_task_text_lower
                    or "execute " in final_task_title_lower
                    or "run " in final_task_title_lower
                )
            )

            if final_is_execution_task:
                normalized_action = "execute"
                normalized_execution_mode = "hybrid"

                output_matches = re.findall(
                    r"\b([A-Za-z0-9_.-]+\.(?:txt|json|csv|md|log|out|xml|yaml|yml))\b",
                    final_task_text,
                    flags=re.IGNORECASE,
                )

                output_matches = [
                    value
                    for value in output_matches
                    if value.lower() != execution_file.lower()
                ]

                if output_matches:
                    target_file = output_matches[-1]
                    target_files = [target_file]

                elif target_file and (
                    target_file.lower() == execution_file.lower()
                ):
                    # Do not use the executable itself as the output
                    # artifact when no distinct output file was found.
                    target_file = ""
                    target_files = []

            else:
                if normalized_execution_mode not in {
                    "ai",
                    "hybrid",
                    "manual",
                    "system",
                }:
                    normalized_execution_mode = ""

            # Output-persistence tasks are implementation tasks, not
            # executable tasks.
            if (
                "write captured output" in final_task_title_lower
                or "persist captured output" in final_task_title_lower
                or "save captured output" in final_task_title_lower
                or "output to " in final_task_title_lower
            ):
                normalized_action = "implement"
                normalized_execution_mode = (
                    normalized_execution_mode or "hybrid"
                )
                execution_file = ""

            # -----------------------------------------------------
            # Enforce execution metadata at the final persistence
            # boundary. Planner-provided values are not authoritative.
            # -----------------------------------------------------

            normalized_execution_mode = str(
                task_spec.get("execution_mode") or ""
            ).strip().lower()

            if is_execution_task and execution_file:
                normalized_action = "execute"
                normalized_execution_mode = "hybrid"
            elif normalized_execution_mode not in {
                "ai",
                "hybrid",
                "manual",
                "system",
            }:
                normalized_execution_mode = ""

            if is_output_persistence_task:
                normalized_action = "implement"
                normalized_execution_mode = (
                    normalized_execution_mode
                    or "hybrid"
                )


            # Persist the task.
            # -----------------------------------------------------

            created_task = (

                self.project_workspace_service.add_task(
                    project_id=project_id,
                    title=task_title,
                    priority=(
                        task_spec.get(
                            "priority"
                        )
                        or "medium"
                    ),
                    description=(
                        task_spec.get(
                            "description"
                        )
                        or ""
                    ),


                    action=normalized_action,
                    execution_mode=normalized_execution_mode,

                    execution_file=execution_file,
                    target_file=target_file,
                    target_files=target_files,
                    target_function=(
                        task_spec.get(
                            "target_function"
                        )
                        or ""
                    ),
                    dependencies=dependencies,
                    expected_output=(
                        task_spec.get(
                            "expected_output"
                        )
                        or ""
                    ),
                    completion_criteria=(
                        task_spec.get(
                            "completion_criteria"
                        )
                        or []
                    ),
                    phase_id=persistent_phase_id,

                    steps=task_steps,

                    content=(
                        task_spec.get(
                            "content"
                        )
                        or ""
                    ),
                    code=(
                        task_spec.get(
                            "code"
                        )
                        or ""
                    ),
                    replacement=(
                        task_spec.get(
                            "replacement"
                        )
                        or ""
                    ),
                    command=(
                        task_spec.get(
                            "command"
                        )
                        or ""
                    ),
                )
            )

            if isinstance(
                created_task,
                dict,
            ):
                persistent_task_id = (
                    created_task.get("id")
                    or created_task.get("task_id")
                    or created_task.get("key")
                )
            else:
                persistent_task_id = created_task

            if not persistent_task_id:
                raise RuntimeError(
                    "Created task did not contain an id"
                )

            persistent_task_id = str(
                persistent_task_id
            ).strip()

            task_id_map[
                planner_task_id
            ] = persistent_task_id

            normalized_task_title_map[
                self._normalize_task_reference(
                    task_title
                )
            ] = persistent_task_id

            created_tasks.append(
                {
                    "id": persistent_task_id,
                    "planner_id": planner_task_id,
                    "title": task_title,
                    "phase_id": persistent_phase_id,
                    "priority": (
                        task_spec.get(
                            "priority"
                        )
                        or "medium"
                    ),
                    "status": (
                        created_task.get(
                            "status",
                            "open",
                        )
                        if isinstance(
                            created_task,
                            dict,
                        )
                        else "open"
                    ),
                }
            )

            if dependencies:
                pending_dependency_records.append(
                    {
                        "task_id": persistent_task_id,
                        "dependencies": dependencies,
                    }
                )

        project = self.project_workspace_service.get_project(
            project_id
        )

        if not isinstance(project, dict):
            raise RuntimeError(
                "Project workspace could not retrieve project "
                f"for project_id={project_id!r}"
            )

        persisted_tasks = project.get(
            "tasks",
            []
        )

        dependency_map = {
            str(
                persisted_task.get("id") or ""
            ).strip(): list(
                persisted_task.get("dependencies") or []
            )
            for persisted_task in persisted_tasks
            if isinstance(
                persisted_task,
                dict,
            )
            and persisted_task.get("id")
        }

        for dependency_record in pending_dependency_records:
            persistent_task_id = dependency_record.get(
                "task_id"
            )

            persistent_task_id = str(
                persistent_task_id or ""
            ).strip()

            resolved_dependencies = []

            for dependency_reference in (
                dependency_record.get(
                    "dependencies"
                )
                or []
            ):
                dependency_reference = str(
                    dependency_reference or ""
                ).strip()

                if not dependency_reference:
                    continue

                resolved_dependency_id = (
                    task_id_map.get(
                        dependency_reference
                    )
                )

                if not resolved_dependency_id:
                    resolved_dependency_id = (
                        task_id_map.get(
                            dependency_reference.lower()
                        )
                    )

                if not resolved_dependency_id:
                    normalized_reference = (
                        self._normalize_task_reference(
                            dependency_reference
                        )
                    )

                    resolved_dependency_id = (
                        normalized_task_title_map.get(
                            normalized_reference
                        )
                    )

                if resolved_dependency_id:
                    resolved_dependencies.append(
                        resolved_dependency_id
                    )

            dependency_map[persistent_task_id] = (
                resolved_dependencies
            )

        for persisted_task in persisted_tasks:
            if not isinstance(
                persisted_task,
                dict,
            ):
                continue

            persisted_task_id = str(
                persisted_task.get("id") or ""
            ).strip()

            if persisted_task_id in dependency_map:
                persisted_task["dependencies"] = (
                    dependency_map[persisted_task_id]
                )

        self.project_workspace_service.update_project_tasks(
            project_id=project_id,
            tasks=persisted_tasks,
        )

        project = self.project_workspace_service.get_project(
            project_id
        )

        self._update_project_brain(
            project_id=project_id,
            plan=plan,
        )

        print(
            "[NOVA PROJECT BUILDER] "
            f"Created {len(created_phases)} phases and "
            f"{len(created_tasks)} tasks."
        )

        return {
            "project_id": project_id,
            "project": project,
            "plan": plan,
            "phases": created_phases,
            "tasks": created_tasks,
        }

    def _build_project_plan(
        self,
        request: str,
        project_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build a project plan.

        Primary path:
        Use Nova Project Intelligence AI to understand the user's goal
        and generate project-specific tasks.

        Fallback path:
        Use the existing deterministic planner if AI planning is
        unavailable or returns an invalid result.
        """

        clean_request = str(
            request or ""
        ).strip()

        if not clean_request:
            raise ValueError(
                "Project request cannot be empty."
            )

        try:
            ai_plan = (
                project_planning_ai_service.build_plan(
                    request=clean_request,
                    project_context=project_context,
                )
            )

            if (
                isinstance(ai_plan, dict)
                and isinstance(
                    ai_plan.get("tasks"),
                    list,
                )
                and ai_plan.get("tasks")
            ):

                normalized_tasks = []

                for task in ai_plan.get(
                    "tasks",
                    [],
                ):
                    if not isinstance(
                        task,
                        dict,
                    ):
                        continue

                    task = dict(task)

                    task_title = str(
                        task.get(
                            "title",
                            "",
                        )
                        or ""
                    ).strip()

                    task_description = str(
                        task.get(
                            "description",
                            "",
                        )
                        or ""
                    ).strip()

                    task_text = " ".join(
                        [
                            task_title,
                            task_description,
                        ]
                    )

                    task_title_lower = task_title.lower()
                    task_text_lower = task_text.lower()


                    is_execution_task = (
                        task_title_lower.startswith("execute ")
                        or task_title_lower.startswith("run ")
                        or task_title_lower.startswith(
                            "implement script execution"
                        )
                        or "script execution" in task_text_lower
                        or "execution metadata" in task_text_lower
                        or "capture output" in task_text_lower
                        or "standard output" in task_text_lower
                    )

                    is_output_persistence_task = (
                        "write captured output" in task_title_lower
                        or "persist captured output" in task_title_lower
                        or "save captured output" in task_title_lower
                        or "output to " in task_title_lower
                    )

                    if is_output_persistence_task:
                        is_execution_task = False
                        task["execution_file"] = ""
                        task["action"] = "implement"
                    else:
                        execution_file = str(
                            task.get(
                                "execution_file",
                                "",
                            )
                            or task.get(
                                "run_file",
                                "",
                            )
                            or task.get(
                                "script_file",
                                "",
                            )
                            or task.get(
                                "test_script",
                                "",
                            )
                            or task.get(
                                "test_file",
                                "",
                            )
                            or ""
                        ).strip()

                        if is_execution_task:
                            execution_match = re.search(
                                r"\b([A-Za-z0-9_.-]+\.py)\b",
                                task_title,
                                flags=re.IGNORECASE,
                            )

                            if execution_match:
                                execution_file = (
                                    execution_match.group(1).strip()
                                )

                            task["action"] = "execute"
                            task["execution_mode"] = "hybrid"

                        task["execution_file"] = execution_file


                    target_file = str(
                        task.get(
                            "target_file",
                            "",
                        )
                        or ""
                    ).strip()

                    if not target_file:
                        file_match = re.search(
                            r"\b[\w./-]+\.(?:py|md|txt|json|js|html|css|yaml|yml)\b",
                            task_text,
                            flags=re.IGNORECASE,
                        )

                        if file_match:
                            target_file = (
                                file_match.group(0)
                            )

                    task["target_file"] = target_file

                    normalized_tasks.append(
                        task
                    )

                ai_plan["tasks"] = normalized_tasks

                print(
                    "[NOVA PROJECT PLANNER] "
                    "AI plan generated successfully.",
                    flush=True,
                )

                ai_plan.setdefault(
                    "description",
                    clean_request,
                )

                ai_plan.setdefault(
                    "objective",
                    ai_plan.get(
                        "mission",
                        clean_request,
                    ),
                )

                ai_name = str(
                    ai_plan.get(
                        "name",
                        "",
                    )
                    or ai_plan.get(
                        "title",
                        "",
                    )
                    or ""
                ).strip()

                if not ai_name:
                    ai_name = self._project_name(
                        clean_request
                    )

                ai_plan["name"] = ai_name
                ai_plan["title"] = ai_name

                ai_plan.setdefault(
                    "mission",
                    clean_request,
                )

                return ai_plan

            raise RuntimeError(
                "AI project planner returned no tasks."
            )

        except Exception as error:
            print(
                "[NOVA PROJECT PLANNER] "
                f"AI planning unavailable, using fallback: {error}",
                flush=True,
            )

        name = self._project_name(
            clean_request
        )

        requirements = self._extract_requirements(
            clean_request
        )

        assumptions = self._build_assumptions(
            clean_request
        )

        unknowns = self._build_unknowns(
            clean_request
        )

        generated_tasks = (
            self._build_implementation_tasks(
                request=clean_request,
            )
        )

        milestones = [
            {
                "id": "milestone_requirements",
                "title": "Requirements defined",
                "status": "pending",
            },
            {
                "id": "milestone_plan",
                "title": "Implementation planned",
                "status": "pending",
            },
            {
                "id": "milestone_build",
                "title": "Project built",
                "status": "pending",
            },
            {
                "id": "milestone_verify",
                "title": "Result verified",
                "status": "pending",
            },
        ]

        return {
            "name": name,
            "title": name,
            "mission": clean_request,
            "description": clean_request,
            "objective": clean_request,
            "requirements": requirements,
            "assumptions": assumptions,
            "unknowns": unknowns,
            "milestones": milestones,
            "tasks": generated_tasks,
            "decisions": [],
            "blockers": [],
            "next_actions": (
                [
                    generated_tasks[0].get(
                        "title"
                    )
                ]
                if generated_tasks
                else []
            ),
            "recommendations": [],
            "created_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }
    # ------------------------------------------------------------------
    # REQUIREMENT EXTRACTION
    # ------------------------------------------------------------------

    def _build_implementation_tasks(
        self,
        request: str,
    ) -> list[dict[str, Any]]:

        text = str(
            request or ""
        ).strip()

        lower_text = text.lower()

        # --------------------------------------------------------------
        # SIMPLE PYTHON HELLO WORLD
        # --------------------------------------------------------------

        if (
            "hello world" in lower_text
            and "python" in lower_text
        ):
            return [
                {
                    "title": (
                        "Create hello world Python application"
                    ),
                    "priority": "high",
                    "description": (
                        "Create the Python entry point for the "
                        "hello world application."
                    ),
                    "action": "write",
                    "target_file": "hello.py",
                    "content": (
                        'print("Hello, World!")\n'
                    ),
                },
            ]

        # --------------------------------------------------------------
        # FLASK SQLITE TASK MANAGER
        # --------------------------------------------------------------

        if (
            "flask" in lower_text
            and (
                "task manager" in lower_text
                or "todo" in lower_text
                or "to-do" in lower_text
            )
        ):
            return [
                {
                    "title": (
                        "Create Flask application"
                    ),
                    "priority": "high",
                    "description": (
                        "Create the main Flask application with "
                        "routes for viewing, creating, editing, "
                        "deleting, and completing tasks."
                    ),
                    "action": "write",
                    "target_file": "task_manager/app.py",
                    "content": (
                        "from flask import (\n"
                        "    Flask,\n"
                        "    redirect,\n"
                        "    render_template,\n"
                        "    request,\n"
                        "    url_for,\n"
                        ")\n"
                        "\n"
                        "from database import (\n"
                        "    create_task,\n"
                        "    delete_task,\n"
                        "    get_task,\n"
                        "    get_tasks,\n"
                        "    init_db,\n"
                        "    toggle_task,\n"
                        "    update_task,\n"
                        ")\n"
                        "\n"
                        "\n"
                        "app = Flask(__name__)\n"
                        "\n"
                        "\n"
                        "@app.route('/')\n"
                        "def index():\n"
                        "    return render_template(\n"
                        "        'index.html',\n"
                        "        tasks=get_tasks(),\n"
                        "    )\n"
                        "\n"
                        "\n"
                        "@app.route('/tasks', methods=['POST'])\n"
                        "def add_task():\n"
                        "    title = request.form.get(\n"
                        "        'title',\n"
                        "        '',\n"
                        "    ).strip()\n"
                        "\n"
                        "    if title:\n"
                        "        create_task(title)\n"
                        "\n"
                        "    return redirect(url_for('index'))\n"
                        "\n"
                        "\n"
                        "@app.route('/tasks/<int:task_id>/edit')\n"
                        "def edit_task(task_id):\n"
                        "    task = get_task(task_id)\n"
                        "\n"
                        "    if task is None:\n"
                        "        return redirect(url_for('index'))\n"
                        "\n"
                        "    return render_template(\n"
                        "        'edit.html',\n"
                        "        task=task,\n"
                        "    )\n"
                        "\n"
                        "\n"
                        "@app.route(\n"
                        "    '/tasks/<int:task_id>/edit',\n"
                        "    methods=['POST'],\n"
                        ")\n"
                        "def save_task(task_id):\n"
                        "    title = request.form.get(\n"
                        "        'title',\n"
                        "        '',\n"
                        "    ).strip()\n"
                        "\n"
                        "    if title:\n"
                        "        update_task(task_id, title)\n"
                        "\n"
                        "    return redirect(url_for('index'))\n"
                        "\n"
                        "\n"
                        "@app.route(\n"
                        "    '/tasks/<int:task_id>/toggle',\n"
                        "    methods=['POST'],\n"
                        ")\n"
                        "def complete_task(task_id):\n"
                        "    toggle_task(task_id)\n"
                        "    return redirect(url_for('index'))\n"
                        "\n"
                        "\n"
                        "@app.route(\n"
                        "    '/tasks/<int:task_id>/delete',\n"
                        "    methods=['POST'],\n"
                        ")\n"
                        "def remove_task(task_id):\n"
                        "    delete_task(task_id)\n"
                        "    return redirect(url_for('index'))\n"
                        "\n"
                        "\n"
                        "if __name__ == '__main__':\n"
                        "    init_db()\n"
                        "    app.run(debug=True)\n"
                    ),
                },
                {
                    "title": (
                        "Create SQLite database layer"
                    ),
                    "priority": "high",
                    "description": (
                        "Create SQLite storage and database functions "
                        "for task persistence."
                    ),
                    "action": "write",
                    "target_file": "task_manager/database.py",
                    "content": (
                        "import sqlite3\n"
                        "\n"
                        "\n"
                        "DATABASE = 'tasks.db'\n"
                        "\n"
                        "\n"
                        "def get_connection():\n"
                        "    connection = sqlite3.connect(DATABASE)\n"
                        "    connection.row_factory = sqlite3.Row\n"
                        "    return connection\n"
                        "\n"
                        "\n"
                        "def init_db():\n"
                        "    connection = get_connection()\n"
                        "\n"
                        "    connection.execute(\n"
                        "        '''\n"
                        "        CREATE TABLE IF NOT EXISTS tasks (\n"
                        "            id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                        "            title TEXT NOT NULL,\n"
                        "            completed INTEGER NOT NULL DEFAULT 0\n"
                        "        )\n"
                        "        '''\n"
                        "    )\n"
                        "\n"
                        "    connection.commit()\n"
                        "    connection.close()\n"
                        "\n"
                        "\n"
                        "def get_tasks():\n"
                        "    connection = get_connection()\n"
                        "    tasks = connection.execute(\n"
                        "        'SELECT * FROM tasks ORDER BY id DESC'\n"
                        "    ).fetchall()\n"
                        "    connection.close()\n"
                        "    return tasks\n"
                        "\n"
                        "\n"
                        "def get_task(task_id):\n"
                        "    connection = get_connection()\n"
                        "    task = connection.execute(\n"
                        "        'SELECT * FROM tasks WHERE id = ?',\n"
                        "        (task_id,),\n"
                        "    ).fetchone()\n"
                        "    connection.close()\n"
                        "    return task\n"
                        "\n"
                        "\n"
                        "def create_task(title):\n"
                        "    connection = get_connection()\n"
                        "    connection.execute(\n"
                        "        'INSERT INTO tasks (title) VALUES (?)',\n"
                        "        (title,),\n"
                        "    )\n"
                        "    connection.commit()\n"
                        "    connection.close()\n"
                        "\n"
                        "\n"
                        "def update_task(task_id, title):\n"
                        "    connection = get_connection()\n"
                        "    connection.execute(\n"
                        "        'UPDATE tasks SET title = ? WHERE id = ?',\n"
                        "        (title, task_id),\n"
                        "    )\n"
                        "    connection.commit()\n"
                        "    connection.close()\n"
                        "\n"
                        "\n"
                        "def toggle_task(task_id):\n"
                        "    connection = get_connection()\n"
                        "    connection.execute(\n"
                        "        '''\n"
                        "        UPDATE tasks\n"
                        "        SET completed = CASE\n"
                        "            WHEN completed = 1 THEN 0\n"
                        "            ELSE 1\n"
                        "        END\n"
                        "        WHERE id = ?\n"
                        "        ''',\n"
                        "        (task_id,),\n"
                        "    )\n"
                        "    connection.commit()\n"
                        "    connection.close()\n"
                        "\n"
                        "\n"
                        "def delete_task(task_id):\n"
                        "    connection = get_connection()\n"
                        "    connection.execute(\n"
                        "        'DELETE FROM tasks WHERE id = ?',\n"
                        "        (task_id,),\n"
                        "    )\n"
                        "    connection.commit()\n"
                        "    connection.close()\n"
                    ),
                },
                {
                    "title": (
                        "Create task manager HTML template"
                    ),
                    "priority": "high",
                    "description": (
                        "Create the main HTML interface for listing "
                        "and managing tasks."
                    ),
                    "action": "write",
                    "target_file": (
                        "task_manager/templates/index.html"
                    ),
                    "content": (
                        "<!DOCTYPE html>\n"
                        "<html lang=\"en\">\n"
                        "<head>\n"
                        "    <meta charset=\"UTF-8\">\n"
                        "    <meta name=\"viewport\" "
                        "content=\"width=device-width, "
                        "initial-scale=1.0\">\n"
                        "    <title>Task Manager</title>\n"
                        "    <link rel=\"stylesheet\" "
                        "href=\"{{ url_for('static', "
                        "filename='style.css') }}\">\n"
                        "</head>\n"
                        "<body>\n"
                        "    <main class=\"container\">\n"
                        "        <h1>Task Manager</h1>\n"
                        "\n"
                        "        <form method=\"post\" "
                        "action=\"{{ url_for('add_task') }}\" "
                        "class=\"task-form\">\n"
                        "            <input\n"
                        "                type=\"text\"\n"
                        "                name=\"title\"\n"
                        "                placeholder=\"What needs to be done?\"\n"
                        "                required\n"
                        "            >\n"
                        "            <button type=\"submit\">"
                        "Add Task</button>\n"
                        "        </form>\n"
                        "\n"
                        "        <section class=\"task-list\">\n"
                        "            {% for task in tasks %}\n"
                        "                <article class=\"task "
                        "{% if task['completed'] %}completed"
                        "{% endif %}\">\n"
                        "                    <form method=\"post\" "
                        "action=\"{{ url_for('complete_task', "
                        "task_id=task['id']) }}\">\n"
                        "                        <button type=\"submit\">"
                        "{% if task['completed'] %}Undo"
                        "{% else %}Complete{% endif %}</button>\n"
                        "                    </form>\n"
                        "\n"
                        "                    <span>{{ task['title'] }}</span>\n"
                        "\n"
                        "                    <a href=\"{{ "
                        "url_for('edit_task', "
                        "task_id=task['id']) }}\">Edit</a>\n"
                        "\n"
                        "                    <form method=\"post\" "
                        "action=\"{{ url_for('remove_task', "
                        "task_id=task['id']) }}\">\n"
                        "                        <button type=\"submit\">"
                        "Delete</button>\n"
                        "                    </form>\n"
                        "                </article>\n"
                        "            {% else %}\n"
                        "                <p>No tasks yet.</p>\n"
                        "            {% endfor %}\n"
                        "        </section>\n"
                        "    </main>\n"
                        "</body>\n"
                        "</html>\n"
                    ),
                },
                {
                    "title": (
                        "Create task edit template"
                    ),
                    "priority": "medium",
                    "description": (
                        "Create the HTML page for editing an "
                        "existing task."
                    ),
                    "action": "write",
                    "target_file": (
                        "task_manager/templates/edit.html"
                    ),
                    "content": (
                        "<!DOCTYPE html>\n"
                        "<html lang=\"en\">\n"
                        "<head>\n"
                        "    <meta charset=\"UTF-8\">\n"
                        "    <meta name=\"viewport\" "
                        "content=\"width=device-width, "
                        "initial-scale=1.0\">\n"
                        "    <title>Edit Task</title>\n"
                        "    <link rel=\"stylesheet\" "
                        "href=\"{{ url_for('static', "
                        "filename='style.css') }}\">\n"
                        "</head>\n"
                        "<body>\n"
                        "    <main class=\"container\">\n"
                        "        <h1>Edit Task</h1>\n"
                        "\n"
                        "        <form method=\"post\" "
                        "class=\"task-form\">\n"
                        "            <input\n"
                        "                type=\"text\"\n"
                        "                name=\"title\"\n"
                        "                value=\"{{ task['title'] }}\"\n"
                        "                required\n"
                        "            >\n"
                        "\n"
                        "            <button type=\"submit\">"
                        "Save Changes</button>\n"
                        "        </form>\n"
                        "\n"
                        "        <p>\n"
                        "            <a href=\"{{ url_for('index') }}\">"
                        "Back to tasks</a>\n"
                        "        </p>\n"
                        "    </main>\n"
                        "</body>\n"
                        "</html>\n"
                    ),
                },
                {
                    "title": (
                        "Create task manager CSS styling"
                    ),
                    "priority": "medium",
                    "description": (
                        "Create CSS styling for the task manager "
                        "interface."
                    ),
                    "action": "write",
                    "target_file": (
                        "task_manager/static/style.css"
                    ),
                    "content": (
                        "* {\n"
                        "    box-sizing: border-box;\n"
                        "}\n"
                        "\n"
                        "body {\n"
                        "    margin: 0;\n"
                        "    font-family: Arial, sans-serif;\n"
                        "    background: #f4f6f8;\n"
                        "    color: #222;\n"
                        "}\n"
                        "\n"
                        ".container {\n"
                        "    max-width: 760px;\n"
                        "    margin: 40px auto;\n"
                        "    padding: 24px;\n"
                        "    background: white;\n"
                        "    border-radius: 12px;\n"
                        "}\n"
                        "\n"
                        ".task-form {\n"
                        "    display: flex;\n"
                        "    gap: 10px;\n"
                        "    margin-bottom: 24px;\n"
                        "}\n"
                        "\n"
                        "input {\n"
                        "    flex: 1;\n"
                        "    padding: 10px;\n"
                        "}\n"
                        "\n"
                        "button {\n"
                        "    padding: 10px 14px;\n"
                        "    cursor: pointer;\n"
                        "}\n"
                        "\n"
                        ".task {\n"
                        "    display: flex;\n"
                        "    align-items: center;\n"
                        "    gap: 10px;\n"
                        "    padding: 12px 0;\n"
                        "    border-bottom: 1px solid #ddd;\n"
                        "}\n"
                        "\n"
                        ".task span {\n"
                        "    flex: 1;\n"
                        "}\n"
                        "\n"
                        ".task.completed span {\n"
                        "    text-decoration: line-through;\n"
                        "    opacity: 0.6;\n"
                        "}\n"
                    ),
                },
                {
                    "title": (
                        "Create Python requirements file"
                    ),
                    "priority": "high",
                    "description": (
                        "Create the dependency list required to run "
                        "the Flask application."
                    ),
                    "action": "write",
                    "target_file": (
                        "task_manager/requirements.txt"
                    ),
                    "content": (
                        "Flask>=3.0.0\n"
                    ),
                },
                {
                    "title": (
                        "Create project documentation"
                    ),
                    "priority": "medium",
                    "description": (
                        "Create README documentation with setup and "
                        "run instructions."
                    ),
                    "action": "write",
                    "target_file": (
                        "task_manager/README.md"
                    ),
                    "content": (
                        "# Flask Task Manager\n\n"
                        "A simple task manager web application "
                        "built with Flask and SQLite.\n\n"
                        "## Features\n\n"
                        "- Create tasks\n"
                        "- Edit tasks\n"
                        "- Delete tasks\n"
                        "- Mark tasks complete\n"
                        "- Persistent SQLite storage\n\n"
                        "## Installation\n\n"
                        "```powershell\n"
                        "pip install -r requirements.txt\n"
                        "```\n\n"
                        "## Run\n\n"
                        "```powershell\n"
                        "python app.py\n"
                        "```\n\n"
                        "Open http://127.0.0.1:5000 in your browser.\n"
                    ),
                },
            ]


        # --------------------------------------------------------------
        # SIMPLE PYTHON CALCULATOR
        # --------------------------------------------------------------

        if (
            "calculator" in lower_text
            and "python" in lower_text
        ):
            return [
                {
                    "title": (
                        "Create calculator application"
                    ),
                    "priority": "high",
                    "description": (
                        "Create the Python calculator application."
                    ),
                    "action": "write",
                    "target_file": (
                        "calculator/main.py"
                    ),
                    "content": (
                        "def add(a, b):\n"
                        "    return a + b\n"
                        "\n"
                        "\n"
                        "def subtract(a, b):\n"
                        "    return a - b\n"
                        "\n"
                        "\n"
                        "def multiply(a, b):\n"
                        "    return a * b\n"
                        "\n"
                        "\n"
                        "def divide(a, b):\n"
                        "    if b == 0:\n"
                        "        raise ValueError(\n"
                        "            'Cannot divide by zero'\n"
                        "        )\n"
                        "\n"
                        "    return a / b\n"
                        "\n"
                        "\n"
                        "def main():\n"
                        "    print('Python Calculator')\n"
                        "    print('2 + 3 =', add(2, 3))\n"
                        "\n"
                        "\n"
                        "if __name__ == '__main__':\n"
                        "    main()\n"
                    ),
                },
                {
                    "title": (
                        "Create calculator documentation"
                    ),
                    "priority": "medium",
                    "description": (
                        "Create documentation for the calculator "
                        "application."
                    ),
                    "action": "write",
                    "target_file": (
                        "calculator/README.md"
                    ),
                    "content": (
                        "# Python Calculator\n\n"
                        "A simple calculator application written "
                        "in Python.\n\n"
                        "## Features\n\n"
                        "- Addition\n"
                        "- Subtraction\n"
                        "- Multiplication\n"
                        "- Division\n\n"
                        "## Run\n\n"
                        "```powershell\n"
                        "python main.py\n"
                        "```\n"
                    ),
                },
            ]



        # --------------------------------------------------------------
        # GENERIC PYTHON APPLICATION
        # --------------------------------------------------------------

        if "python" in lower_text:
            return [
                {
                    "title": (
                        "Create Python application entry point"
                    ),
                    "priority": "high",
                    "description": (
                        "Create the main Python application file."
                    ),
                    "action": "write",
                    "target_file": "main.py",
                    "content": (
                        'def main():\n'
                        '    print("Application started")\n'
                        '\n'
                        '\n'
                        'if __name__ == "__main__":\n'
                        '    main()\n'
                    ),
                },
            ]

        # --------------------------------------------------------------
        # FALLBACK PROJECT ARTIFACT
        # --------------------------------------------------------------

        return [
            {
                "title": "Create project specification",
                "priority": "high",
                "description": (
                    "Create the initial project specification "
                    "from the requested objective."
                ),
                "action": "write",
                "target_file": "PROJECT.md",
                "content": (
                    "# Project\n\n"
                    f"{text}\n"
                ),
            },
        ]

    def _extract_requirements(
        self,
        request: str,
    ) -> list[str]:

        text = str(request or "").strip()

        requirements = []

        if not text:
            return requirements

        requirements.append(
            f"Primary objective: {text}"
        )

        keyword_requirements = {
            "web": (
                "Provide a web-based user interface."
            ),
            "website": (
                "Provide a website interface."
            ),
            "application": (
                "Provide an application interface."
            ),
            "app": (
                "Provide an application interface."
            ),
            "search": (
                "Support searching or filtering where applicable."
            ),
            "user": (
                "Provide functionality for end users."
            ),
            "users": (
                "Provide functionality for end users."
            ),
            "manage": (
                "Support management operations for project data."
            ),
            "create": (
                "Support creation of relevant project data."
            ),
            "edit": (
                "Support editing of relevant project data."
            ),
            "delete": (
                "Support deletion of relevant project data."
            ),
            "api": (
                "Provide API functionality where required."
            ),
            "database": (
                "Persist application data."
            ),
            "login": (
                "Provide authentication functionality."
            ),
            "authentication": (
                "Provide authentication functionality."
            ),
        }

        lower_text = text.lower()

        for keyword, requirement in (
            keyword_requirements.items()
        ):
            if keyword in lower_text:

                if requirement not in requirements:
                    requirements.append(
                        requirement
                    )

        return requirements

    # ------------------------------------------------------------------
    # ASSUMPTIONS
    # ------------------------------------------------------------------

    def _build_assumptions(
        self,
        request: str,
    ) -> list[str]:

        return [
            (
                "Nova should preserve the user's stated "
                "objective as the primary project goal."
            ),
            (
                "Implementation details not explicitly provided "
                "will require planning decisions."
            ),
            (
                "The project should remain modular so additional "
                "requirements can be added later."
            ),
        ]

    # ------------------------------------------------------------------
    # UNKNOWNS
    # ------------------------------------------------------------------

    def _build_unknowns(
        self,
        request: str,
    ) -> list[str]:

        return [
            "Preferred technology stack.",
            "Detailed user interface requirements.",
            "Data storage requirements.",
            "Deployment environment.",
        ]

    # ------------------------------------------------------------------
    # PROJECT NAME
    # ------------------------------------------------------------------

    def _project_name(
        self,
        request: str,
    ) -> str:

        text = re.sub(
            r"\s+",
            " ",
            request,
        ).strip()

        text = re.sub(
            (
                r"^(please\s+)?"
                r"(build|create|make|develop|design|implement)\s+"
            ),
            "",
            text,
            flags=re.IGNORECASE,
        )

        if not text:
            text = "New Nova Project"

        if len(text) > 80:
            text = text[:80].rstrip()

        return (
            text[:1].upper()
            + text[1:]
        )

    # ------------------------------------------------------------------
    # PROJECT BRAIN
    # ------------------------------------------------------------------

    def _update_project_brain(
        self,
        project_id: str,
        plan: dict[str, Any],
    ) -> None:
        """
        Merge new project intelligence into the existing Project Brain.

        Existing intelligence is preserved unless the new plan provides
        genuinely new information. This prevents project expansions from
        erasing requirements, assumptions, decisions, blockers, milestones,
        or other accumulated project knowledge.
        """

        projects = (
            self.project_workspace_service._load_projects()
        )

        if not isinstance(
            projects,
            list,
        ):
            return

        def merge_unique(
            existing,
            incoming,
        ):
            merged = []
            seen = set()

            for source in (
                existing or [],
                incoming or [],
            ):
                if not isinstance(
                    source,
                    list,
                ):
                    continue

                for item in source:

                    if isinstance(
                        item,
                        dict,
                    ):
                        key = str(
                            item.get(
                                "id",
                                item.get(
                                    "title",
                                    item,
                                ),
                            )
                        ).strip().lower()

                    else:
                        key = str(
                            item
                        ).strip().lower()

                    if not key:
                        continue

                    if key in seen:
                        continue

                    seen.add(key)
                    merged.append(item)

            return merged

        for project in projects:

            if project.get("id") != project_id:
                continue

            brain = project.get(
                "brain"
            )

            if not isinstance(
                brain,
                dict,
            ):
                brain = {}

            existing_goal = str(
                brain.get(
                    "goal",
                    "",
                )
            ).strip()

            incoming_goal = str(
                plan.get(
                    "objective",
                    plan.get(
                        "mission",
                        "",
                    ),
                )
            ).strip()

            if incoming_goal:
                brain["goal"] = incoming_goal
            elif existing_goal:
                brain["goal"] = existing_goal

            brain["requirements"] = merge_unique(
                brain.get(
                    "requirements",
                    [],
                ),
                plan.get(
                    "requirements",
                    [],
                ),
            )

            brain["assumptions"] = merge_unique(
                brain.get(
                    "assumptions",
                    [],
                ),
                plan.get(
                    "assumptions",
                    [],
                ),
            )

            brain["unknowns"] = merge_unique(
                brain.get(
                    "unknowns",
                    [],
                ),
                plan.get(
                    "unknowns",
                    [],
                ),
            )

            brain["milestones"] = merge_unique(
                brain.get(
                    "milestones",
                    [],
                ),
                plan.get(
                    "milestones",
                    [],
                ),
            )

            brain["decisions"] = merge_unique(
                brain.get(
                    "decisions",
                    [],
                ),
                plan.get(
                    "decisions",
                    [],
                ),
            )

            brain["blockers"] = merge_unique(
                brain.get(
                    "blockers",
                    [],
                ),
                plan.get(
                    "blockers",
                    [],
                ),
            )

            brain["next_actions"] = merge_unique(
                brain.get(
                    "next_actions",
                    [],
                ),
                plan.get(
                    "next_actions",
                    [],
                ),
            )

            brain["recommendations"] = merge_unique(
                brain.get(
                    "recommendations",
                    [],
                ),
                plan.get(
                    "recommendations",
                    [],
                ),
            )

            # ----------------------------------------------------------
            # LIVE PROJECT STATE
            #
            # Keep the Project Brain synchronized with actual task
            # progress so future intelligence decisions understand the
            # real state of the project.
            # ----------------------------------------------------------

            tasks = project.get(
                "tasks",
                [],
            )

            if not isinstance(
                tasks,
                list,
            ):
                tasks = []

            total_tasks = len(tasks)

            completed_tasks = 0
            in_progress_tasks = 0
            pending_tasks = 0

            current_focus = []

            for task in tasks:

                if not isinstance(
                    task,
                    dict,
                ):
                    continue

                status = str(
                    task.get(
                        "status",
                        "pending",
                    )
                ).strip().lower()

                title = str(
                    task.get(
                        "title",
                        "",
                    )
                ).strip()

                if status == "completed":

                    completed_tasks += 1

                elif status in (
                    "in_progress",
                    "in progress",
                    "active",
                    "running",
                ):

                    in_progress_tasks += 1

                    if title:
                        current_focus.append(
                            title
                        )

                else:

                    pending_tasks += 1

            # If nothing is actively running, expose the next pending
            # task as the current focus.

            if (
                not current_focus
                and pending_tasks > 0
            ):

                for task in tasks:

                    if not isinstance(
                        task,
                        dict,
                    ):
                        continue

                    status = str(
                        task.get(
                            "status",
                            "pending",
                        )
                    ).strip().lower()

                    title = str(
                        task.get(
                            "title",
                            "",
                        )
                    ).strip()

                    if (
                        status not in (
                            "completed",
                            "in_progress",
                            "in progress",
                            "active",
                            "running",
                        )
                        and title
                    ):

                        current_focus.append(
                            title
                        )

                        break

            completion_percentage = 0.0

            if total_tasks > 0:

                completion_percentage = round(
                    (
                        completed_tasks
                        / total_tasks
                    ) * 100,
                    1,
                )

            brain["current_state"] = {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "pending_tasks": pending_tasks,
                "completion_percentage": (
                    completion_percentage
                ),
                "current_focus": current_focus[:5],
            }

            # ----------------------------------------------------------
            # PROJECT EVOLUTION HISTORY
            #
            # Preserve a lightweight history of meaningful planning
            # updates so Nova can understand how the project evolved.
            # ----------------------------------------------------------

            history = brain.get(
                "history",
                [],
            )

            if not isinstance(
                history,
                list,
            ):
                history = []

            history_entry = {
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "objective": str(
                    plan.get(
                        "objective",
                        plan.get(
                            "mission",
                            "",
                        ),
                    )
                ).strip(),
                "task_count": len(
                    plan.get(
                        "tasks",
                        [],
                    )
                ),
                "requirements_count": len(
                    plan.get(
                        "requirements",
                        [],
                    )
                ),
                "decisions_count": len(
                    plan.get(
                        "decisions",
                        [],
                    )
                ),
                "blockers_count": len(
                    plan.get(
                        "blockers",
                        [],
                    )
                ),
            }

            duplicate_history_entry = False

            if history:

                latest_entry = history[-1]

                if isinstance(
                    latest_entry,
                    dict,
                ):

                    duplicate_history_entry = (
                        latest_entry.get(
                            "objective"
                        )
                        == history_entry.get(
                            "objective"
                        )
                        and latest_entry.get(
                            "task_count"
                        )
                        == history_entry.get(
                            "task_count"
                        )
                    )

            if not duplicate_history_entry:

                history.append(
                    history_entry
                )

            # Keep history bounded so Project Brain storage does not
            # grow indefinitely.

            brain["history"] = history[-50:]

            brain["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            project["brain"] = brain

            project["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            self.project_workspace_service._save_projects(
                projects
            )

            return































