# notepad C:\Users\Owner\nova\services\document_service.py
from __future__ import annotations

import csv
import json
import re
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================================================
# config
# =========================================================

MAX_RAW_TEXT_CHARS = 40000
MAX_EXTRACT_TEXT_CHARS = 24000
MAX_SUMMARY_CHARS = 1200
MAX_PREVIEW_CHARS = 360
MAX_CHUNKS = 12
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 180
MAX_CSV_ROWS = 60
MAX_JSON_ITEMS = 80

DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".log",
    ".pdf",
    ".xml",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".log",
    ".xml",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
}

STRUCTURED_EXTENSIONS = {
    ".json",
    ".csv",
}

TEXTUAL_MIME_PREFIXES = ("text/",)
TEXTUAL_MIME_TYPES = {
    "application/json",
    "application/xml",
    "text/xml",
    "application/csv",
    "text/csv",
    "application/x-csv",
    "text/markdown",
    "application/yaml",
    "text/yaml",
    "application/x-yaml",
}
PDF_MIME_TYPES = {"application/pdf"}


# =========================================================
# generic helpers
# =========================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def extension_for_path(path: Path) -> str:
    return path.suffix.lower().strip()


def guess_kind(path: Path, mime_type: str = "") -> str:
    ext = extension_for_path(path)
    mime_type = clean_text(mime_type).lower()

    if ext == ".pdf" or mime_type in PDF_MIME_TYPES:
        return "pdf"
    if ext in STRUCTURED_EXTENSIONS:
        return "structured"
    if ext in TEXT_EXTENSIONS:
        return "text"
    if mime_type in TEXTUAL_MIME_TYPES or any(mime_type.startswith(p) for p in TEXTUAL_MIME_PREFIXES):
        return "text"
    return "document"


