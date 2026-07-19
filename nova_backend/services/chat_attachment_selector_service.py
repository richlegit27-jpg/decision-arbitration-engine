class ChatAttachmentSelectorService:

    def find_image_attachment(self, attachments):
        if not isinstance(attachments, list):
            return None

        for item in attachments:
            if not isinstance(item, dict):
                continue

            mime = str(
                item.get("mime_type")
                or item.get("type")
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

            if (
                mime.startswith("image/")
                or any(
                    ext in name
                    for ext in (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".gif",
                    )
                )
            ):
                return item

        return None