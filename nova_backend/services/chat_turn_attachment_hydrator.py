# NOVA_CHAT_TURN_ATTACHMENT_HYDRATOR_20260705
"""
Server-side attachment hydration for ChatTurn.

This intentionally only reads local files from the app's uploads directory.
It does not fetch URLs, does not read arbitrary paths, and keeps extracted text compact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import copy
import json
import re
import zipfile
import xml.etree.ElementTree as ET


_MAX_READ_BYTES = 250_000
_MAX_EXTRACTED_CHARS = 2200

_TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".mjs",
    ".cjs",
    ".py",
    ".log",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
}


_SUMMARY_KEYS = {
    "summary",
    "attachment_summary",
    "analysis",
    "description",
    "caption",
    "ocr_text",
    "extracted_text",
    "text",
    "content",
    "body",
    "preview",
}


_PATH_KEYS = (
    "local_path",
    "file_path",
    "filepath",
    "saved_path",
    "server_path",
    "path",
    "url",
    "download_url",
    "src",
    "href",
    "filename",
    "original_filename",
    "name",
    "file_name",
)


def _stringify(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, str):
        return value

    try:
        return str(value)
    except Exception:
        return ""


def _dict_from_attachment(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return copy.deepcopy(item)

    data: dict[str, Any] = {}

    try:
        raw = vars(item)
    except Exception:
        raw = {}

    if isinstance(raw, dict):
        data.update(raw)

    for key in _PATH_KEYS + tuple(_SUMMARY_KEYS) + ("mime_type", "content_type", "type", "size", "size_bytes"):
        if key in data:
            continue

        try:
            value = getattr(item, key)
        except Exception:
            value = None

        if value is not None:
            data[key] = value

    return data


def _already_has_context(data: dict[str, Any]) -> bool:
    for key in _SUMMARY_KEYS:
        value = data.get(key)

        if _stringify(value).strip():
            return True

    return False


def _candidate_path_strings(data: dict[str, Any]) -> list[str]:
    values: list[str] = []

    for key in _PATH_KEYS:
        value = _stringify(data.get(key)).strip()

        if value:
            values.append(value)

    return values


def _extract_upload_name(value: str) -> str:
    value = value.strip().replace("\\", "/")

    if not value:
        return ""

    marker = "/api/uploads/"

    if marker in value:
        return value.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]

    marker = "api/uploads/"

    if marker in value:
        return value.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]

    marker = "/uploads/"

    if marker in value:
        return value.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]

    if value.startswith("uploads/"):
        return value.split("uploads/", 1)[1].split("?", 1)[0].split("#", 1)[0]

    return value.split("?", 1)[0].split("#", 1)[0]


def _safe_resolve_upload_path(data: dict[str, Any], uploads_dir: Path | None = None) -> Path | None:
    base = (uploads_dir or Path.cwd() / "uploads").resolve()

    for raw in _candidate_path_strings(data):
        name = _extract_upload_name(raw)

        if not name:
            continue

        # Prevent traversal by only allowing the final filename inside uploads/.
        safe_name = Path(name).name

        if not safe_name:
            continue

        candidate = (base / safe_name).resolve()

        try:
            candidate.relative_to(base)
        except Exception:
            continue

        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def _compact_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = text.strip()

    if len(text) > _MAX_EXTRACTED_CHARS:
        text = text[:_MAX_EXTRACTED_CHARS].rstrip() + "..."

    return text


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()[:_MAX_READ_BYTES]

    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
            return _compact_text(json.dumps(parsed, ensure_ascii=False, indent=2))
        except Exception:
            pass

    return _compact_text(raw.decode("utf-8", errors="replace"))


def _read_docx(path: Path) -> str:
    chunks: list[str] = []

    with zipfile.ZipFile(path) as archive:
        with archive.open("word/document.xml") as handle:
            root = ET.fromstring(handle.read())

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    for node in root.iter(namespace + "t"):
        if node.text:
            chunks.append(node.text)

    return _compact_text(" ".join(chunks))


def extract_local_upload_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in _TEXT_SUFFIXES:
        return _read_text_file(path)

    if suffix == ".docx":
        return _read_docx(path)

    return ""


def hydrate_attachment_for_context(item: Any, uploads_dir: Path | None = None) -> Any:
    data = _dict_from_attachment(item)

    if not data:
        return item

    if _already_has_context(data):
        return data

    path = _safe_resolve_upload_path(data, uploads_dir=uploads_dir)

    if not path:
        return data

    try:
        extracted = extract_local_upload_text(path)
    except Exception:
        extracted = ""

    if extracted:
        data["extracted_text"] = extracted
        data["attachment_summary"] = f"Extracted text from uploaded file {path.name}: {extracted}"

        if not data.get("filename") and not data.get("name"):
            data["filename"] = path.name

        if not data.get("size_bytes"):
            try:
                data["size_bytes"] = path.stat().st_size
            except Exception:
                pass

    return data


def hydrate_attachments_for_context(
    attachments: list[Any] | tuple[Any, ...] | None,
    uploads_dir: Path | None = None,
) -> list[Any]:
    return [
        hydrate_attachment_for_context(item, uploads_dir=uploads_dir)
        for item in list(attachments or [])
    ]

# NOVA_ATTACHMENT_HYDRATOR_REGRESSION_REPAIR_20260705
def _nova_restore_original_upload_name(filename):
    import re

    text = str(filename or "").replace("\\", "/").rstrip("/").split("/")[-1]
    return re.sub(r"_([0-9a-fA-F]{32})(?=\.)", "", text)


def _nova_upload_candidate_path(item):
    from pathlib import Path
    from urllib.parse import urlparse, unquote

    if not isinstance(item, dict):
        return None

    raw = ""

    for key in (
        "local_path",
        "file_path",
        "filepath",
        "saved_path",
        "server_path",
        "path",
        "download_url",
        "file_url",
        "url",
        "href",
        "src",
        "filename",
        "saved_filename",
        "name",
    ):
        value = item.get(key)

        if value:
            raw = str(value)
            break

    if not raw:
        return None

    parsed = urlparse(raw)
    path_text = unquote(parsed.path or raw)
    filename = path_text.replace("\\", "/").rstrip("/").split("/")[-1]

    if not filename or filename in {".", ".."}:
        return None

    uploads_dir = (Path.cwd() / "uploads").resolve()
    candidate = (uploads_dir / filename).resolve()

    try:
        candidate.relative_to(uploads_dir)
    except ValueError:
        return None

    if candidate.exists() and candidate.is_file():
        return candidate

    return None


def _nova_can_read_as_text(path, item):
    suffix = path.suffix.lower()
    mime = str(item.get("mime_type") or item.get("content_type") or "").lower()

    if "text" in mime:
        return True

    return suffix in {
        ".txt",
        ".md",
        ".csv",
        ".json",
        ".html",
        ".htm",
        ".css",
        ".js",
        ".py",
        ".log",
        ".xml",
        ".yaml",
        ".yml",
    }


def hydrate_attachments_for_context(attachments):
    output = []

    for item in list(attachments or []):
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = {
                "filename": getattr(item, "filename", None) or getattr(item, "name", None),
                "mime_type": getattr(item, "mime_type", None) or getattr(item, "content_type", None),
            }

        saved_name = (
            data.get("saved_filename")
            or data.get("filename")
            or data.get("download_url")
            or data.get("file_url")
            or data.get("url")
            or data.get("path")
            or data.get("name")
        )

        original_name = (
            data.get("original_filename")
            or data.get("display_name")
            or _nova_restore_original_upload_name(saved_name)
        )

        if original_name:
            data.setdefault("original_filename", original_name)
            data.setdefault("display_name", original_name)

        path = _nova_upload_candidate_path(data)

        if path is not None:
            try:
                data.setdefault("size_bytes", path.stat().st_size)
            except Exception:
                pass

            has_summary = any(
                data.get(key)
                for key in (
                    "summary",
                    "attachment_summary",
                    "analysis",
                    "description",
                    "caption",
                    "ocr_text",
                    "extracted_text",
                    "text",
                    "content",
                    "body",
                    "preview",
                )
            )

            if not has_summary and _nova_can_read_as_text(path, data):
                try:
                    extracted = path.read_text(encoding="utf-8", errors="replace").strip()
                except Exception:
                    extracted = ""

                if extracted:
                    if len(extracted) > 1400:
                        extracted = extracted[:1400].rstrip() + "..."

                    data["extracted_text"] = extracted
                    data["attachment_summary"] = extracted
                    data["summary"] = extracted

        output.append(data)

    return output
