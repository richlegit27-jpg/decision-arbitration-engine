from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = 1

PROJECT_COLLECTIONS = (
    "goals",
    "deadlines",
    "decisions",
    "documents",
    "workflows",
    "knowledge",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: Any) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        _clean(value).lower(),
    ).strip("-")

    return normalized or "project"


class PersistentProjectRegistry:
    """
    Canonical Phase 8 multi-project registry.

    This does not replace Nova's current-project checkpoint or Project Brain
    operator milestones. It owns durable user/project operating-system records.
    """

    def __init__(
        self,
        path: str | Path | None = None,
    ) -> None:
        root = Path(__file__).resolve().parents[2]

        self.path = Path(
            path
            or root / "data" / "nova_projects.json"
        )

        self._lock = RLock()

    @staticmethod
    def empty_store() -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "active_project_id": None,
            "projects": [],
            "updated_at": None,
        }

    @staticmethod
    def _normalize_project(
        project: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(project)

        normalized["id"] = _clean(
            normalized.get("id")
        )
        normalized["title"] = _clean(
            normalized.get("title")
        )
        normalized["description"] = _clean(
            normalized.get("description")
        )
        normalized["status"] = (
            _clean(normalized.get("status"))
            or "active"
        )
        normalized["created_at"] = _clean(
            normalized.get("created_at")
        )
        normalized["updated_at"] = _clean(
            normalized.get("updated_at")
        )

        metadata = normalized.get("metadata")
        normalized["metadata"] = (
            dict(metadata)
            if isinstance(metadata, dict)
            else {}
        )

        for collection in PROJECT_COLLECTIONS:
            records = normalized.get(collection)

            normalized[collection] = (
                [
                    dict(record)
                    for record in records
                    if isinstance(record, dict)
                ]
                if isinstance(records, list)
                else []
            )

        return normalized

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return self.empty_store()

            raw = json.loads(
                self.path.read_text(
                    encoding="utf-8-sig",
                )
            )

            if not isinstance(raw, dict):
                raise ValueError(
                    "Project registry root must be an object"
                )

            projects = raw.get("projects")

            if not isinstance(projects, list):
                raise ValueError(
                    "Project registry projects must be a list"
                )

            normalized_projects = [
                self._normalize_project(project)
                for project in projects
                if isinstance(project, dict)
            ]

            known_ids = {
                project["id"]
                for project in normalized_projects
                if project["id"]
            }

            active_project_id = _clean(
                raw.get("active_project_id")
            ) or None

            if active_project_id not in known_ids:
                active_project_id = (
                    normalized_projects[0]["id"]
                    if normalized_projects
                    else None
                )

            return {
                "version": SCHEMA_VERSION,
                "active_project_id": active_project_id,
                "projects": normalized_projects,
                "updated_at": (
                    _clean(raw.get("updated_at"))
                    or None
                ),
            }

    def _save(
        self,
        store: dict[str, Any],
    ) -> dict[str, Any]:
        store = deepcopy(store)
        store["version"] = SCHEMA_VERSION
        store["updated_at"] = _utc_now()

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.path.with_name(
            self.path.name
            + ".tmp"
        )

        temporary.write_text(
            json.dumps(
                store,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            temporary,
            self.path,
        )

        return deepcopy(store)

    @staticmethod
    def _find_project(
        store: dict[str, Any],
        project_id: str,
    ) -> dict[str, Any]:
        wanted = _clean(project_id)

        for project in store["projects"]:
            if project.get("id") == wanted:
                return project

        raise KeyError(
            f"Unknown project: {wanted}"
        )

    def list_projects(self) -> list[dict[str, Any]]:
        return deepcopy(
            self.load()["projects"]
        )

    def get_project(
        self,
        project_id: str,
    ) -> dict[str, Any]:
        store = self.load()

        return deepcopy(
            self._find_project(
                store,
                project_id,
            )
        )

    def get_active_project(
        self,
    ) -> dict[str, Any] | None:
        store = self.load()
        project_id = store["active_project_id"]

        if not project_id:
            return None

        return deepcopy(
            self._find_project(
                store,
                project_id,
            )
        )

    def create_project(
        self,
        title: str,
        description: str = "",
        project_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_title = _clean(title)

        if not clean_title:
            raise ValueError(
                "Project title is required"
            )

        with self._lock:
            store = self.load()

            base_id = _slug(
                project_id
                or clean_title
            )
            final_id = base_id
            existing_ids = {
                project.get("id")
                for project in store["projects"]
            }

            if final_id in existing_ids:
                final_id = (
                    base_id
                    + "-"
                    + uuid4().hex[:8]
                )

            now = _utc_now()

            project = {
                "id": final_id,
                "title": clean_title,
                "description": _clean(description),
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "metadata": (
                    dict(metadata)
                    if isinstance(metadata, dict)
                    else {}
                ),
            }

            for collection in PROJECT_COLLECTIONS:
                project[collection] = []

            store["projects"].append(project)

            if not store["active_project_id"]:
                store["active_project_id"] = final_id

            self._save(store)

            return deepcopy(project)

    def ensure_project(
        self,
        title: str,
        description: str = "",
    ) -> dict[str, Any]:
        wanted = _clean(title).lower()

        with self._lock:
            store = self.load()

            for project in store["projects"]:
                if _clean(project.get("title")).lower() == wanted:
                    return deepcopy(project)

            return self.create_project(
                title=title,
                description=description,
            )

    def set_active_project(
        self,
        project_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            store = self.load()
            project = self._find_project(
                store,
                project_id,
            )

            store["active_project_id"] = project["id"]
            self._save(store)

            return deepcopy(project)

    def add_record(
        self,
        project_id: str,
        collection: str,
        title: str,
        details: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        collection = _clean(collection).lower()

        if collection not in PROJECT_COLLECTIONS:
            raise ValueError(
                "Unsupported project collection: "
                + collection
            )

        clean_title = _clean(title)

        if not clean_title:
            raise ValueError(
                "Record title is required"
            )

        with self._lock:
            store = self.load()
            project = self._find_project(
                store,
                project_id,
            )
            now = _utc_now()

            record = {
                "id": (
                    collection.rstrip("s")
                    + "-"
                    + uuid4().hex
                ),
                "title": clean_title,
                "details": _clean(details),
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "metadata": (
                    dict(metadata)
                    if isinstance(metadata, dict)
                    else {}
                ),
            }

            project[collection].append(record)
            project["updated_at"] = now

            self._save(store)

            return deepcopy(record)
