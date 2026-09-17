from __future__ import annotations

import os
import uuid


class UploadRouteService:

    def __init__(
        self,
        uploads_dir,
        upload_ownership_service,
        attachment_analysis_service=None,
    ):
        self.uploads_dir = uploads_dir
        self.upload_ownership_service = upload_ownership_service
        self.attachment_analysis_service = attachment_analysis_service

    def _build_attachment_analysis(
        self,
        save_path,
        mime_type,
        logger=None,
    ):
        extracted_text = ""
        summary = ""

        service = self.attachment_analysis_service

        if service is None:
            return {
                "attachment_summary": "",
                "extracted_text": "",
                "summary": "",
            }

        try:
            analysis_result = (
                service.analyze_binary_attachment_for_prompt(
                    str(save_path),
                    mime_type,
                )
            )

            if isinstance(analysis_result, dict):
                extracted_text = (
                    analysis_result.get("extracted_text")
                    or analysis_result.get("text")
                    or analysis_result.get("content")
                    or ""
                )

                summary_value = (
                    analysis_result.get("summary")
                    or analysis_result.get("attachment_summary")
                    or ""
                )

                if isinstance(summary_value, dict):
                    summary = (
                        summary_value.get("summary")
                        or summary_value.get("preview")
                        or ""
                    )
                else:
                    summary = str(summary_value or "")

            elif analysis_result is not None:
                extracted_text = str(
                    analysis_result
                )

        except Exception:
            if logger is not None:
                logger.exception(
                    "Attachment analysis failed for uploaded file: %s",
                    save_path,
                )

        if not extracted_text:
            try:
                extracted_text = (
                    service.existing_attachment_text(
                        {
                            "path": str(save_path),
                            "mime_type": mime_type,
                        }
                    )
                    or ""
                )
            except Exception:
                extracted_text = ""

        extracted_text = str(
            extracted_text or ""
        ).replace(
            "\ufeff",
            "",
        ).strip()

        if extracted_text:
            try:
                extracted_text = (
                    service.clean_extracted_attachment_text(
                        extracted_text
                    )
                    or ""
                ).replace(
                    "\ufeff",
                    "",
                ).strip()
            except Exception:
                extracted_text = extracted_text.strip()

        if not summary and extracted_text:
            try:
                summary_result = (
                    service.local_summary_from_text(
                        extracted_text
                    )
                )

                if isinstance(summary_result, dict):
                    summary = (
                        summary_result.get("summary")
                        or summary_result.get("preview")
                        or ""
                    )
                else:
                    summary = str(
                        summary_result or ""
                    )

            except Exception:
                summary = extracted_text[:500].strip()

        summary = str(
            summary or ""
        ).replace(
            "\ufeff",
            "",
        ).strip()

        attachment_summary = (
            summary
            or extracted_text[:500].strip()
        )

        return {
            "attachment_summary": attachment_summary,
            "extracted_text": extracted_text,
            "summary": summary,
        }

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

        safe_name = (
            secure_filename(original_name)
            if secure_filename is not None
            else original_name
        ) or "upload.bin"

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

        analysis = self._build_attachment_analysis(
            save_path=save_path,
            mime_type=mime_type,
            logger=logger,
        )

        return {
            "ok": True,
            "filename": final_name,
            "original_filename": original_name,
            "file_url": f"/api/uploads/{final_name}",
            "url": f"/api/uploads/{final_name}",
            "path": str(save_path),
            "mime_type": mime_type,
            "size": size,
            **analysis,
        }
