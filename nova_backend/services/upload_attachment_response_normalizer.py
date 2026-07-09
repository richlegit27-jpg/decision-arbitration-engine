# NOVA_UPLOAD_ATTACHMENT_RESPONSE_NORMALIZER_20260705
"""
Canonicalize /api/upload JSON responses for backend attachment handling.

This does not change upload storage.
It only adds stable alias fields when possible:
- filename
- name
- url
- mime_type
- size_bytes
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote


_FILENAME_KEYS = (
    "filename",
    "original_filename",
    "stored_filename",
    "saved_filename",
    "name",
    "file_name",
    "path",
    "local_path",
    "file_path",
    "filepath",
    "url",
    "download_url",
)

_URL_KEYS = (
    "url",
    "download_url",
    "href",
    "src",
    "file_url",
)

_MIME_KEYS = (
    "mime_type",
    "content_type",
    "mimetype",
    "type",
    "media_type",
)

_SIZE_KEYS = (
    "size_bytes",
    "bytes",
    "size",
    "length",
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


def _first_text(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _stringify(data.get(key)).strip()

        if value:
            return value

    return ""


def _nested_upload_dict(payload: dict[str, Any]) -> dict[str, Any]:
    for key in (
        "file",
        "upload",
        "attachment",
        "data",
        "result",
    ):
        value = payload.get(key)

        if isinstance(value, dict):
            return value

    return {}


def _basename(value: str) -> str:
    value = value.strip().replace("\\", "/").split("?", 1)[0].split("#", 1)[0]

    if "/api/uploads/" in value:
        value = value.split("/api/uploads/", 1)[1]

    if "api/uploads/" in value:
        value = value.split("api/uploads/", 1)[1]

    if "/uploads/" in value:
        value = value.split("/uploads/", 1)[1]

    if value.startswith("uploads/"):
        value = value.split("uploads/", 1)[1]

    return Path(value).name


def _coerce_size(value: Any) -> Any:
    if isinstance(value, int):
        return value

    text = _stringify(value).strip()

    if not text:
        return None

    try:
        return int(float(text))
    except Exception:
        return value


def normalize_upload_response_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    output = dict(payload)

    nested = _nested_upload_dict(output)

    merged = {}
    merged.update(nested)
    merged.update(output)

    filename_source = _first_text(merged, _FILENAME_KEYS)
    filename = _basename(filename_source)

    if filename:
        output.setdefault("filename", filename)
        output.setdefault("name", filename)

    url = _first_text(merged, _URL_KEYS)

    if not url and filename:
        url = "/api/uploads/" + quote(filename)

    if url:
        output.setdefault("url", url)
        output.setdefault("download_url", url)

    mime_type = _first_text(merged, _MIME_KEYS)

    if mime_type:
        output.setdefault("mime_type", mime_type)
        output.setdefault("content_type", mime_type)

    size = None

    for key in _SIZE_KEYS:
        if key in merged:
            size = _coerce_size(merged.get(key))
            break

    if size is not None:
        output.setdefault("size_bytes", size)

    return output
