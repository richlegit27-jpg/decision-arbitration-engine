from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
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

        # --------------------------------------------------------------
        # EXISTING PROJECT CONTEXT
        #
        # Load an existing project before AI planning so Nova understands
        # existing tasks, progress, decisions, blockers, and next actions.
        # --------------------------------------------------------------

        project = None
        project_context = {}

        if project_id:

            project = (
                self.project_workspace_service.get_project(
                    project_id
                )
            )

            if project:

                project_context = (
                    self.project_workspace_service.get_project_context(
                        project_id
                    )
                )

                if not isinstance(
                    project_context,
                    dict,
                ):
                    project_context = {}

        # --------------------------------------------------------------
        # PROJECT INTELLIGENCE
        # --------------------------------------------------------------

        plan = self._build_project_plan(
            clean_request,
            project_context=project_context,
        )

        # --------------------------------------------------------------
        # PROJECT PERSISTENCE
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # TASK MERGE
        #
        # Never destroy existing project progress when Nova rebuilds or
        # expands a project.
        #
        # Existing tasks remain authoritative. The AI plan can add new
        # work, but completed and in-progress work must survive.
        # --------------------------------------------------------------

        existing_tasks = project.get(
            "tasks",
            [],
        )

        existing_titles = set()

        for existing_task in existing_tasks:

            if not isinstance(
                existing_task,
                dict,
            ):
                continue

            existing_title = str(
                existing_task.get(
                    "title",
                    "",
                )
            ).strip().lower()

            if existing_title:
                existing_titles.add(
                    existing_title
                )

        created_tasks = []

        skipped_existing_tasks = []

        for task_spec in plan.get(
            "tasks",
            [],
        ):

            if not isinstance(
                task_spec,
                dict,
            ):
                continue

            task_title = str(
                task_spec.get(
                    "title",
                    "New Task",
                )
            ).strip()

            if not task_title:
                continue

            normalized_title = (
                task_title.lower()
            )

            # Do not duplicate work that already exists in the project.
            if normalized_title in existing_titles:

                skipped_existing_tasks.append(
                    task_title
                )

                continue

            task_action = str(
                task_spec.get(
                    "action",
                    "",
                )
            ).strip().lower()

            target_file = str(
                task_spec.get(
                    "target_file",
                    "",
                )
            ).strip()

            task_description = str(
                task_spec.get(
                    "description",
                    "",
                )
            ).strip()

            # ----------------------------------------------------------
            # TARGET FILE RESOLUTION
            #
            # The planner is authoritative for explicit target files.
            # Do not invent filenames here based on keywords. If Nova
            # does not have a concrete file target, the execution layer
            # will treat this as a general AI task rather than forcing
            # a fake file implementation.
            # ----------------------------------------------------------

            if not target_file:

                task_text = (
                    task_title
                    + " "
                    + task_description
                )

                file_match = re.search(
                    r"\b[\w./\\-]+\.(?:py|md|txt|json|js|html|css|yaml|yml)\b",
                    task_text,
                    flags=re.IGNORECASE,
                )

                if file_match:
                    target_file = (
                        file_match.group(0)
                    )

            created_task = (
                self.project_workspace_service.add_task(
                    project_id=resolved_project_id,
                    title=task_title,
                    priority=task_spec.get(
                        "priority",
                        "medium",
                    ),
                    description=task_description,
                    action=task_action,

                    execution_mode=task_spec.get(
                        "execution_mode",
                        "",
                    ),

                    target_file=target_file,

                    target_files=task_spec.get(
                        "target_files",
                        [],
                    ),

                    target_function=task_spec.get(
                        "target_function",
                        "",
                    ),

                    dependencies=task_spec.get(
                        "dependencies",
                        [],
                    ),

                    expected_output=task_spec.get(
                        "expected_output",
                        "",
                    ),

                    completion_criteria=task_spec.get(
                        "completion_criteria",
                        [],
                    ),

                    content=task_spec.get(
                        "content",
                        "",
                    ),

                    code=task_spec.get(
                        "code",
                        "",
                    ),

                    replacement=task_spec.get(
                        "replacement",
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

                existing_titles.add(
                    normalized_title
                )

        if skipped_existing_tasks:

            print(
                "[NOVA PROJECT BUILDER] "
                f"Preserved {len(skipped_existing_tasks)} "
                "existing matching tasks.",
                flush=True,
            )

        if created_tasks:

            print(
                "[NOVA PROJECT BUILDER] "
                f"Added {len(created_tasks)} new tasks.",
                flush=True,
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

                    target_file = str(
                        task.get(
                            "target_file",
                            "",
                        )
                        or ""
                    ).strip()

                    if not target_file:

                        task_text = " ".join(
                            [
                                str(
                                    task.get(
                                        "title",
                                        "",
                                    )
                                    or ""
                                ),
                                str(
                                    task.get(
                                        "description",
                                        "",
                                    )
                                    or ""
                                ),
                            ]
                        )

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