def looks_like_binary(raw: bytes) -> bool:
    if not raw:
        return False
    if b"\x00" in raw[:4096]:
        return True
    sample = raw[:4096]
    weird = 0
    for b in sample:
        if b in (9, 10, 13):
            continue
        if b < 32 or b > 126:
            weird += 1
    return weird > max(24, len(sample) // 5)


def read_text_file(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except Exception:
        return ""

    if looks_like_binary(raw):
        return ""

    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding, errors="replace")
        except Exception:
            continue
    return ""


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def strip_html(html: str) -> str:
    if not html:
        return ""
    html = unescape(html)
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p\s*>", "\n\n", html)
    html = re.sub(r"(?i)</div\s*>", "\n", html)
    html = re.sub(r"(?i)</li\s*>", "\n", html)
    html = re.sub(r"(?i)<li[^>]*>", "- ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return clean_text(html)


# =========================================================
# summary + chunk helpers
# =========================================================

def sentence_split(text: str) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [clean_text(x) for x in parts if clean_text(x)]


def summarize_text(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    text = clean_text(text)
    if not text:
        return ""

    parts = sentence_split(text)
    if not parts:
        return truncate(text, limit)

    kept: List[str] = []
    total = 0

    for part in parts:
        if total + len(part) > limit:
            break
        kept.append(part)
        total += len(part) + 1
        if len(kept) >= 6:
            break

    if not kept:
        return truncate(text, limit)

    return truncate(" ".join(kept), limit)


def preview_text(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    return truncate(compact_whitespace(text), limit)


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = clean_text(text)
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length and len(chunks) < MAX_CHUNKS:
        end = min(length, start + chunk_size)
        piece = text[start:end]

        if end < length:
            split_at = max(piece.rfind("\n\n"), piece.rfind(". "), piece.rfind("\n"), piece.rfind(" "))
            if split_at > max(200, chunk_size // 3):
                piece = piece[:split_at + 1]
                end = start + len(piece)

        piece = clean_text(piece)
        if piece:
            chunks.append(piece)

        if end >= length:
            break

        start = max(end - overlap, start + 1)

    return chunks


# =========================================================
# structured formatting helpers
# =========================================================

def flatten_json(
    value: Any,
    *,
    prefix: str = "",
    out: Optional[List[str]] = None,
    max_items: int = MAX_JSON_ITEMS,
) -> List[str]:
    if out is None:
        out = []

    if len(out) >= max_items:
        return out

    if isinstance(value, dict):
        for key, subvalue in value.items():
            if len(out) >= max_items:
                break
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            flatten_json(subvalue, prefix=new_prefix, out=out, max_items=max_items)
        return out

    if isinstance(value, list):
        for idx, subvalue in enumerate(value):
            if len(out) >= max_items:
                break
            new_prefix = f"{prefix}[{idx}]"
            flatten_json(subvalue, prefix=new_prefix, out=out, max_items=max_items)
        return out

    value_text = clean_text(value)
    if value_text:
        out.append(f"{prefix}: {truncate(value_text, 240)}")
    return out


def parse_json_file(path: Path) -> Dict[str, Any]:
    raw = read_text_file(path)
    if not raw:
        return {
            "text": "",
            "summary": "",
            "preview": "",
            "metadata": {"format": "json", "parse_ok": False},
        }

    try:
        parsed = json.loads(raw)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
        flat = flatten_json(parsed)
        flattened_text = "\n".join(flat)
        final_text = truncate(pretty, MAX_EXTRACT_TEXT_CHARS)

        if flattened_text:
            summary_source = flattened_text
        else:
            summary_source = final_text

        return {
            "text": final_text,
            "summary": summarize_text(summary_source),
            "preview": preview_text(summary_source),
            "metadata": {
                "format": "json",
                "parse_ok": True,
                "top_level_type": type(parsed).__name__,
                "flattened_items": len(flat),
            },
        }
    except Exception:
        fallback = truncate(raw, MAX_EXTRACT_TEXT_CHARS)
        return {
            "text": fallback,
            "summary": summarize_text(fallback),
            "preview": preview_text(fallback),
            "metadata": {"format": "json", "parse_ok": False},
        }


def parse_csv_file(path: Path) -> Dict[str, Any]:
    raw = read_text_file(path)
    if not raw:
        return {
            "text": "",
            "summary": "",
            "preview": "",
            "metadata": {"format": "csv", "parse_ok": False},
        }

    lines: List[str] = []
    row_count = 0
    column_count = 0

    try:
        reader = csv.reader(raw.splitlines())
        for idx, row in enumerate(reader):
            row_count += 1
            column_count = max(column_count, len(row))
            if idx >= MAX_CSV_ROWS:
                continue
            cleaned = [truncate(compact_whitespace(cell), 120) for cell in row]
            lines.append(" | ".join(cleaned))

        text = truncate("\n".join(lines), MAX_EXTRACT_TEXT_CHARS)
        summary_bits = []
        if lines:
            header = lines[0]
            summary_bits.append(f"CSV with about {row_count} rows and {column_count} columns.")
            summary_bits.append(f"Header/sample: {truncate(header, 260)}")
        summary = truncate(" ".join(summary_bits).strip() or summarize_text(text), MAX_SUMMARY_CHARS)

        return {
            "text": text,
            "summary": summary,
            "preview": preview_text(text),
            "metadata": {
                "format": "csv",
                "parse_ok": True,
                "rows": row_count,
                "columns": column_count,
                "sample_rows": min(row_count, MAX_CSV_ROWS),
            },
        }
    except Exception:
        fallback = truncate(raw, MAX_EXTRACT_TEXT_CHARS)
        return {
            "text": fallback,
            "summary": summarize_text(fallback),
            "preview": preview_text(fallback),
            "metadata": {"format": "csv", "parse_ok": False},
        }


# =========================================================
# pdf integration
# =========================================================

def parse_pdf_file(path: Path) -> Dict[str, Any]:
    try:
        from services.pdf_service import analyze_pdf_attachment  # type: ignore
    except Exception:
        analyze_pdf_attachment = None  # type: ignore

    if callable(analyze_pdf_attachment):
        try:
            result = analyze_pdf_attachment(path)
            if isinstance(result, dict):
                text = clean_text(
                    result.get("text")
                    or result.get("content")
                    or result.get("body")
                    or result.get("summary")
                )
                text = truncate(text, MAX_EXTRACT_TEXT_CHARS)
                summary = clean_text(result.get("summary")) or summarize_text(text)
                preview = clean_text(result.get("preview")) or preview_text(text)
                metadata = safe_dict(result.get("metadata"))
                metadata["format"] = "pdf"
                metadata["parse_ok"] = True
                return {
                    "text": text,
                    "summary": truncate(summary, MAX_SUMMARY_CHARS),
                    "preview": truncate(preview, MAX_PREVIEW_CHARS),
                    "metadata": metadata,
                }
            if isinstance(result, str):
                text = truncate(clean_text(result), MAX_EXTRACT_TEXT_CHARS)
                return {
                    "text": text,
                    "summary": summarize_text(text),
                    "preview": preview_text(text),
                    "metadata": {"format": "pdf", "parse_ok": True},
                }
        except Exception:
            pass

    return {
        "text": "",
        "summary": "PDF attached, but text extraction was unavailable.",
        "preview": "PDF attached, but text extraction was unavailable.",
        "metadata": {"format": "pdf", "parse_ok": False},
    }


# =========================================================
# generic document analyzers
# =========================================================

def parse_plain_text_file(path: Path) -> Dict[str, Any]:
    ext = extension_for_path(path)
    raw = read_text_file(path)
    if not raw:
        return {
            "text": "",
            "summary": "",
            "preview": "",
            "metadata": {"format": ext.lstrip(".") or "text", "parse_ok": False},
        }

    if ext in {".html", ".htm"}:
        text = strip_html(raw)
    else:
        text = clean_text(raw)

    text = truncate(text, MAX_EXTRACT_TEXT_CHARS)

    return {
        "text": text,
        "summary": summarize_text(text),
        "preview": preview_text(text),
        "metadata": {
            "format": ext.lstrip(".") or "text",
            "parse_ok": True,
            "characters": len(text),
        },
    }


def analyze_document_attachment(path: Path | str, mime_type: str = "") -> Dict[str, Any]:
    path = Path(path)
    exists = path.exists()
    ext = extension_for_path(path)
    mime_type = clean_text(mime_type).lower()
    kind = guess_kind(path, mime_type)

    result: Dict[str, Any] = {
        "ok": exists,
        "path": str(path),
        "name": path.name,
        "filename": path.name,
        "extension": ext,
        "mime_type": mime_type,
        "kind": kind,
        "text": "",
        "summary": "",
        "preview": "",
        "chunks": [],
        "metadata": {
            "exists": exists,
            "format": ext.lstrip(".") or kind,
            "parse_ok": False,
            "size_bytes": path.stat().st_size if exists else 0,
        },
        "error": None,
    }

    if not exists:
        result["error"] = {"code": "file_not_found", "message": "Document path does not exist."}
        return result

    try:
        if ext == ".pdf" or mime_type in PDF_MIME_TYPES:
            parsed = parse_pdf_file(path)
        elif ext == ".json":
            parsed = parse_json_file(path)
        elif ext == ".csv":
            parsed = parse_csv_file(path)
        else:
            parsed = parse_plain_text_file(path)

        text = truncate(clean_text(parsed.get("text")), MAX_EXTRACT_TEXT_CHARS)
        summary = truncate(clean_text(parsed.get("summary")) or summarize_text(text), MAX_SUMMARY_CHARS)
        preview = truncate(clean_text(parsed.get("preview")) or preview_text(text or summary), MAX_PREVIEW_CHARS)
        chunks = split_into_chunks(text)

        metadata = {
            **safe_dict(result.get("metadata")),
            **safe_dict(parsed.get("metadata")),
        }
        metadata["parse_ok"] = bool(text or summary or preview)
        metadata["chunk_count"] = len(chunks)
        metadata["characters"] = len(text)

        result.update(
            {
                "text": text,
                "summary": summary,
                "preview": preview,
                "chunks": chunks,
                "metadata": metadata,
                "error": None,
            }
        )
        return result

    except Exception as exc:
        fallback_text = ""
        try:
            fallback_text = truncate(clean_text(read_text_file(path)), MAX_EXTRACT_TEXT_CHARS)
        except Exception:
            fallback_text = ""

        result["text"] = fallback_text
        result["summary"] = summarize_text(fallback_text) if fallback_text else ""
        result["preview"] = preview_text(fallback_text) if fallback_text else ""
        result["chunks"] = split_into_chunks(fallback_text) if fallback_text else []
        result["metadata"] = {
            **safe_dict(result.get("metadata")),
            "parse_ok": bool(fallback_text),
            "chunk_count": len(result["chunks"]),
            "characters": len(result["text"]),
        }
        result["error"] = {
            "code": "document_parse_failed",
            "message": str(exc),
        }
        return result


# =========================================================
# prompt shaping
# =========================================================

def build_document_prompt_context(path: Path | str, mime_type: str = "") -> Dict[str, Any]:
    analyzed = analyze_document_attachment(path, mime_type=mime_type)

    chunks = safe_list(analyzed.get("chunks"))
    selected_chunks = chunks[:6]

    lines: List[str] = []
    name = clean_text(analyzed.get("name") or "document")
    summary = clean_text(analyzed.get("summary"))
    preview = clean_text(analyzed.get("preview"))

    lines.append(f"Document: {name}")
    if summary:
        lines.append(f"Summary: {summary}")
    elif preview:
        lines.append(f"Preview: {preview}")

    if selected_chunks:
        lines.append("Relevant text:")
        for idx, chunk in enumerate(selected_chunks, 1):
            chunk_text = truncate(clean_text(chunk), 1200)
            if chunk_text:
                lines.append(f"[Chunk {idx}] {chunk_text}")

    return {
        "ok": bool(analyzed.get("ok")),
        "document": analyzed,
        "prompt_text": "\n".join(lines).strip(),
    }


def summarize_document(path: Path | str, mime_type: str = "") -> str:
    analyzed = analyze_document_attachment(path, mime_type=mime_type)
    summary = clean_text(analyzed.get("summary"))
    if summary:
        return summary
    text = clean_text(analyzed.get("text"))
    return summarize_text(text)


def preview_document(path: Path | str, mime_type: str = "") -> str:
    analyzed = analyze_document_attachment(path, mime_type=mime_type)
    preview = clean_text(analyzed.get("preview"))
    if preview:
        return preview
    text = clean_text(analyzed.get("text"))
    return preview_text(text)


def extract_document_text(path: Path | str, mime_type: str = "") -> str:
    analyzed = analyze_document_attachment(path, mime_type=mime_type)
    return clean_text(analyzed.get("text"))


def extract_document_chunks(path: Path | str, mime_type: str = "") -> List[str]:
    analyzed = analyze_document_attachment(path, mime_type=mime_type)
    return [clean_text(x) for x in safe_list(analyzed.get("chunks")) if clean_text(x)]


# =========================================================
# multi-doc helpers
# =========================================================

def analyze_many_documents(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    analyzed: List[Dict[str, Any]] = []

    for raw in safe_list(items):
        item = safe_dict(raw)
        path_value = clean_text(item.get("path"))
        if not path_value:
            continue
        mime_type = clean_text(item.get("mime_type"))
        result = analyze_document_attachment(path_value, mime_type=mime_type)

        analyzed.append(
            {
                "id": clean_text(item.get("id")),
                "path": path_value,
                "name": clean_text(item.get("name") or result.get("name")),
                "mime_type": mime_type,
                "summary": clean_text(result.get("summary")),
                "preview": clean_text(result.get("preview")),
                "text": clean_text(result.get("text")),
                "chunks": safe_list(result.get("chunks")),
                "metadata": safe_dict(result.get("metadata")),
                "error": result.get("error"),
            }
        )

    return {
        "ok": True,
        "count": len(analyzed),
        "documents": analyzed,
    }


def documents_to_prompt_text(items: List[Dict[str, Any]]) -> str:
    result = analyze_many_documents(items)
    docs = safe_list(result.get("documents"))
    lines: List[str] = []

    if not docs:
        return ""

    lines.append("Document context:")
    for doc in docs[:8]:
        d = safe_dict(doc)
        name = clean_text(d.get("name") or "document")
        summary = clean_text(d.get("summary") or d.get("preview"))
        lines.append(f"- {name}")
        if summary:
            lines.append(f"  {truncate(summary, MAX_SUMMARY_CHARS)}")

        chunks = [clean_text(x) for x in safe_list(d.get("chunks")) if clean_text(x)]
        for idx, chunk in enumerate(chunks[:3], 1):
            lines.append(f"  [Chunk {idx}] {truncate(chunk, 700)}")

    return "\n".join(lines).strip()