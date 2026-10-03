"""Deterministic validation and safe normalization for Project plans."""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any


class ProjectPlanValidationError(ValueError):
    """Raised when a plan cannot be repaired without guessing user intent."""


class ProjectPlanQualityService:
    OWNERS = {"NOVA", "USER", "COLLABORATIVE"}
    FILE_ACTIONS = {"create", "write", "implement", "modify", "edit", "patch", "fix", "delete", "refactor"}
    ACTIONS = {
        "research", "analyze", "analysis", "plan", "planning", "design",
        "write", "document", "implement", "modify", "create", "fix",
        "refactor", "run", "execute", "verify", "test", "validate",
        "review", "edit", "patch", "command", "manual", "user_action",
    }
    NOVA_ACTIONS = {
        "research", "analyze", "analysis", "plan", "planning", "design",
        "write", "document", "implement", "modify", "create", "fix",
        "refactor", "run", "execute", "verify", "test", "validate",
        "review", "edit", "patch", "command",
    }
    META_TASKS = (
        "execute the first project task",
        "execute first project task",
        "run all",
        "continue project",
        "continue the project",
        "move to next phase",
        "move to the next phase",
        "review project status",
        "execute first task",
        "execute the first task",
        "run the next task",
        "continue execution",
    )
    GENERIC_OUTPUTS = {
        "a completed implementation", "completed implementation", "the completed task",
        "a completed task", "concrete result", "result", "done", "completed",
        "a completed result", "a completed project",
        "output", "success", "successful", "as requested", "the requested result",
        "the result", "the output", "file created", "task complete",
    }

    def validate(
        self,
        plan: dict[str, Any],
        request: str = "",
        available_tools: set[str] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(plan, dict):
            raise ProjectPlanValidationError("The project planner returned an invalid plan.")

        result = dict(plan)
        tasks = result.get("tasks")
        if not isinstance(tasks, list):
            raise ProjectPlanValidationError("The project plan must contain a task list.")

        normalized_tasks = []
        seen_titles: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        for index, raw_task in enumerate(tasks, start=1):
            if not isinstance(raw_task, dict):
                raise ProjectPlanValidationError(f"Project task {index} is malformed.")
            task = dict(raw_task)
            title = self._text(task.get("title") or task.get("name"))
            if not title:
                raise ProjectPlanValidationError(f"Project task {index} has no title.")
            normalized = self._key(title)
            if self._is_meta_task(normalized):
                # Controller instructions are behavior, never user deliverables.
                continue
            for prior_title, prior_key in seen_titles:
                if self._overlaps(normalized, prior_key):
                    raise ProjectPlanValidationError(
                        f"Duplicate or substantially overlapping project tasks: '{prior_title}' and '{title}'."
                    )
            seen_titles.append((title, normalized))
            task["title"] = title
            task["id"] = self._text(task.get("id") or task.get("task_id") or task.get("key")) or f"task_{index}"
            if task["id"] in seen_ids:
                raise ProjectPlanValidationError(f"Duplicate project task id '{task['id']}'.")
            seen_ids.add(task["id"])

            action = self._text(task.get("action") or "analyze").lower().replace("-", "_")
            # Missing ownership is resolved conservatively from the planned
            # operation. Real-world user actions must be explicitly assigned.
            inferred_owner = "USER" if action in {"manual", "user_action"} else "NOVA"
            owner_value = task.get("owner", task.get("ownership", task.get("actor", inferred_owner)))
            owner = self._normalize_owner(owner_value)
            task["owner"] = owner

            if action not in self.ACTIONS:
                raise ProjectPlanValidationError(
                    f"Task '{title}' uses unsupported action '{action}'."
                )
            if owner == "NOVA" and action not in self.NOVA_ACTIONS:
                raise ProjectPlanValidationError(
                    f"Task '{title}' uses action '{action}' that Nova cannot execute."
                )
            action = {"document": "write"}.get(action, action)
            task["action"] = action

            tool_name = self._text(task.get("tool_name") or task.get("tool"))
            if owner == "NOVA" and tool_name and available_tools is not None and tool_name not in available_tools:
                raise ProjectPlanValidationError(
                    f"Task '{title}' requires unsupported Nova tool '{tool_name}'."
                )

            task_target = self._text(task.get("target_file"))
            task_targets = task.get("target_files") if isinstance(task.get("target_files"), list) else []
            if not task_target and task_targets:
                task_target = next((self._text(item) for item in task_targets if self._text(item)), "")
            step_items = task.get("steps") if isinstance(task.get("steps"), list) else []
            if not task_target:
                for candidate_step in step_items:
                    if not isinstance(candidate_step, dict):
                        continue
                    step_targets = candidate_step.get("target_files") if isinstance(candidate_step.get("target_files"), list) else []
                    task_target = self._text(candidate_step.get("target_file")) or next(
                        (self._text(item) for item in step_targets if self._text(item)),
                        "",
                    )
                    if task_target:
                        break
            if owner == "NOVA" and action in self.FILE_ACTIONS:
                has_target = bool(task_target or any(self._text(item) for item in task_targets))
                if not has_target and not any(
                    isinstance(step, dict) and (self._text(step.get("target_file")) or self._has_text(step.get("target_files")))
                    for step in step_items
                ):
                    raise ProjectPlanValidationError(
                        f"Nova-owned file task '{title}' has no authoritative target file."
                    )

            steps = []
            for step_index, raw_step in enumerate(step_items, start=1):
                if not isinstance(raw_step, dict):
                    raise ProjectPlanValidationError(f"Task '{title}' contains a malformed step {step_index}.")
                step = dict(raw_step)
                step_title = self._text(step.get("title") or step.get("name"))
                if not step_title:
                    raise ProjectPlanValidationError(f"Task '{title}' contains a step without a title.")
                step_key = self._key(step_title)
                if self._overlaps(normalized, step_key):
                    raise ProjectPlanValidationError(
                        f"Step '{step_title}' substantially repeats its parent task '{title}'."
                    )
                step_owner = self._normalize_owner(step.get("owner", step.get("ownership", owner)))
                if step_owner != owner:
                    raise ProjectPlanValidationError(
                        f"Task '{title}' mixes ownership. Split work into separate tasks so execution boundaries stay clear."
                    )
                step["owner"] = step_owner
                step_action = self._text(step.get("action") or action).lower().replace("-", "_")
                if step_action not in self.ACTIONS:
                    raise ProjectPlanValidationError(
                        f"Step '{step_title}' uses unsupported action '{step_action}'."
                    )
                if step_owner == "NOVA" and step_action not in self.NOVA_ACTIONS:
                    raise ProjectPlanValidationError(
                        f"Step '{step_title}' uses action '{step_action}' that Nova cannot execute."
                    )
                step_action = {"document": "write"}.get(step_action, step_action)
                step["action"] = step_action
                step_tool_name = self._text(step.get("tool_name") or step.get("tool"))
                if (
                    step_owner == "NOVA"
                    and step_tool_name
                    and available_tools is not None
                    and step_tool_name not in available_tools
                ):
                    raise ProjectPlanValidationError(
                        f"Step '{step_title}' requires unsupported Nova tool '{step_tool_name}'."
                    )
                step_target = self._text(step.get("target_file"))
                step_targets = step.get("target_files") if isinstance(step.get("target_files"), list) else []
                if step_owner == "NOVA" and step_action in self.FILE_ACTIONS and not (
                    step_target or any(self._text(item) for item in step_targets) or task_target
                ):
                    raise ProjectPlanValidationError(
                        f"Nova-owned file step '{step_title}' has no authoritative target file."
                    )
                step["title"] = step_title
                step["id"] = self._text(step.get("id") or step.get("step_id")) or f"{task['id']}_step_{step_index}"
                steps.append(step)
            task["steps"] = steps

            expected = self._text(task.get("expected_output"))
            if self._is_generic(expected):
                expected = ""
            if not expected:
                if task_target:
                    expected = f"{task_target} exists with the planned content."
                elif owner == "USER":
                    expected = f"Real-world outcome completed: {title}."
                elif owner == "COLLABORATIVE":
                    expected = f"The agreed outcome for '{title}' is recorded or confirmed."
                elif action in {"research", "analyze", "analysis", "review", "verify", "test", "validate"}:
                    expected = f"Findings or verification results for: {title}."
                else:
                    raise ProjectPlanValidationError(
                        f"Nova-owned task '{title}' needs a concrete expected_output."
                    )
            task["expected_output"] = expected

            criteria = self._text(task.get("completion_criteria"))
            if self._is_generic(criteria):
                criteria = ""
            if not criteria:
                if task_target:
                    criteria = f"Verify that {task_target} exists and contains the planned content."
                elif owner == "USER":
                    criteria = "The user confirms the real-world outcome is complete."
                elif owner == "COLLABORATIVE":
                    criteria = "The user confirms the agreed result or decision."
                else:
                    criteria = f"Verify that the expected result is produced: {expected}"
            task["completion_criteria"] = criteria

            deps = task.get("dependencies", task.get("depends_on", []))
            if isinstance(deps, str):
                deps = [deps]
            task["dependencies"] = [self._text(item) for item in deps if self._text(item)] if isinstance(deps, list) else []
            if owner == "USER":
                task["execution_mode"] = "manual"
            elif owner == "COLLABORATIVE":
                task["execution_mode"] = "manual"
            normalized_tasks.append(task)

        if not normalized_tasks:
            raise ProjectPlanValidationError(
                "The project plan contains no user deliverables after removing execution-control instructions."
            )

        self._validate_dependencies(normalized_tasks)
        result["tasks"] = normalized_tasks

        phases = result.get("phases", result.get("milestones", []))
        if isinstance(phases, list):
            phases = [phase for phase in phases if isinstance(phase, dict) and self._text(phase.get("title") or phase.get("name"))]
            simple_plan = len(normalized_tasks) <= 2 and all(not task["dependencies"] for task in normalized_tasks)
            if simple_plan:
                phases = []
                for task in normalized_tasks:
                    task.pop("phase_id", None)
                    task.pop("phase", None)
            else:
                self._validate_phase_titles({"phases": phases}, normalized_tasks)
            result["phases"] = phases
            result["milestones"] = phases
        else:
            self._validate_phase_titles(result, normalized_tasks)

        result["goal"] = self._text(result.get("goal") or result.get("mission") or result.get("objective") or request)
        complexity = self._text(result.get("complexity")).lower()
        result["complexity"] = complexity if complexity in {"trivial", "small", "medium", "large"} else self._infer_complexity(normalized_tasks)
        result["work_type"] = self._text(result.get("work_type") or result.get("goal_type")) or "general"
        return result

    def _validate_phase_titles(self, plan: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
        phases = plan.get("phases", plan.get("milestones", []))
        if not isinstance(phases, list):
            return
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            title = self._text(phase.get("title") or phase.get("name"))
            phase_key = self._key(title)
            for task in tasks:
                if self._overlaps(phase_key, self._key(task.get("title"))):
                    raise ProjectPlanValidationError(
                        f"Phase '{title}' substantially repeats task '{task.get('title')}'."
                    )

    def _validate_dependencies(self, tasks: list[dict[str, Any]]) -> None:
        references = {}
        for task in tasks:
            references[self._key(task["id"])] = task["id"]
            references[self._key(task["title"])] = task["id"]
        graph: dict[str, set[str]] = defaultdict(set)
        for task in tasks:
            current = task["id"]
            for dependency in task["dependencies"]:
                resolved = references.get(self._key(dependency))
                if resolved is None:
                    raise ProjectPlanValidationError(
                        f"Task '{task['title']}' depends on missing task '{dependency}'."
                    )
                if resolved == current:
                    raise ProjectPlanValidationError(
                        f"Task '{task['title']}' cannot depend on itself."
                    )
                graph[current].add(resolved)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ProjectPlanValidationError("Project task dependencies contain a cycle.")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in graph.get(task_id, set()):
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task in tasks:
            visit(task["id"])

    @classmethod
    def _normalize_owner(cls, value: Any) -> str:
        owner = cls._text(value).upper().replace(" ", "_").replace("-", "_")
        aliases = {"NOVA": "NOVA", "AI": "NOVA", "ASSISTANT": "NOVA", "USER": "USER", "HUMAN": "USER", "ME": "USER", "COLLABORATIVE": "COLLABORATIVE", "BOTH": "COLLABORATIVE", "SHARED": "COLLABORATIVE"}
        if owner not in aliases:
            raise ProjectPlanValidationError(f"Unsupported action owner '{value}'. Use NOVA, USER, or COLLABORATIVE.")
        return aliases[owner]

    @staticmethod
    def _text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _has_text(value: Any) -> bool:
        return isinstance(value, list) and any(str(item or "").strip() for item in value)

    @classmethod
    def _key(cls, value: Any) -> str:
        text = re.sub(r"[^a-z0-9]+", " ", cls._text(value).lower()).strip()
        return re.sub(r"\s+", " ", text)

    @classmethod
    def _overlaps(cls, left: str, right: str) -> bool:
        if not left or not right:
            return False
        if left == right:
            return True
        left_words = set(left.split())
        right_words = set(right.split())
        if len(left_words) < 3 or len(right_words) < 3:
            return False
        containment = len(left_words & right_words) / min(len(left_words), len(right_words))
        similarity = SequenceMatcher(None, left, right).ratio()
        return similarity >= 0.92 or (containment >= 0.9 and similarity >= 0.82)

    @classmethod
    def _is_meta_task(cls, key: str) -> bool:
        return key in cls.META_TASKS or any(key.startswith(prefix + " ") for prefix in cls.META_TASKS)

    @classmethod
    def _is_generic(cls, value: str) -> bool:
        key = cls._key(value)
        return not key or key in cls.GENERIC_OUTPUTS or key.startswith(("concrete result for ", "the task has produced its expected output"))

    @staticmethod
    def _infer_complexity(tasks: list[dict[str, Any]]) -> str:
        if len(tasks) <= 1:
            return "trivial"
        if len(tasks) <= 3 and not any(task.get("dependencies") for task in tasks):
            return "small"
        if len(tasks) <= 7:
            return "medium"
        return "large"


project_plan_quality_service = ProjectPlanQualityService()
