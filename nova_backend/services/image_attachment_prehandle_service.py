class ImageAttachmentPrehandleService:

    def is_image_command(self, text):
        clean = str(text or "").strip().lower()

        return (
            clean.startswith("/image")
            or clean.startswith("image ")
            or clean.startswith("generate image")
            or clean.startswith("generate an image")
            or clean.startswith("draw ")
            or clean.startswith("create image")
            or clean.startswith("make image")
        )

    def extract_image_attachments(self, attachments):
        images = []

        for item in attachments or []:
            if not isinstance(item, dict):
                continue

            mime = str(
                item.get("mime_type")
                or item.get("type")
                or item.get("mime")
                or ""
            ).lower().strip()

            name = str(
                item.get("original_filename")
                or item.get("filename")
                or item.get("name")
                or item.get("url")
                or item.get("file_url")
                or "image attachment"
            ).strip()

            url = str(
                item.get("file_url")
                or item.get("url")
                or ""
            ).strip()

            if mime.startswith("image/") or name.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp", ".gif")
            ):
                images.append({
                    "name": name,
                    "mime": mime or "image/*",
                    "url": url,
                })

        return images



    def should_bypass_attachments_for_image_command(self, text):
        clean = str(text or "").strip().lower()

        return (
            clean.startswith("/image")
            or clean.startswith("image ")
            or clean.startswith("generate image")
            or clean.startswith("generate an image")
            or clean.startswith("draw ")
            or clean.startswith("create image")
            or clean.startswith("make image")
        )

image_attachment_prehandle_service = ImageAttachmentPrehandleService()
