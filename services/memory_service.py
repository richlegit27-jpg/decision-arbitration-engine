# notepad C:\Users\Owner\nova\services\memory_service.py
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================================================
# paths + config
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = DATA_DIR / "nova_memory.json"
MAX_MEMORY_ITEMS = 50
MAX_PROMPT_ITEMS = 12

# =========================================================
# helpers
# =========================================================

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    import uuid
    return str(uuid.uuid4())


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return default
        return json.loads(raw)
    except Exception:
        return default


def _safe_json_save(path: Path, payload: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


# =========================================================
# memory operations
# =========================================================

def _ensure_memory_file() -> None:
    if not MEMORY_FILE.exists():
        _safe_json_save(MEMORY_FILE, {"items": []})


def _load_memory_store() -> Dict[str, Any]:
    _ensure_memory_file()
    store = _safe_json_load(MEMORY_FILE, {"items": []})
    if not isinstance(store, dict):
        return {"items": []}
    items = store.get("items")
    if not isinstance(items, list):
        store["items"] = []
    return store


def _save_memory_store(store: Dict[str, Any]) -> None:
    _safe_json_save(MEMORY_FILE, store)


# =========================================================
# public API
# =========================================================

def get_all_memory() -> List[Dict[str, Any]]:
    store = _load_memory_store()
    return _coerce_list(store.get("items"))


def search_memory(query: str) -> List[Dict[str, Any]]:
    results = []
    query_lower = query.lower().strip()
    for item in get_all_memory():
        kind = str(item.get("kind", "")).lower()
        value = str(item.get("value", "")).lower()
        if query_lower in kind or query_lower in value:
            results.append(item)
    return results


def add_memory(kind: str, value: str) -> Dict[str, Any]:
    kind = kind.strip() if kind else "memory"
    value = value.strip() if value else ""
    if not value:
        raise ValueError("Memory value cannot be empty.")

    store = _load_memory_store()
    items = _coerce_list(store.get("items"))

    # maintain max memory items
    if len(items) >= MAX_MEMORY_ITEMS:
        items = items[-(MAX_MEMORY_ITEMS - 1):]

    item = {
        "id": _new_id(),
        "kind": kind,
        "value": value,
        "created_at": _now_iso(),
    }
    items.append(item)
    store["items"] = items
    _save_memory_store(store)
    return item


def add_memory_from_text(text: str) -> Optional[Dict[str, Any]]:
    text = str(text or "").strip()
    if not text:
        return None
    return add_memory(kind="extracted", value=text)


def delete_memory(item_id: str) -> bool:
    store = _load_memory_store()
    items = _coerce_list(store.get("items"))
    filtered = [item for item in items if str(item.get("id")) != str(item_id)]
    changed = len(filtered) != len(items)
    store["items"] = filtered
    _save_memory_store(store)
    return changed


def export_memory() -> List[Dict[str, Any]]:
    return get_all_memory()