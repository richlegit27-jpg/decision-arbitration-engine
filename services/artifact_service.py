# notepad C:\Users\Owner\nova\services\artifact_service.py
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================================================
# paths + config
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MAX_ARTIFACTS = int(os.getenv("NOVA_MAX_ARTIFACTS", "500"))
MAX_ARTIFACTS_PROMPT_ITEMS = int(os.getenv("NOVA_MAX_ARTIFACT_PROMPT_ITEMS", "8"))
MAX_ARTIFACT_TITLE_CHARS = int(os.getenv("NOVA_MAX_ARTIFACT_TITLE_CHARS", "180"))
MAX_ARTIFACT_KIND_CHARS = int(os.getenv("NOVA_MAX_ARTIFACT_KIND_CHARS", "40"))
MAX_ARTIFACT_TEXT_CHARS = int(os.getenv("NOVA_MAX_ARTIFACT_TEXT_CHARS", "60000"))
MAX_ARTIFACT_PREVIEW_CHARS = int(os.getenv("NOVA_MAX_ARTIFACT_PREVIEW_CHARS", "360"))
MAX_ARTIFACT_SUMMARY_CHARS = int(os.getenv("NOVA_MAX_ARTIFACT_SUMMARY_CHARS", "1200"))
MAX_ARTIFACT_QUERY_CHARS = int(os.getenv("NOVA_MAX_ARTIFACT_QUERY_CHARS", "3000"))

ALLOWED_KINDS = {
    "note",
    "document",
    "code",
    "image",
    "chat",
    "web",
    "plan",
    "draft",
    "file",
    "other",
}


# =========================================================
# helpers
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def preview_text(text: str, limit: int = MAX_ARTIFACT_PREVIEW_CHARS) -> str:
    return truncate(re.sub(r"\s+", " ", clean_text(text)), limit)


def summarize_text(text: str, limit: int = MAX_ARTIFACT_SUMMARY_CHARS) -> str:
    text = clean_text(text)
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    kept: List[str] = []
    total = 0
    for part in parts:
        part = clean_text(part)
        if not part:
            continue
        if total + len(part) > limit:
            break
        kept.append(part)
        total += len(part) + 1
        if len(kept) >= 6:
            break
    if not kept:
        return truncate(text, limit)
    return truncate(" ".join(kept), limit)


def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def canonicalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def tokenize(value: Any) -> List[str]:
    text = clean_text(value).lower()
    return re.findall(r"[a-z0-9]{2,}", text)


def json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, default=json_default)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise


