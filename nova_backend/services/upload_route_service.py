from __future__ import annotations

import os
import uuid


class UploadRouteService:

    def __init__(
        self,
        uploads_dir,
        upload_ownership_service,
    ):
        self.uploads_dir = uploads_dir
        self.upload_ownership_service = upload_ownership_service

    def handle_upload(
        self,
        file,
        auth_user_id="",
        logger=None,
        secure_filename=None,
    ):
        original_name = os.path.basename(
            str(file.filename or "upload")
        )

        safe_name = secure_filename(original_name) or "upload.bin"

        base, ext = os.path.splitext(safe_name)
        ext = ext or ""

        final_name = f"{base}_{uuid.uuid4().hex}{ext}"

        save_path = self.uploads_dir / final_name

        file.save(str(save_path))

        if auth_user_id:
            self.upload_ownership_service.register_upload(
                final_name,
                auth_user_id,
            )

        mime_type = (
            getattr(file, "mimetype", None)
            or "application/octet-stream"
        )

        size = (
            save_path.stat().st_size
            if save_path.exists()
            else 0
        )

        return {
            "ok": True,
            "filename": final_name,
            "original_filename": original_name,
            "file_url": f"/api/uploads/{final_name}",
            "url": f"/api/uploads/{final_name}",
            "mime_type": mime_type,
            "size": size,
        }