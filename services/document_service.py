# notepad C:\Users\Owner\nova\services\document_service.py
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================================================
# config
# =========================================================

MAX_RAW_CHARS = 30000
MAX_PROMPT_CHARS = 8000
MAX_ROWS = 40
MAX_JSON_ITEMS = 80
MAX_SNIPPET_CHARS = 4000
MAX_SUMMARY_CHARS = 600

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".log",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".xml",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
}
DOCUMENT_MIME_PREFIXES = ("text/",)
DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/json",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/csv",
    "application/x-csv",
    "application/xml",
    "text/xml",
    "text/html",
    "application/xhtml+xml",
}

# =========================================================
# optional imports
# =========================================================

try:
    from services.pdf_service import analyze_pdf_attachment as _pdf_analyze
except Exception:
    _pdf_analyze = None


# =========================================================
# helpers
# =========================================================

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _collapse_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value)).strip()


def _truncate(value: Any, limit: int) -> str:
    text = _clean_text(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "...(truncated)"


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _safe_read_text(path: Path, limit: int = MAX_RAW_CHARS) -> str:
    raw = path.read_bytes()[:limit]
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding, errors="ignore")
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extension(name: str) -> str:
    return Path(name).suffix.lower().strip()


def is_document_attachment(attachment: Dict[str, Any]) -> bool:
    attachment = _coerce_dict(attachment)
    name = _clean_text(attachment.get("name"))
    mime_type = _clean_text(attachment.get("mime_type") or attachment.get("type"))
    ext = _extension(name)

    if ext in DOCUMENT_EXTENSIONS:
        return True
    if mime_type in DOCUMENT_MIME_TYPES:
        return True
    return any(mime_type.startswith(prefix) for prefix in DOCUMENT_MIME_PREFIXES)


def _preview_lines(text: str, max_lines: int = 40) -> str:
    lines = _clean_text(text).splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + "\n...(truncated)"


def _file_exists(path_value: str) -> Optional[Path]:
    path_value = _clean_text(path_value).strip()
    if not path_value:
        return None
    path = Path(path_value)
    if path.exists() and path.is_file():
        return path
    return None


def _read_json_preview(path: Path) -> Dict[str, Any]:
    result = {
        "summary": "JSON document attached.",
        "snippet": "",
        "prompt_text": "",
        "meta": {},
    }

    raw = _safe_read_text(path, limit=MAX_RAW_CHARS)
    try:
        parsed = json.loads(raw)
    except Exception:
        snippet = _truncate(raw, MAX_SNIPPET_CHARS)
        result["summary"] = "JSON-like document attached (raw parse fallback)."
        result["snippet"] = snippet
        result["prompt_text"] = f"Attached JSON/raw file:\n{_truncate(raw, MAX_PROMPT_CHARS)}"
        result["meta"] = {"mode": "raw_fallback"}
        return result

    if isinstance(parsed, dict):
        keys = list(parsed.keys())[:MAX_JSON_ITEMS]
        compact = json.dumps({k: parsed[k] for k in keys}, indent=2, ensure_ascii=False)
        snippet = _truncate(compact, MAX_SNIPPET_CHARS)
        result["summary"] = f"JSON object attached with {len(parsed)} top-level keys."
        result["snippet"] = snippet
        result["prompt_text"] = f"Attached JSON object preview:\n{_truncate(compact, MAX_PROMPT_CHARS)}"
        result["meta"] = {"mode": "json_object", "top_level_keys": keys}
        return result

    if isinstance(parsed, list):
        sample = parsed[:MAX_JSON_ITEMS]
        compact = json.dumps(sample, indent=2, ensure_ascii=False)
        snippet = _truncate(compact, MAX_SNIPPET_CHARS)
        result["summary"] = f"JSON array attached with {len(parsed)} items."
        result["snippet"] = snippet
        result["prompt_text"] = f"Attached JSON array preview:\n{_truncate(compact, MAX_PROMPT_CHARS)}"
        result["meta"] = {"mode": "json_array", "sample_count": len(sample)}
        return result

    compact = json.dumps(parsed, indent=2, ensure_ascii=False)
    snippet = _truncate(compact, MAX_SNIPPET_CHARS)
    result["summary"] = "JSON value attached."
    result["snippet"] = snippet
    result["prompt_text"] = f"Attached JSON value:\n{_truncate(compact, MAX_PROMPT_CHARS)}"
    result["meta"] = {"mode": "json_scalar"}
    return result


