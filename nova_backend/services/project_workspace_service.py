from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from nova_backend.services.auth_context import get_current_user_id


class ProjectWorkspaceService:

    def __init__(
        self,
        data_dir="data",
    ):
        self.data_dir = Path(data_dir)

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.projects_file = (
            self.data_dir / "nova_projects.json"
        )

        self._ensure_storage()

    def _current_owner_id(
        self,
    ):
        return get_current_user_id()

    def _same_project_owner(
        self,
        project,
    ):
        owner_id = self._current_owner_id()

        if not owner_id:
            return True

        return str(
            project.get("owner_id", "")
        ) == str(owner_id)

    def _ensure_storage(
        self,
    ):
        if not self.projects_file.exists():
            self.projects_file.write_text(
                "[]",
                encoding="utf-8",
            )

    def _load_projects(
        self,
    ):
        try:
            return json.loads(
                self.projects_file.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return []

    def _save_projects(
        self,
        projects,
    ):
        self.projects_file.write_text(
            json.dumps(
                projects,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def list_projects(
        self,
    ):
        return [
            project
            for project in self._load_projects()
            if self._same_project_owner(project)
        ]

    def get_project(
        self,
        project_id,
    ):
        for project in self._load_projects():
            if (
                project.get("id") == project_id
                and self._same_project_owner(project)
            ):
                return project

        return None

    def create_project(
        self,
        name,
        description="",
    ):
        projects = self._load_projects()

        project = {
            "id": f"project_{uuid.uuid4().hex[:12]}",
            "owner_id": self._current_owner_id(),
            "name": str(name or "New Project"),
            "title": str(name or "New Project"),
            "description": str(description or ""),
            "status": "active",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "metadata": {},
            "sessions": [],
            "files": [],
            "tasks": [],
            "notes": [],
            "documents": [],
            "knowledge": [],
"workflows": [],

"brain": {
    "goal": "",
    "decisions": [],
    "blockers": [],
    "next_actions": [],
    "milestones": [],
},

"timeline": [],

"active": True,
        }

        projects.append(project)

        self._save_projects(
            projects
        )

        return project

    def update_project(
        self,
        project_id,
        name=None,
        description=None,
        status=None,
    ):

        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            if name is not None:
                project["name"] = str(
                    name
                )

                project["title"] = str(
                    name
                )

            if description is not None:
                project["description"] = str(
                    description
                )

            if status is not None:
                project["status"] = str(
                    status
                )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return project

        return None

def archive_project(
    self,
    project_id,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        project["status"] = "archived"
        project["active"] = False

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return project

    return None


def restore_project(
    self,
    project_id,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        project["status"] = "active"
        project["active"] = True

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return project

    return None

def add_activity(
    self,
    project_id,
    action,
    details="",
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        activity = {
            "id": str(
                uuid.uuid4()
            ),
            "action": str(
                action
            ),
            "details": str(
                details
            ),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        project.setdefault(
            "timeline",
            [],
        ).append(
            activity
        )

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return activity

    return None

    def get_project_summary(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description"),
            "status": project.get("status"),
            "task_count": len(
                project.get("tasks", [])
            ),
            "file_count": len(
                project.get("files", [])
            ),
            "note_count": len(
                project.get("notes", [])
            ),
            "updated_at": project.get(
                "updated_at",
                "",
            ),
        }

def add_task(
    self,
    project_id,
    title,
    priority="medium",
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        tasks = project.setdefault(
            "tasks",
            [],
        )

        task = {
            "id": str(
                uuid.uuid4()
            ),
            "title": str(
                title or "New Task"
            ),
            "priority": str(
                priority
            ),
            "status": "open",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        tasks.append(
            task
        )

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return task

    return None


def update_task_status(
    self,
    project_id,
    task_id,
    status,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        for task in project.get(
            "tasks",
            [],
        ):
            if task.get("id") == task_id:
                task["status"] = str(
                    status
                )

                project["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                self._save_projects(
                    projects
                )

                return task

    return None

def delete_task(
    self,
    project_id,
    task_id,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        project["tasks"] = [
            task
            for task in project.get(
                "tasks",
                [],
            )
            if task.get("id") != task_id
        ]

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return True

    return False

def delete_file(
    self,
    project_id,
    file_id,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        project["files"] = [
            item
            for item in project.get(
                "files",
                [],
            )
            if item.get("id") != file_id
        ]

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return True

    return False

    def list_notes(
        self,
        project_id,
    ):
        project = self.get_project(project_id)

        if not project:
            return []

        return project.get(
            "notes",
            [],
        )

    def add_note(
        self,
        project_id,
        title,
        content="",
    ):
        projects = self._load_projects()

        for project in projects:
            if project.get("id") != project_id:
                continue

            note = {
                "id": str(uuid.uuid4()),
                "title": title or "Untitled Note",
                "content": content or "",
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            project.setdefault(
                "notes",
                [],
            ).append(note)

            self._save_projects(projects)

            return note

        return None

    def list_notes(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return []

        notes = project.get(
            "notes",
            [],
        )

        return (
            notes
            if isinstance(notes, list)
            else []
        )

    def update_note(
        self,
        project_id,
        note_id,
        title=None,
        content=None,
    ):
        projects = self._load_projects()

        for project in projects:
            if project.get("id") != project_id:
                continue

            for note in project.get("notes", []):
                if note.get("id") == note_id:

                    if title is not None:
                        note["title"] = title

                    if content is not None:
                        note["content"] = content

                    self._save_projects(projects)

                    return note

        return None

    def delete_note(
        self,
        project_id,
        note_id,
    ):
        projects = self._load_projects()

        for project in projects:
            if project.get("id") != project_id:
                continue

            project["notes"] = [
                note
                for note in project.get("notes", [])
                if note.get("id") != note_id
            ]

            self._save_projects(projects)

            return True

        return False

    def set_active_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        for project in projects:
            project["active"] = (
                project.get("id") == project_id
            )

        self._save_projects(projects)

        return self.get_project(project_id)

    def get_active_project(
        self,
    ):
        for project in self._load_projects():
            if project.get("active"):
                return project

        return None

def add_next_action(
    self,
    project_id,
    action,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        brain = project.setdefault(
            "brain",
            {},
        )

        actions = brain.setdefault(
            "next_actions",
            [],
        )

        item = {
            "id": str(
                uuid.uuid4()
            ),
            "action": str(
                action
            ),
            "status": "open",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        actions.append(
            item
        )

        self._save_projects(
            projects
        )

        return item

    return None

def get_project_brain_summary(
    self,
    project_id,
):
    project = self.get_project(
        project_id
    )

    if not project:
        return None

    brain = project.get(
        "brain",
        {},
    )

    return {
        "project_id": project.get(
            "id"
        ),
        "name": project.get(
            "name"
        ),
        "goal": brain.get(
            "goal",
            "",
        ),
        "decisions": brain.get(
            "decisions",
            [],
        ),
        "blockers": brain.get(
            "blockers",
            [],
        ),
        "next_actions": brain.get(
            "next_actions",
            [],
        ),
        "milestones": brain.get(
            "milestones",
            [],
        ),
        "tasks_open": len(
            [
                task
                for task in project.get(
                    "tasks",
                    [],
                )
                if task.get(
                    "status"
                ) == "open"
            ]
        ),
        "files": len(
            project.get(
                "files",
                [],
            )
        ),
        "notes": len(
            project.get(
                "notes",
                [],
            )
        ),
    }

def add_project_decision(
    self,
    project_id,
    decision,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        brain = project.setdefault(
            "brain",
            {},
        )

        decisions = brain.setdefault(
            "decisions",
            [],
        )

        item = {
            "id": str(
                uuid.uuid4()
            ),
            "decision": str(
                decision
            ),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        decisions.append(
            item
        )

        self._save_projects(
            projects
        )

        return item

    return None

def update_project_brain(
    self,
    project_id,
    goal=None,
):
    projects = self._load_projects()

    for project in projects:
        if (
            project.get("id") != project_id
            or not self._same_project_owner(project)
        ):
            continue

        brain = project.setdefault(
            "brain",
            {
                "goal": "",
                "decisions": [],
                "blockers": [],
                "next_actions": [],
                "milestones": [],
            },
        )

        if goal is not None:
            brain["goal"] = str(
                goal
            )

        project["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        self._save_projects(
            projects
        )

        return brain

    return None

def get_project_ai_context(
    self,
    project_id,
):
    project = self.get_project(
        project_id
    )

    if not project:
        return {}

    brain = project.get(
        "brain",
        {},
    )

    return {
        "project": {
            "id": project.get(
                "id"
            ),
            "name": project.get(
                "name",
                "",
            ),
            "description": project.get(
                "description",
                "",
            ),
            "status": project.get(
                "status",
                "",
            ),
        },

        "goal": brain.get(
            "goal",
            "",
        ),

        "decisions": brain.get(
            "decisions",
            [],
        ),

        "blockers": brain.get(
            "blockers",
            [],
        ),

        "next_actions": brain.get(
            "next_actions",
            [],
        ),

        "tasks": project.get(
            "tasks",
            [],
        ),

        "files": [
            file.get(
                "filename",
            )
            for file in project.get(
                "files",
                [],
            )
        ],
    }

def get_project_context(
    self,
    project_id,
):
    project = self.get_project(
        project_id
    )

    if not project:
        return {}

    brain = project.get(
        "brain",
        {},
    )

    return {
        "project_name": project.get(
            "name",
            "",
        ),
        "description": project.get(
            "description",
            "",
        ),
        "goal": brain.get(
            "goal",
            "",
        ),
        "decisions": brain.get(
            "decisions",
            [],
        ),
        "blockers": brain.get(
            "blockers",
            [],
        ),
        "next_actions": brain.get(
            "next_actions",
            [],
        ),
        "tasks": project.get(
            "tasks",
            [],
        ),
        "files": project.get(
            "files",
            [],
        ),
    }