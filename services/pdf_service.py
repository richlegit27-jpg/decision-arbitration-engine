# notepad C:\Users\Owner\nova\services\pdf_service.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================================================
# config
# =========================================================

MAX_PAGES = 12
MAX_CHARS_PER_PAGE = 5000
MAX_TOTAL_RAW_CHARS = 30000
MAX_SNIPPET_CHARS = 4000
MAX_PROMPT_CHARS = 8000
MAX_SUMMARY_CHARS = 600

# =========================================================
# optional imports
# =========================================================

_PDF_BACKEND = "none"

try:
    from pypdf import PdfReader  # type: ignore

    _PDF_BACKEND = "pypdf"
except Exception:
    PdfReader = None  # type: ignore

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


def _file_exists(path_value: str) -> Optional[Path]:
    path_value = _clean_text(path_value).strip()
    if not path_value:
        return None
    path = Path(path_value)
    if path.exists() and path.is_file():
        return path
    return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_page_text(value: Any) -> str:
    text = _clean_text(value)
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _estimate_words(text: str) -> int:
    if not text.strip():
        return 0
    return len(re.findall(r"\b\w+\b", text))


def _build_snippet(page_blocks: List[str]) -> str:
    joined = "\n\n".join(block for block in page_blocks if block.strip())
    return _truncate(joined, MAX_SNIPPET_CHARS)


def _build_prompt_text(name: str, page_blocks: List[str], page_count: int) -> str:
    parts: List[str] = [f"Attached PDF: {name}", f"PDF page count: {page_count}"]
    if page_blocks:
        parts.append("Extracted PDF text preview:")
        parts.append("\n\n".join(page_blocks))
    return _truncate("\n".join(parts), MAX_PROMPT_CHARS)


def _fallback_result(
    attachment: Dict[str, Any],
    *,
    name: str,
    mime_type: str,
    summary: str,
    status: str,
    meta: Optional[Dict[str, Any]] = None,
    snippet: str = "",
    prompt_text: str = "",
) -> Dict[str, Any]:
    return {
        "id": attachment.get("id"),
        "name": name,
        "mime_type": mime_type or "application/pdf",
        "type": "document",
        "summary": _truncate(summary, MAX_SUMMARY_CHARS),
        "snippet": _truncate(snippet, MAX_SNIPPET_CHARS),
        "prompt_text": _truncate(prompt_text or f"Attached PDF: {name}", MAX_PROMPT_CHARS),
        "text": _truncate(snippet, MAX_TOTAL_RAW_CHARS),
        "status": status,
        "meta": meta or {},
    }


# =========================================================
# extraction
# =========================================================


def _extract_with_pypdf(path: Path) -> Dict[str, Any]:
    if PdfReader is None:
        raise RuntimeError("pypdf backend unavailable")

    reader = PdfReader(str(path))
    total_pages = len(reader.pages)

    page_blocks: List[str] = []
    collected_text_parts: List[str] = []
    pages_with_text = 0
    pages_processed = 0

    for index, page in enumerate(reader.pages[:MAX_PAGES]):
        pages_processed += 1
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""

        normalized = _normalize_page_text(raw_text)
        if normalized:
            pages_with_text += 1
            trimmed = _truncate(normalized, MAX_CHARS_PER_PAGE)
            page_label = f"[Page {index + 1}]"
            block = f"{page_label}\n{trimmed}"
            page_blocks.append(block)
            collected_text_parts.append(trimmed)

        current_size = sum(len(part) for part in collected_text_parts)
        if current_size >= MAX_TOTAL_RAW_CHARS:
            break

    extracted_text = "\n\n".join(collected_text_parts)
    snippet = _build_snippet(page_blocks)
    word_count_preview = _estimate_words(extracted_text)

    return {
        "page_count": total_pages,
        "pages_processed": pages_processed,
        "pages_with_text": pages_with_text,
        "text": _truncate(extracted_text, MAX_TOTAL_RAW_CHARS),
        "snippet": snippet,
        "word_count_preview": word_count_preview,
        "backend": "pypdf",
    }


# =========================================================
# public analyzer
# =========================================================


def analyze_pdf_attachment(attachment: Dict[str, Any]) -> Dict[str, Any]:
    attachment = _coerce_dict(attachment)

    name = _clean_text(attachment.get("name")) or "document.pdf"
    mime_type = _clean_text(attachment.get("mime_type") or attachment.get("type") or "application/pdf")
    path = _file_exists(_clean_text(attachment.get("stored_path") or attachment.get("path")))

    if not path:
        return _fallback_result(
            attachment,
            name=name,
            mime_type=mime_type,
            summary="PDF file is unavailable.",
            status="missing_file",
            meta={},
        )

    if path.suffix.lower() != ".pdf" and mime_type != "application/pdf":
        return _fallback_result(
            attachment,
            name=name,
            mime_type=mime_type,
            summary="Attachment is not recognized as a PDF.",
            status="skipped",
            meta={},
            prompt_text=f"Attached file: {name}",
        )

    if PdfReader is None:
        return _fallback_result(
            attachment,
            name=name,
            mime_type="application/pdf",
            summary="PDF attached but PDF text extraction backend is unavailable.",
            status="ready",
            meta={
                "backend": _PDF_BACKEND,
                "page_count": 0,
                "pages_processed": 0,
                "pages_with_text": 0,
                "extractable_text": False,
            },
            prompt_text=f"Attached PDF: {name}",
        )

    try:
        extracted = _extract_with_pypdf(path)

        page_count = _safe_int(extracted.get("page_count"))
        pages_processed = _safe_int(extracted.get("pages_processed"))
        pages_with_text = _safe_int(extracted.get("pages_with_text"))
        text = _clean_text(extracted.get("text"))
        snippet = _clean_text(extracted.get("snippet"))
        word_count_preview = _safe_int(extracted.get("word_count_preview"))
        backend = _clean_text(extracted.get("backend")) or _PDF_BACKEND

        if text.strip():
            summary = (
                f"PDF attached with {page_count} pages. "
                f"Extracted text from {pages_with_text} of {pages_processed} previewed pages."
            )
            status = "ready"
            extractable_text = True
        else:
            summary = (
                f"PDF attached with {page_count} pages, but little or no extractable text was found "
                f"in the previewed pages."
            )
            status = "ready"
            extractable_text = False

        prompt_text = _build_prompt_text(name=name, page_blocks=snippet.split("\n\n") if snippet else [], page_count=page_count)

        return {
            "id": attachment.get("id"),
            "name": name,
            "mime_type": "application/pdf",
            "type": "document",
            "summary": _truncate(summary, MAX_SUMMARY_CHARS),
            "snippet": _truncate(snippet, MAX_SNIPPET_CHARS),
            "prompt_text": _truncate(prompt_text, MAX_PROMPT_CHARS),
            "text": _truncate(text, MAX_TOTAL_RAW_CHARS),
            "status": status,
            "meta": {
                "backend": backend,
                "page_count": page_count,
                "pages_processed": pages_processed,
                "pages_with_text": pages_with_text,
                "extractable_text": extractable_text,
                "word_count_preview": word_count_preview,
                "max_pages": MAX_PAGES,
                "max_chars_per_page": MAX_CHARS_PER_PAGE,
                "source_path": str(path),
            },
        }

    except Exception as exc:
        return _fallback_result(
            attachment,
            name=name,
            mime_type="application/pdf",
            summary=f"Failed to analyze PDF: {exc}",
            status="error",
            meta={
                "backend": _PDF_BACKEND,
                "source_path": str(path),
            },
            prompt_text=f"Attached PDF: {name}",
        )