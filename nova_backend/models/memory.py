from __future__ import annotations

import uuid
from typing import Any, Dict

from nova_backend.utils.time_utils import iso_now, ensure_iso


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _trim(text: str, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "â€¦"


# -----------------------
# CREATE
# -----------------------

def new_memory(
    text: str = "",
    kind: str = "note",
    source: str = "assistant",
    session_id: str = "",
    meta: Dict[str, Any] | None = None,
) -> dict:
    now = iso_now()

    clean_text = _safe_str(text, "").strip()

    return {
        "id": f"memory_{uuid.uuid4().hex}",
        "text": clean_text,
        "preview": _trim(clean_text, 120),
        "kind": _safe_str(kind, "note").strip() or "note",
        "source": _safe_str(source, "assistant").strip() or "assistant",
        "session_id": _safe_str(session_id, "").strip(),
        "meta": _safe_dict(meta),
        "created_at": now,
        "updated_at": now,
    }


# -----------------------
# NORMALIZE
# -----------------------

def normalize_memory(raw: Dict[str, Any]) -> dict:
    if not isinstance(raw, dict):
        return new_memory()

    text = _safe_str(raw.get("text"), raw.get("content", "")).strip()

    preview = _safe_str(raw.get("preview"), "").strip()
    if not preview:
        preview = _trim(text, 120)

    return {
        "id": _safe_str(raw.get("id"), f"memory_{uuid.uuid4().hex}"),
        "text": text,
        "preview": preview,
        "kind": _safe_str(raw.get("kind"), "note").strip() or "note",
        "source": _safe_str(raw.get("source"), "assistant").strip() or "assistant",
        "session_id": _safe_str(raw.get("session_id"), "").strip(),
        "meta": _safe_dict(raw.get("meta")),
        "created_at": ensure_iso(raw.get("created_at")),
        "updated_at": ensure_iso(raw.get("updated_at")),
    }


# -----------------------
# HELPERS
# -----------------------

def memory_preview(memory: dict) -> str:
    try:
        preview = _safe_str(memory.get("preview"), "").strip()
        if preview:
            return preview

        text = _safe_str(memory.get("text"), "").strip()
        if text:
            return _trim(text, 120)

        return ""
    except Exception:
        return ""


def memory_score(memory: dict, query: str) -> float:
    """
    simple relevance scoring (can upgrade later)
    """
    try:
        text = _safe_str(memory.get("text"), "").lower()
        q = _safe_str(query, "").lower()

        if not text or not q:
            return 0.0

        score = 0.0

        # keyword match boost
        if q in text:
            score += 1.0

        # partial overlap
        for word in q.split():
            if word and word in text:
                score += 0.2

        # longer memories slightly stronger
        score += min(len(text) / 500.0, 0.3)

        return score
    except Exception:
        return 0.0

