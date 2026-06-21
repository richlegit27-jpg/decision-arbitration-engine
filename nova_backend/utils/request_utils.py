from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flask import Request


def get_json_body(request: Request) -> Dict[str, Any]:
    try:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_str(data: Dict[str, Any], key: str, default: str = "") -> str:
    try:
        value = data.get(key, default)
    except Exception:
        return str(default or "").strip()
    return str(value or "").strip()


def get_bool(data: Dict[str, Any], key: str, default: bool = False) -> bool:
    try:
        value = data.get(key, default)
    except Exception:
        return bool(default)

    if isinstance(value, bool):
        return value

    lowered = str(value or "").strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def get_list(data: Dict[str, Any], key: str) -> List[Any]:
    try:
        value = data.get(key, [])
    except Exception:
        return []
    return value if isinstance(value, list) else []


def require_str(
    data: Dict[str, Any],
    key: str,
    label: Optional[str] = None,
) -> Tuple[bool, str, str]:
    value = get_str(data, key)
    if value:
        return True, value, ""
    name = str(label or key or "value")
    return False, "", f"{name} is required."


def clip_text(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def normalize_session_id(value: Any) -> str:
    return str(value or "").strip()


def normalize_attachments(value):
    # NORMALIZE_ATTACHMENTS_PRESERVE_UPLOAD_FIELDS_LOCK
    """
    Normalize attachment payloads without destroying upload metadata.

    Mobile/frontend tests expect the /api/upload payload fields to survive:
    - filename
    - original_filename
    - file_url
    - url

    Older normalizers sometimes collapsed these into name/url only, which made
    /api/chat response.session_attachments fail to match the current upload.
    """
    if not isinstance(value, list):
        return []

    normalized = []

    for item in value:
        if not isinstance(item, dict):
            continue

        filename = str(
            item.get("filename")
            or item.get("stored_filename")
            or item.get("name")
            or ""
        ).strip()

        original_filename = str(
            item.get("original_filename")
            or item.get("original_name")
            or item.get("name")
            or filename
            or ""
        ).strip()

        file_url = str(
            item.get("file_url")
            or item.get("url")
            or ""
        ).strip()

        url = str(
            item.get("url")
            or item.get("file_url")
            or ""
        ).strip()

        if not filename and file_url:
            filename = file_url.replace("\\", "/").rsplit("/", 1)[-1].strip()

        if not original_filename:
            original_filename = filename

        if not filename and not original_filename and not file_url and not url:
            continue

        cleaned = dict(item)
        cleaned["filename"] = filename
        cleaned["original_filename"] = original_filename
        cleaned["file_url"] = file_url or url
        cleaned["url"] = url or file_url

        if "name" not in cleaned or not str(cleaned.get("name") or "").strip():
            cleaned["name"] = original_filename or filename

        normalized.append(cleaned)

    return normalized



