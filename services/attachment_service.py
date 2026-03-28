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
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# paths + config
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ATTACHMENTS_FILE = DATA_DIR / "nova_attachments.json"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MAX_ATTACHMENTS = int(os.getenv("NOVA_MAX_ATTACHMENTS", "500"))
MAX_ATTACHMENTS_PER_REQUEST = int(os.getenv("NOVA_MAX_ATTACHMENTS_PER_REQUEST", "12"))
MAX_ATTACHMENT_BYTES = int(os.getenv("NOVA_MAX_ATTACHMENT_BYTES", str(20 * 1024 * 1024)))
MAX_TOTAL_REQUEST_ATTACHMENT_BYTES = int(os.getenv("NOVA_MAX_TOTAL_REQUEST_ATTACHMENT_BYTES", str(40 * 1024 * 1024)))
MAX_TEXT_EXTRACT_CHARS = int(os.getenv("NOVA_MAX_ATTACHMENT_TEXT_EXTRACT_CHARS", "20000"))
MAX_SUMMARY_CHARS = int(os.getenv("NOVA_MAX_ATTACHMENT_SUMMARY_CHARS", "900"))
MAX_PREVIEW_CHARS = int(os.getenv("NOVA_MAX_ATTACHMENT_PREVIEW_CHARS", "320"))

ALLOWED_DOCUMENT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log", ".pdf", ".xml", ".yaml", ".yml", ".html", ".htm"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
ALLOWED_GENERIC_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS

TEXTUAL_MIME_PREFIXES = ("text/",)
TEXTUAL_MIME_TYPES = {"application/json","application/xml","text/xml","application/csv","text/csv","application/x-csv","text/markdown"}
DOCUMENT_MIME_TYPES = {"application/pdf","application/json","application/xml","text/xml","text/plain","text/markdown","text/csv","application/csv","application/x-csv"}
IMAGE_MIME_PREFIXES = ("image/",)

# =========================================================
# helpers
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    return text if len(text) <= limit else text[:limit].rstrip() + "…"

def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}

def safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def safe_int(value: Any, default: int = 0) -> int:
    try: return int(value)
    except Exception: return default

def safe_bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default

def file_safe_name(value: Any, fallback: str = "attachment") -> str:
    text = clean_text(value)
    if not text: return fallback
    text = re.sub(r"[^A-Za-z0-9._ -]+", "", text).strip()
    text = text.replace(" ", "_")
    text = re.sub(r"_+", "_", text)
    text = text[:140].strip("._-")
    return text or fallback

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path, chunk_size: int = 1024*1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()

def guess_mime_type(filename: str, explicit_mime: Optional[str] = None) -> str:
    mime = clean_text(explicit_mime).lower() if explicit_mime else ""
    if mime: return mime
    guessed, _ = mimetypes.guess_type(filename)
    return clean_text(guessed).lower() or "application/octet-stream"

def extension_for_name(filename: str) -> str:
    return Path(clean_text(filename)).suffix.lower()

def is_image_mime(mime_type: str) -> bool:
    return any(clean_text(mime_type).startswith(prefix) for prefix in IMAGE_MIME_PREFIXES)

def is_text_mime(mime_type: str) -> bool:
    mime_type = clean_text(mime_type)
    return mime_type in TEXTUAL_MIME_TYPES or any(mime_type.startswith(prefix) for prefix in TEXTUAL_MIME_PREFIXES)

def is_document_mime(mime_type: str) -> bool:
    mime_type = clean_text(mime_type)
    return mime_type in DOCUMENT_MIME_TYPES or is_text_mime(mime_type)

def is_document_extension(ext: str) -> bool:
    return clean_text(ext).lower() in ALLOWED_DOCUMENT_EXTENSIONS

def is_image_extension(ext: str) -> bool:
    return clean_text(ext).lower() in ALLOWED_IMAGE_EXTENSIONS

def classify_attachment(filename: str, mime_type: str) -> str:
    ext = extension_for_name(filename)
    if is_image_mime(mime_type) or is_image_extension(ext):
        return "image"
    if is_document_mime(mime_type) or is_document_extension(ext):
        return "document"
    return "file"

