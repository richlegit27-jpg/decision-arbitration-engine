from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ProjectWorkspaceService:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.projects_file = (
            self.data_dir / "nova_projects.json"
        )

        self._ensure_storage()

    def _ensure_storage(self):
        if not self.projects_file.exists():
            self.projects_file.write_text(
                "[]",
                encoding="utf-8",
            )

    def _load_projects(self):
        try:
            return json.loads(
                self.projects_file.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return []

    def _save_projects(self, projects):
        self.projects_file.write_text(
            json.dumps(
                projects,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def create_project(
        self,
        name,
        description="",
    ):
        projects = self._load_projects()

        project = {
            "id": f"project_{uuid.uuid4().hex[:12]}",
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
            "decisions": [],
            "goals": [],
            "deadlines": [],
            "documents": [],
            "workflows": [],
            "knowledge": [],
        }

        projects.append(project)

        self._save_projects(
            projects
        )

        return project

    def list_projects(self):
        return self._load_projects()

    def get_project(
        self,
        project_id,
    ):
        for project in self._load_projects():
            if project.get("id") == project_id:
                return project

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

        tasks = project.get(
            "tasks",
            [],
        )

        files = project.get(
            "files",
            [],
        )

        return {
            "id": project.get("id"),
            "name": project.get("name", ""),
            "description": project.get(
                "description",
                "",
            ),
            "status": project.get(
                "status",
                "active",
            ),
            "task_count": len(tasks),
            "file_count": len(files),
            "last_activity": project.get(
                "updated_at",
                "",
            ),
            "next_move": project.get(
                "next_move",
                "",
            ),
        }

    def add_task(
        self,
        project_id,
        title,
        priority="medium",
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        tasks = project.setdefault(
            "tasks",
            []
        )

        task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "status": "open",
            "priority": priority,
        }

        tasks.append(task)

        self.save_project(
            project
        )

        return task


    def update_task_status(
        self,
        project_id,
        task_id,
        status,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        for task in project.get(
            "tasks",
            []
        ):
            if task.get("id") == task_id:
                task["status"] = status

                self.save_project(
                    project
                )

                return task

        return None