from pathlib import Path


class AttachmentRouteService:

    def __init__(
        self,
        attachment_analysis_service,
        attachment_endpoint_service,
        uploads_dir,
    ):
        self.attachment_analysis_service = attachment_analysis_service
        self.attachment_endpoint_service = attachment_endpoint_service
        self.uploads_dir = uploads_dir

    def extract(self, payload):

        try:
            upload_url = str(
                payload.get("url")
                or payload.get("file_url")
                or ""
            ).strip()

            local_path = str(
                payload.get("path")
                or ""
            ).strip()

            mime_type = str(
                payload.get("mime_type")
                or payload.get("type")
                or ""
            ).strip()

            if not local_path and upload_url:
                filename = (
                    upload_url
                    .replace("\\", "/")
                    .split("/")[-1]
                    .strip()
                )

                if filename:
                    local_path = str(
                        Path(self.uploads_dir) / filename
                    )

            if not local_path:
                return {
                    "ok": False,
                    "error": "Missing url or path.",
                }, 400

            file_path = Path(local_path)

            if not file_path.exists():
                return {
                    "ok": False,
                    "error": f"File not found: {file_path}",
                }, 404

            if not mime_type:
                suffix = file_path.suffix.lower()

                if suffix == ".pdf":
                    mime_type = "application/pdf"
                elif suffix in {".jpg", ".jpeg"}:
                    mime_type = "image/jpeg"
                elif suffix == ".png":
                    mime_type = "image/png"
                elif suffix == ".webp":
                    mime_type = "image/webp"
                else:
                    mime_type = "application/octet-stream"

            extracted_text = (
                self.attachment_analysis_service
                .analyze_binary_attachment_for_prompt(
                    str(file_path),
                    mime_type,
                )
            )

            extracted_text = str(
                extracted_text or ""
            ).strip()

            return {
                "ok": True,
                "path": str(file_path),
                "url": upload_url,
                "mime_type": mime_type,
                "chars": len(extracted_text),
                "text": extracted_text,
            }

        except Exception as error:
            return {
                "ok": False,
                "error": str(error),
            }, 500