def preview_text_func(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    return truncate(re.sub(r"\s+", " ", clean_text(text)), limit)

def summarize_text_func(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    text = clean_text(text)
    if not text: return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept: List[str] = []
    total = 0
    for part in parts:
        part = clean_text(part)
        if not part: continue
        if total + len(part) > limit: break
        kept.append(part)
        total += len(part)+1
        if len(kept) >= 4: break
    return truncate(" ".join(kept) if kept else text, limit)

def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem+"_",
                              suffix=".tmp",
                              dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except Exception: pass
        raise

def backup_file(path: Path) -> Optional[Path]:
    if not path.exists(): return None
    backup_path = BACKUP_DIR / f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
    try: shutil.copy2(path, backup_path); return backup_path
    except Exception: return None

# =========================================================
# persistence
# =========================================================

def default_store() -> Dict[str, Any]:
    return {"items": [], "updated_at": utc_now_iso()}

def strip_internal_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(item)
    out.pop("canonical_name", None)
    return out

def normalize_attachment_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    item = safe_dict(item)
    filename = clean_text(item.get("name") or item.get("filename") or "attachment")
    mime_type = guess_mime_type(filename, item.get("mime_type") or item.get("content_type"))
    ext = extension_for_name(filename)
    size = max(0, safe_int(item.get("size"), 0))
    path_value = clean_text(item.get("path"))
    file_hash = clean_text(item.get("sha256") or item.get("hash"))
    kind = clean_text(item.get("kind")) or classify_attachment(filename, mime_type)

    return {
        "id": clean_text(item.get("id")) or str(uuid.uuid4()),
        "session_id": clean_text(item.get("session_id")) or None,
        "message_id": clean_text(item.get("message_id")) or None,
        "name": filename,
        "filename": filename,
        "path": path_value,
        "mime_type": mime_type,
        "content_type": mime_type,
        "extension": ext,
        "kind": kind,
        "size": size,
        "sha256": file_hash,
        "summary": clean_text(item.get("summary")),
        "preview": clean_text(item.get("preview")),
        "text": truncate(clean_text(item.get("text")), MAX_TEXT_EXTRACT_CHARS),
        "status": clean_text(item.get("status") or "ready"),
        "created_at": clean_text(item.get("created_at")) or utc_now_iso(),
        "updated_at": clean_text(item.get("updated_at")) or utc_now_iso(),
        "metadata": safe_dict(item.get("metadata")),
        "canonical_name": canonicalize_text(filename),
    }

# =========================================================
# store
# =========================================================

def load_store() -> Dict[str, Any]:
    if not ATTACHMENTS_FILE.exists():
        store = default_store()
        atomic_write_json(ATTACHMENTS_FILE, store)
        return normalize_store(store)
    try:
        raw = json.loads(ATTACHMENTS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict): raise ValueError()
    except Exception:
        backup_file(ATTACHMENTS_FILE)
        fallback = default_store()
        atomic_write_json(ATTACHMENTS_FILE, fallback)
        return normalize_store(fallback)
    return normalize_store(raw)

def save_store(store: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_store(store)
    normalized["updated_at"] = utc_now_iso()
    serializable = {
        "items": [strip_internal_fields(item) for item in normalized["items"]],
        "updated_at": normalized["updated_at"],
    }
    atomic_write_json(ATTACHMENTS_FILE, serializable)
    return normalize_store(serializable)

def normalize_store(store: Dict[str, Any]) -> Dict[str, Any]:
    store = safe_dict(store)
    items = [normalize_attachment_item(x) for x in safe_list(store.get("items")) if normalize_attachment_item(x)]
    items = dedupe_items(items)
    return {"items": items, "updated_at": clean_text(store.get("updated_at")) or utc_now_iso()}

def dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in items:
        item = normalize_attachment_item(raw)
        if not item: continue
        merged = False
        for idx, existing in enumerate(out):
            same_id = existing.get("id") == item.get("id")
            same_hash = existing.get("sha256") and existing.get("sha256") == item.get("sha256")
            same_path = existing.get("path") and existing.get("path") == item.get("path")
            if same_id or same_hash or same_path:
                out[idx] = choose_better_item(existing, item)
                merged = True
                break
        if not merged: out.append(item)
    out.sort(key=lambda x: x.get("updated_at",""), reverse=True)
    return out[:MAX_ATTACHMENTS]

def choose_better_item(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    a_exists = Path(clean_text(a.get("path"))).exists() if clean_text(a.get("path")) else False
    b_exists = Path(clean_text(b.get("path"))).exists() if clean_text(b.get("path")) else False
    winner = a if a_exists else b if b_exists else (a if clean_text(a.get("updated_at")) >= clean_text(b.get("updated_at")) else b)
    loser = b if winner is a else a
    winner = dict(winner)
    winner["updated_at"] = max(clean_text(a.get("updated_at")), clean_text(b.get("updated_at"))) or utc_now_iso()
    winner["metadata"] = {**safe_dict(loser.get("metadata")), **safe_dict(winner.get("metadata"))}
    if not winner.get("summary"): winner["summary"] = clean_text(loser.get("summary"))
    if not winner.get("preview"): winner["preview"] = clean_text(loser.get("preview"))
    if not winner.get("text"): winner["text"] = clean_text(loser.get("text"))
    if not winner.get("sha256"): winner["sha256"] = clean_text(loser.get("sha256"))
    return winner