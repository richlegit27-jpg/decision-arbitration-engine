from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def ensure_iso(value: Any) -> str:
    if value is None:
        return iso_now()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return iso_now()

    parsed = parse_iso(text)
    if parsed is None:
        return iso_now()

    return parsed.isoformat()


def parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def sort_key(item: Any, *fields: str) -> datetime:
    if not fields:
        fields = ("updated_at", "created_at", "timestamp")

    if isinstance(item, dict):
        for field in fields:
            if field in item:
                parsed = parse_iso(item.get(field))
                if parsed is not None:
                    return parsed
        return datetime.min.replace(tzinfo=timezone.utc)

    for field in fields:
        if hasattr(item, field):
            parsed = parse_iso(getattr(item, field, None))
            if parsed is not None:
                return parsed

    return datetime.min.replace(tzinfo=timezone.utc)


def newest_first(items: list[Any], *fields: str) -> list[Any]:
    return sorted(items or [], key=lambda x: sort_key(x, *fields), reverse=True)


def oldest_first(items: list[Any], *fields: str) -> list[Any]:
    return sorted(items or [], key=lambda x: sort_key(x, *fields), reverse=False)

