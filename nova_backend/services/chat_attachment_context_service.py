from pathlib import Path


class ChatAttachmentContextService:

    def __init__(
        self,
        uploads_dir,
        base_dir,
        attachment_analysis_service,
    ):
        self.uploads_dir = Path(uploads_dir)
        self.base_dir = Path(base_dir)
        self.attachment_analysis_service = attachment_analysis_service

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
                or Path(str(attachment.get("stored_name") or "")).name
                or Path(str(attachment.get("file_url") or "")).name
                or Path(str(attachment.get("url") or "")).name
                or ""
            )

            local_path_value = str(
                attachment.get("local_path")
                or attachment.get("path")
                or ""
            ).strip()

            candidate_paths = []

            if local_path_value:
                candidate_paths.append(
                    Path(local_path_value).expanduser()
                )

            if raw_attachment_name:
                safe_name = Path(
                    str(raw_attachment_name).strip().lstrip("/\\")
                ).name

                candidate_paths.append(
                    (self.uploads_dir / safe_name).resolve()
                )

            file_path = None
            uploads_root = self.uploads_dir.resolve()

            for candidate in candidate_paths:
                try:
                    candidate = candidate.resolve()
                except Exception:
                    continue

                if not candidate.exists() or not candidate.is_file():
                    continue

                if (
                    str(candidate).startswith(str(uploads_root))
                    or str(candidate).startswith(str(self.base_dir.resolve()))
                ):
                    file_path = candidate
                    break

            if file_path is None and raw_attachment_name:
                file_path = (
                    self.uploads_dir
                    / Path(
                        str(raw_attachment_name).strip().lstrip("/\\")
                    ).name
                ).resolve()

            content_snippet = ""

            try:
                if (
                    file_path.exists()
                    and file_path.is_file()
                    and str(file_path).startswith(str(uploads_root))
                ):
                    content_snippet = file_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )[:4000]

                    if logger:
                        logger.info(
                            "[AttachmentContentFinal] loaded file content path=%s chars=%s",
                            str(file_path),
                            len(content_snippet),
                        )
                else:
                    if logger:
                        logger.warning(
                            "[AttachmentContentFinal] file unavailable path=%s exists=%s",
                            str(file_path),
                            file_path.exists(),
                        )

            except Exception as exc:
                if logger:
                    logger.warning(
                        "[AttachmentContentFinal] failed reading %s: %s",
                        str(file_path),
                        exc,
                    )

            try:
                uploads_root = self.uploads_dir.resolve()

                if (
                    str(file_path).startswith(str(uploads_root))
                    and file_path.exists()
                    and file_path.is_file()
                ):
                    mime_type = str(
                        attachment.get("mime_type") or ""
                    ).lower().strip()

                    filename_for_type = str(
                        attachment.get("original_filename")
                        or attachment.get("filename")
                        or ""
                    ).lower().strip()

                    binary_extensions = (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".webp",
                        ".bmp",
                        ".ico",
                        ".pdf",
                        ".zip",
                        ".7z",
                        ".rar",
                        ".exe",
                        ".dll",
                        ".mp3",
                        ".mp4",
                        ".mov",
                        ".wav",
                        ".webm",
                    )

                    is_binary_attachment = (
                        mime_type.startswith("image/")
                        or mime_type.startswith("audio/")
                        or mime_type.startswith("video/")
                        or mime_type in {
                            "application/pdf",
                            "application/zip",
                            "application/octet-stream",
                        }
                        or filename_for_type.endswith(binary_extensions)
                    )

                    if is_binary_attachment:
                        attachment_path = str(file_path)

                        extracted_attachment_text = (
                            self.attachment_analysis_service
                            .analyze_binary_attachment_for_prompt(
                                attachment_path,
                                mime_type,
                            )
                        )

                        if extracted_attachment_text:
                            extracted_attachment_text = (
                                self.attachment_analysis_service
                                .strip_urls_from_extracted_attachment_text(
                                    extracted_attachment_text
                                )
                            )

                            content_snippet = (
                                extracted_attachment_text[:4000]
                            )

                        else:
                            content_snippet = (
                                "[Attachment received, but no readable "
                                "text could be extracted.]"
                            )

                    else:
                        content_snippet = file_path.read_text(
                            encoding="utf-8",
                            errors="replace",
                        )[:4000]

            except Exception as exc:
                if logger:
                    logger.warning(
                        "[AttachmentContent] failed reading %s: %s",
                        file_path,
                        exc,
                    )

            content_snippet = str(content_snippet or "")
            content_snippet = (
                content_snippet
                .replace("\ufeff", "")
                .replace("\u200b", "")
                .strip()
            )

            fallback_text = (
                "[Attachment content could not be read from disk.]"
            )

            attachment_display_name = (
                attachment.get("original_filename")
                or attachment.get("filename")
                or "<unknown>"
            )

            if not str(
                attachment.get("mime_type") or ""
            ).lower().startswith(("image/", "application/pdf")):
                content_snippet = (
                    content_snippet
                    .replace(
                        "This uploaded attachment contains readable text about:",
                        "",
                    )
                    .strip()
                )

            attachment_content_lines.append(
                f"Attachment {attachment_display_name} content:\n"
                f"{content_snippet if content_snippet else fallback_text}"
            )

        return attachment_content_lines