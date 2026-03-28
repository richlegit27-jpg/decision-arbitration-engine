# notepad C:\Users\Owner\nova\services\artifact_service.py
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

ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MAX_ARTIFACTS = 200

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
# artifact operations
# =========================================================

def _ensure_artifacts_file() -> None:
    if not ARTIFACTS_FILE.exists():
        _safe_json_save(ARTIFACTS_FILE, {"items": []})


def _load_artifacts_store() -> Dict[str, Any]:
    _ensure_artifacts_file()
    store = _safe_json_load(ARTIFACTS_FILE, {"items": []})
    if not isinstance(store, dict):
        return {"items": []}
    items = store.get("items")
    if not isinstance(items, list):
        store["items"] = []
    return store


def _save_artifacts_store(store: Dict[str, Any]) -> None:
    _safe_json_save(ARTIFACTS_FILE, store)


# =========================================================
# public API
# =========================================================

def list_artifacts(query: str = "", session_id: Optional[str] = None, pinned_only: bool = False) -> List[Dict[str, Any]]:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))

    result = []
    query_lower = query.lower().strip()
    for item in items:
        if pinned_only and not item.get("pinned", False):
            continue
        if session_id and item.get("session_id") != session_id:
            continue
        if query_lower and query_lower not in str(item.get("title", "")).lower():
            continue
        result.append(item)
    return result


def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    items = _coerce_list(_load_artifacts_store().get("items"))
    for item in items:
        if str(item.get("id")) == str(artifact_id):
            return item
    return None


def create_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))

    if len(items) >= MAX_ARTIFACTS:
        items = items[-(MAX_ARTIFACTS - 1):]

    artifact = {
        "id": payload.get("id") or _new_id(),
        "title": str(payload.get("title") or "Untitled Artifact"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "session_id": payload.get("session_id"),
        "pinned": bool(payload.get("pinned", False)),
        "content": str(payload.get("content") or ""),
        "meta": _coerce_dict(payload.get("meta")),
    }
    items.append(artifact)
    store["items"] = items
    _save_artifacts_store(store)
    return artifact


def save_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    artifact_id = str(payload.get("id") or "")
    if not artifact_id:
        return create_artifact(payload)

    updated = update_artifact(payload)
    return updated


def update_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))
    artifact_id = str(payload.get("id") or "")

    updated = None
    for idx, item in enumerate(items):
        if str(item.get("id")) == artifact_id:
            for key, value in payload.items():
                if key not in {"id", "created_at"}:
                    item[key] = value
            item["updated_at"] = _now_iso()
            updated = item
            items[idx] = item
            break

    if updated:
        store["items"] = items
        _save_artifacts_store(store)
        return updated
    else:
        return create_artifact(payload)


def delete_artifact(artifact_id: str) -> bool:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))
    filtered = [item for item in items if str(item.get("id")) != str(artifact_id)]
    changed = len(filtered) != len(items)
    store["items"] = filtered
    _save_artifacts_store(store)
    return changed


def toggle_artifact_pin(artifact_id: str) -> Optional[Dict[str, Any]]:
    artifact = get_artifact(artifact_id)
    if not artifact:
        return None
    artifact["pinned"] = not bool(artifact.get("pinned", False))
    artifact["updated_at"] = _now_iso()
    return update_artifact(artifact)


def pin_artifact(artifact_id: str, pinned: bool = True) -> Optional[Dict[str, Any]]:
    artifact = get_artifact(artifact_id)
    if not artifact:
        return None
    artifact["pinned"] = bool(pinned)
    artifact["updated_at"] = _now_iso()
    return update_artifact(artifact)


def maybe_create_artifacts_for_message(session: Dict[str, Any], user_message: Dict[str, Any], assistant_message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Optional hook: create artifacts from messages. Currently a placeholder.
    """
    return []


def export_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    artifact = get_artifact(artifact_id)
    return artifact.copy() if artifact else None