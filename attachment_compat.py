from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename


attachment_compat = Blueprint("attachment_compat", __name__)

ALLOWED_EXTENSIONS = {
    "txt",
    "md",
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "csv",
    "json",
    "log",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "py",
    "js",
    "html",
    "css",
    "xml",
    "yaml",
    "yml",
    "zip",
}


def _upload_dir() -> Path:
    configured = current_app.config.get("UPLOAD_DIR")
    if configured:
        path = Path(configured)
    else:
        path = Path(current_app.root_path) / "data" / "uploads"

    path.mkdir(parents=True, exist_ok=True)
    return path


def _allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower().strip()
    return ext in ALLOWED_EXTENSIONS


def _safe_name(name: str) -> str:
    name = secure_filename(name or "file")
    if not name:
        name = "file"
    return name


def _split_name(filename: str) -> tuple[str, str]:
    path = Path(filename)
    return path.stem, path.suffix


def _build_saved_name(original_name: str) -> str:
    clean = _safe_name(original_name)
    stem, suffix = _split_name(clean)
    unique = uuid.uuid4().hex[:10]
    return f"{stem}_{unique}{suffix}"


def _public_url_for(saved_name: str) -> str:
    return f"/uploads/{saved_name}"


def _attachment_record(
    *,
    original_name: str,
    saved_name: str,
    size: int,
    mime_type: str,
) -> Dict[str, Any]:
    ext = ""
    if "." in original_name:
        ext = original_name.rsplit(".", 1)[-1].lower().strip()

    return {
        "id": saved_name,
        "file_id": saved_name,
        "name": original_name,
        "filename": original_name,
        "saved_name": saved_name,
        "url": _public_url_for(saved_name),
        "file_url": _public_url_for(saved_name),
        "size": int(size or 0),
        "type": mime_type or "",
        "mime_type": mime_type or "",
        "ext": ext,
    }


def normalize_attachment_payload(value: Any) -> List[Dict[str, Any]]:
    """
    Normalize frontend payloads from:
      - payload["attachments"]
      - payload["files"]

    Supported shapes:
      [{"id","url","name","size","type"}]
      [{"file_id","file_url","filename"}]
    """
    if not isinstance(value, list):
        return []

    normalized: List[Dict[str, Any]] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        name = str(
            item.get("name")
            or item.get("filename")
            or item.get("original_name")
            or "file"
        ).strip()

        file_id = str(item.get("id") or item.get("file_id") or "").strip()
        url = str(item.get("url") or item.get("file_url") or "").strip()
        size = int(item.get("size") or 0)
        mime_type = str(item.get("type") or item.get("mime_type") or "").strip()

        ext = ""
        if "." in name:
            ext = name.rsplit(".", 1)[-1].lower().strip()

        normalized.append(
            {
                "id": file_id,
                "file_id": file_id,
                "url": url,
                "file_url": url,
                "name": name,
                "filename": name,
                "size": size,
                "type": mime_type,
                "mime_type": mime_type,
                "ext": ext,
            }
        )

    return normalized


def extract_attachments_from_json(payload: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    payload = payload or {}

    attachments = normalize_attachment_payload(payload.get("attachments"))
    files = normalize_attachment_payload(payload.get("files"))

    merged: List[Dict[str, Any]] = []
    seen = set()

    for item in attachments + files:
        key = (
            item.get("file_id") or "",
            item.get("file_url") or "",
            item.get("filename") or "",
            str(item.get("size") or 0),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    return merged


@attachment_compat.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify(
            {
                "ok": False,
                "error": "No file field found. Expected multipart form field named 'file'.",
            }
        ), 400

    incoming = request.files["file"]

    if incoming is None or not incoming.filename:
        return jsonify(
            {
                "ok": False,
                "error": "No file selected.",
            }
        ), 400

    original_name = incoming.filename.strip()

    if not _allowed_file(original_name):
        return jsonify(
            {
                "ok": False,
                "error": "File type not allowed.",
                "filename": original_name,
            }
        ), 400

    upload_dir = _upload_dir()
    saved_name = _build_saved_name(original_name)
    dest = upload_dir / saved_name

    incoming.save(dest)

    try:
        size = dest.stat().st_size
    except OSError:
        size = 0

    record = _attachment_record(
        original_name=original_name,
        saved_name=saved_name,
        size=size,
        mime_type=incoming.mimetype or "",
    )

    return jsonify(
        {
            "ok": True,
            **record,
        }
    )


@attachment_compat.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename: str):
    safe_filename = re.sub(r"[\\/]+", "", filename or "").strip()
    if not safe_filename:
        return jsonify({"ok": False, "error": "Missing filename."}), 400

    return send_from_directory(_upload_dir(), safe_filename, as_attachment=False)