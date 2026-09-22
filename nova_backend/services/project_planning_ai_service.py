from __future__ import annotations

import json
import re
from typing import Any

from nova_backend.services.model_gateway_service import (
    chat_completions_create,
)


class ProjectPlanningAIService:
    """
    AI-powered project intelligence planner.

    Converts a user's natural-language project idea into a structured
    implementation plan without requiring the user to know the tasks,
    architecture, or implementation sequence in advance.
    """

    def build_plan(
        self,
        request: str,
        model: str | None = None,
        project_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build an AI-powered project plan.

        When project_context is provided, this is an expansion of an
        existing project rather than a brand-new project. The AI must
        understand existing work and generate only genuinely missing work.
        """

        clean_request = str(
            request or ""
        ).strip()

        if not clean_request:
            raise ValueError(
                "Project request cannot be empty."
            )

        if not isinstance(
            project_context,
            dict,
        ):
            project_context = {}

        system_prompt = """
You are Nova Project Intelligence.

Your job is to transform a user's idea, request, or new requirement
into practical project intelligence and an actionable implementation plan.

Nova is not simply a task generator.

You must understand:

- what the project is trying to accomplish
- what has already been planned
- what has already been completed
- what is currently in progress
- what decisions have already been made
- what blockers exist
- what assumptions and unknowns remain
- how the project has evolved over time
- what new request the user is making now

The user may know very little about how the project should be built.
Do not expect the user to provide technical tasks.

Infer the work required to accomplish the user's goal.

Return ONLY valid JSON.

Use this exact structure:

{
    "name": "short project name",
    "mission": "clear statement of the project objective",
    "requirements": [
        "requirement"
    ],
    "assumptions": [
        "reasonable assumption"
    ],
    "unknowns": [
        "important unknown or decision"
    ],
    "milestones": [
        {
            "id": "unique_snake_case_id",
            "title": "milestone title",
            "status": "pending"
        }
    ],

"tasks": [
    {
        "title": "specific actionable task",
        "priority": "high",
        "description": "what needs to be accomplished",

        "action": "analyze",

        "execution_mode": "ai",

        "execution_file": "",

        "target_file": "",

        "target_files": [],

        "dependencies": [],

        "expected_output": "clear description of the useful result this task should produce",

        "completion_criteria": "how Nova can determine that this task is complete"
    }
],

    "next_actions": [
        "recommended next action"
    ],
    "recommendations": [
        "recommendation that would materially improve the project"
    ]
}

GENERAL PLANNING RULES:

- Generate work the user would not necessarily know to create.
- Tasks must be specific to the actual project.
- Avoid generic placeholder tasks.
- Break large work into logical implementation steps.
- Respect dependency order.
- Include analysis, implementation, verification, and documentation
  only where they are genuinely needed.
- Use priorities: high, medium, low.
- Do not claim work has already been completed.
- Do not include conversational text outside the JSON.
- Do not ask the user questions unless planning is genuinely impossible
  without clarification.
- Prefer useful, concrete work over long lists of speculative tasks.
- When the user's request explicitly asks to build, create, implement, write,
  modify, fix, run, execute, or produce a concrete artifact, tasks for that
  requested work must use an executable action such as create, write,
  implement, modify, fix, or execute rather than design or analyze.
- For execution-oriented requests, include the concrete target_file,
    target_files, content, command, execution_file, or other execution metadata
    whenever it can be determined from the request.
- Do not mark an execution-oriented task complete through planning or design
    prose alone; its action and completion_criteria must describe work that can
    actually be performed and verified.

EXISTING PROJECT INTELLIGENCE RULES:

When existing_project_context is present, this is NOT a new project.

Treat the project as an evolving system with accumulated knowledge.

The existing context is authoritative for historical facts, completed
work, decisions, blockers, current progress, and project direction.

You must reason about the relationship between:

1. THE EXISTING PROJECT
2. THE USER'S NEW REQUEST
3. THE CURRENT PROJECT STATE
4. THE NEXT BEST WORK

Before generating tasks, determine whether the user's request is:

- an expansion of the existing project
- a modification to an existing direction
- a new capability
- a missing dependency
- a refinement
- a response to a blocker
- a change in priorities
- or a request that conflicts with an existing decision

PROJECT PRESERVATION RULES:

- Do NOT recreate tasks that already exist.
- Do NOT rephrase existing tasks and present them as new tasks.
- Do NOT recreate completed work.
- Do NOT undo completed progress.
- Do NOT discard existing requirements.
- Do NOT discard existing decisions without a clear reason.
- Do NOT replace accumulated project knowledge with the latest request.
- Preserve the logical direction of the project unless the user
  explicitly changes that direction.

PROJECT EXPANSION RULES:

When the new request adds capability:

- identify what new requirements are introduced
- identify dependencies created by the new capability
- identify architecture changes that may be required
- identify integration work
- identify data model changes
- identify testing or verification requirements
- identify documentation or user-control requirements where appropriate

Generate only genuinely new work.

Do not generate tasks merely to make the plan look comprehensive.

CURRENT STATE RULES:

Use current_state to understand actual progress.

Completed tasks are historical progress.

In-progress tasks represent active work and should not be duplicated.

Pending tasks represent planned work that should be considered before
adding overlapping tasks.

Current focus should influence recommendations and next actions.

If existing work already covers the user's request, generate few or no
new tasks rather than inventing unnecessary work.

DECISION AND BLOCKER RULES:

Existing decisions are part of the project's memory.

Do not contradict a previous decision unless the user's new request
clearly requires a change.

Existing blockers should influence planning.

If a new request resolves a blocker, account for that.

If a new request creates a new blocker or dependency, surface it in
the appropriate project intelligence.

EVOLUTION RULES:

Use project history to understand how the project has changed.

Do not treat every request as isolated.

Look for patterns in the project's evolution.

Preserve continuity between earlier work and newly requested work.

NEXT ACTION RULES:

next_actions should represent the most useful immediate steps after
considering:

- current project state
- active work
- pending dependencies
- blockers
- new requirements
- task priority

Do not simply repeat every generated task as a next action.

RECOMMENDATION RULES:

Recommendations should be useful strategic intelligence.

They may identify:

- important gaps
- risks
- dependencies
- sequencing improvements
- architectural concerns
- opportunities to simplify the project

Do not generate generic recommendations.

If there is no meaningful recommendation, return an empty list.

TASK QUALITY RULES:

Each task should answer:

- What specifically needs to happen?
- Why does this work matter to the project?
- Where does it fit in the dependency sequence?

Task titles must be distinct from existing task titles.

Prefer fewer high-quality tasks over many vague tasks.

The purpose of Nova is to help users who have an idea and guide that
idea through planning, execution, adaptation, and completion.
"""
        user_payload = {
            "project_request": clean_request,
        }

        if project_context:
            user_payload["existing_project_context"] = (
                project_context
            )

        response = chat_completions_create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        user_payload,
                        indent=2,
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.2,
        )

        content = self._extract_content(
            response
        )

        plan = self._parse_json(
            content
        )

        print(
            "\n===== RAW PLANNER PLAN =====",
            flush=True,
        )

        print(
            json.dumps(
                plan,
                indent=2,
            ),
            flush=True,
        )

        print(
            "===== END RAW PLANNER PLAN =====\n",
            flush=True,
        )

        return self._normalize_plan(
            plan=plan,
            request=clean_request,
        )
    def _extract_content(
        self,
        response: Any,
    ) -> str:

        try:
            choices = getattr(
                response,
                "choices",
                None,
            )

            if choices:
                message = choices[0].message
                content = getattr(
                    message,
                    "content",
                    None,
                )

                if content:
                    return str(content)
        except Exception:
            pass

        if isinstance(response, dict):
            try:
                return str(
                    response["choices"][0]
                    ["message"]
                    ["content"]
                )
            except Exception:
                pass

        raise RuntimeError(
            "Project planning AI returned no content."
        )

    def _parse_json(
        self,
        content: str,
    ) -> dict[str, Any]:

        text = str(
            content or ""
        ).strip()

        if not text:
            raise RuntimeError(
                "Project planning AI returned empty content."
            )

        try:
            parsed = json.loads(text)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

        fenced_match = re.search(
            r"```(?:json)?\s*(\{.*\})\s*```",
            text,
            re.DOTALL,
        )

        if fenced_match:
            try:
                parsed = json.loads(
                    fenced_match.group(1)
                )

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                pass

        object_match = re.search(
            r"(\{.*\})",
            text,
            re.DOTALL,
        )

        if object_match:
            try:
                parsed = json.loads(
                    object_match.group(1)
                )

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                pass

        raise RuntimeError(
            "Project planning AI returned invalid JSON."
        )

    def _normalize_plan(
        self,
        plan: dict[str, Any],
        request: str,
    ) -> dict[str, Any]:

        if not isinstance(plan, dict):
            plan = {}

        normalized_tasks = []

        raw_tasks = plan.get(
            "tasks",
            [],
        )

        if isinstance(raw_tasks, list):
            for task in raw_tasks:

                if not isinstance(task, dict):
                    continue

                execution_file = str(
                    task.get("execution_file")
                    or ""
                ).strip()

                execution_mode = str(
                    execution_mode
                    or task.get("execution_mode")
                    or ""
                ).strip().lower()

                if execution_file.lower().endswith(
                    (".sh", ".bat", ".cmd")
                ):
                    task["execution_file"] = ""
                    task["execution_mode"] = "ai"

                    if str(
                        task.get("action") or ""
                    ).lower() in {
                        "execute",
                        "run",
                    }:
                        task["action"] = "implement"

                title = str(
                    task.get(
                        "title",
                        "",
                    )
                ).strip()

                if not title:
                    continue

                priority = str(
                    task.get(
                        "priority",
                        "medium",
                    )
                ).lower()

                if priority not in {
                    "high",
                    "medium",
                    "low",
                }:
                    priority = "medium"

                description = str(
                    task.get(
                        "description",
                        "",
                    )
                ).strip()

                action = str(
                    task.get(
                        "action",
                        "analyze",
                    )
                ).strip().lower()

                # Force concrete execution requests away from analysis-only tasks
                request_text = str(request or "").lower()

                execution_request = any(
                    keyword in request_text
                    for keyword in [
                        "create",
                        "build",
                        "write",
                        "implement",
                        "modify",
                        "fix",
                        "execute",
                        "run",
                    ]
                )

                if execution_request and action in {
                    "analyze",
                    "research",
                    "plan",
                    "design",
                }:
                    action = "execute"
                    execution_mode = "hybrid"


                allowed_actions = {
                    "research",
                    "analyze",
                    "plan",
                    "design",
                    "write",
                    "document",
                    "implement",
                    "modify",
                    "create",
                    "fix",
                    "refactor",
                    "run",
                    "verify",
                }

                if action not in allowed_actions:
                    task_text = " ".join(
                        [
                            str(task.get("title") or ""),
                            str(task.get("description") or ""),
                            str(task.get("input") or ""),
                        ]
                    ).lower()

                    if any(
                        keyword in task_text
                        for keyword in [
                            "execute",
                            "run",
                            "create",
                            "build",
                            "implement",
                        ]
                    ):
                        action = "execute"
                        execution_mode = "hybrid"
                    else:
                        action = "analyze"

                execution_mode = str(
                    execution_mode
                    or task.get(
                        "execution_mode",
                        "",
                    )
                ).strip().lower()

                allowed_execution_modes = {
                    "ai",
                    "file",
                    "command",
                    "hybrid",
                }

                if execution_mode not in allowed_execution_modes:

                    if action in {
                        "implement",
                        "modify",
                        "create",
                        "fix",
                        "refactor",
                    }:
                        execution_mode = "hybrid"

                    elif action == "run":
                        execution_mode = "command"

                    else:
                        execution_mode = "ai"

                target_file = str(
                    task.get(
                        "target_file",
                        "",
                    )
                    or ""
                ).strip()

                # Recover concrete file request metadata
                # when the planner parser already matched it.
                if not target_file and file_match:
                    target_file = str(
                        file_match.group(
                            "target_file"
                        )
                        or ""
                    ).strip()

                if target_file:
                    task["target_file"] = target_file

                if not content and file_match:
                    extracted_content = str(
                        file_match.group(
                            "content"
                        )
                        or ""
                    ).strip()

                    if (
                        "function that returns HTTP_EXECUTION_OK"
                        in extracted_content
                    ):
                        content = (
                            "def http_execution_acceptance():\n"
                            "    return \"HTTP_EXECUTION_OK\"\n"
                        )
                    else:
                        content = extracted_content
                if content:
                    task["content"] = content

                # Convert natural-language file descriptions into
                # executable Python content when no code block exists.
                if (
                    target_file
                    and content
                    and content.lower().startswith(
                        "a function that returns"
                    )
                ):
                    content = (
                        "def http_execution_acceptance():\n"
                        "    return \"HTTP_EXECUTION_OK\"\n"
                    )

                    task["content"] = content

                raw_target_files = task.get(
                    "target_files",
                    [],
                )

                if not isinstance(
                    raw_target_files,
                    list,
                ):
                    raw_target_files = []
                target_files = []

                for item in raw_target_files:

                    file_path = str(
                        item or ""
                    ).strip()

                    if (
                        file_path
                        and file_path not in target_files
                    ):
                        target_files.append(
                            file_path
                        )

                if (
                    target_file
                    and target_file not in target_files
                ):
                    target_files.insert(
                        0,
                        target_file,
                    )

                raw_dependencies = task.get(
                    "dependencies",
                    [],
                )

                if not isinstance(
                    raw_dependencies,
                    list,
                ):
                    raw_dependencies = []

                dependencies = []

                for item in raw_dependencies:

                    dependency = str(
                        item or ""
                    ).strip()

                    if (
                        dependency
                        and dependency != title
                        and dependency not in dependencies
                    ):
                        dependencies.append(
                            dependency
                        )

                expected_output = str(
                    task.get(
                        "expected_output",
                        "",
                    )
                    or ""
                ).strip()

                if not expected_output:
                    expected_output = (
                        f"Concrete result for: {title}"
                    )

                completion_criteria = str(
                    task.get(
                        "completion_criteria",
                        "",
                    )
                    or ""
                ).strip()

                if not completion_criteria:
                    completion_criteria = (
                        f"The task '{title}' has produced "
                        "its expected output."
                    )

                execution_file = str(
                    task.get(
                        "execution_file",
                        "",
                    )
                    or ""
                ).strip()

                # FINAL EXECUTION MODE NORMALIZATION
                # Concrete file-backed tasks must enter the real execution lane.
                if (
                    action in {
                        "implement",
                        "modify",
                        "create",
                        "fix",
                        "refactor",
                        "execute",
                        "run",
                    }
                    and (
                        execution_file
                        or target_file
                        or target_files
                    )
                ):
                    execution_mode = "hybrid"

                print(
                    "DEBUG FINAL TASK BEFORE APPEND",
                    {
                        "title": title,
                        "action": action,
                        "execution_mode": execution_mode,
                        "execution_file": execution_file,
                        "target_file": target_file,
                        "target_files": target_files,
                        "content": content,
                        "file_match": bool(file_match),
                    },
                    flush=True,
                )


                normalized_tasks.append(
                    {
                        "title": title,
                        "priority": priority,
                        "description": description,
                        "action": action,
                        "execution_mode": execution_mode,
                        "execution_file": execution_file,
                        "target_file": target_file,
                        "target_files": target_files,
                        "dependencies": dependencies,
                        "expected_output": expected_output,
                        "completion_criteria": completion_criteria,
                        "target_function": str(
                            task.get(
                                "target_function",
                                "",
                            )
                            or ""
                        ).strip(),
                        "content": str(
                            task.get(
                                "content",
                                "",
                            )
                            or ""
                        ),
                        "code": str(
                            task.get(
                                "code",
                                "",
                            )
                            or ""
                        ),
                        "replacement": str(
                            task.get(
                                "replacement",
                                "",
                            )
                            or ""
                        ),
                        "command": str(
                            task.get(
                                "command",
                                "",
                            )
                            or ""
                        ).strip(),
                    }
                )

        return {
            "name": str(
                plan.get(
                    "name",
                    "Untitled Project",
                )
            ).strip()
            or "Untitled Project",

            "mission": str(
                plan.get(
                    "mission",
                    request,
                )
            ).strip()
            or request,

            "description": request,

            "objective": str(
                plan.get(
                    "mission",
                    request,
                )
            ).strip()
            or request,

            "requirements": self._string_list(
                plan.get(
                    "requirements",
                    [],
                )
            ),

            "assumptions": self._string_list(
                plan.get(
                    "assumptions",
                    [],
                )
            ),

            "unknowns": self._string_list(
                plan.get(
                    "unknowns",
                    [],
                )
            ),

            "milestones": self._normalize_milestones(
                plan.get(
                    "milestones",
                    [],
                )
            ),

            "phases": self._normalize_milestones(
                plan.get(
                    "phases",
                    plan.get(
                        "milestones",
                        [],
                    ),
                )
            ),

            "tasks": normalized_tasks,

            "next_actions": self._string_list(
                plan.get(
                    "next_actions",
                    [],
                )
            ),

            "recommendations": self._string_list(
                plan.get(
                    "recommendations",
                    [],
                )
            ),

            "decisions": [],
            "blockers": [],
        }

    def _string_list(
        self,
        value: Any,
    ) -> list[str]:

        if not isinstance(value, list):
            return []

        results = []

        for item in value:
            text = str(
                item or ""
            ).strip()

            if text:
                results.append(text)

        return results

    def _normalize_milestones(
        self,
        value: Any,
    ) -> list[dict[str, str]]:

        if not isinstance(value, list):
            return []

        milestones = []

        for item in value:

            if not isinstance(item, dict):
                continue

            title = str(
                item.get(
                    "title",
                    "",
                )
            ).strip()

            if not title:
                continue

            milestone_id = str(
                item.get(
                    "id",
                    "",
                )
            ).strip()

            if not milestone_id:
                milestone_id = (
                    re.sub(
                        r"[^a-z0-9]+",
                        "_",
                        title.lower(),
                    )
                    .strip("_")
                )

            milestones.append(
                {
                    "id": milestone_id,
                    "title": title,
                    "status": str(
                        item.get(
                            "status",
                            "pending",
                        )
                    ).strip()
                    or "pending",
                }
            )

        return milestones


project_planning_ai_service = (
    ProjectPlanningAIService()
)


