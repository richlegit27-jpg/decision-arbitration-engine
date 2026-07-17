import os
import zipfile
import xml.etree.ElementTree as ET
import re


class AttachmentContextService:

    def __init__(
        self,
        uploads_dir=None,
    ):
        self.uploads_dir = uploads_dir

    def safe_clean_attachment_text(
        self,
        raw_text,
        max_chars=6000,
    ):
        text_value = str(raw_text or "").replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )

        cleaned_lines = []
        seen = set()

        noisy_contains = (
            "url removed from extracted attachment text",
            "sponsored",
            "ads",
            "google",
            "bing",
            "search images",
        )

        for raw_line in text_value.split("\n"):
            line = re.sub(
                r"\s+",
                " ",
                str(raw_line or ""),
            ).strip()

            if not line:
                continue

            low = line.lower()

            if any(
                bad in low
                for bad in noisy_contains
            ):
                continue

            key = low[:180]

            if key in seen:
                continue

            seen.add(key)
            cleaned_lines.append(line)

        cleaned = "\n".join(
            cleaned_lines
        ).strip()

        if not cleaned:
            cleaned = text_value.strip()

        return cleaned[:max_chars].strip()

    def is_text_attachment(
        self,
        item,
    ):
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

            text_exts = (
                ".txt",
                ".md",
                ".json",
                ".jsonl",
                ".py",
                ".js",
                ".css",
                ".html",
                ".csv",
                ".xml",
                ".yaml",
                ".yml",
                ".docx",
            )

            if mime.startswith("text/"):
                return True

            return name.endswith(text_exts)

        except Exception:
            return False

    def upload_path_from_attachment(
        self,
        item,
    ):
        try:
            raw = str(
                item.get("path")
                or item.get("local_path")
                or item.get("file_path")
                or item.get("url")
                or item.get("file_url")
                or ""
            ).strip()

            if not raw:
                return None

            if os.path.isabs(raw):
                return raw

            filename = (
                raw
                .split("/")[-1]
                .split("\\")[-1]
                .split("?")[0]
            )

            if self.uploads_dir:
                return os.path.join(
                    str(self.uploads_dir),
                    filename,
                )

            return filename

        except Exception:
            return None

    def extract_docx_text(
        self,
        path,
    ):
        try:
            chunks = []

            with zipfile.ZipFile(
                path,
                "r",
            ) as archive:

                xml_bytes = archive.read(
                    "word/document.xml"
                )

                root = ET.fromstring(
                    xml_bytes
                )

                namespace = {
                    "w": (
                        "http://schemas."
                        "openxmlformats.org/"
                        "wordprocessingml/"
                        "2006/main"
                    )
                }

                for paragraph in root.findall(
                    ".//w:p",
                    namespace,
                ):
                    texts = []

                    for node in paragraph.findall(
                        ".//w:t",
                        namespace,
                    ):
                        if node.text:
                            texts.append(
                                node.text
                            )

                    line = "".join(
                        texts
                    ).strip()

                    if line:
                        chunks.append(
                            line
                        )

            return "\n".join(
                chunks
            ).strip()

        except Exception:
            return ""

    def read_text_attachments(
        self,
        attachments,
        logger=None,
    ):
        sections = []

        for item in attachments or []:
            try:
                if not self.is_text_attachment(
                    item
                ):
                    continue

                path = self.upload_path_from_attachment(
                    item
                )

                if not path:
                    continue

                if not os.path.exists(path):
                    continue

                if str(path).lower().endswith(
                    ".docx"
                ):
                    text = self.extract_docx_text(
                        path
                    )
                else:
                    with open(
                        path,
                        "rb",
                    ) as handle:
                        raw = handle.read(
                            120000
                        )

                    text = None

                    for encoding in (
                        "utf-8",
                        "utf-8-sig",
                        "cp1252",
                        "latin-1",
                    ):
                        try:
                            text = raw.decode(
                                encoding
                            )
                            break

                        except Exception:
                            continue

                    if text is None:
                        continue

                text = self.safe_clean_attachment_text(
                    text
                )

                if not text:
                    continue

                sections.append(
                    text
                )

            except Exception as error:
                if logger:
                    logger.warning(
                        "[AttachmentContextService] failed item=%s error=%s",
                        item,
                        error,
                    )

        return sections

    def append_text_attachments_to_user_text(
        self,
        user_text,
        attachments,
        logger=None,
    ):
        try:
            sections = self.read_text_attachments(
                attachments,
                logger=logger,
            )

            if not sections:
                return user_text

            original = str(
                user_text or ""
            ).strip()

            return (
                original
                + "\n\n\n[CURRENT UPLOADED TEXT ATTACHMENTS]\n"
                + "\n\n---\n\n".join(
                    sections
                )
                + "\n[/CURRENT UPLOADED TEXT ATTACHMENTS]\n"
            ).strip()

        except Exception as error:
            if logger:
                logger.warning(
                    "[AttachmentContextService] append failed error=%s",
                    error,
                )

            return user_text