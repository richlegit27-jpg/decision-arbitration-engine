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
            data = json.loads(
                self.projects_file.read_text(
                    encoding="utf-8",
                )
            )

            if not isinstance(data, list):
                return []

            changed = False

            for project in data:
                if not isinstance(project, dict):
                    continue

                if not isinstance(
                    project.get("execution"),
                    dict,
                ):
                    project["execution"] = (
                        self._default_execution_state()
                    )

                    changed = True

            if changed:
                self._save_projects(
                    data
                )

            return data

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

    def _default_execution_state(
        self,
    ):
        return {
            "status": "idle",
            "current_task_id": None,
            "current_step": None,
            "queue": [],
            "last_action": None,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def _default_execution_state(
        self,
    ):
        return {
            "status": "idle",
            "current_task_id": None,
            "current_step": None,
            "queue": [],
            "last_action": None,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

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

        now = datetime.now(
            timezone.utc
        ).isoformat()

        for existing_project in projects:
            if self._same_project_owner(
                existing_project
            ):
                existing_project["active"] = False

        if isinstance(
            name,
            (dict, list, tuple, set),
        ):
            return None

        clean_name = str(
            name or "New Project"
        ).strip()

        if not clean_name:
            clean_name = "New Project"

        project = {
            "id": f"project_{uuid.uuid4().hex[:12]}",
            "owner_id": self._current_owner_id(),
            "name": clean_name,
            "title": clean_name,
            "description": str(
                description or ""
            ),
            "status": "active",
            "created_at": now,
            "updated_at": now,
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

        projects.append(
            project
        )

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
                if isinstance(
                    name,
                    (dict, list, tuple, set),
                ):
                    return None

                clean_name = str(
                    name
                ).strip()

                if not clean_name:
                    return None

                project["name"] = clean_name
                project["title"] = clean_name

            if description is not None:
                if isinstance(
                    description,
                    (dict, list, tuple, set),
                ):
                    return None

                project["description"] = str(
                    description
                ).strip()

            if status is not None:
                if isinstance(
                    status,
                    (dict, list, tuple, set),
                ):
                    return None

                project["status"] = str(
                    status
                ).strip()

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return project

        return None

    def get_execution_state(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        execution = project.get(
            "execution"
        )

        if not isinstance(
            execution,
            dict,
        ):
            execution = self._default_execution_state()

            project["execution"] = execution

            projects = self._load_projects()

            for index, stored_project in enumerate(
                projects
            ):
                if (
                    stored_project.get("id")
                    == project_id
                ):
                    projects[index] = project
                    break

            self._save_projects(
                projects
            )

        return execution

    def update_execution_state(
        self,
        project_id,
        status=None,
        current_task_id=None,
        current_step=None,
        queue=None,
        last_action=None,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(
                    project
                )
            ):
                continue

            execution = project.get(
                "execution"
            )

            if not isinstance(
                execution,
                dict,
            ):
                execution = (
                    self._default_execution_state()
                )

            if status is not None:
                execution["status"] = str(
                    status
                ).strip()

            if current_task_id is not None:
                execution[
                    "current_task_id"
                ] = current_task_id

            if current_step is not None:
                execution[
                    "current_step"
                ] = current_step

            if queue is not None:
                execution["queue"] = (
                    queue
                    if isinstance(queue, list)
                    else []
                )

            if last_action is not None:
                execution[
                    "last_action"
                ] = str(
                    last_action
                ).strip()

            execution["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            project["execution"] = execution
            project["updated_at"] = (
                execution["updated_at"]
            )

            self._save_projects(
                projects
            )

            return execution

        return None

    def reset_execution_state(
        self,
        project_id,
    ):
        execution = (
            self._default_execution_state()
        )

        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(
                    project
                )
            ):
                continue

            project["execution"] = execution
            project["updated_at"] = (
                execution["updated_at"]
            )

            self._save_projects(
                projects
            )

            return execution

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

            original = project.get(
                "tasks",
                [],
            )

            project["tasks"] = [
                task
                for task in original
                if task.get("id") != task_id
            ]

            if len(project["tasks"]) == len(original):
                return False

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return True

        return False

    def list_files(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return []

        files = project.get(
            "files",
            [],
        )

        return (
            files
            if isinstance(files, list)
            else []
        )

    def add_file(
        self,
        project_id,
        filename,
        path="",
        size=0,
        mime_type="",
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            files = project.setdefault(
                "files",
                [],
            )

            file_record = {
                "id": str(
                    uuid.uuid4()
                ),
                "filename": str(
                    filename or "Untitled file"
                ),
                "name": str(
                    filename or "Untitled file"
                ),
                "path": str(
                    path or ""
                ),
                "size": int(
                    size or 0
                ),
                "mime_type": str(
                    mime_type or ""
                ),
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            files.append(
                file_record
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return file_record

        return None

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

            files = project.get(
                "files",
                [],
            )

            original_count = len(
                files
            )

            project["files"] = [
                item
                for item in files
                if item.get("id") != file_id
            ]

            if len(project["files"]) == original_count:
                return False

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

    def add_note(
        self,
        project_id,
        title,
        content="",
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            notes = project.setdefault(
                "notes",
                [],
            )

            note = {
                "id": str(
                    uuid.uuid4()
                ),
                "title": str(
                    title or "Untitled Note"
                ).strip(),
                "content": str(
                    content or ""
                ),
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            notes.append(
                note
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return note

        return None

    def update_note(
        self,
        project_id,
        note_id,
        title=None,
        content=None,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            for note in project.get(
                "notes",
                [],
            ):
                if note.get("id") != note_id:
                    continue

                if title is not None:
                    note["title"] = str(
                        title
                    ).strip()

                if content is not None:
                    note["content"] = str(
                        content
                    )

                note["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                project["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                self._save_projects(
                    projects
                )

                return note

        return None

    def delete_note(
        self,
        project_id,
        note_id,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            notes = project.get(
                "notes",
                [],
            )

            original_count = len(
                notes
            )

            project["notes"] = [
                note
                for note in notes
                if note.get("id") != note_id
            ]

            if len(project["notes"]) == original_count:
                return False

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return True

        return False

    def set_active_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        target_project = None

        for project in projects:
            if not self._same_project_owner(project):
                continue

            if project.get("id") == project_id:
                target_project = project

        if target_project is None:
            return None

        now = datetime.now(
            timezone.utc
        ).isoformat()

        for project in projects:
            if not self._same_project_owner(project):
                continue

            project["active"] = (
                project.get("id") == project_id
            )

            if project.get("id") == project_id:
                project["status"] = "active"

            project["updated_at"] = now

        self._save_projects(
            projects
        )

        return target_project

    def get_active_project(
        self,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("active")
                and self._same_project_owner(project)
            ):
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
                    file.get(
                        "name",
                        "",
                    ),
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

    def delete_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        if not isinstance(
            projects,
            list,
        ):
            return None

        project = None

        for item in projects:
            if (
                item.get("id") == project_id
                and self._same_project_owner(item)
            ):
                project = item
                break

        if not project:
            return None

        projects = [
            item
            for item in projects
            if item.get("id") != project_id
        ]

        self._save_projects(
            projects
        )

        return project