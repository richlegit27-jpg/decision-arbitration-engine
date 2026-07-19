from pathlib import Path
import json
import re

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
    def clean_attachment_analysis_response(
        self,
        response,
    ):
        try:
            from flask import request

            if request.path != "/api/chat":
                return response

            content_type = str(
                response.headers.get("Content-Type") or ""
            ).lower()

            if "application/json" not in content_type:
                return response

            data = response.get_json(
                silent=True
            )

            if not isinstance(data, dict):
                return response

            assistant_message = data.get(
                "assistant_message"
            )

            if not isinstance(
                assistant_message,
                dict,
            ):
                return response

            text_value = str(
                assistant_message.get("text")
                or ""
            )

            if "Attachment analysis:" not in text_value:
                return response

            noisy_exact = {
                "attachment <unknown> content:",
                "attachment content:",
                "[pdf page 1]",
                "search",
                "images",
                "videos",
                "create",
                "inspiration",
                "keypoints",
                "copy",
                "regen",
                "regenerate",
                "continue",
                "cop",
                "filt",
                "moderate",
                "amazon",
                "bath",
                "related content",
            }

            noisy_contains = (
                "wayfair",
                "save big",
                "prices you'll love",
                "eye-catching prints",
                "url removed from extracted attachment text",
                "free_shipping",
                "furniture & décor",
                "kitchen appliances",
                "love, horror and more themes",
                "plain field in front of mountain peak",
                "free stock photo",
                "6000 ×",
                "jpeg",
            )

            def clean_line(line):
                line = re.sub(
                    r"^\s*\d+\.\s*",
                    "",
                    str(line or ""),
                ).strip()

                line = line.replace(
                    "Attachment <unknown>",
                    "uploaded attachment",
                )

                line = line.replace(
                    "Attachment content:",
                    "",
                ).strip()

                line = re.sub(
                    r"^Attachment\s+.*?\s+content:\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()

                line = re.sub(
                    r"\s+",
                    " ",
                    line,
                ).strip()

                return line

            raw_lines = []

            for line in text_value.splitlines():
                cleaned = clean_line(line)

                if not cleaned:
                    continue

                low = cleaned.lower().strip(
                    " :;-•*|"
                )

                low_compact = re.sub(
                    r"[^a-z0-9]+",
                    " ",
                    low,
                ).strip()

                if low_compact in noisy_exact:
                    continue

                if any(
                    bad in low
                    for bad in noisy_contains
                ):
                    continue

                if len(cleaned) <= 2:
                    continue

                raw_lines.append(cleaned)

            useful = []
            seen = set()

            skip_prefixes = (
                "attachment analysis",
                "this attachment appears to be about",
                "key points",
                "preview",
            )

            for line in raw_lines:
                low = line.lower()

                if any(
                    low.startswith(prefix)
                    for prefix in skip_prefixes
                ):
                    continue

                key = re.sub(
                    r"[^a-z0-9]+",
                    " ",
                    low,
                ).strip()[:160]

                if not key or key in seen:
                    continue

                seen.add(key)
                useful.append(line)

            if useful:
                top = useful[:8]
                topic = "; ".join(top[:3])

                cleaned_text = (
                    "Attachment analysis:\n"
                )

                cleaned_text += (
                    f"{topic}\n\n"
                )

                cleaned_text += (
                    "Key points:\n"
                )

                for index, item in enumerate(
                    top,
                    start=1,
                ):
                    cleaned_text += (
                        f"{index}. {item}\n"
                    )

                cleaned_text += (
                    "\nPreview:\n"
                )

                cleaned_text += (
                    "\n".join(top[:6])
                )

            else:
                cleaned_text = (
                    "Attachment analysis:\n"
                    "The attachment was received and text was extracted, "
                    "but most of the extracted text looks like noisy "
                    "search-page/navigation content rather than a clean "
                    "document body."
                )

            _nova_existing_content = str(
                assistant_message.get("content")
                or ""
            ).strip()

            _nova_candidate_text = (
                cleaned_text.strip()
            )

            if (
                _nova_existing_content.startswith(
                    "Attachment analysis:"
                )
                and "Attachment " in _nova_existing_content
                and " content:" in _nova_existing_content
                and (
                    "This uploaded attachment contains readable text about:"
                    in _nova_candidate_text
                )
            ):
                assistant_message["text"] = (
                    _nova_existing_content
                )

                assistant_message["content"] = (
                    _nova_existing_content
                )

            else:
                # DISABLED_RECURSIVE_ATTACHMENT_TEXT_REWRITE_20260615
                pass

            data["assistant_message"] = assistant_message

            payload = json.dumps(data)

            response.set_data(payload)

            response.headers["Content-Length"] = str(
                len(payload.encode("utf-8"))
            )

            return response

        except Exception:
            return response