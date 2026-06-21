from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT_DIR / "runtime"
ATTACHMENT_MEMORY_FILE = RUNTIME_DIR / "attachments_memory.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load() -> List[Dict[str, Any]]:
    try:
        if not ATTACHMENT_MEMORY_FILE.exists():
            return []

        data = json.loads(ATTACHMENT_MEMORY_FILE.read_text(encoding="utf-8"))

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict) and isinstance(data.get("attachments"), list):
            return [item for item in data["attachments"] if isinstance(item, dict)]

        return []
    except Exception:
        return []


def _safe_write(items: List[Dict[str, Any]]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "ok": True,
        "updated_at": _now_iso(),
        "count": len(items),
        "attachments": items[-1000:],
    }

    ATTACHMENT_MEMORY_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize_attachment_memory_item(
    attachment: Dict[str, Any],
    *,
    session_id: str = "",
    client_session_id: str = "",
) -> Dict[str, Any]:
    file_url = str(
        attachment.get("file_url")
        or attachment.get("url")
        or ""
    ).strip()

    fallback_name = Path(file_url).name.strip()

    filename = str(
        attachment.get("filename")
        or attachment.get("original_filename")
        or attachment.get("name")
        or fallback_name
        or ""
    ).strip()

    original_filename = str(
        attachment.get("original_filename")
        or attachment.get("filename")
        or attachment.get("name")
        or filename
        or fallback_name
        or ""
    ).strip()

    if not filename or filename == "<unknown>":
        filename = fallback_name

    if not original_filename or original_filename == "<unknown>":
        original_filename = filename or fallback_name

    return {
        "filename": filename or fallback_name or "<unknown>",
        "original_filename": original_filename or filename or fallback_name or "<unknown>",
        "file_url": file_url,
        "url": str(attachment.get("url") or file_url or "").strip(),
        "mime_type": str(attachment.get("mime_type") or attachment.get("type") or "").strip(),
        "size": int(attachment.get("size") or 0),
        "session_id": str(session_id or "").strip(),
        "client_session_id": str(client_session_id or session_id or "").strip(),
        "created_at": _now_iso(),
    }


def persist_attachments_for_session(
    attachments: Iterable[Dict[str, Any]],
    *,
    session_id: str = "",
    client_session_id: str = "",
) -> int:
    existing = _safe_load()
    added = 0

    for attachment in attachments or []:
        if not isinstance(attachment, dict):
            continue

        item = normalize_attachment_memory_item(
            attachment,
            session_id=session_id,
            client_session_id=client_session_id,
        )

        dedupe_key = (
            item.get("session_id"),
            item.get("client_session_id"),
            item.get("filename"),
            item.get("file_url"),
            item.get("size"),
        )

        already_exists = any(
            (
                old.get("session_id"),
                old.get("client_session_id"),
                old.get("filename"),
                old.get("file_url"),
                old.get("size"),
            ) == dedupe_key
            for old in existing
        )

        if already_exists:
            continue

        existing.append(item)
        added += 1

    if added:
        _safe_write(existing)

    return added


# ATTACHMENT_MEMORY_SESSION_RETRIEVAL_LOCK
def get_attachments_for_session(
    session_id: str,
    *,
    limit: int = 50,
    client_session_id: str = "",
) -> List[Dict[str, Any]]:
    target_session_id = str(session_id or "").strip()
    target_client_session_id = str(client_session_id or "").strip()

    if not target_session_id and not target_client_session_id:
        return []

    items = _safe_load()
    matched = []

    for item in items:
        item_session_id = str(item.get("session_id") or "").strip()
        item_client_session_id = str(item.get("client_session_id") or "").strip()

        if target_session_id and (
            item_session_id == target_session_id
            or item_client_session_id == target_session_id
        ):
            matched.append(item)
            continue

        if target_client_session_id and (
            item_session_id == target_client_session_id
            or item_client_session_id == target_client_session_id
        ):
            matched.append(item)

    return matched[-max(1, int(limit or 50)):]


def summarize_attachments_for_session(
    session_id: str,
    *,
    limit: int = 10,
    client_session_id: str = "",
) -> List[Dict[str, Any]]:
    attachments = get_attachments_for_session(
        session_id,
        limit=limit,
        client_session_id=client_session_id,
    )

    summary = []

    for item in attachments:
        summary.append({
            "filename": item.get("filename") or "<unknown>",
            "original_filename": item.get("original_filename") or item.get("filename") or "<unknown>",
            "file_url": item.get("file_url") or item.get("url") or "",
            "mime_type": item.get("mime_type") or "",
            "size": item.get("size") or 0,
            "client_session_id": item.get("client_session_id") or "",
            "session_id": item.get("session_id") or "",
            "created_at": item.get("created_at") or "",
        })

    return summary

# ATTACHMENT_MEMORY_SESSION_ALIAS_FIX_LOCK
# ATTACHMENT_FILENAME_FIX_LOCK
# ATTACHMENT_FILENAME_FROM_URL_LOCK

# ATTACHMENT_FORCE_FILENAME_FIX_LOCK


