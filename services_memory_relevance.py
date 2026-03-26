from __future__ import annotations

import uuid
from typing import Any, Callable


def get_user_memory_items_impl(
    username: str,
    memory_items: list[dict[str, Any]],
    normalize_username_func: Callable[[str], str],
) -> list[dict[str, Any]]:
    username = normalize_username_func(username)
    return [
        item
        for item in memory_items
        if normalize_username_func(str(item.get("user", ""))) == username
    ]


def extract_memory_impl(
    text: str,
    clean_text_func: Callable[[Any], str],
    now_iso_func: Callable[[], str],
) -> dict[str, Any] | None:
    raw = clean_text_func(text)
    lowered = raw.lower()

    triggers = [
        "my name is",
        "i am",
        "i like",
        "i want",
        "my goal is",
        "i prefer",
    ]

    if any(trigger in lowered for trigger in triggers):
        return {
            "id": str(uuid.uuid4()),
            "value": raw[:200],
            "kind": "memory",
            "created_at": now_iso_func(),
            "updated_at": now_iso_func(),
        }

    return None


def get_relevant_memory_impl(
    username: str,
    user_text: str,
    memory_items: list[dict[str, Any]],
    normalize_username_func: Callable[[str], str],
    clean_text_func: Callable[[Any], str],
) -> list[dict[str, Any]]:
    text = clean_text_func(user_text).lower()
    user_items = get_user_memory_items_impl(
        username=username,
        memory_items=memory_items,
        normalize_username_func=normalize_username_func,
    )

    scored: list[tuple[int, dict[str, Any]]] = []

    for item in user_items:
        value = str(item.get("value", "")).lower()
        score = sum(1 for word in text.split() if word and word in value)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda row: row[0], reverse=True)
    return [item for _, item in scored[:3]]