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


def normalize_attachments(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "id": str(item.get("id") or "").strip(),
                "name": str(item.get("name") or "").strip(),
                "type": str(item.get("type") or "").strip(),
                "mime_type": str(item.get("mime_type") or item.get("mimeType") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "path": str(item.get("path") or "").strip(),
                "size": int(item.get("size") or 0),
            }
        )

    return normalized