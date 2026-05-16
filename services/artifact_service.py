from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ArtifactService:
    def __init__(self, artifacts_file: Path, sessions_file: Path | None = None) -> None:
        self.artifacts_file = Path(artifacts_file)
        self.sessions_file = Path(sessions_file) if sessions_file else None
        self.artifacts_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read_json_file(self, path: Path, default: Any) -> Any:
        try:
            if not path.exists():
                return default
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                return default
            return json.loads(raw)
        except Exception:
            return default

    def _write_json_file(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_artifacts(self) -> list[dict[str, Any]]:
        data = self._read_json_file(self.artifacts_file, [])
        if isinstance(data, list):
            return [self._normalize_artifact(item) for item in data if isinstance(item, dict)]
        if isinstance(data, dict) and isinstance(data.get("artifacts"), list):
            return [
                self._normalize_artifact(item)
                for item in data.get("artifacts", [])
                if isinstance(item, dict)
            ]
        return []

    def _write_artifacts(self, artifacts: list[dict[str, Any]]) -> None:
        normalized = [self._normalize_artifact(item) for item in artifacts if isinstance(item, dict)]
        self._write_json_file(self.artifacts_file, normalized)

    def _normalize_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        artifact = dict(artifact or {})
        created_at = str(artifact.get("created_at") or self.utc_now())
        updated_at = str(artifact.get("updated_at") or created_at)

        normalized = {
            "id": str(artifact.get("id") or uuid.uuid4()),
            "session_id": str(artifact.get("session_id") or "default-session"),
            "title": str(artifact.get("title") or artifact.get("name") or "Untitled artifact"),
            "content": str(
                artifact.get("content")
                or artifact.get("text")
                or artifact.get("body")
                or ""
            ),
            "kind": str(artifact.get("kind") or artifact.get("type") or "artifact"),
            "pinned": bool(artifact.get("pinned", False)),
            "created_at": created_at,
            "updated_at": updated_at,
            "meta": artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {},
        }
        return normalized

    def _sort_artifacts(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def key(item: dict[str, Any]):
            pinned_rank = 0 if item.get("pinned") else 1
            updated_at = item.get("updated_at") or item.get("created_at") or ""
            return (pinned_rank, updated_at)

        return sorted(artifacts, key=key)

    def _sort_artifacts_desc_within_groups(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pinned = [item for item in artifacts if item.get("pinned")]
        unpinned = [item for item in artifacts if not item.get("pinned")]

        pinned = sorted(
            pinned,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
        unpinned = sorted(
            unpinned,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
        return pinned + unpinned

    def list_artifacts(self, session_id: str | None = None) -> list[dict[str, Any]]:
        artifacts = self._read_artifacts()
        normalized_session_id = str(session_id).strip() if session_id else None

        if normalized_session_id:
            artifacts = [
                item for item in artifacts if str(item.get("session_id") or "") == normalized_session_id
            ]

        return self._sort_artifacts_desc_within_groups(artifacts)

    def create_artifact(
        self,
        session_id: str,
        title: str,
        content: str,
        kind: str = "artifact",
        meta: dict[str, Any] | None = None,
        pinned: bool = False,
    ) -> dict[str, Any] | None:
        session_id = str(session_id or "default-session").strip() or "default-session"
        title = str(title or "").strip() or "Untitled artifact"
        content = str(content or "").strip()

        if not content:
            return None

        now = self.utc_now()
        artifact = self._normalize_artifact(
            {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "title": title,
                "content": content,
                "kind": kind,
                "pinned": pinned,
                "created_at": now,
                "updated_at": now,
                "meta": meta or {},
            }
        )

        artifacts = self._read_artifacts()
        artifacts.append(artifact)
        self._write_artifacts(artifacts)
        return artifact

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        artifact_id = str(artifact_id or "").strip()
        if not artifact_id:
            return None

        for artifact in self._read_artifacts():
            if str(artifact.get("id")) == artifact_id:
                return artifact
        return None

    def set_pinned(self, artifact_id: str, pinned: bool) -> dict[str, Any] | None:
        artifact_id = str(artifact_id or "").strip()
        if not artifact_id:
            return None

        artifacts = self._read_artifacts()
        updated = None
        now = self.utc_now()

        for idx, artifact in enumerate(artifacts):
            if str(artifact.get("id")) == artifact_id:
                artifact["pinned"] = bool(pinned)
                artifact["updated_at"] = now
                artifacts[idx] = self._normalize_artifact(artifact)
                updated = artifacts[idx]
                break

        if updated is None:
            return None

        self._write_artifacts(artifacts)
        return updated

    def delete_artifact(self, artifact_id: str) -> bool:
        artifact_id = str(artifact_id or "").strip()
        if not artifact_id:
            return False

        artifacts = self._read_artifacts()
        kept = [item for item in artifacts if str(item.get("id")) != artifact_id]

        if len(kept) == len(artifacts):
            return False

        self._write_artifacts(kept)
        return True

    def purge_session_artifacts(self, session_id: str) -> int:
        session_id = str(session_id or "").strip()
        if not session_id:
            return 0

        artifacts = self._read_artifacts()
        kept = [item for item in artifacts if str(item.get("session_id") or "") != session_id]
        removed = len(artifacts) - len(kept)

        if removed:
            self._write_artifacts(kept)

        return removed

    def dedupe_session_artifacts(self, session_id: str) -> int:
        session_id = str(session_id or "").strip()
        if not session_id:
            return 0

        artifacts = self._read_artifacts()
        seen: set[tuple[str, str, str]] = set()
        kept: list[dict[str, Any]] = []
        removed = 0

        for artifact in self._sort_artifacts_desc_within_groups(artifacts):
            key = (
                str(artifact.get("session_id") or ""),
                str(artifact.get("title") or ""),
                str(artifact.get("content") or ""),
            )

            if artifact.get("session_id") == session_id and key in seen:
                removed += 1
                continue

            if artifact.get("session_id") == session_id:
                seen.add(key)

            kept.append(artifact)

        if removed:
            self._write_artifacts(kept)

        return removed