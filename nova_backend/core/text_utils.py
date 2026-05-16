from __future__ import annotations

from typing import Any


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def summarize_text(value: str, limit: int = 120) -> str:
    text = normalize_text(value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def textish(value: Any) -> str:
    return str(value or "").strip()