from __future__ import annotations

from typing import Any, Dict, List, Optional

from nova_backend.models.artifact import (
    new_artifact,
    normalize_artifact,
    artifact_preview,
    artifact_viewer_payload,
)
from nova_backend.utils.file_utils import (
    read_json_file,
    atomic_write_json,
    safe_list,
)
from nova_backend.utils.time_utils import iso_now, newest_first


class ArtifactService:
    def __init__(self, artifacts_file: str):
        self.artifacts_file = artifacts_file
        self.artifacts: List[dict] = []
        self._load()

    # -----------------------
    # LOAD / SAVE
    # -----------------------

    def _load(self) -> None:
        data = read_json_file(self.artifacts_file, default=[])
        raw_artifacts = safe_list(data)
        self.artifacts = [normalize_artifact(a) for a in raw_artifacts]
        self.artifacts = newest_first(self.artifacts, "updated_at")

    def _save(self) -> None:
        atomic_write_json(self.artifacts_file, self.artifacts)

    # -----------------------
    # GETTERS
    # -----------------------

    def get_all(self) -> List[dict]:
        return newest_first(list(self.artifacts), "updated_at")

    def get_by_id(self, artifact_id: str | None) -> Optional[dict]:
        if not artifact_id:
            return None

        for artifact in self.artifacts:
            if artifact.get("id") == artifact_id:
                return normalize_artifact(artifact)

        return None

    def get_by_session_id(self, session_id: str | None) -> List[dict]:
        if not session_id:
            return []

        matches = [
            normalize_artifact(a)
            for a in self.artifacts
            if str(a.get("session_id") or "").strip() == str(session_id).strip()
        ]
        return newest_first(matches, "updated_at")

    # -----------------------
    # CREATE / UPDATE
    # -----------------------

    def create(
        self,
        kind: str = "artifact",
        title: str = "Untitled",
        body: str = "",
        session_id: str = "",
        source: str = "",
        meta: Dict[str, Any] | None = None,
    ) -> dict:
        artifact = new_artifact(
            kind=kind,
            title=title,
            body=body,
            session_id=session_id,
            source=source,
            meta=meta,
        )
        normalized = normalize_artifact(artifact)
        self.artifacts.insert(0, normalized)
        self.artifacts = newest_first(self.artifacts, "updated_at")
        self._save()
        return normalized

    def upsert(self, artifact: Dict[str, Any]) -> dict:
        normalized = normalize_artifact(artifact)
        artifact_id = normalized.get("id")

        for index, existing in enumerate(self.artifacts):
            if existing.get("id") == artifact_id:
                normalized["created_at"] = existing.get("created_at") or normalized.get("created_at")
                normalized["updated_at"] = iso_now()
                self.artifacts[index] = normalize_artifact(normalized)
                self.artifacts = newest_first(self.artifacts, "updated_at")
                self._save()
                return self.artifacts[index]

        normalized["updated_at"] = iso_now()
        self.artifacts.insert(0, normalize_artifact(normalized))
        self.artifacts = newest_first(self.artifacts, "updated_at")
        self._save()
        return self.artifacts[0]

    def delete(self, artifact_id: str) -> bool:
        before = len(self.artifacts)
        self.artifacts = [a for a in self.artifacts if a.get("id") != artifact_id]

        if len(self.artifacts) == before:
            return False

        self._save()
        return True

    # -----------------------
    # PAYLOADS
    # -----------------------

    def build_list_payload(self) -> List[dict]:
        payload: List[dict] = []

        for artifact in newest_first(self.artifacts, "updated_at"):
            normalized = normalize_artifact(artifact)
            payload.append(
                {
                    "id": normalized.get("id", ""),
                    "kind": normalized.get("kind", "artifact"),
                    "title": normalized.get("title", "Untitled"),
                    "preview": artifact_preview(normalized),
                    "session_id": normalized.get("session_id", ""),
                    "source": normalized.get("source", ""),
                    "created_at": normalized.get("created_at", ""),
                    "updated_at": normalized.get("updated_at", ""),
                    "viewer": artifact_viewer_payload(normalized),
                }
            )

        return payload

    def build_view_payload(self, artifact_id: str) -> Optional[dict]:
        artifact = self.get_by_id(artifact_id)
        if not artifact:
            return None

        normalized = normalize_artifact(artifact)

        return {
            "id": normalized.get("id", ""),
            "kind": normalized.get("kind", "artifact"),
            "title": normalized.get("title", "Untitled"),
            "body": normalized.get("body", ""),
            "preview": artifact_preview(normalized),
            "session_id": normalized.get("session_id", ""),
            "source": normalized.get("source", ""),
            "meta": normalized.get("meta", {}),
            "created_at": normalized.get("created_at", ""),
            "updated_at": normalized.get("updated_at", ""),
            "viewer": artifact_viewer_payload(normalized),
        }