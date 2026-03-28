from __future__ import annotations

import json
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


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


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


def _normalize_media_item(item: Any) -> Dict[str, Any]:
    item = _coerce_dict(item)
    meta = _coerce_dict(item.get("meta"))

    return {
        "id": _clean_text(item.get("id")).strip() or _new_id(),
        "kind": _clean_text(item.get("kind")).strip() or "file",
        "title": _clean_text(item.get("title")).strip(),
        "source_url": _clean_text(item.get("source_url")).strip(),
        "preview_url": _clean_text(item.get("preview_url")).strip(),
        "thumbnail_url": _clean_text(item.get("thumbnail_url")).strip(),
        "local_path": _clean_text(item.get("local_path")).strip(),
        "mime_type": _clean_text(item.get("mime_type")).strip(),
        "status": _clean_text(item.get("status")).strip() or "ready",
        "summary": _clean_text(item.get("summary")).strip(),
        "extracted_text": _clean_text(item.get("extracted_text")).strip(),
        "transcript": _clean_text(item.get("transcript")).strip(),
        "duration_seconds": item.get("duration_seconds"),
        "width": item.get("width"),
        "height": item.get("height"),
        "size_bytes": item.get("size_bytes"),
        "provider": _clean_text(item.get("provider")).strip(),
        "host": _clean_text(item.get("host")).strip(),
        "created_at": _clean_text(item.get("created_at")).strip() or _now_iso(),
        "errors": [str(x) for x in _coerce_list(item.get("errors")) if str(x).strip()],
        "meta": meta,
    }


def _normalize_media_list(value: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen = set()

    for raw in _coerce_list(value):
        item = _normalize_media_item(raw)
        key = (
            _clean_text(item.get("kind")).lower(),
            _clean_text(item.get("source_url")),
            _clean_text(item.get("preview_url")),
        )
        if not key[1] and not key[2]:
            key = ("id", _clean_text(item.get("id")), "")
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)

    return normalized


def _media_to_attachments(media: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    attachments: List[Dict[str, Any]] = []

    for item in media:
        item = _coerce_dict(item)
        url = _clean_text(item.get("preview_url") or item.get("source_url")).strip()
        source_url = _clean_text(item.get("source_url")).strip()
        kind = _clean_text(item.get("kind")).strip() or "file"
        title = _clean_text(item.get("title")).strip()

        filename = ""
        if url:
            try:
                filename = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
            except Exception:
                filename = ""
        if not filename:
            filename = title or f"{kind}_asset"

        attachments.append(
            {
                "id": _clean_text(item.get("id")).strip(),
                "name": filename,
                "mime_type": _clean_text(item.get("mime_type")).strip(),
                "type": kind,
                "url": url,
                "source_url": source_url,
                "stored_path": _clean_text(item.get("local_path")).strip(),
                "path": _clean_text(item.get("local_path")).strip(),
                "size": item.get("size_bytes") or 0,
                "meta": {
                    "kind": kind,
                    "title": title,
                    "thumbnail_url": _clean_text(item.get("thumbnail_url")).strip(),
                    "host": _clean_text(item.get("host")).strip(),
                    "provider": _clean_text(item.get("provider")).strip(),
                },
            }
        )

    return attachments


def _split_media_compat(media: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    images: List[Dict[str, Any]] = []
    videos: List[Dict[str, Any]] = []
    audios: List[Dict[str, Any]] = []

    for item in media:
        item = _coerce_dict(item)
        kind = _clean_text(item.get("kind")).lower()
        compat_item = {
            "url": _clean_text(item.get("preview_url") or item.get("source_url")).strip(),
            "kind": kind,
            "source": _clean_text(_coerce_dict(item.get("meta")).get("source")).strip(),
            "alt": _clean_text(_coerce_dict(item.get("meta")).get("alt")).strip(),
            "title": _clean_text(item.get("title")).strip(),
            "mime_type": _clean_text(item.get("mime_type")).strip(),
            "poster": _clean_text(item.get("thumbnail_url")).strip(),
        }
        if kind == "image":
            images.append(compat_item)
        elif kind == "video":
            videos.append(compat_item)
        elif kind == "audio":
            audios.append(compat_item)

    return {
        "images": images,
        "videos": videos,
        "audios": audios,
    }


def _normalize_artifact(payload: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = _coerce_dict(payload)
    existing = _coerce_dict(existing)

    media = _normalize_media_list(payload.get("media") if "media" in payload else existing.get("media"))
    attachments = _media_to_attachments(media)
    compat = _split_media_compat(media)

    created_at = _clean_text(payload.get("created_at")).strip() or _clean_text(existing.get("created_at")).strip() or _now_iso()

    artifact = {
        "id": _clean_text(payload.get("id")).strip() or _clean_text(existing.get("id")).strip() or _new_id(),
        "title": _clean_text(payload.get("title")).strip() or _clean_text(existing.get("title")).strip() or "Untitled Artifact",
        "type": _clean_text(payload.get("type")).strip() or _clean_text(existing.get("type")).strip() or "artifact",
        "session_id": payload.get("session_id") if "session_id" in payload else existing.get("session_id"),
        "content": _clean_text(payload.get("content")) if "content" in payload else _clean_text(existing.get("content")),
        "media": media,
        "attachments": attachments,
        "images": compat["images"],
        "videos": compat["videos"],
        "audios": compat["audios"],
        "created_at": created_at,
        "updated_at": _now_iso(),
        "pinned": bool(payload.get("pinned", existing.get("pinned", False))),
        "meta": {
            **_coerce_dict(existing.get("meta")),
            **_coerce_dict(payload.get("meta")),
        },
    }
    return artifact


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
    normalized_items: List[Dict[str, Any]] = []
    for item in _coerce_list(store.get("items")):
        normalized_items.append(_normalize_artifact(_coerce_dict(item)))
    store["items"] = normalized_items
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
        item = _coerce_dict(item)
        if pinned_only and not item.get("pinned", False):
            continue
        if session_id and item.get("session_id") != session_id:
            continue

        if query_lower:
            haystack = " ".join(
                [
                    _clean_text(item.get("title")),
                    _clean_text(item.get("content")),
                    _clean_text(json.dumps(item.get("meta", {}), ensure_ascii=False)),
                    _clean_text(json.dumps(item.get("media", []), ensure_ascii=False)),
                ]
            ).lower()
            if query_lower not in haystack:
                continue

        result.append(item)

    result.sort(key=lambda x: (_clean_text(x.get("updated_at")), _clean_text(x.get("created_at"))), reverse=True)
    return result


def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    items = _coerce_list(_load_artifacts_store().get("items"))
    for item in items:
        item = _coerce_dict(item)
        if str(item.get("id")) == str(artifact_id):
            return item
    return None


def create_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))

    if len(items) >= MAX_ARTIFACTS:
        items = items[-(MAX_ARTIFACTS - 1):]

    artifact = _normalize_artifact(payload)
    items.append(artifact)
    store["items"] = items
    _save_artifacts_store(store)
    return artifact


def save_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    artifact_id = str(payload.get("id") or "").strip()
    if not artifact_id:
        return create_artifact(payload)
    return update_artifact(payload)


def update_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))
    artifact_id = str(payload.get("id") or "").strip()

    if not artifact_id:
        return create_artifact(payload)

    updated: Optional[Dict[str, Any]] = None
    for idx, item in enumerate(items):
        item = _coerce_dict(item)
        if str(item.get("id")) == artifact_id:
            updated = _normalize_artifact(payload, existing=item)
            items[idx] = updated
            break

    if updated is None:
        return create_artifact(payload)

    store["items"] = items
    _save_artifacts_store(store)
    return updated


