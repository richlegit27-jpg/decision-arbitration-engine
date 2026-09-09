from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from nova_backend.services.auth_context import get_current_user_id


class PersistentProjectRegistry:

    def __init__(
        self,
        base_dir: Path | None = None,
    ):

        if base_dir is None:

            base_dir = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

        self.base_dir = Path(base_dir)

        self.data_dir = (
            self.base_dir / "data"
        )

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.file_path = (
            self.data_dir
            / "nova_projects.json"
        )


    def _current_user_id(self):

        user_id = get_current_user_id()

        if not user_id:

            return None

        return str(user_id)


    def _load(self):

        if not self.file_path.exists():

            return {
                "projects": [],
            }

        try:

            raw = self.file_path.read_text(
                encoding="utf-8",
            )

            data = json.loads(raw)

            if not isinstance(data, dict):

                return {
                    "projects": [],
                }

            projects = data.get(
                "projects",
                [],
            )

            if not isinstance(projects, list):

                projects = []

            return {
                "projects": projects,
            }

        except Exception:

            return {
                "projects": [],
            }


    def _save(
        self,
        data,
    ):

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.file_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


    def _same_owner(
        self,
        project,
    ):

        if not isinstance(project, dict):

            return False

        current_user_id = (
            self._current_user_id()
        )

        if not current_user_id:

            return False

        return (
            str(
                project.get(
                    "user_id",
                    "",
                )
            )
            == current_user_id
        )


    def list_projects(self):

        data = self._load()

        projects = data.get(
            "projects",
            [],
        )

        return [
            project
            for project in projects
            if self._same_owner(project)
        ]


    def get_project(
        self,
        project_id,
    ):

        project_id = str(project_id)

        for project in self.list_projects():

            if (
                str(
                    project.get(
                        "id",
                        "",
                    )
                )
                == project_id
            ):

                return project

        return None


    def create_project(
        self,
        project,
    ):

        current_user_id = (
            self._current_user_id()
        )

        if not current_user_id:

            raise PermissionError(
                "Authentication required."
            )

        if not isinstance(project, dict):

            project = {}

        data = self._load()

        project = dict(project)

        project.setdefault(
            "id",
            "project_"
            + uuid.uuid4().hex,
        )

        project["user_id"] = (
            current_user_id
        )

        project.setdefault(
            "created_at",
            datetime.now(
                timezone.utc,
            ).isoformat(),
        )

        project[
            "updated_at"
        ] = datetime.now(
            timezone.utc,
        ).isoformat()

        data["projects"].append(
            project
        )

        self._save(data)

        return project


    def update_project(
        self,
        project_id,
        updates,
    ):

        current_user_id = (
            self._current_user_id()
        )

        if not current_user_id:

            return None

        if not isinstance(updates, dict):

            updates = {}

        data = self._load()

        project_id = str(project_id)

        for index, project in enumerate(
            data.get(
                "projects",
                [],
            )
        ):

            if (
                str(
                    project.get(
                        "id",
                        "",
                    )
                )
                != project_id
            ):

                continue

            if not self._same_owner(project):

                return None

            protected_fields = {
                "id",
                "user_id",
                "created_at",
            }

            safe_updates = {

                key: value

                for key, value in updates.items()

                if key
                not in protected_fields

            }

            project.update(
                safe_updates
            )

            project[
                "user_id"
            ] = current_user_id

            project[
                "updated_at"
            ] = datetime.now(
                timezone.utc,
            ).isoformat()

            data["projects"][index] = (
                project
            )

            self._save(data)

            return project

        return None


    def delete_project(
        self,
        project_id,
    ):

        current_user_id = (
            self._current_user_id()
        )

        if not current_user_id:

            return False

        data = self._load()

        project_id = str(project_id)

        projects = data.get(
            "projects",
            [],
        )

        for index, project in enumerate(
            projects
        ):

            if (
                str(
                    project.get(
                        "id",
                        "",
                    )
                )
                != project_id
            ):

                continue

            if not self._same_owner(project):

                return False

            del projects[index]

            data["projects"] = projects

            self._save(data)

            return True

        return False