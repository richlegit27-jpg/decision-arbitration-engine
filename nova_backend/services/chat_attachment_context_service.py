from pathlib import Path


class ChatAttachmentContextService:

    def build_attachment_content_lines(
        self,
        attachments,
        logger=None,
    ):
        attachment_content_lines = []

        for attachment in attachments or []:
            if not isinstance(attachment, dict):
                continue

            attachment_filename = str(
                attachment.get("filename") or ""
            ).strip()

            attachment_original_filename = str(
                attachment.get("original_filename") or ""
            ).strip()

            if attachment_filename == "<unknown>":
                attachment_filename = ""

            if attachment_original_filename == "<unknown>":
                attachment_original_filename = ""

            raw_attachment_name = (
                attachment_filename
                or attachment_original_filename
                or Path(
                    str(attachment.get("stored_name") or "")
                ).name
                or Path(
                    str(attachment.get("file_url") or "")
                ).name
                or "<unknown>"
            )

            attachment_content_lines.append(
                str(raw_attachment_name)
            )

        return attachment_content_lines