from __future__ import annotations

import csv
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional PDF support
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None  # type: ignore

# Optional image metadata support
try:
    from PIL import Image
except Exception:
    Image = None  # type: ignore


BASE_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = BASE_DIR / "uploads"

TEXT_EXTENSIONS = {
    ".txt", ".log", ".md", ".markdown",
    ".html", ".htm", ".xml",
    ".yaml", ".yml",
}
JSON_EXTENSIONS = {".json"}
CSV_EXTENSIONS = {".csv", ".tsv"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

TEXT_MIME_PREFIXES = ("text/",)
JSON_MIMES = {"application/json", "text/json"}
CSV_MIMES = {"text/csv", "application/csv", "text/tab-separated-values"}
PDF_MIMES = {"application/pdf"}
IMAGE_MIME_PREFIXES = ("image/",)

MAX_FILE_READ_CHARS = 120000
MAX_JSON_ITEMS = 200
MAX_JSON_PREVIEW_CHARS = 16000
MAX_CSV_ROWS = 120
MAX_CSV_PREVIEW_CHARS = 16000
MAX_PDF_PAGES = 40
MAX_PDF_PREVIEW_CHARS = 24000

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 180
DEFAULT_TOP_CHUNKS = 3
DEFAULT_MAX_CONTEXT_CHARS = 7000


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\x00", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def normalize_for_search(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text


def token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]{3,}", normalize_for_search(text)))


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or ""


def is_textish_extension(ext: str) -> bool:
    return ext in TEXT_EXTENSIONS


def is_json_extension(ext: str) -> bool:
    return ext in JSON_EXTENSIONS


def is_csv_extension(ext: str) -> bool:
    return ext in CSV_EXTENSIONS


def is_pdf_extension(ext: str) -> bool:
    return ext in PDF_EXTENSIONS


def is_image_extension(ext: str) -> bool:
    return ext in IMAGE_EXTENSIONS


def flatten_json(value: Any, prefix: str = "", items: Optional[List[str]] = None) -> List[str]:
    if items is None:
        items = []

    if len(items) >= MAX_JSON_ITEMS:
        return items

    if isinstance(value, dict):
        for key, subvalue in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            flatten_json(subvalue, next_prefix, items)
            if len(items) >= MAX_JSON_ITEMS:
                break
    elif isinstance(value, list):
        for idx, subvalue in enumerate(value):
            next_prefix = f"{prefix}[{idx}]"
            flatten_json(subvalue, next_prefix, items)
            if len(items) >= MAX_JSON_ITEMS:
                break
    else:
        items.append(f"{prefix}: {value}")

    return items


def split_into_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    text = clean_text(text)
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - overlap)

    return chunks


def score_chunk(chunk: str, query: str) -> float:
    if not chunk:
        return -9999.0

    q_tokens = token_set(query)
    c_tokens = token_set(chunk)

    overlap = len(q_tokens & c_tokens)
    richness = min(len(chunk) / 300.0, 8.0)

    exact_phrase_bonus = 0.0
    q_norm = normalize_for_search(query)
    c_norm = normalize_for_search(chunk)
    if q_norm and q_norm in c_norm:
        exact_phrase_bonus += 12.0

    return (overlap * 10.0) + richness + exact_phrase_bonus


def select_relevant_chunks(
    text: str,
    query: str,
    top_k: int = DEFAULT_TOP_CHUNKS,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> List[str]:
    text = clean_text(text)
    if not text:
        return []

    chunks = split_into_chunks(text)
    if not chunks:
        return []

    if not clean_text(query):
        selected: List[str] = []
        running = 0
        for chunk in chunks[:top_k]:
            if running + len(chunk) > max_chars:
                break
            selected.append(chunk)
            running += len(chunk)
        return selected

    scored = [(score_chunk(chunk, query), chunk) for chunk in chunks]
    scored.sort(key=lambda item: item[0], reverse=True)

    selected = []
    running = 0
    for _, chunk in scored[: max(top_k * 2, top_k)]:
        if running + len(chunk) > max_chars:
            break
        selected.append(chunk)
        running += len(chunk)
        if len(selected) >= top_k:
            break

    return selected


@dataclass
class DocumentAnalysis:
    ok: bool
    kind: str
    name: str
    path: str
    mime_type: str
    chars: int
    words: int
    preview: str
    content: str
    chunks: List[str]
    error: str = ""
    meta: Optional[Dict[str, Any]] = None

    def to_debug_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "kind": self.kind,
            "name": self.name,
            "path": self.path,
            "type": self.mime_type,
            "chars": self.chars,
            "words": self.words,
            "preview": self.preview,
            "error": self.error,
            "meta": self.meta or {},
        }


