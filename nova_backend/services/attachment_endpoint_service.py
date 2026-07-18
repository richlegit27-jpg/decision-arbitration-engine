from pathlib import Path


class AttachmentEndpointService:

    def __init__(self):
        pass

    def clean_attachment_endpoint_response(
        self,
        local_summary,
        cleaned_text,
        file_path,
        mime_type,
    ):
        summary = ""

        if isinstance(local_summary, dict):
            summary = str(
                local_summary.get("summary")
                or local_summary.get("text")
                or ""
            ).strip()

            key_points = local_summary.get("key_points") or []
            preview = local_summary.get("preview") or ""

        else:
            summary = str(local_summary or "").strip()
            key_points = []
            preview = ""

        cleaned_text = str(cleaned_text or "").strip()

        if not summary:
            summary = self._fallback_summary(cleaned_text)

        if not preview:
            preview = self._build_preview(cleaned_text)

        if not key_points:
            key_points = self._build_key_points(cleaned_text)

        return {
            "summary": summary,
            "key_points": key_points,
            "preview": preview,
            "file_name": self._safe_filename(file_path),
            "mime_type": str(mime_type or ""),
        }

    def _fallback_summary(self, text):
        text = str(text or "").strip()

        if not text:
            return "No readable content was extracted."

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            return "No readable content was extracted."

        return " ".join(lines[:3])[:500]

    def _build_preview(self, text, limit=1200):
        text = str(text or "").strip()

        if not text:
            return ""

        return text[:limit]

    def _build_key_points(self, text, limit=5):
        lines = [
            line.strip()
            for line in str(text or "").splitlines()
            if line.strip()
        ]

        points = []

        for line in lines:
            cleaned = line.lstrip("-•* ").strip()

            if len(cleaned) < 10:
                continue

            points.append(cleaned)

            if len(points) >= limit:
                break

        return points

    def _safe_filename(self, file_path):
        try:
            return Path(str(file_path)).name
        except Exception:
            return ""