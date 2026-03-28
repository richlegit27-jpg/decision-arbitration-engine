# notepad C:\Users\Owner\nova\services\pdf_service.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================================================
# config
# =========================================================

MAX_PDF_TEXT_CHARS = 24000
MAX_SUMMARY_CHARS = 1200
MAX_PREVIEW_CHARS = 360
MAX_PAGES_TO_READ = 40
MAX_CHUNKS = 12
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 180


# =========================================================
# helpers
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


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def summarize_text(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    text = clean_text(text)
    if not text:
        return ""

    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    parts = [clean_text(x) for x in parts if clean_text(x)]

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
                piece = piece[: split_at + 1]
                end = start + len(piece)

        piece = clean_text(piece)
        if piece:
            chunks.append(piece)

        if end >= length:
            break

        start = max(end - overlap, start + 1)

    return chunks


# =========================================================
# low-level extractors
# =========================================================

def _extract_with_pypdf(path: Path) -> Dict[str, Any]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:
        return {
            "ok": False,
            "engine": "pypdf",
            "pages": [],
            "page_count": 0,
            "error": f"pypdf unavailable: {exc}",
        }

    try:
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)
        pages: List[Dict[str, Any]] = []

        for index, page in enumerate(reader.pages[:MAX_PAGES_TO_READ]):
            try:
                text = clean_text(page.extract_text() or "")
            except Exception:
                text = ""
            pages.append(
                {
                    "page_number": index + 1,
                    "text": text,
                    "chars": len(text),
                }
            )

        return {
            "ok": True,
            "engine": "pypdf",
            "pages": pages,
            "page_count": total_pages,
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "engine": "pypdf",
            "pages": [],
            "page_count": 0,
            "error": str(exc),
        }


def _extract_with_pymupdf(path: Path) -> Dict[str, Any]:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        return {
            "ok": False,
            "engine": "pymupdf",
            "pages": [],
            "page_count": 0,
            "error": f"pymupdf unavailable: {exc}",
        }

    doc = None
    try:
        doc = fitz.open(str(path))
        total_pages = len(doc)
        pages: List[Dict[str, Any]] = []

        for index in range(min(total_pages, MAX_PAGES_TO_READ)):
            try:
                page = doc[index]
                text = clean_text(page.get_text("text") or "")
            except Exception:
                text = ""
            pages.append(
                {
                    "page_number": index + 1,
                    "text": text,
                    "chars": len(text),
                }
            )

        return {
            "ok": True,
            "engine": "pymupdf",
            "pages": pages,
            "page_count": total_pages,
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "engine": "pymupdf",
            "pages": [],
            "page_count": 0,
            "error": str(exc),
        }
    finally:
        try:
            if doc is not None:
                doc.close()
        except Exception:
            pass


