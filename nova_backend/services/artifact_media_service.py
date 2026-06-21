from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class ArtifactMediaService:
    def __init__(self, uploads_dir: str | Path):
        self.uploads_dir = Path(uploads_dir)

    def _clean(self, value: Any) -> str:
        return str(value or "").strip()

    def _uploads_prefixes(self) -> tuple[str, ...]:
        return (
            "/api/uploads/",
            "/uploads/",
            "api/uploads/",
            "uploads/",
        )

    def extract_upload_filename(self, url: Any) -> str:
        raw = self._clean(url)
        if not raw:
            return ""

        for prefix in self._uploads_prefixes():
            if raw.startswith(prefix):
                return raw[len(prefix):].strip()

        return ""

    def resolve_upload_url(self, url: Any) -> Tuple[Optional[str], bool, Optional[str]]:
        raw = self._clean(url)
        if not raw:
            return None, False, None

        filename = self.extract_upload_filename(raw)
        if not filename:
            return raw, False, None

        full_path = self.uploads_dir / filename
        if full_path.exists():
            return f"/api/uploads/{filename}", False, str(full_path)

        return None, True, str(full_path)

    def normalize_artifact_media(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(artifact, dict):
            return artifact

        viewer = artifact.get("viewer")
        if not isinstance(viewer, dict):
            viewer = {}
            artifact["viewer"] = viewer

        meta = artifact.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            artifact["meta"] = meta

        image_candidates = [
            viewer.get("image_url"),
            artifact.get("image_url"),
            meta.get("image_url"),
            meta.get("url"),
        ]

        video_candidates = [
            viewer.get("video_url"),
            artifact.get("video_url"),
            meta.get("video_url"),
        ]

        audio_candidates = [
            viewer.get("audio_url"),
            artifact.get("audio_url"),
            meta.get("audio_url"),
        ]

        image_url = next((x for x in image_candidates if self._clean(x)), "")
        video_url = next((x for x in video_candidates if self._clean(x)), "")
        audio_url = next((x for x in audio_candidates if self._clean(x)), "")

        resolved_image_url, image_missing, image_path = self.resolve_upload_url(image_url)
        resolved_video_url, video_missing, video_path = self.resolve_upload_url(video_url)
        resolved_audio_url, audio_missing, audio_path = self.resolve_upload_url(audio_url)

        viewer["image_url"] = resolved_image_url
        viewer["video_url"] = resolved_video_url
        viewer["audio_url"] = resolved_audio_url

        viewer["media_missing"] = bool(image_missing or video_missing or audio_missing)
        viewer["image_missing"] = bool(image_missing)
        viewer["video_missing"] = bool(video_missing)
        viewer["audio_missing"] = bool(audio_missing)

        viewer["image_path"] = image_path
        viewer["video_path"] = video_path
        viewer["audio_path"] = audio_path

        artifact["image_url"] = resolved_image_url
        artifact["video_url"] = resolved_video_url
        artifact["audio_url"] = resolved_audio_url

        artifact["media_missing"] = viewer["media_missing"]
        artifact["image_missing"] = viewer["image_missing"]
        artifact["video_missing"] = viewer["video_missing"]
        artifact["audio_missing"] = viewer["audio_missing"]

        return artifact

