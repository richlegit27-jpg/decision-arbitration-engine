from pathlib import Path


class AttachmentUtilsService:

    def attachment_url_key(self, value):
        try:
            value = str(value or "").strip()
        except Exception:
            return ""

        if not value:
            return ""

        value = value.replace("\\", "/")

        if "/api/uploads/" in value:
            return value[value.find("/api/uploads/"):]

        return value


    def attachment_name_key(self, item):
        if not isinstance(item, dict):
            return ""

        for key in (
            "url",
            "file_url",
            "path",
            "stored_name",
            "filename",
            "name",
            "original_filename",
        ):
            value = item.get(key)
            cleaned = self.attachment_url_key(value)

            if cleaned:
                return cleaned

        return ""


    def is_binary_or_container_attachment(self, item):
        if not isinstance(item, dict):
            return True

        mime = str(
            item.get("mime_type")
            or item.get("mime")
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

        binary_exts = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".bmp",
            ".ico",
            ".mp3",
            ".wav",
            ".m4a",
            ".mp4",
            ".mov",
            ".avi",
            ".webm",
            ".pdf",
            ".zip",
            ".rar",
            ".7z",
            ".exe",
            ".dll",
        )

        container_exts = (
            ".docx",
            ".pptx",
            ".xlsx",
        )

        if any(
            name.endswith(ext)
            for ext in binary_exts + container_exts
        ):
            return True

        if (
            mime.startswith("image/")
            or mime.startswith("audio/")
            or mime.startswith("video/")
        ):
            return True

        if mime in {
            "application/pdf",
            "application/zip",
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }:
            return True

        return False


    def filter_current_attachments_only(
        self,
        candidate_attachments,
        current_attachments,
    ):
        if not isinstance(candidate_attachments, list):
            return []

        if (
            not isinstance(current_attachments, list)
            or not current_attachments
        ):
            return []

        current_keys = set()

        for item in current_attachments:
            key = self.attachment_name_key(item)

            if key:
                current_keys.add(key)

        if not current_keys:
            return []

        filtered = []
        seen = set()

        for item in candidate_attachments:
            key = self.attachment_name_key(item)

            if not key or key not in current_keys:
                continue

            if key in seen:
                continue

            seen.add(key)
            filtered.append(item)

        return filtered


    def should_skip_raw_attachment_injection(
        self,
        item,
    ):
        return self.is_binary_or_container_attachment(item)


    def filter_raw_injection_attachments(
        self,
        attachments,
        logger=None,
    ):
        kept = []
        skipped = []

        for item in attachments or []:
            if self.should_skip_raw_attachment_injection(item):
                skipped.append(item)
            else:
                kept.append(item)

        if skipped and logger:
            try:
                names = [
                    str(
                        x.get("original_filename")
                        or x.get("filename")
                        or x.get("name")
                        or x.get("url")
                        or "attachment"
                    )
                    for x in skipped
                    if isinstance(x, dict)
                ]

                logger.info(
                    "[RawAttachmentInjectionGuard] skipped raw binary injection for attachments=%s",
                    names,
                )
            except Exception:
                pass

        return kept


    def safe_attachment_name(
        self,
        attachment,
        fallback="uploaded attachment",
    ):
        if not isinstance(attachment, dict):
            return fallback

        return str(
            attachment.get("original_filename")
            or attachment.get("filename")
            or attachment.get("name")
            or fallback
        )


    def find_uploaded_file_path(
        self,
        attachment,
    ):
        try:
            item = (
                attachment
                if isinstance(attachment, dict)
                else {}
            )

            candidates = [
                item.get("path"),
                item.get("file_path"),
                item.get("stored_path"),
                item.get("local_path"),
                item.get("filename"),
                item.get("stored_filename"),
                item.get("name"),
                item.get("url"),
                item.get("file_url"),
            ]

            base_dir = Path(__file__).resolve().parents[2]
            upload_dir = base_dir / "uploads"

            for raw in candidates:
                if not raw:
                    continue

                value = str(raw).strip()

                candidate = Path(value)

                if candidate.exists():
                    return str(candidate)

                upload_candidate = upload_dir / value

                if upload_candidate.exists():
                    return str(upload_candidate)

            return ""

        except Exception:
            return ""