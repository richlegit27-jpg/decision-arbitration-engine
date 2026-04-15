from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from nova_backend.config import UPLOADS_DIR
from nova_backend.services.artifact_media_service import ArtifactMediaService
from nova_backend.utils.file_utils import load_json_file, save_json_file
from nova_backend.utils.time_utils import iso_now


class ArtifactService:
    def __init__(self, artifacts_file: str):
        self.artifacts_file = Path(artifacts_file)
        self.media = ArtifactMediaService(UPLOADS_DIR)
        self._ensure_store()

    def _ensure_store(self) -> None:
        if not self.artifacts_file.exists():
            save_json_file(self.artifacts_file, {"artifacts": []})

    def _read_store(self) -> Dict[str, Any]:
        data = load_json_file(self.artifacts_file, {"artifacts": []})
        if not isinstance(data, dict):
            return {"artifacts": []}
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, list):
            data["artifacts"] = []
        return data

    def _write_store(self, data: Dict[str, Any]) -> None:
        save_json_file(self.artifacts_file, data)

    def _viewer_from_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
        content = str(
            artifact.get("content")
            or artifact.get("text")
            or artifact.get("body")
            or ""
        ).strip()

        filename = str(
            meta.get("filename")
            or artifact.get("filename")
            or ""
        ).strip()

        image_url = str(
            artifact.get("image_url")
            or meta.get("image_url")
            or (f"/api/uploads/{filename}" if filename else "")
        ).strip()

        viewer = {
            "kind": str(artifact.get("kind") or meta.get("kind") or "artifact"),
            "title": str(artifact.get("title") or meta.get("title") or "Untitled artifact"),
            "body": content or str(meta.get("summary") or meta.get("body") or "").strip(),
            "source_url": str(
                artifact.get("source_url")
                or meta.get("source_url")
                or meta.get("url")
                or ""
            ).strip(),
            "image_url": image_url,
            "video_url": str(
                artifact.get("video_url")
                or meta.get("video_url")
                or ""
            ).strip(),
            "audio_url": str(
                artifact.get("audio_url")
                or meta.get("audio_url")
                or ""
            ).strip(),
            "filename": filename,
        }
        return viewer

    def _normalize_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(artifact or {})
        normalized["viewer"] = self._viewer_from_artifact(normalized)
        normalized = self.media.normalize_artifact_media(normalized)

        meta = normalized.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            normalized["meta"] = meta

        viewer = normalized.get("viewer") if isinstance(normalized.get("viewer"), dict) else {}

        if not meta.get("filename") and viewer.get("image_url", "").startswith("/api/uploads/"):
            meta["filename"] = viewer["image_url"].split("/api/uploads/", 1)[1]

        if viewer.get("image_url") and not meta.get("image_url"):
            meta["image_url"] = viewer["image_url"]

        normalized["preview"] = str(
            normalized.get("preview")
            or viewer.get("body")
            or viewer.get("title")
            or ""
        ).strip()[:200]

        return normalized

    def all(self) -> List[Dict[str, Any]]:
        return self._read_store().get("artifacts", [])

    def build_list_payload(self) -> List[Dict[str, Any]]:
        artifacts = self.all()
        normalized = [self._normalize_artifact(item) for item in artifacts if isinstance(item, dict)]
        normalized.sort(
            key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""),
            reverse=True,
        )
        return normalized

    def build_view_payload(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        artifact_id = str(artifact_id or "").strip()
        if not artifact_id:
            return None

        for item in self.all():
            if str(item.get("id") or "").strip() == artifact_id:
                return self._normalize_artifact(item)
        return None

    def save_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read_store()
        artifacts = data.get("artifacts", [])

        artifact = dict(artifact or {})
        meta = artifact.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            artifact["meta"] = meta

        filename = str(
            meta.get("filename")
            or artifact.get("filename")
            or ""
        ).strip()

        if filename and not meta.get("image_url") and not artifact.get("image_url"):
            image_url = f"/api/uploads/{filename}"
            meta["image_url"] = image_url
            artifact["image_url"] = image_url

        now = iso_now()

        if not artifact.get("id"):
            import uuid
            artifact["id"] = f"artifact_{uuid.uuid4().hex}"

        artifact["updated_at"] = now
        if not artifact.get("created_at"):
            artifact["created_at"] = now

        replaced = False
        for idx, existing in enumerate(artifacts):
            if str(existing.get("id") or "") == str(artifact["id"]):
                artifacts[idx] = artifact
                replaced = True
                break

        if not replaced:
            artifacts.append(artifact)

        data["artifacts"] = artifacts
        self._write_store(data)
        return self._normalize_artifact(artifact)