def _pick_best_extraction(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []

    for result in results:
        pages = safe_list(result.get("pages"))
        total_chars = sum(len(clean_text(page.get("text"))) for page in pages if isinstance(page, dict))
        scored.append(
            {
                "result": result,
                "score": total_chars,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)

    if scored and scored[0]["score"] > 0:
        return safe_dict(scored[0]["result"])

    for item in scored:
        result = safe_dict(item["result"])
        if result.get("ok"):
            return result

    return safe_dict(scored[0]["result"]) if scored else {
        "ok": False,
        "engine": "none",
        "pages": [],
        "page_count": 0,
        "error": "No PDF extraction engines available.",
    }


# =========================================================
# analysis
# =========================================================

def _build_page_map(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for raw in safe_list(pages):
        page = safe_dict(raw)
        text = clean_text(page.get("text"))
        out.append(
            {
                "page_number": int(page.get("page_number") or 0),
                "text": text,
                "chars": len(text),
                "preview": preview_text(text, 180),
            }
        )

    return out


def _join_pages(pages: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []

    for raw in safe_list(pages):
        page = safe_dict(raw)
        page_number = int(page.get("page_number") or 0)
        text = clean_text(page.get("text"))
        if not text:
            continue
        blocks.append(f"[Page {page_number}]\n{text}")

    return truncate("\n\n".join(blocks).strip(), MAX_PDF_TEXT_CHARS)


def _build_pdf_summary(path: Path, text: str, page_count: int, pages_read: int) -> str:
    base = summarize_text(text, MAX_SUMMARY_CHARS)
    prefix_parts = [f"PDF document: {path.name}."]
    if page_count:
        prefix_parts.append(f"Total pages: {page_count}.")
    if pages_read and pages_read != page_count:
        prefix_parts.append(f"Pages read: {pages_read}.")
    prefix = " ".join(prefix_parts).strip()

    if base:
        return truncate(f"{prefix} {base}".strip(), MAX_SUMMARY_CHARS)

    return truncate(prefix or f"PDF document: {path.name}.", MAX_SUMMARY_CHARS)


def analyze_pdf_attachment(path: Path | str) -> Dict[str, Any]:
    path = Path(path)

    result: Dict[str, Any] = {
        "ok": False,
        "path": str(path),
        "name": path.name,
        "filename": path.name,
        "mime_type": "application/pdf",
        "kind": "document",
        "text": "",
        "content": "",
        "summary": "",
        "preview": "",
        "chunks": [],
        "pages": [],
        "metadata": {
            "exists": path.exists(),
            "format": "pdf",
            "parse_ok": False,
            "engine": None,
            "page_count": 0,
            "pages_read": 0,
            "characters": 0,
            "size_bytes": path.stat().st_size if path.exists() else 0,
        },
        "error": None,
    }

    if not path.exists():
        result["error"] = {
            "code": "file_not_found",
            "message": "PDF path does not exist.",
        }
        return result

    extraction_candidates = [
        _extract_with_pymupdf(path),
        _extract_with_pypdf(path),
    ]
    best = _pick_best_extraction(extraction_candidates)

    raw_pages = _build_page_map(safe_list(best.get("pages")))
    combined_text = _join_pages(raw_pages)
    summary = _build_pdf_summary(
        path=path,
        text=combined_text,
        page_count=int(best.get("page_count") or 0),
        pages_read=len(raw_pages),
    )
    preview = preview_text(combined_text or summary)
    chunks = split_into_chunks(combined_text)

    parse_ok = bool(combined_text or summary)
    engine = clean_text(best.get("engine"))
    error_text = clean_text(best.get("error"))

    result.update(
        {
            "ok": parse_ok,
            "text": combined_text,
            "content": combined_text,
            "summary": summary,
            "preview": preview,
            "chunks": chunks,
            "pages": raw_pages,
            "metadata": {
                **safe_dict(result.get("metadata")),
                "parse_ok": parse_ok,
                "engine": engine or None,
                "page_count": int(best.get("page_count") or 0),
                "pages_read": len(raw_pages),
                "characters": len(combined_text),
                "chunk_count": len(chunks),
            },
            "error": None if parse_ok else {
                "code": "pdf_parse_failed",
                "message": error_text or "Unable to extract text from PDF.",
            },
        }
    )

    return result


# =========================================================
# prompt helpers
# =========================================================

def build_pdf_prompt_context(path: Path | str) -> Dict[str, Any]:
    analyzed = analyze_pdf_attachment(path)

    lines: List[str] = []
    name = clean_text(analyzed.get("name") or "document")
    summary = clean_text(analyzed.get("summary"))
    chunks = [clean_text(x) for x in safe_list(analyzed.get("chunks")) if clean_text(x)]

    lines.append(f"PDF: {name}")
    if summary:
        lines.append(f"Summary: {summary}")

    if chunks:
        lines.append("Relevant text:")
        for idx, chunk in enumerate(chunks[:6], 1):
            lines.append(f"[Chunk {idx}] {truncate(chunk, 1200)}")

    return {
        "ok": bool(analyzed.get("ok")),
        "document": analyzed,
        "prompt_text": "\n".join(lines).strip(),
    }


def summarize_pdf(path: Path | str) -> str:
    analyzed = analyze_pdf_attachment(path)
    summary = clean_text(analyzed.get("summary"))
    if summary:
        return summary
    return summarize_text(clean_text(analyzed.get("text")))


def preview_pdf(path: Path | str) -> str:
    analyzed = analyze_pdf_attachment(path)
    preview = clean_text(analyzed.get("preview"))
    if preview:
        return preview
    return preview_text(clean_text(analyzed.get("text")))


def extract_pdf_text(path: Path | str) -> str:
    analyzed = analyze_pdf_attachment(path)
    return clean_text(analyzed.get("text"))


def extract_pdf_chunks(path: Path | str) -> List[str]:
    analyzed = analyze_pdf_attachment(path)
    return [clean_text(x) for x in safe_list(analyzed.get("chunks")) if clean_text(x)]


# =========================================================
# diagnostics
# =========================================================

def pdf_engine_status() -> Dict[str, Any]:
    status = {
        "pymupdf": False,
        "pypdf": False,
    }

    try:
        import fitz  # type: ignore  # noqa: F401
        status["pymupdf"] = True
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore  # noqa: F401
        status["pypdf"] = True
    except Exception:
        pass

    preferred = None
    if status["pymupdf"]:
        preferred = "pymupdf"
    elif status["pypdf"]:
        preferred = "pypdf"

    return {
        "ok": True,
        "available": status,
        "preferred": preferred,
    }