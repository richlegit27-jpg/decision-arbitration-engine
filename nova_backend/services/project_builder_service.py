from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import re


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

    def build_project_from_request(
        self,
        user_text: str | None = None,
        owner_id: str | None = None,
        project_id: str | None = None,
        request: str | None = None,
    ) -> dict[str, Any]:
        """
        Build or update a persistent Nova project from a natural-language
        request.

        Flow:
        1. Build the project plan.
        2. Create or update the persistent project.
        3. Create persistent tasks from the plan.
        4. Update the project brain.
        5. Return the final project and plan.
        """

        clean_request = str(
            user_text
            or request
            or ""
        ).strip()

        if not clean_request:
            raise ValueError(
                "Project request cannot be empty."
            )

        plan = self._build_project_plan(
            clean_request
        )

        project = None

        if project_id:
            project = (
                self.project_workspace_service.get_project(
                    project_id
                )
            )

            if project:
                project = (
                    self.project_workspace_service.update_project(
                        project_id=project_id,
                        name=plan.get("name"),
                        description=plan.get("description"),
                    )
                )

        if not project:
            project = (
                self.project_workspace_service.create_project(
                    name=plan.get("name"),
                    description=plan.get("description"),
                )
            )

        if not project:
            raise RuntimeError(
                "Failed to create project."
            )

        resolved_project_id = project.get("id")

        if not resolved_project_id:
            raise RuntimeError(
                "Created project does not have an ID."
            )

        existing_tasks = project.get(
            "tasks",
            [],
        )

        for task in existing_tasks:
            task_id = task.get("id")

            if task_id:
                self.project_workspace_service.delete_task(
                    project_id=resolved_project_id,
                    task_id=task_id,
                )

        created_tasks = []

        for task_spec in plan.get(
            "tasks",
            [],
        ):
            if not isinstance(
                task_spec,
                dict,
            ):
                continue

            created_task = (
                self.project_workspace_service.add_task(
                    project_id=resolved_project_id,
                    title=task_spec.get(
                        "title",
                        "New Task",
                    ),
                    priority=task_spec.get(
                        "priority",
                        "medium",
                    ),
                    description=task_spec.get(
                        "description",
                        "",
                    ),
                    action=task_spec.get(
                        "action",
                        "",
                    ),
                    target_file=task_spec.get(
                        "target_file",
                        "",
                    ),
                    content=task_spec.get(
                        "content",
                        "",
                    ),
                    command=task_spec.get(
                        "command",
                        "",
                    ),
                )
            )

            if created_task:
                created_tasks.append(
                    created_task
                )

        self._update_project_brain(
            project_id=resolved_project_id,
            plan=plan,
        )

        self.project_workspace_service.add_activity(
            project_id=resolved_project_id,
            action="project_built",
            details=clean_request,
        )

        final_project = (
            self.project_workspace_service.get_project(
                resolved_project_id
            )
        )

        return {
            "project_id": resolved_project_id,
            "project": final_project,
            "plan": plan,
            "tasks": created_tasks,
        }

    def _build_project_plan(
        self,
        request: str,
    ) -> dict[str, Any]:

        name = self._project_name(
            request
        )

        requirements = self._extract_requirements(
            request
        )

        assumptions = self._build_assumptions(
            request
        )

        unknowns = self._build_unknowns(
            request
        )

        generated_tasks = (
            self._build_implementation_tasks(
                request=request,
            )
        )

        tasks = [
            {
                "title": "Define project requirements",
                "priority": "high",
                "description": (
                    "Analyze the project request and identify "
                    "functional requirements, constraints, "
                    "assumptions, and unknowns."
                ),
                "action": "analyze",
            },
            {
                "title": "Design implementation plan",
                "priority": "high",
                "description": (
                    "Define the architecture, components, "
                    "implementation sequence, and dependencies."
                ),
                "action": "plan",
            },
        ]

        tasks.extend(
            generated_tasks
        )

        tasks.append(
            {
                "title": "Verify the result",
                "priority": "high",
                "description": (
                    "Inspect the completed project and verify "
                    "that the requested objective was achieved."
                ),
                "action": "verify",
            }
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
            "description": request,
            "objective": request,
            "requirements": requirements,
            "assumptions": assumptions,
            "unknowns": unknowns,
            "milestones": milestones,
            "tasks": tasks,
            "decisions": [],
            "blockers": [],
            "next_actions": [
                "Define project requirements",
            ],
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

        projects = (
            self.project_workspace_service._load_projects()
        )

        if not isinstance(
            projects,
            list,
        ):
            return

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

            brain["goal"] = plan.get(
                "objective",
                "",
            )

            brain["requirements"] = plan.get(
                "requirements",
                [],
            )

            brain["assumptions"] = plan.get(
                "assumptions",
                [],
            )

            brain["unknowns"] = plan.get(
                "unknowns",
                [],
            )

            brain["milestones"] = plan.get(
                "milestones",
                [],
            )

            brain["decisions"] = plan.get(
                "decisions",
                [],
            )

            brain["blockers"] = plan.get(
                "blockers",
                [],
            )

            brain["next_actions"] = plan.get(
                "next_actions",
                [],
            )

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