def backup_file(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    backup_path = BACKUP_DIR / f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except Exception:
        return None


# =========================================================
# persistence
# =========================================================

def default_store() -> Dict[str, Any]:
    return {
        "items": [],
        "updated_at": utc_now_iso(),
    }


def strip_internal_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(item)
    out.pop("canonical_title", None)
    out.pop("canonical_text", None)
    out.pop("token_set", None)
    out.pop("search_blob", None)
    return out


def infer_kind(value: Any) -> str:
    kind = clean_text(value).lower()
    if kind in ALLOWED_KINDS:
        return kind
    return "other"


def normalize_artifact_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    item = safe_dict(item)

    title = truncate(clean_text(item.get("title")) or "Untitled artifact", MAX_ARTIFACT_TITLE_CHARS)
    kind = infer_kind(item.get("kind") or "other")
    text = truncate(clean_text(item.get("text") or item.get("content") or ""), MAX_ARTIFACT_TEXT_CHARS)
    summary = truncate(clean_text(item.get("summary")) or summarize_text(text), MAX_ARTIFACT_SUMMARY_CHARS)
    preview = truncate(clean_text(item.get("preview")) or preview_text(text or summary or title), MAX_ARTIFACT_PREVIEW_CHARS)

    created_at = clean_text(item.get("created_at")) or utc_now_iso()
    updated_at = clean_text(item.get("updated_at")) or created_at

    normalized = {
        "id": clean_text(item.get("id")) or str(uuid.uuid4()),
        "session_id": clean_text(item.get("session_id")) or None,
        "message_id": clean_text(item.get("message_id")) or None,
        "title": title,
        "kind": kind,
        "text": text,
        "content": text,
        "summary": summary,
        "preview": preview,
        "pinned": safe_bool(item.get("pinned"), False),
        "source": clean_text(item.get("source")) or "manual",
        "created_at": created_at,
        "updated_at": updated_at,
        "metadata": safe_dict(item.get("metadata")),
        "canonical_title": canonicalize_text(title),
        "canonical_text": canonicalize_text(text[:2000]),
        "token_set": sorted(set(tokenize(f"{title}\n{text}\n{summary}"))),
        "search_blob": clean_text(f"{title}\n{text}\n{summary}\n{preview}").lower(),
    }
    return normalized


def choose_better_item(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    a_score = 0
    b_score = 0

    if safe_bool(a.get("pinned")):
        a_score += 10
    if safe_bool(b.get("pinned")):
        b_score += 10

    a_score += len(clean_text(a.get("text")))
    b_score += len(clean_text(b.get("text")))

    winner = dict(a if a_score >= b_score else b)
    loser = dict(b if winner is a else a)

    winner["updated_at"] = max(clean_text(a.get("updated_at")), clean_text(b.get("updated_at"))) or utc_now_iso()
    winner["metadata"] = {
        **safe_dict(loser.get("metadata")),
        **safe_dict(winner.get("metadata")),
    }
    if not clean_text(winner.get("summary")):
        winner["summary"] = clean_text(loser.get("summary"))
    if not clean_text(winner.get("preview")):
        winner["preview"] = clean_text(loser.get("preview"))
    if not clean_text(winner.get("text")):
        winner["text"] = clean_text(loser.get("text"))
        winner["content"] = clean_text(loser.get("text"))
    if not clean_text(winner.get("session_id")):
        winner["session_id"] = clean_text(loser.get("session_id")) or None
    if not clean_text(winner.get("message_id")):
        winner["message_id"] = clean_text(loser.get("message_id")) or None

    return normalize_artifact_item(winner) or normalize_artifact_item(a) or normalize_artifact_item(b) or {}


def dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for raw in safe_list(items):
        item = normalize_artifact_item(raw)
        if not item:
            continue

        merged = False
        for idx, existing in enumerate(out):
            same_id = existing.get("id") == item.get("id")
            same_content = (
                existing.get("canonical_title") == item.get("canonical_title")
                and existing.get("canonical_text") == item.get("canonical_text")
            )
            if same_id or same_content:
                better = choose_better_item(existing, item)
                if better:
                    out[idx] = better
                merged = True
                break

        if not merged:
            out.append(item)

    pinned = [x for x in out if safe_bool(x.get("pinned"))]
    unpinned = [x for x in out if not safe_bool(x.get("pinned"))]

    pinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    unpinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    return (pinned + unpinned)[:MAX_ARTIFACTS]


def normalize_store(store: Dict[str, Any]) -> Dict[str, Any]:
    store = safe_dict(store)
    items = [normalize_artifact_item(x) for x in safe_list(store.get("items"))]
    items = [x for x in items if x]
    items = dedupe_items(items)
    return {
        "items": items,
        "updated_at": clean_text(store.get("updated_at")) or utc_now_iso(),
    }


def load_store() -> Dict[str, Any]:
    if not ARTIFACTS_FILE.exists():
        store = default_store()
        atomic_write_json(ARTIFACTS_FILE, store)
        return normalize_store(store)

    try:
        with ARTIFACTS_FILE.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("artifacts file must contain an object")
    except Exception:
        backup_file(ARTIFACTS_FILE)
        fallback = default_store()
        atomic_write_json(ARTIFACTS_FILE, fallback)
        return normalize_store(fallback)

    return normalize_store(raw)


def save_store(store: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_store(store)
    normalized["updated_at"] = utc_now_iso()
    serializable = {
        "items": [strip_internal_fields(x) for x in normalized["items"]],
        "updated_at": normalized["updated_at"],
    }
    atomic_write_json(ARTIFACTS_FILE, serializable)
    return normalize_store(serializable)


# =========================================================
# scoring + search
# =========================================================

def score_artifact(item: Dict[str, Any], query: str = "", session_id: Optional[str] = None) -> int:
    item = normalize_artifact_item(item) or {}
    if not item:
        return 0

    score = 0
    query = truncate(clean_text(query), MAX_ARTIFACT_QUERY_CHARS)
    query_tokens = set(tokenize(query))
    item_tokens = set(safe_list(item.get("token_set")))

    if safe_bool(item.get("pinned")):
        score += 20

    if session_id and clean_text(item.get("session_id")) and clean_text(item.get("session_id")) == clean_text(session_id):
        score += 12

    overlap = len(query_tokens & item_tokens)
    score += overlap * 6

    blob = clean_text(item.get("search_blob")).lower()
    query_lower = query.lower()
    if query_lower:
        if query_lower in blob:
            score += 12
        elif any(token in blob for token in query_tokens):
            score += 4

    kind = clean_text(item.get("kind"))
    kind_weights = {
        "document": 6,
        "code": 6,
        "draft": 5,
        "plan": 5,
        "note": 4,
        "web": 4,
        "chat": 3,
        "image": 2,
        "file": 2,
        "other": 1,
    }
    score += kind_weights.get(kind, 0)

    if clean_text(item.get("updated_at")):
        score += 1

    return score


def list_filtered_artifacts(
    *,
    session_id: Optional[str] = None,
    query: str = "",
    kind: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    items = load_store()["items"]

    if session_id:
        items = [x for x in items if clean_text(x.get("session_id")) == clean_text(session_id)]

    if kind:
        kind = infer_kind(kind)
        items = [x for x in items if clean_text(x.get("kind")) == kind]

    if query:
        scored: List[Dict[str, Any]] = []
        for item in items:
            enriched = dict(item)
            enriched["relevance_score"] = score_artifact(item, query=query, session_id=session_id)
            scored.append(enriched)

        scored.sort(
            key=lambda x: (
                -safe_int(x.get("relevance_score"), 0),
                not safe_bool(x.get("pinned")),
                x.get("updated_at", ""),
            )
        )
        items = [x for x in scored if safe_int(x.get("relevance_score"), 0) > 0]
    else:
        pinned = [x for x in items if safe_bool(x.get("pinned"))]
        unpinned = [x for x in items if not safe_bool(x.get("pinned"))]
        pinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        unpinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        items = pinned + unpinned

    return [strip_internal_fields(x) for x in items[: max(1, limit)]]


# =========================================================
# CRUD
# =========================================================

def list_artifacts(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = safe_dict(payload)
    session_id = clean_text(payload.get("session_id")) or None
    query = truncate(clean_text(payload.get("q") or payload.get("query")), MAX_ARTIFACT_QUERY_CHARS)
    kind = clean_text(payload.get("kind"))
    limit = max(1, safe_int(payload.get("limit"), 200))

    items = list_filtered_artifacts(
        session_id=session_id,
        query=query,
        kind=kind,
        limit=limit,
    )

    return {
        "ok": True,
        "items": items,
        "artifacts": items,
        "count": len(items),
        "updated_at": load_store().get("updated_at"),
        "error": None,
    }


def get_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))
    if not artifact_id:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "id or artifact_id is required.",
            },
        }

    for item in load_store()["items"]:
        if clean_text(item.get("id")) == artifact_id:
            return {
                "ok": True,
                "artifact": strip_internal_fields(item),
                "error": None,
            }

    return {
        "ok": False,
        "error": {
            "code": "not_found",
            "message": "Artifact not found.",
        },
    }


def create_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)

    item = normalize_artifact_item(
        {
            "session_id": clean_text(payload.get("session_id")) or None,
            "message_id": clean_text(payload.get("message_id")) or None,
            "title": clean_text(payload.get("title")) or "Untitled artifact",
            "kind": clean_text(payload.get("kind")) or "other",
            "text": clean_text(payload.get("text") or payload.get("content")),
            "summary": clean_text(payload.get("summary")),
            "preview": clean_text(payload.get("preview")),
            "pinned": safe_bool(payload.get("pinned"), False),
            "source": clean_text(payload.get("source")) or "manual",
            "metadata": safe_dict(payload.get("metadata")),
        }
    )
    if not item:
        return {
            "ok": False,
            "error": {
                "code": "invalid_artifact",
                "message": "Artifact payload could not be normalized.",
            },
        }

    store = load_store()
    store["items"].append(item)
    saved = save_store(store)

    final = next((x for x in saved["items"] if x.get("id") == item.get("id")), None) or item

    return {
        "ok": True,
        "artifact": strip_internal_fields(final),
        "error": None,
    }