class DocumentService:
    @staticmethod
    def resolve_attachment_path(attachment: Dict[str, Any]) -> Tuple[Optional[Path], str, str]:
        name = clean_text(
            attachment.get("name")
            or attachment.get("filename")
            or attachment.get("stored_name")
            or "attachment"
        )

        mime_type = clean_text(
            attachment.get("type")
            or attachment.get("mime_type")
            or attachment.get("content_type")
            or ""
        )

        candidate_values = [
            attachment.get("path"),
            attachment.get("stored_path"),
            attachment.get("filepath"),
            attachment.get("file_path"),
            attachment.get("url"),
        ]

        for raw in candidate_values:
            raw = clean_text(raw)
            if not raw:
                continue

            path = Path(raw)
            if not path.is_absolute():
                raw_norm = raw.replace("\\", "/").lstrip("/")
                if raw_norm.startswith("uploads/"):
                    path = BASE_DIR / raw_norm
                else:
                    path = UPLOADS_DIR / Path(raw_norm).name

            if path.exists() and path.is_file():
                if not mime_type:
                    mime_type = guess_mime(path)
                return path, name or path.name, mime_type

        stored_name = clean_text(attachment.get("stored_name"))
        if stored_name:
            path = UPLOADS_DIR / stored_name
            if path.exists() and path.is_file():
                if not mime_type:
                    mime_type = guess_mime(path)
                return path, name or path.name, mime_type

        if name:
            by_name = UPLOADS_DIR / Path(name).name
            if by_name.exists() and by_name.is_file():
                if not mime_type:
                    mime_type = guess_mime(by_name)
                return by_name, name or by_name.name, mime_type

        return None, name, mime_type

    @staticmethod
    def analyze_text_file(path: Path, name: str, mime_type: str) -> DocumentAnalysis:
        raw = safe_read_text(path)
        text = clean_text(raw)
        text = truncate(text, MAX_FILE_READ_CHARS)

        return DocumentAnalysis(
            ok=True,
            kind="text",
            name=name,
            path=str(path),
            mime_type=mime_type or guess_mime(path),
            chars=len(text),
            words=len(text.split()),
            preview=truncate(text, 220),
            content=text,
            chunks=split_into_chunks(text),
            meta={"extension": path.suffix.lower()},
        )

    @staticmethod
    def analyze_json_file(path: Path, name: str, mime_type: str) -> DocumentAnalysis:
        raw = safe_read_text(path)
        parsed = json.loads(raw)
        flattened = flatten_json(parsed)
        summary = "\n".join(flattened)
        summary = truncate(summary, MAX_JSON_PREVIEW_CHARS)

        meta: Dict[str, Any] = {
            "extension": path.suffix.lower(),
            "top_level_type": type(parsed).__name__,
        }

        if isinstance(parsed, dict):
            meta["top_level_keys"] = list(parsed.keys())[:40]
        elif isinstance(parsed, list):
            meta["top_level_length"] = len(parsed)

        return DocumentAnalysis(
            ok=True,
            kind="json",
            name=name,
            path=str(path),
            mime_type=mime_type or "application/json",
            chars=len(summary),
            words=len(summary.split()),
            preview=truncate(summary, 220),
            content=summary,
            chunks=split_into_chunks(summary),
            meta=meta,
        )

    @staticmethod
    def analyze_csv_file(path: Path, name: str, mime_type: str) -> DocumentAnalysis:
        ext = path.suffix.lower()
        delimiter = "\t" if ext == ".tsv" else ","

        rows: List[List[str]] = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for idx, row in enumerate(reader):
                if idx >= MAX_CSV_ROWS:
                    break
                rows.append([clean_text(cell) for cell in row])

        if not rows:
            raise ValueError("CSV/TSV file is empty")

        header = rows[0]
        body = rows[1:]

        lines: List[str] = []
        lines.append("Columns: " + ", ".join(header[:50]))

        for idx, row in enumerate(body[: min(len(body), MAX_CSV_ROWS - 1)], start=1):
            pairs = []
            for col_idx, cell in enumerate(row[: len(header)]):
                col_name = header[col_idx] if col_idx < len(header) else f"col_{col_idx}"
                pairs.append(f"{col_name}={cell}")
            lines.append(f"Row {idx}: " + "; ".join(pairs[:25]))

        content = "\n".join(lines)
        content = truncate(content, MAX_CSV_PREVIEW_CHARS)

        return DocumentAnalysis(
            ok=True,
            kind="csv",
            name=name,
            path=str(path),
            mime_type=mime_type or guess_mime(path),
            chars=len(content),
            words=len(content.split()),
            preview=truncate(content, 220),
            content=content,
            chunks=split_into_chunks(content),
            meta={
                "extension": ext,
                "row_count_previewed": len(rows),
                "column_count": len(header),
                "columns": header[:50],
            },
        )

    @staticmethod
    def analyze_pdf_file(path: Path, name: str, mime_type: str) -> DocumentAnalysis:
        if PdfReader is None:
            raise RuntimeError("PyPDF2 is not installed")

        reader = PdfReader(str(path))
        pages = reader.pages[:MAX_PDF_PAGES]

        texts: List[str] = []
        extracted_pages = 0

        for page in pages:
            try:
                page_text = clean_text(page.extract_text() or "")
            except Exception:
                page_text = ""
            if page_text:
                extracted_pages += 1
                texts.append(page_text)

        joined = "\n\n".join(texts)
        joined = truncate(joined, MAX_PDF_PREVIEW_CHARS)

        return DocumentAnalysis(
            ok=True,
            kind="pdf",
            name=name,
            path=str(path),
            mime_type=mime_type or "application/pdf",
            chars=len(joined),
            words=len(joined.split()),
            preview=truncate(joined, 220),
            content=joined,
            chunks=split_into_chunks(joined),
            meta={
                "extension": path.suffix.lower(),
                "page_count_total": len(reader.pages),
                "page_count_processed": len(pages),
                "page_count_with_text": extracted_pages,
                "pdf_supported": True,
            },
        )

    @staticmethod
    def analyze_image_file(path: Path, name: str, mime_type: str) -> DocumentAnalysis:
        description_lines = [f"Image attachment: {name}"]

        meta: Dict[str, Any] = {
            "extension": path.suffix.lower(),
            "image_supported": Image is not None,
        }

        if Image is not None:
            try:
                with Image.open(path) as img:
                    width, height = img.size
                    mode = getattr(img, "mode", "")
                    fmt = getattr(img, "format", "")
                    description_lines.append(f"Format: {fmt or 'unknown'}")
                    description_lines.append(f"Dimensions: {width}x{height}")
                    if mode:
                        description_lines.append(f"Color mode: {mode}")
                    meta["width"] = width
                    meta["height"] = height
                    meta["mode"] = mode
                    meta["format"] = fmt
            except Exception as exc:
                meta["image_open_error"] = str(exc)

        content = "\n".join(description_lines)

        return DocumentAnalysis(
            ok=True,
            kind="image",
            name=name,
            path=str(path),
            mime_type=mime_type or guess_mime(path),
            chars=len(content),
            words=len(content.split()),
            preview=truncate(content, 220),
            content=content,
            chunks=[content],
            meta=meta,
        )

    @staticmethod
    def analyze_attachment(attachment: Dict[str, Any]) -> DocumentAnalysis:
        path, name, mime_type = DocumentService.resolve_attachment_path(attachment)

        if path is None:
            return DocumentAnalysis(
                ok=False,
                kind="unknown",
                name=name or "attachment",
                path="",
                mime_type=mime_type,
                chars=0,
                words=0,
                preview="",
                content="",
                chunks=[],
                error="Attachment file not found",
                meta={},
            )

        ext = path.suffix.lower()
        mime_type = mime_type or guess_mime(path)

        try:
            if is_textish_extension(ext) or mime_type.startswith(TEXT_MIME_PREFIXES):
                return DocumentService.analyze_text_file(path, name, mime_type)

            if is_json_extension(ext) or mime_type in JSON_MIMES:
                return DocumentService.analyze_json_file(path, name, mime_type)

            if is_csv_extension(ext) or mime_type in CSV_MIMES:
                return DocumentService.analyze_csv_file(path, name, mime_type)

            if is_pdf_extension(ext) or mime_type in PDF_MIMES:
                return DocumentService.analyze_pdf_file(path, name, mime_type)

            if is_image_extension(ext) or mime_type.startswith(IMAGE_MIME_PREFIXES):
                return DocumentService.analyze_image_file(path, name, mime_type)

            # last-chance text read for unknown files
            try:
                return DocumentService.analyze_text_file(path, name, mime_type)
            except Exception:
                return DocumentAnalysis(
                    ok=False,
                    kind="unsupported",
                    name=name,
                    path=str(path),
                    mime_type=mime_type,
                    chars=0,
                    words=0,
                    preview="",
                    content="",
                    chunks=[],
                    error=f"Unsupported attachment type: {ext or mime_type or 'unknown'}",
                    meta={"extension": ext},
                )

        except Exception as exc:
            return DocumentAnalysis(
                ok=False,
                kind="error",
                name=name,
                path=str(path),
                mime_type=mime_type,
                chars=0,
                words=0,
                preview="",
                content="",
                chunks=[],
                error=str(exc),
                meta={"extension": ext},
            )

    @staticmethod
    def analyze_attachments(
        attachments: Optional[List[Dict[str, Any]]],
        query: str = "",
        top_k_per_doc: int = DEFAULT_TOP_CHUNKS,
        max_total_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    ) -> Dict[str, Any]:
        attachments = attachments or []

        analyses: List[DocumentAnalysis] = []
        debug_docs: List[Dict[str, Any]] = []
        selected_blocks: List[str] = []

        total_context_chars = 0
        total_doc_chars = 0

        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue

            analysis = DocumentService.analyze_attachment(attachment)
            analyses.append(analysis)
            debug_docs.append(analysis.to_debug_dict())

            if not analysis.ok or not analysis.content:
                continue

            total_doc_chars += analysis.chars

            chosen_chunks = select_relevant_chunks(
                text=analysis.content,
                query=query,
                top_k=top_k_per_doc,
                max_chars=max_total_context_chars,
            )

            if not chosen_chunks:
                continue

            block_parts = [f"[Attachment: {analysis.name} | kind={analysis.kind}]"]
            block_parts.extend(chosen_chunks)
            block = "\n".join(block_parts).strip()

            if total_context_chars + len(block) > max_total_context_chars:
                remaining = max_total_context_chars - total_context_chars
                if remaining > 160:
                    selected_blocks.append(truncate(block, remaining))
                    total_context_chars += min(len(block), remaining)
                break

            selected_blocks.append(block)
            total_context_chars += len(block)

        context_text = "\n\n".join(selected_blocks).strip()

        return {
            "ok": True,
            "context_text": context_text,
            "document_used": bool(context_text),
            "document_count": len(analyses),
            "document_ok_count": sum(1 for item in analyses if item.ok),
            "document_error_count": sum(1 for item in analyses if not item.ok),
            "document_chars": total_doc_chars,
            "document_names": [item.name for item in analyses],
            "document_preview": truncate(context_text, 300) if context_text else "",
            "documents": debug_docs,
        }

