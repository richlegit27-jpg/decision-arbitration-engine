# notepad C:\Users\Owner\nova\services\attachment_service.py
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# =========================================================
# paths + config
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ATTACHMENTS_INDEX_FILE = DATA_DIR / "nova_attachments.json"

MAX_ATTACHMENT_ITEMS = 2000
MAX_ATTACHMENT_PROMPT_CHARS = 8000
MAX_TEXT_READ_CHARS = 30000
MAX_DOCUMENT_SNIPPET_CHARS = 4000
MAX_IMAGE_SNIPPET_CHARS = 1000
MAX_NAME_CHARS = 180
MAX_FILE_BYTES_FOR_INLINE_TEXT = 2 * 1024 * 1024  # 2MB
CHUNK_PREVIEW_LINES = 40

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".log",
    ".xml",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
}
IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".svg",
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
IMAGE_MIME_PREFIXES = ("image/",)

# =========================================================
# optional service imports
# =========================================================

try:
    from services.document_service import analyze_document_attachment as _document_analyze
except Exception:
    _document_analyze = None

try:
    from services.pdf_service import analyze_pdf_attachment as _pdf_analyze
except Exception:
    _pdf_analyze = None


# =========================================================
# helpers
# =========================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


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


def _safe_json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return default
        return json.loads(raw)
    except Exception:
        return default


def _safe_json_save(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _ensure_index_file() -> None:
    if not ATTACHMENTS_INDEX_FILE.exists():
        _safe_json_save(ATTACHMENTS_INDEX_FILE, {"items": []})


def _load_index() -> Dict[str, Any]:
    _ensure_index_file()
    store = _safe_json_load(ATTACHMENTS_INDEX_FILE, {"items": []})
    if not isinstance(store, dict):
        return {"items": []}
    items = store.get("items")
    if not isinstance(items, list):
        store["items"] = []
    return store


def _save_index(store: Dict[str, Any]) -> None:
    _safe_json_save(ATTACHMENTS_INDEX_FILE, store)


def _guess_mime_type(path: Optional[Path], fallback_name: str = "") -> str:
    if path and path.exists():
        guessed, _ = mimetypes.guess_type(str(path))
        if guessed:
            return guessed
    guessed, _ = mimetypes.guess_type(fallback_name)
    return guessed or "application/octet-stream"


def _safe_name(name: str) -> str:
    name = _clean_text(name).strip() or "attachment"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "attachment"
    if len(name) > MAX_NAME_CHARS:
        stem, suffix = os.path.splitext(name)
        keep = MAX_NAME_CHARS - len(suffix)
        name = stem[: max(1, keep)] + suffix
    return name


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(path: Path, max_bytes: Optional[int] = None) -> bytes:
    if max_bytes is None:
        return path.read_bytes()
    with path.open("rb") as f:
        return f.read(max_bytes)


def _safe_read_text(path: Path, limit: int = MAX_TEXT_READ_CHARS) -> str:
    raw = path.read_bytes()[:limit]
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding, errors="ignore")
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extension(name: str) -> str:
    return Path(name).suffix.lower().strip()


def _is_document_type(name: str, mime_type: str) -> bool:
    ext = _extension(name)
    if ext in DOCUMENT_EXTENSIONS:
        return True
    if mime_type in DOCUMENT_MIME_TYPES:
        return True
    return any(mime_type.startswith(prefix) for prefix in DOCUMENT_MIME_PREFIXES)


def _is_image_type(name: str, mime_type: str) -> bool:
    ext = _extension(name)
    if ext in IMAGE_EXTENSIONS:
        return True
    return any(mime_type.startswith(prefix) for prefix in IMAGE_MIME_PREFIXES)


def _trim_lines(text: str, max_lines: int = CHUNK_PREVIEW_LINES) -> str:
    lines = _clean_text(text).splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + "\n...(truncated)"


def _best_existing_path(raw: Dict[str, Any]) -> Optional[Path]:
    for key in ("stored_path", "path", "local_path", "saved_path", "file_path", "temp_path"):
        candidate = _clean_text(raw.get(key)).strip()
        if candidate:
            p = Path(candidate)
            if p.exists() and p.is_file():
                return p
    return None


def _extract_inline_bytes(raw: Dict[str, Any]) -> Optional[bytes]:
    value = raw.get("content_bytes")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return None


def _extract_inline_text(raw: Dict[str, Any]) -> str:
    for key in ("text", "content", "body", "raw_text"):
        value = raw.get(key)
        if isinstance(value, str):
            return value
    return ""