def save_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)

    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))
    if artifact_id:
        return update_artifact(payload)

    return create_artifact(payload)


def update_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))
    if not artifact_id:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "id or artifact_id is required.",
            },
        }

    store = load_store()
    found = None
    updated_items: List[Dict[str, Any]] = []

    for item in store["items"]:
        if clean_text(item.get("id")) != artifact_id:
            updated_items.append(item)
            continue

        found = dict(item)
        merged = {
            **item,
            "title": clean_text(payload.get("title")) or item.get("title"),
            "kind": clean_text(payload.get("kind")) or item.get("kind"),
            "text": clean_text(payload.get("text") or payload.get("content")) or item.get("text"),
            "summary": clean_text(payload.get("summary")) or item.get("summary"),
            "preview": clean_text(payload.get("preview")) or item.get("preview"),
            "session_id": clean_text(payload.get("session_id")) or item.get("session_id"),
            "message_id": clean_text(payload.get("message_id")) or item.get("message_id"),
            "pinned": safe_bool(payload.get("pinned"), safe_bool(item.get("pinned"))),
            "source": clean_text(payload.get("source")) or item.get("source"),
            "updated_at": utc_now_iso(),
            "metadata": {
                **safe_dict(item.get("metadata")),
                **safe_dict(payload.get("metadata")),
            },
        }
        updated_items.append(normalize_artifact_item(merged) or item)

    if found is None:
        return {
            "ok": False,
            "error": {
                "code": "not_found",
                "message": "Artifact not found.",
            },
        }

    store["items"] = updated_items
    saved = save_store(store)
    final = next((x for x in saved["items"] if x.get("id") == artifact_id), None)

    return {
        "ok": True,
        "artifact": strip_internal_fields(final or found),
        "error": None,
    }