def _read_csv_preview(path: Path) -> Dict[str, Any]:
    result = {
        "summary": "CSV document attached.",
        "snippet": "",
        "prompt_text": "",
        "meta": {},
    }

    rows: List[List[str]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx >= MAX_ROWS:
                break
            rows.append([_clean_text(cell) for cell in row])

    if not rows:
        result["summary"] = "CSV attached but appears empty."
        result["meta"] = {"row_count": 0}
        return result

    header = rows[0]
    body = rows[1:]
    lines = []
    if header:
        lines.append(" | ".join(header))
        lines.append("-" * min(120, max(12, len(" | ".join(header)))))
    for row in body:
        lines.append(" | ".join(row))

    preview = "\n".join(lines)
    snippet = _truncate(preview, MAX_SNIPPET_CHARS)

    result["summary"] = f"CSV attached with {len(rows)} preview rows and {len(header)} columns."
    result["snippet"] = snippet
    result["prompt_text"] = f"Attached CSV preview:\n{_truncate(preview, MAX_PROMPT_CHARS)}"
    result["meta"] = {
        "row_count_preview": len(rows),
        "column_count": len(header),
        "header": header,
    }
    return result


def _read_plaintext_preview(path: Path) -> Dict[str, Any]:
    raw = _safe_read_text(path, limit=MAX_RAW_CHARS)
    cleaned = _preview_lines(raw, max_lines=40)
    snippet = _truncate(cleaned, MAX_SNIPPET_CHARS)

    nonempty_lines = [line for line in raw.splitlines() if line.strip()]
    summary = f"Text document attached with {len(nonempty_lines)} non-empty preview lines."

    return {
        "summary": _truncate(summary, MAX_SUMMARY_CHARS),
        "snippet": snippet,
        "prompt_text": f"Attached document content:\n{_truncate(raw, MAX_PROMPT_CHARS)}",
        "meta": {
            "chars_read": len(raw),
            "nonempty_lines_preview": len(nonempty_lines[:40]),
        },
    }


def _read_markup_preview(path: Path, label: str) -> Dict[str, Any]:
    raw = _safe_read_text(path, limit=MAX_RAW_CHARS)
    cleaned = _preview_lines(raw, max_lines=40)
    snippet = _truncate(cleaned, MAX_SNIPPET_CHARS)

    title_match = re.search(r"<title>(.*?)</title>", raw, flags=re.IGNORECASE | re.DOTALL)
    title = _collapse_ws(title_match.group(1)) if title_match else ""

    summary = f"{label} document attached."
    if title:
        summary += f" Title: {title}"

    return {
        "summary": _truncate(summary, MAX_SUMMARY_CHARS),
        "snippet": snippet,
        "prompt_text": f"Attached {label.lower()} preview:\n{_truncate(raw, MAX_PROMPT_CHARS)}",
        "meta": {
            "title": title,
            "chars_read": len(raw),
        },
    }


def _fallback_missing_result(attachment: Dict[str, Any], reason: str) -> Dict[str, Any]:
    name = _clean_text(attachment.get("name")) or "document"
    mime_type = _clean_text(attachment.get("mime_type") or attachment.get("type"))
    return {
        "id": attachment.get("id"),
        "name": name,
        "mime_type": mime_type,
        "type": "document",
        "summary": _truncate(reason, MAX_SUMMARY_CHARS),
        "snippet": "",
        "prompt_text": f"Attached document: {name}",
        "status": "missing_file",
        "meta": {},
    }


# =========================================================
# public analyzer
# =========================================================

def analyze_document_attachment(attachment: Dict[str, Any]) -> Dict[str, Any]:
    attachment = _coerce_dict(attachment)

    name = _clean_text(attachment.get("name")) or "document"
    mime_type = _clean_text(attachment.get("mime_type") or attachment.get("type"))
    path = _file_exists(_clean_text(attachment.get("stored_path") or attachment.get("path")))

    base = {
        "id": attachment.get("id"),
        "name": name,
        "mime_type": mime_type,
        "type": "document",
        "summary": "",
        "snippet": "",
        "prompt_text": "",
        "status": "ready",
        "meta": {},
    }

    if not is_document_attachment(attachment):
        base["status"] = "skipped"
        base["summary"] = "Attachment is not recognized as a document."
        base["prompt_text"] = f"Attached file: {name}"
        return base

    if not path:
        return _fallback_missing_result(attachment, "Document file is unavailable.")

    ext = _extension(name)

    try:
        if ext == ".pdf" or mime_type == "application/pdf":
            if _pdf_analyze:
                pdf_result = _pdf_analyze(
                    {
                        "id": attachment.get("id"),
                        "name": name,
                        "mime_type": mime_type or "application/pdf",
                        "stored_path": str(path),
                    }
                )
                if isinstance(pdf_result, dict):
                    base["summary"] = _truncate(pdf_result.get("summary", "PDF attached."), MAX_SUMMARY_CHARS)
                    base["snippet"] = _truncate(
                        pdf_result.get("snippet") or pdf_result.get("text") or pdf_result.get("prompt_text") or "",
                        MAX_SNIPPET_CHARS,
                    )
                    base["prompt_text"] = _truncate(
                        pdf_result.get("prompt_text")
                        or pdf_result.get("snippet")
                        or pdf_result.get("text")
                        or f"Attached PDF: {name}",
                        MAX_PROMPT_CHARS,
                    )
                    base["status"] = _clean_text(pdf_result.get("status")) or "ready"
                    base["meta"] = _coerce_dict(pdf_result.get("meta"))
                    return base

            base["summary"] = "PDF attached and available for downstream processing."
            base["prompt_text"] = f"Attached PDF: {name}"
            base["status"] = "ready"
            return base

        if ext == ".json" or mime_type == "application/json":
            preview = _read_json_preview(path)
        elif ext == ".csv" or "csv" in mime_type:
            preview = _read_csv_preview(path)
        elif ext in {".html", ".htm"} or "html" in mime_type:
            preview = _read_markup_preview(path, "HTML")
        elif ext == ".xml" or "xml" in mime_type:
            preview = _read_markup_preview(path, "XML")
        else:
            preview = _read_plaintext_preview(path)

        base["summary"] = _truncate(preview.get("summary", f"Document attached: {name}"), MAX_SUMMARY_CHARS)
        base["snippet"] = _truncate(preview.get("snippet", ""), MAX_SNIPPET_CHARS)
        base["prompt_text"] = _truncate(
            preview.get("prompt_text") or preview.get("snippet") or f"Attached document: {name}",
            MAX_PROMPT_CHARS,
        )
        base["meta"] = _coerce_dict(preview.get("meta"))
        base["status"] = "ready"
        return base

    except Exception as exc:
        base["status"] = "error"
        base["summary"] = _truncate(f"Failed to analyze document: {exc}", MAX_SUMMARY_CHARS)
        base["prompt_text"] = f"Attached document: {name}"
        return base