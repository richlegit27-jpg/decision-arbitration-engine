from __future__ import annotations


class AttachmentActionService:
    def __init__(
        self,
        upload_route_service=None,
        attachment_analysis_service=None,
        logger=None,
        secure_filename=None,
    ):
        self.upload_route_service = upload_route_service
        self.attachment_analysis_service = attachment_analysis_service
        self.logger = logger
        self.secure_filename = secure_filename

    def upload(
        self,
        file=None,
        auth_user_id="",
    ) -> dict:
        if self.upload_route_service is None:
            return {
                "ok": False,
                "error": "Upload route service is not configured.",
            }

        if file is None:
            return {
                "ok": False,
                "error": "No file provided.",
            }

        return self.upload_route_service.handle_upload(
            file,
            auth_user_id=str(auth_user_id or "").strip(),
            logger=self.logger,
            secure_filename=self.secure_filename,
        )

    def analyze(
        self,
        file_id=None,
        path=None,
        mime_type="application/octet-stream",
    ) -> dict:
        if self.attachment_analysis_service is None:
            return {
                "ok": False,
                "error": "Attachment analysis service is not configured.",
            }

        attachment_path = str(path or file_id or "").strip()

        if not attachment_path:
            return {
                "ok": False,
                "error": "Missing attachment path or file id.",
            }

        try:
            extracted_text = (
                self.attachment_analysis_service
                .analyze_binary_attachment_for_prompt(
                    attachment_path,
                    str(mime_type or "application/octet-stream"),
                )
            )

            cleaned_text = (
                self.attachment_analysis_service
                .clean_extracted_attachment_text(
                    extracted_text
                )
            )

            summary = (
                self.attachment_analysis_service
                .local_summary_from_text(
                    extracted_text
                )
            )

            return {
                "ok": True,
                "file_id": file_id,
                "path": attachment_path,
                "mime_type": str(
                    mime_type
                    or "application/octet-stream"
                ),
                "text": cleaned_text,
                "summary": summary,
            }

        except Exception as error:
            return {
                "ok": False,
                "file_id": file_id,
                "path": attachment_path,
                "error": str(error),
            }