def delete_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))
    if not artifact_id:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "id or artifact_id is required.",
            },
        }

    store = load_store()
    kept: List[Dict[str, Any]] = []
    found = False

    for item in store["items"]:
        if clean_text(item.get("id")) == artifact_id:
            found = True
            continue
        kept.append(item)

    if not found:
        return {
            "ok": False,
            "error": {
                "code": "not_found",
                "message": "Artifact not found.",
            },
        }

    store["items"] = kept
    save_store(store)

    return {
        "ok": True,
        "deleted_id": artifact_id,
        "error": None,
    }


# =========================================================
# pinning
# =========================================================

def pin_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))
    pinned = safe_bool(payload.get("pinned"), True)

    if not artifact_id:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "id or artifact_id is required.",
            },
        }

    return update_artifact(
        {
            "id": artifact_id,
            "pinned": pinned,
        }
    )


def toggle_artifact_pin(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))
    if not artifact_id:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "id or artifact_id is required.",
            },
        }

    current = get_artifact({"id": artifact_id})
    if not current.get("ok"):
        return current

    artifact = safe_dict(current.get("artifact"))
    new_value = not safe_bool(artifact.get("pinned"), False)
    return update_artifact(
        {
            "id": artifact_id,
            "pinned": new_value,
        }
    )


