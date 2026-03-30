from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MAX_ARTIFACTS = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _safe_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ArtifactService:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or ARTIFACTS_FILE
        if not self.path.exists():
            _safe_write_json(self.path, [])

    def _load(self) -> List[Dict[str, Any]]:
        data = _safe_read_json(self.path, [])
        if isinstance(data, list):
            return data
        return []

    def _save(self, artifacts: List[Dict[str, Any]]) -> None:
        artifacts = artifacts[:MAX_ARTIFACTS]
        _safe_write_json(self.path, artifacts)

    def list_artifacts(
        self,
        session_id: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        artifacts = self._load()
        if session_id:
            artifacts = [a for a in artifacts if a.get("session_id") == session_id]
        if kind:
            artifacts = [a for a in artifacts if a.get("kind") == kind]
        return sorted(
            artifacts,
            key=lambda a: a.get("updated_at") or a.get("created_at") or "",
            reverse=True,
        )

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        for artifact in self._load():
            if artifact.get("id") == artifact_id:
                return artifact
        return None

    def create_artifact(
        self,
        title: str,
        content: str = "",
        *,
        kind: str = "note",
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        pinned: bool = False,
    ) -> Dict[str, Any]:
        now = _now_iso()
        artifact = {
            "id": _new_id(),
            "title": title or "Untitled Artifact",
            "kind": kind,
            "content": content or "",
            "session_id": session_id,
            "tags": tags or [],
            "meta": meta or {},
            "pinned": bool(pinned),
            "created_at": now,
            "updated_at": now,
        }

        artifacts = self._load()
        artifacts.insert(0, artifact)
        self._save(artifacts)
        return artifact

    def create_image_artifact(
        self,
        *,
        title: str,
        image_url: str,
        prompt: str = "",
        session_id: Optional[str] = None,
        source: str = "generated",
        mime_type: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        model: Optional[str] = None,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = {
            "image_url": image_url,
            "prompt": prompt,
            "source": source,
            "mime_type": mime_type,
            "file_name": file_name,
            "file_size": file_size,
            "width": width,
            "height": height,
            "model": model,
        }
        if extra_meta:
            meta.update(extra_meta)

        return self.create_artifact(
            title=title or "Saved Image",
            content=prompt or "",
            kind="image",
            session_id=session_id,
            tags=["image", source],
            meta=meta,
        )

    def update_artifact(self, artifact_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        artifacts = self._load()
        for index, artifact in enumerate(artifacts):
            if artifact.get("id") != artifact_id:
                continue

            safe_updates = dict(updates or {})
            safe_updates.pop("id", None)
            safe_updates["updated_at"] = _now_iso()

            artifact.update(safe_updates)
            artifacts[index] = artifact
            self._save(artifacts)
            return artifact
        return None

    def delete_artifact(self, artifact_id: str) -> bool:
        artifacts = self._load()
        kept = [a for a in artifacts if a.get("id") != artifact_id]
        deleted = len(kept) != len(artifacts)
        if deleted:
            self._save(kept)
        return deleted