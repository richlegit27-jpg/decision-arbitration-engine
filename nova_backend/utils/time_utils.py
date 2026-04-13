from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_iso(value: Any) -> str:
    if value is None:
        return iso_now()

    text = str(value).strip()
    if not text:
        return iso_now()

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except Exception:
        return iso_now()

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat()


def parse_iso(value: Any) -> datetime:
    text = ensure_iso(value)

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed = datetime.fromisoformat(text)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def newest_first(items: Iterable[Dict[str, Any]] | None, field: str = "updated_at") -> List[Dict[str, Any]]:
    def sort_key(item: Dict[str, Any]) -> datetime:
        if not isinstance(item, dict):
            return datetime.min.replace(tzinfo=timezone.utc)

        for key in (field, "updated_at", "created_at", "timestamp"):
            if item.get(key):
                return parse_iso(item.get(key))

        return datetime.min.replace(tzinfo=timezone.utc)

    return sorted(list(items or []), key=sort_key, reverse=True)


__all__ = [
    "iso_now",
    "ensure_iso",
    "parse_iso",
    "newest_first",
]