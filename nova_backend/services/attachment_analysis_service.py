import re


class AttachmentAnalysisService:

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
            from pathlib import Path

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
                        text = page.get_text(
                            "text"
                        )

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