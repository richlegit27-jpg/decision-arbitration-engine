from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from core.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_TEXT_EXTENSIONS,
    ALLOWED_UPLOAD_EXTENSIONS,
    FILES_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOADS_DIR,
)
from core.state import load_upload_index, save_upload_index

# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def _utc_now_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_upload_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)


def detect_file_kind(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return "image"

    if suffix in ALLOWED_DOCUMENT_EXTENSIONS:
        return "document"

    if suffix in ALLOWED_TEXT_EXTENSIONS:
        return "text"

    return "unknown"


def is_allowed_file(filename: str) -> bool:
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_UPLOAD_EXTENSIONS


def _safe_filename(filename: str) -> str:
    cleaned = "".join(ch for ch in filename if ch.isalnum() or ch in ("-", "_", ".", " "))
    cleaned = cleaned.strip().replace(" ", "_")
    return cleaned or "upload.bin"


def _build_saved_filename(filename: str) -> str:
    original = _safe_filename(filename)
    stamp = _utc_now_stamp()
    return f"{stamp}_{original}"


def _read_upload_bytes(upload: UploadFile) -> bytes:
    content = upload.file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("File exceeds max upload size.")
    return content

# ---------------------------------------------------
# Text extraction
# ---------------------------------------------------

def extract_text_from_saved_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in ALLOWED_TEXT_EXTENSIONS:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    return ""

# ---------------------------------------------------
# Upload persistence
# ---------------------------------------------------

def save_upload(upload: UploadFile) -> dict[str, Any]:
    ensure_upload_dirs()

    filename = upload.filename or "upload.bin"

    if not is_allowed_file(filename):
        raise ValueError(f"Unsupported file type: {filename}")

    upload.file.seek(0)
    content = _read_upload_bytes(upload)

    saved_name = _build_saved_filename(filename)
    saved_path = UPLOADS_DIR / saved_name

    with open(saved_path, "wb") as handle:
        handle.write(content)

    kind = detect_file_kind(filename)
    extracted_text = extract_text_from_saved_file(saved_path)

    items = load_upload_index()
    next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1

    entry = {
        "id": next_id,
        "original_name": filename,
        "saved_name": saved_name,
        "path": str(saved_path),
        "kind": kind,
        "size_bytes": len(content),
        "created_at": _utc_now_iso(),
        "text_preview": extracted_text[:4000] if extracted_text else "",
    }

    items.append(entry)
    save_upload_index(items)

    return entry


def list_uploads() -> list[dict[str, Any]]:
    return load_upload_index()


def delete_upload(upload_id: int) -> dict[str, Any]:
    items = load_upload_index()
    target: dict[str, Any] | None = None
    filtered: list[dict[str, Any]] = []

    for item in items:
        if int(item.get("id", 0)) == upload_id and target is None:
            target = item
        else:
            filtered.append(item)

    if target is None:
        raise ValueError(f"Upload {upload_id} not found.")

    path_str = str(target.get("path", "")).strip()
    if path_str:
        path = Path(path_str)
        if path.exists() and path.is_file():
            path.unlink()

    save_upload_index(filtered)

    return {
        "ok": True,
        "deleted_upload_id": upload_id,
    }


def build_file_context(limit: int = 5) -> str:
    items = list_uploads()
    if not items:
        return ""

    lines: list[str] = []

    for item in items[-limit:]:
        name = item.get("original_name", "unknown")
        kind = item.get("kind", "unknown")
        preview = str(item.get("text_preview", "")).strip()

        lines.append(f"- File: {name} ({kind})")
        if preview:
            lines.append(preview[:1000])

    return "\n".join(lines)