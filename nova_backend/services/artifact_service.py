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
        print("ARTIFACT FILE PATH =", self.artifacts_file)

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

    def list_by_session(self, session_id: str):
        session_id = str(session_id or "").strip()
        artifacts = self.list_all() if hasattr(self, "list_all") else []
        if not session_id:
            return artifacts
        return [
            artifact
            for artifact in (artifacts or [])
            if str((artifact or {}).get("session_id") or "").strip() == session_id
        ]

    def list_all(self):
        try:
            data = self._read_store()
            artifacts = data.get("artifacts") or []
            return artifacts if isinstance(artifacts, list) else []
        except Exception as e:
            print("ARTIFACT SERVICE LIST_ALL FAILED =", e)
            return []

    # =========================
    # 🔥 NORMALIZATION CORE
    # =========================
    def _normalize_kind(self, kind: str) -> str:
        k = str(kind or "").lower().strip()
        if "image" in k:
            return "image"
        if "web" in k:
            return "web"
        if "analysis" in k:
            return "analysis"
        if "chat" in k:
            return "chat"
        return "other"

    def _derive_group(self, kind: str) -> str:
        mapping = {
            "image": "Images",
            "web": "Web",
            "analysis": "Analysis",
            "chat": "Chat",
            "other": "Other",
        }
        return mapping.get(kind, "Other")

    def _derive_title(self, artifact: Dict[str, Any]) -> str:
        meta = artifact.get("meta", {}) or {}
        prompt = str(meta.get("prompt") or "").strip()

        kind = self._normalize_kind(artifact.get("kind"))

        if kind == "image" and prompt:
            return f"Image: {prompt[:40]}"
        if kind == "web":
            return str(meta.get("title") or meta.get("domain") or "Web page")
        if kind == "analysis":
            return "Analysis"
        if kind == "chat":
            text = str(artifact.get("body") or "").strip()
            return text[:60] if text else "Chat reply"

        return str(artifact.get("title") or "Artifact")

    def _derive_preview(self, artifact: Dict[str, Any]) -> str:
        text = str(
            artifact.get("preview")
            or artifact.get("body")
            or artifact.get("content")
            or ""
        ).strip()
        return text[:160]

    def _viewer_from_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}

        filename = str(meta.get("filename") or "").strip()

        image_url = str(
            artifact.get("image_url")
            or meta.get("image_url")
            or (f"/api/uploads/{filename}" if filename else "")
        ).strip()

        return {
            "kind": artifact.get("kind"),
            "title": artifact.get("title"),
            "body": artifact.get("body") or "",
            "image_url": image_url,
            "video_url": artifact.get("video_url") or "",
            "audio_url": artifact.get("audio_url") or "",
            "source_url": meta.get("source_url") or meta.get("url") or "",
            "filename": filename,
        }

    def _normalize_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        a = dict(artifact or {})

        a["kind"] = self._normalize_kind(a.get("kind"))
        a["group"] = self._derive_group(a["kind"])

        if not a.get("title"):
            a["title"] = self._derive_title(a)

        a["preview"] = self._derive_preview(a)

        if not a.get("session_id"):
            a["session_id"] = ""

        a["viewer"] = self._viewer_from_artifact(a)
        a = self.media.normalize_artifact_media(a)

        return a

    # =========================
    # CORE API
    # =========================
    def all(self) -> List[Dict[str, Any]]:
        return self._read_store().get("artifacts", [])

    def build_list_payload(self) -> List[Dict[str, Any]]:
        items = [self._normalize_artifact(x) for x in self.all()]
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return items

    def build_view_payload(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        for item in self.all():
            if str(item.get("id")) == str(artifact_id):
                return self._normalize_artifact(item)
        return None

    def save_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read_store()
        items = data.get("artifacts", [])

        # =========================
        # ENSURE ARTIFACT ID FIRST
        # =========================
        if not artifact.get("id"):
            import uuid
            artifact["id"] = f"artifact_{uuid.uuid4().hex}"

        # =========================
        # VERSIONING CORE
        # =========================
        parent_id = artifact.get("parent_id")
        parent_version = 0

        if parent_id:
            for existing in items:
                if existing.get("id") == parent_id:
                    parent_version = existing.get("version", 0)
                    break

        artifact["version"] = parent_version + 1
        artifact["parent_id"] = parent_id

        # =========================
        # ROOT CHAIN RESOLUTION
        # =========================
        root_id = parent_id

        if parent_id:
            for existing in items:
                if existing.get("id") == parent_id:
                    root_id = existing.get("root_id") or parent_id
                    break
        else:
            root_id = artifact["id"]

        artifact["root_id"] = root_id

        now = iso_now()

        artifact["updated_at"] = now
        if not artifact.get("created_at"):
            artifact["created_at"] = now

        replaced = False
        for i, existing in enumerate(items):
            if existing.get("id") == artifact["id"]:
                items[i] = artifact
                replaced = True
                break

        if not replaced:
            items.append(artifact)

        # 🔥 STORAGE CONTROL
        MAX_ARTIFACTS = 100
        items = items[-MAX_ARTIFACTS:]

        data["artifacts"] = items[-MAX_ARTIFACTS:]

        return self._normalize_artifact(artifact)

    def create(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        return self.save_artifact(artifact)