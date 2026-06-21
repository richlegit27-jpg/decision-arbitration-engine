from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


class GeneratedMediaService:
    def __init__(self, uploads_dir: str | Path):
        self.uploads_dir = Path(uploads_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def _safe_ext(self, value: str) -> str:
        raw = str(value or "").strip().lower().lstrip(".")
        if raw in {"png", "jpg", "jpeg", "webp"}:
            return raw
        return "png"

    def _filename(self, prefix: str = "generated_img", ext: str = "png") -> str:
        safe_ext = self._safe_ext(ext)
        return f"{prefix}_{uuid.uuid4().hex}.{safe_ext}"

    def save_base64_image(
        self,
        image_b64: str,
        *,
        prefix: str = "generated_img",
        ext: str = "png",
    ) -> Dict[str, Any]:
        raw = str(image_b64 or "").strip()
        if not raw:
            raise ValueError("image_b64 is required")

        filename = self._filename(prefix=prefix, ext=ext)
        path = self.uploads_dir / filename

        binary = base64.b64decode(raw)
        path.write_bytes(binary)

        return {
            "filename": filename,
            "file_path": str(path),
            "url": f"/api/uploads/{filename}",
            "mime_type": f"image/{self._safe_ext(ext)}",
        }

    def save_binary_image(
        self,
        image_bytes: bytes,
        *,
        prefix: str = "generated_img",
        ext: str = "png",
    ) -> Dict[str, Any]:
        if not image_bytes:
            raise ValueError("image_bytes is required")

        filename = self._filename(prefix=prefix, ext=ext)
        path = self.uploads_dir / filename
        path.write_bytes(image_bytes)

        return {
            "filename": filename,
            "file_path": str(path),
            "url": f"/api/uploads/{filename}",
            "mime_type": f"image/{self._safe_ext(ext)}",
        }

    def build_image_artifact(
        self,
        *,
        prompt: str,
        saved: Dict[str, Any],
        session_id: str = "",
        title: str = "Generated image",
        kind: str = "image_generation",
    ) -> Dict[str, Any]:
        filename = str(saved.get("filename") or "").strip()
        image_url = str(saved.get("url") or "").strip()
        file_path = str(saved.get("file_path") or "").strip()
        mime_type = str(saved.get("mime_type") or "image/png").strip()

        return {
            "kind": kind,
            "title": title,
            "content": str(prompt or "").strip(),
            "session_id": str(session_id or "").strip(),
            "image_url": image_url,
            "meta": {
                "kind": kind,
                "title": title,
                "prompt": str(prompt or "").strip(),
                "filename": filename,
                "file_path": file_path,
                "image_url": image_url,
                "mime_type": mime_type,
            },
        }

    def coerce_generation_payload(
        self,
        *,
        prompt: str,
        image_b64: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        prefix: str = "generated_img",
        ext: str = "png",
        session_id: str = "",
        title: str = "Generated image",
    ) -> Dict[str, Any]:
        if image_b64:
            saved = self.save_base64_image(
                image_b64,
                prefix=prefix,
                ext=ext,
            )
        elif image_bytes:
            saved = self.save_binary_image(
                image_bytes,
                prefix=prefix,
                ext=ext,
            )
        else:
            raise ValueError("Either image_b64 or image_bytes is required")

        artifact = self.build_image_artifact(
            prompt=prompt,
            saved=saved,
            session_id=session_id,
            title=title,
        )

        return {
            "saved": saved,
            "artifact": artifact,
        }