def delete_artifact(artifact_id: str) -> bool:
    store = _load_artifacts_store()
    items = _coerce_list(store.get("items"))
    filtered = [item for item in items if str(_coerce_dict(item).get("id")) != str(artifact_id)]
    changed = len(filtered) != len(items)
    store["items"] = filtered
    _save_artifacts_store(store)
    return changed


def toggle_artifact_pin(artifact_id: str) -> Optional[Dict[str, Any]]:
    artifact = get_artifact(artifact_id)
    if not artifact:
        return None
    artifact["pinned"] = not bool(artifact.get("pinned", False))
    return update_artifact(artifact)


def pin_artifact(artifact_id: str, pinned: bool = True) -> Optional[Dict[str, Any]]:
    artifact = get_artifact(artifact_id)
    if not artifact:
        return None
    artifact["pinned"] = bool(pinned)
    return update_artifact(artifact)


def maybe_create_artifacts_for_message(session: Dict[str, Any], user_message: Dict[str, Any], assistant_message: Dict[str, Any]) -> List[Dict[str, Any]]:
    session = _coerce_dict(session)
    user_message = _coerce_dict(user_message)
    assistant_message = _coerce_dict(assistant_message)

    content = _clean_text(assistant_message.get("content")).strip()
    media = _normalize_media_list(assistant_message.get("media"))
    attachments = _coerce_list(assistant_message.get("attachments"))

    if not content and not media and not attachments:
        return []

    artifact = create_artifact(
        {
            "title": _clean_text(session.get("title")).strip() or "Chat Artifact",
            "type": "chat_message",
            "session_id": session.get("id"),
            "content": content,
            "media": media,
            "meta": {
                "source": "assistant_message",
                "user_message_id": user_message.get("id"),
                "assistant_message_id": assistant_message.get("id"),
            },
        }
    )
    return [artifact]


def export_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    artifact = get_artifact(artifact_id)
    return json.loads(json.dumps(artifact, ensure_ascii=False)) if artifact else None