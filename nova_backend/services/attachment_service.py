class AttachmentService:

    def should_skip_raw_attachment_injection(self, item):
        try:
            if not isinstance(item, dict):
                return False

            mime = str(
                item.get("mime_type")
                or item.get("type")
                or item.get("content_type")
                or ""
            ).lower()

            name = str(
                item.get("filename")
                or item.get("original_filename")
                or item.get("name")
                or item.get("url")
                or item.get("file_url")
                or ""
            ).lower()

            blocked_exts = (
                ".docx",
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".gif",
                ".zip",
                ".exe",
                ".dll",
                ".bin",
            )

            blocked_mimes = {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/pdf",
                "application/zip",
                "application/octet-stream",
            }

            if mime in blocked_mimes:
                return True

            if mime.startswith("image/"):
                return True

            return name.endswith(blocked_exts)

        except Exception:
            return False


attachment_service = AttachmentService()