def _write_bytes_to_uploads(data: bytes, name: str) -> Path:
    safe_name = _safe_name(name)
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    dest = UPLOADS_DIR / unique_name
    dest.write_bytes(data)
    return dest


def _copy_file_to_uploads(source: Path, name: str) -> Path:
    safe_name = _safe_name(name or source.name)
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    dest = UPLOADS_DIR / unique_name
    shutil.copy2(source, dest)
    return dest


def _store_inline_text(text: str, name: str) -> Path:
    safe_name = _safe_name(name)
    if "." not in safe_name:
        safe_name += ".txt"
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    dest = UPLOADS_DIR / unique_name
    dest.write_text(text, encoding="utf-8")
    return dest


# =========================================================
# persistence
# =========================================================

def list_saved_attachments() -> List[Dict[str, Any]]:
    store = _load_index()
    items = _coerce_list(store.get("items"))
    items.sort(key=lambda x: _clean_text(x.get("created_at")), reverse=True)
    return items


def get_saved_attachment(attachment_id: str) -> Optional[Dict[str, Any]]:
    for item in list_saved_attachments():
        if _clean_text(item.get("id")) == _clean_text(attachment_id):
            return item
    return None


def _upsert_attachment_record(record: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_index()
    items = _coerce_list(store.get("items"))

    found = False
    for i, existing in enumerate(items):
        if _clean_text(existing.get("id")) == _clean_text(record.get("id")):
            items[i] = record
            found = True
            break

    if not found:
        items.append(record)

    if len(items) > MAX_ATTACHMENT_ITEMS:
        items = items[-MAX_ATTACHMENT_ITEMS:]

    store["items"] = items
    _save_index(store)
    return record


# =========================================================
# normalization
# =========================================================

def normalize_attachment(raw: Any) -> Dict[str, Any]:
    raw = _coerce_dict(raw)

    provided_name = (
        _clean_text(raw.get("name"))
        or _clean_text(raw.get("filename"))
        or _clean_text(raw.get("original_name"))
        or "attachment"
    )
    provided_name = _safe_name(provided_name)

    existing_path = _best_existing_path(raw)
    inline_bytes = _extract_inline_bytes(raw)
    inline_text = _extract_inline_text(raw)

    stored_path: Optional[Path] = None
    size: Optional[int] = None
    sha256 = ""
    source = "metadata"

    if existing_path:
        stored_path = _copy_file_to_uploads(existing_path, provided_name)
        source = "file_copy"
        try:
            size = stored_path.stat().st_size
            sha256 = _sha256_bytes(_read_bytes(stored_path, max_bytes=5 * 1024 * 1024))
        except Exception:
            size = None
            sha256 = ""
    elif inline_bytes is not None:
        stored_path = _write_bytes_to_uploads(inline_bytes, provided_name)
        source = "inline_bytes"
        size = len(inline_bytes)
        sha256 = _sha256_bytes(inline_bytes[: 5 * 1024 * 1024])
    elif inline_text:
        stored_path = _store_inline_text(inline_text, provided_name)
        source = "inline_text"
        encoded = inline_text.encode("utf-8", errors="ignore")
        size = len(encoded)
        sha256 = _sha256_bytes(encoded[: 5 * 1024 * 1024])

    mime_type = (
        _clean_text(raw.get("mime_type"))
        or _clean_text(raw.get("type"))
        or _guess_mime_type(stored_path, fallback_name=provided_name)
    )

    if stored_path and size is None:
        try:
            size = stored_path.stat().st_size
        except Exception:
            size = None

    kind = "other"
    if _is_document_type(provided_name, mime_type):
        kind = "document"
    elif _is_image_type(provided_name, mime_type):
        kind = "image"

    attachment = {
        "id": _clean_text(raw.get("id")).strip() or _new_id(),
        "name": provided_name,
        "original_name": provided_name,
        "mime_type": mime_type or "application/octet-stream",
        "size": size,
        "extension": _extension(provided_name),
        "kind": kind,
        "source": source,
        "created_at": _now_iso(),
        "stored_path": str(stored_path) if stored_path else "",
        "sha256": sha256,
        "status": "ready",
        "meta": _coerce_dict(raw.get("meta")),
    }

    return attachment


# =========================================================
# analyzers
# =========================================================

def _fallback_document_analysis(attachment: Dict[str, Any]) -> Dict[str, Any]:
    path_value = _clean_text(attachment.get("stored_path")).strip()
    path = Path(path_value) if path_value else None

    result = {
        "id": attachment.get("id"),
        "name": attachment.get("name"),
        "mime_type": attachment.get("mime_type"),
        "type": "document",
        "summary": "",
        "snippet": "",
        "prompt_text": "",
        "status": "ready",
        "meta": {},
    }

    if not path or not path.exists():
        result["status"] = "missing_file"
        result["summary"] = "Document file is unavailable."
        return result

    ext = _extension(_clean_text(attachment.get("name")))
    try:
        if ext == ".pdf":
            result["summary"] = "PDF attached."
            result["snippet"] = "PDF available for downstream PDF service."
            result["prompt_text"] = f"Attached PDF: {attachment.get('name')}"
            return result

        text = _safe_read_text(path, limit=MAX_TEXT_READ_CHARS)
        text = _trim_lines(text, CHUNK_PREVIEW_LINES)
        snippet = _truncate(text, MAX_DOCUMENT_SNIPPET_CHARS)

        result["summary"] = f"Document attached: {attachment.get('name')}"
        result["snippet"] = snippet
        result["prompt_text"] = f"Attached document: {attachment.get('name')}\n{snippet}"
        result["meta"] = {
            "chars_read": len(text),
        }
        return result
    except Exception as exc:
        result["status"] = "error"
        result["summary"] = f"Failed to analyze document: {exc}"
        return result


def _analyze_document(attachment: Dict[str, Any]) -> Dict[str, Any]:
    path_value = _clean_text(attachment.get("stored_path")).strip()
    name = _clean_text(attachment.get("name"))
    mime_type = _clean_text(attachment.get("mime_type"))
    ext = _extension(name)

    if path_value and ext == ".pdf" and _pdf_analyze:
        try:
            result = _pdf_analyze(
                {
                    "id": attachment.get("id"),
                    "name": name,
                    "mime_type": mime_type,
                    "stored_path": path_value,
                }
            )
            if isinstance(result, dict):
                return {
                    "id": attachment.get("id"),
                    "name": name,
                    "mime_type": mime_type,
                    "type": "document",
                    "summary": _truncate(result.get("summary", "PDF attached."), 600),
                    "snippet": _truncate(
                        result.get("snippet") or result.get("text") or result.get("prompt_text") or "",
                        MAX_DOCUMENT_SNIPPET_CHARS,
                    ),
                    "prompt_text": _truncate(
                        result.get("prompt_text")
                        or result.get("snippet")
                        or result.get("text")
                        or f"Attached PDF: {name}",
                        MAX_ATTACHMENT_PROMPT_CHARS,
                    ),
                    "status": _clean_text(result.get("status")) or "ready",
                    "meta": _coerce_dict(result.get("meta")),
                }
        except Exception:
            pass

    if _document_analyze:
        try:
            result = _document_analyze(
                {
                    "id": attachment.get("id"),
                    "name": name,
                    "mime_type": mime_type,
                    "stored_path": path_value,
                }
            )
            if isinstance(result, dict):
                return {
                    "id": attachment.get("id"),
                    "name": name,
                    "mime_type": mime_type,
                    "type": "document",
                    "summary": _truncate(result.get("summary", f"Document attached: {name}"), 600),
                    "snippet": _truncate(
                        result.get("snippet") or result.get("text") or result.get("prompt_text") or "",
                        MAX_DOCUMENT_SNIPPET_CHARS,
                    ),
                    "prompt_text": _truncate(
                        result.get("prompt_text")
                        or result.get("snippet")
                        or result.get("text")
                        or f"Attached document: {name}",
                        MAX_ATTACHMENT_PROMPT_CHARS,
                    ),
                    "status": _clean_text(result.get("status")) or "ready",
                    "meta": _coerce_dict(result.get("meta")),
                }
        except Exception:
            pass

    return _fallback_document_analysis(attachment)


def _analyze_image(attachment: Dict[str, Any]) -> Dict[str, Any]:
    name = _clean_text(attachment.get("name"))
    mime_type = _clean_text(attachment.get("mime_type"))
    path_value = _clean_text(attachment.get("stored_path")).strip()

    return {
        "id": attachment.get("id"),
        "name": name,
        "mime_type": mime_type,
        "type": "image",
        "summary": f"Image attached: {name}",
        "snippet": _truncate(f"Image file available at {path_value}" if path_value else f"Image file attached: {name}", MAX_IMAGE_SNIPPET_CHARS),
        "prompt_text": f"Attached image: {name}",
        "status": "ready",
        "meta": {},
    }


# =========================================================
# public processing API
# =========================================================

def save_attachment(raw: Any) -> Dict[str, Any]:
    attachment = normalize_attachment(raw)
    return _upsert_attachment_record(attachment)


def save_attachments(raw_attachments: Iterable[Any]) -> List[Dict[str, Any]]:
    saved: List[Dict[str, Any]] = []
    for raw in raw_attachments:
        try:
            saved.append(save_attachment(raw))
        except Exception:
            continue
    return saved


def process_attachments_for_chat(raw_attachments: List[Any]) -> Dict[str, Any]:
    result = {
        "attachments": [],
        "documents": [],
        "images": [],
        "prompt_context": "",
        "errors": [],
    }

    attachments: List[Dict[str, Any]] = []
    documents: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    prompt_parts: List[str] = []

    for raw in _coerce_list(raw_attachments):
        try:
            attachment = save_attachment(raw)
            attachments.append(
                {
                    "id": attachment.get("id"),
                    "name": attachment.get("name"),
                    "type": attachment.get("mime_type"),
                    "mime_type": attachment.get("mime_type"),
                    "size": attachment.get("size"),
                    "kind": attachment.get("kind"),
                    "status": attachment.get("status"),
                    "stored_path": attachment.get("stored_path"),
                }
            )

            kind = _clean_text(attachment.get("kind"))
            if kind == "document":
                analyzed = _analyze_document(attachment)
                documents.append(analyzed)
                prompt_text = _clean_text(analyzed.get("prompt_text")).strip()
                if prompt_text:
                    prompt_parts.append(prompt_text)
            elif kind == "image":
                analyzed = _analyze_image(attachment)
                images.append(analyzed)
                prompt_text = _clean_text(analyzed.get("prompt_text")).strip()
                if prompt_text:
                    prompt_parts.append(prompt_text)
            else:
                prompt_parts.append(f"Attached file: {_clean_text(attachment.get('name'))}")
        except Exception as exc:
            result["errors"].append(f"attachment processing failed: {exc}")

    result["attachments"] = attachments
    result["documents"] = documents
    result["images"] = images
    result["prompt_context"] = _truncate("\n\n".join([p for p in prompt_parts if p]).strip(), MAX_ATTACHMENT_PROMPT_CHARS)

    return result


# =========================================================
# inspection / admin helpers
# =========================================================

def delete_attachment(attachment_id: str) -> bool:
    store = _load_index()
    items = _coerce_list(store.get("items"))

    kept: List[Dict[str, Any]] = []
    deleted = False

    for item in items:
        if _clean_text(item.get("id")) == _clean_text(attachment_id):
            deleted = True
            path_value = _clean_text(item.get("stored_path")).strip()
            if path_value:
                try:
                    path = Path(path_value)
                    if path.exists() and path.is_file():
                        path.unlink()
                except Exception:
                    pass
            continue
        kept.append(item)

    if deleted:
        store["items"] = kept
        _save_index(store)

    return deleted


def export_attachment(attachment_id: str) -> Optional[Dict[str, Any]]:
    item = get_saved_attachment(attachment_id)
    if not item:
        return None
    return dict(item)


def get_attachment_text_preview(attachment_id: str, limit: int = 4000) -> Dict[str, Any]:
    item = get_saved_attachment(attachment_id)
    if not item:
        return {
            "ok": False,
            "error": "Attachment not found.",
            "code": "not_found",
        }

    path_value = _clean_text(item.get("stored_path")).strip()
    path = Path(path_value) if path_value else None
    if not path or not path.exists():
        return {
            "ok": False,
            "error": "Attachment file is unavailable.",
            "code": "missing_file",
            "attachment": item,
        }

    mime_type = _clean_text(item.get("mime_type"))
    if not _is_document_type(_clean_text(item.get("name")), mime_type):
        return {
            "ok": True,
            "attachment": item,
            "preview": "",
            "message": "Preview only available for document-like attachments.",
        }

    try:
        if path.stat().st_size > MAX_FILE_BYTES_FOR_INLINE_TEXT:
            preview = f"File too large for full inline preview. Name: {item.get('name')}"
        else:
            preview = _safe_read_text(path, limit=limit)
        return {
            "ok": True,
            "attachment": item,
            "preview": _truncate(preview, limit),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "code": "preview_failed",
            "attachment": item,
        }