# =========================================================
# export
# =========================================================

def export_artifact(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    artifact_id = clean_text(payload.get("id") or payload.get("artifact_id"))

    if artifact_id:
        result = get_artifact({"id": artifact_id})
        if not result.get("ok"):
            return result
        artifact = safe_dict(result.get("artifact"))
        return {
            "ok": True,
            "artifact": artifact,
            "export": artifact,
            "error": None,
        }

    items = [strip_internal_fields(x) for x in load_store()["items"]]
    return {
        "ok": True,
        "items": items,
        "count": len(items),
        "updated_at": load_store().get("updated_at"),
        "error": None,
    }


# =========================================================
# prompt context
# =========================================================

def select_relevant_artifacts(
    *,
    query: str,
    session_id: Optional[str] = None,
    limit: int = MAX_ARTIFACTS_PROMPT_ITEMS,
) -> List[Dict[str, Any]]:
    items = load_store()["items"]
    scored: List[Dict[str, Any]] = []

    for item in items:
        enriched = dict(item)
        enriched["relevance_score"] = score_artifact(item, query=query, session_id=session_id)
        scored.append(enriched)

    scored.sort(
        key=lambda x: (
            -safe_int(x.get("relevance_score"), 0),
            not safe_bool(x.get("pinned")),
            x.get("updated_at", ""),
        )
    )

    selected = [x for x in scored if safe_int(x.get("relevance_score"), 0) > 0]
    return [strip_internal_fields(x) for x in selected[:limit]]


def build_artifact_prompt_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    raw_items = safe_list(payload.get("artifacts"))
    query = truncate(clean_text(payload.get("query") or payload.get("content")), MAX_ARTIFACT_QUERY_CHARS)
    session_id = clean_text(payload.get("session_id")) or None

    items: List[Dict[str, Any]] = []

    if raw_items:
        for raw in raw_items[:MAX_ARTIFACTS_PROMPT_ITEMS]:
            item = normalize_artifact_item(raw)
            if item:
                items.append(strip_internal_fields(item))
    elif query:
        items = select_relevant_artifacts(
            query=query,
            session_id=session_id,
            limit=MAX_ARTIFACTS_PROMPT_ITEMS,
        )

    lines: List[str] = []
    if items:
        lines.append("Artifact context:")

    for item in items:
        artifact = safe_dict(item)
        title = clean_text(artifact.get("title")) or "Untitled artifact"
        kind = clean_text(artifact.get("kind")) or "other"
        summary = clean_text(artifact.get("summary"))
        text = clean_text(artifact.get("text"))

        lines.append(f"- {title} ({kind})")
        if summary:
            lines.append(f"  Summary: {truncate(summary, MAX_ARTIFACT_SUMMARY_CHARS)}")
        elif text:
            lines.append(f"  Preview: {truncate(text, 700)}")

    return {
        "ok": True,
        "items": items,
        "artifacts": items,
        "prompt_text": "\n".join(lines).strip(),
        "error": None,
    }


# =========================================================
# diagnostics
# =========================================================

def artifact_stats() -> Dict[str, Any]:
    items = load_store()["items"]

    by_kind: Dict[str, int] = {}
    pinned_count = 0
    total_chars = 0

    for item in items:
        kind = clean_text(item.get("kind")) or "other"
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if safe_bool(item.get("pinned")):
            pinned_count += 1
        total_chars += len(clean_text(item.get("text")))

    return {
        "ok": True,
        "count": len(items),
        "pinned_count": pinned_count,
        "total_chars": total_chars,
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: kv[0])),
        "file": str(ARTIFACTS_FILE),
        "updated_at": load_store().get("updated_at"),
        "error": None,
    }