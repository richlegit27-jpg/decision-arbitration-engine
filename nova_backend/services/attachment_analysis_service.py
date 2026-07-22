import re
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


class AttachmentAnalysisService:

    def __init__(self):
        pass

    def normalize_attachment(self, attachment):
        if isinstance(attachment, dict):
            return attachment

        if isinstance(attachment, str):
            value = attachment.strip()

            if not value:
                return {}

            return {
                "filename": value,
                "original_filename": value,
                "path": value,
            }

        return {}

    def resolve_attachment_path(self, attachment):
        root = Path(r"C:\Users\Owner\nova")
        uploads = root / "uploads"

        attachment = self.normalize_attachment(
            attachment
        )

        candidates = []

        for key in (
            "path",
            "file_path",
            "local_path",
        ):
            value = attachment.get(key)

            if value:
                candidate = Path(str(value))
                candidates.append(candidate)
                candidates.append(
                    uploads / candidate.name
                )

        for key in (
            "stored_name",
            "saved_name",
            "filename",
            "stored_filename",
            "name",
            "original_filename",
        ):
            value = attachment.get(key)

            if value:
                candidates.append(
                    uploads / Path(str(value)).name
                )

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                pass

        return None

    def existing_attachment_text(
        self,
        attachment,
        limit=6000,
    ):
        attachment = self.normalize_attachment(
            attachment
        )

        text = str(
            attachment.get("attachment_summary")
            or attachment.get("extracted_text")
            or attachment.get("text")
            or ""
        )

        if (
            text.startswith("PK\x03\x04")
            or "[Content_Types].xml" in text[:500]
            or "PK" in text[:20]
        ):
            return ""

        return text[:limit].strip()


    def extracted_file_text(
        self,
        attachment,
        limit=6000,
    ):
        path = self.resolve_attachment_path(
            attachment
        )

        if not path:
            return ""

        text = self.read_attachment_text(
            path
        )

        return str(text or "")[:limit].strip()

    def clean_extracted_attachment_text(
        self,
        text,
        limit=6000,
    ):
        raw = str(text or "")
        lines = []

        skip_fragments = (
            "sponsored",
            "safesearch",
            "create a new collection",
            "saved images",
            "saved to collections",
            "related searches",
            "more images on this site",
            "go to site",
        )

        for line in raw.splitlines():
            cleaned = " ".join(
                str(line or "").strip().split()
            )

            if not cleaned:
                continue

            lowered = cleaned.lower()

            if any(
                fragment in lowered
                for fragment in skip_fragments
            ):
                continue

            if len(cleaned) <= 2:
                continue

            lines.append(cleaned)

        joined = "\n".join(lines)

        return joined[:limit]


    def local_summary_from_text(
        self,
        text,
    ):
        cleaned = self.clean_extracted_attachment_text(
            text
        )

        lines = [
            line
            for line in cleaned.splitlines()
            if line.strip()
        ]

        if not lines:
            return {
                "summary": "No clean readable text was found.",
                "key_points": [],
                "preview": "",
            }

        key_points = []
        seen = set()

        for line in lines:
            lowered = line.lower()

            if lowered in seen:
                continue

            seen.add(lowered)

            if len(line) >= 12:
                key_points.append(line)

            if len(key_points) >= 10:
                break

        return {
            "summary": "; ".join(lines[:5]),
            "key_points": key_points,
            "preview": "\n".join(lines[:8])[:1200],
        }


    def clean_attachment_endpoint_text(
        self,
        value,
    ):
        text_value = str(value or "")

        text_value = text_value.replace(
            "\ufeff",
            "",
        )

        text_value = text_value.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )

        lines = []

        seen = set()

        for raw_line in text_value.splitlines():
            line = str(raw_line or "").strip()

            if not line:
                continue

            low = line.lower()

            if "tesseract is not installed" in low:
                continue

            if low in {
                "copy",
                "regen",
                "regenerate",
                "summary:",
                "preview:",
            }:
                continue

            key = re.sub(
                r"[^a-z0-9]+",
                " ",
                low,
            ).strip()

            if key in seen:
                continue

            seen.add(key)
            lines.append(line)

        return "\n".join(lines).strip()


    def clean_attachment_endpoint_payload(
        self,
        local_summary,
        cleaned_text,
    ):
        clean_text = self.clean_attachment_endpoint_text(
            cleaned_text
        )

        return {
            "summary": clean_text[:1200],
            "key_points": (
                local_summary or {}
            ).get(
                "key_points",
                [],
            ),
            "preview": clean_text[:1200],
        }


    def clean_attachment_analysis_response(
        self,
        response,
    ):
        return response


    def strip_urls_from_extracted_attachment_text(
        self,
        value,
    ):
        text_value = str(value or "")

        text_value = re.sub(
            r"https?://\S+",
            "[URL removed from extracted attachment text]",
            text_value,
        )

        text_value = re.sub(
            r"www\.\S+",
            "[URL removed from extracted attachment text]",
            text_value,
        )

        return self.clean_extracted_attachment_text(
            text_value
        )

    def analyze_binary_attachment_for_prompt(
        self,
        attachment_path,
        mime_type,
    ):
        try:
            path_obj = Path(
                str(attachment_path or "")
            )

            if not path_obj.exists():
                return ""

            mime = str(
                mime_type or ""
            ).lower()

            if (
                "pdf" in mime
                or path_obj.suffix.lower() == ".pdf"
            ):
                try:
                    import fitz

                    document = fitz.open(
                        str(path_obj)
                    )

                    pieces = []

                    for page in document:
                        text = page.get_text("text")

                        if text:
                            pieces.append(text)

                    return "\n\n".join(
                        pieces
                    ).strip()

                except Exception:
                    return ""

            return ""

        except Exception:
            return ""


    def read_attachment_text(
        self,
        file_path,
    ):
        try:
            path = Path(
                str(file_path or "")
            )

            if not path.exists():
                return ""

            if path.suffix.lower() == ".docx":
                return self.extract_docx_text(path)

            return path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:
            return ""


    def extract_docx_text(
        self,
        file_path,
    ):
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return ""

            chunks = []

            with zipfile.ZipFile(file_path) as docx:
                xml_names = [
                    name
                    for name in docx.namelist()
                    if (
                        name == "word/document.xml"
                        or name.startswith("word/header")
                        or name.startswith("word/footer")
                    )
                ]

                for xml_name in xml_names:
                    raw = docx.read(xml_name)
                    root = ET.fromstring(raw)

                    for node in root.iter():
                        if node.tag.endswith("}t") and node.text:
                            chunks.append(node.text)

                        elif node.tag.endswith("}tab"):
                            chunks.append("\t")

                        elif node.tag.endswith("}br"):
                            chunks.append("\n")

            return " ".join(
                " ".join(chunks).split()
            ).strip()

        except Exception:
            return ""

    def execute_attachment_analysis(
        self,
        attachments=None,
        *args,
        **kwargs,
    ):
        results = []

        for attachment in attachments or []:
            path = self.resolve_attachment_path(
                attachment
            )

            text = self.read_attachment_text(
                path
            )

            results.append(
                {
                    "path": path,
                    "text": self.clean_extracted_attachment_text(
                        text
                    ),
                }
            )

        return results