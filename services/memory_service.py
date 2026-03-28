# notepad C:\Users\Owner\nova\services\memory_service.py
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

MEMORY_FILE = DATA_DIR / "nova_memory.json"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MAX_MEMORY_ITEMS = int(os.getenv("MAX_MEMORY_ITEMS", "50"))
MAX_MEMORY_PROMPT_ITEMS = int(os.getenv("MAX_MEMORY_PROMPT_ITEMS", "12"))
MAX_MEMORY_VALUE_CHARS = int(os.getenv("NOVA_MAX_MEMORY_VALUE_CHARS", "600"))
MAX_MEMORY_QUERY_CHARS = int(os.getenv("NOVA_MAX_MEMORY_QUERY_CHARS", "3000"))
MAX_MEMORY_PREVIEW_CHARS = int(os.getenv("NOVA_MAX_MEMORY_PREVIEW_CHARS", "240"))

MEMORY_KINDS = {
    "identity",
    "goal",
    "project",
    "preference",
    "workflow",
    "skill",
    "background",
    "note",
}

LOW_SIGNAL_VALUES = {
    "",
    "ok",
    "okay",
    "yes",
    "no",
    "maybe",
    "test",
    "testing",
    "hello",
    "hi",
    "thanks",
    "thank you",
    "cool",
    "nice",
    "sure",
    "done",
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


def preview_text(text: str, limit: int = MAX_MEMORY_PREVIEW_CHARS) -> str:
    text = re.sub(r"\s+", " ", clean_text(text))
    return truncate(text, limit)


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
    tokens = re.findall(r"[a-z0-9]{2,}", text)
    return tokens


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
    out.pop("canonical_value", None)
    out.pop("token_set", None)
    return out


def normalize_memory_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    item = safe_dict(item)

    value = truncate(clean_text(item.get("value")), MAX_MEMORY_VALUE_CHARS)
    if not value:
        return None

    kind = clean_text(item.get("kind")).lower() or "note"
    if kind not in MEMORY_KINDS:
        kind = "note"

    created_at = clean_text(item.get("created_at")) or utc_now_iso()
    updated_at = clean_text(item.get("updated_at")) or created_at

    normalized = {
        "id": clean_text(item.get("id")) or str(uuid.uuid4()),
        "kind": kind,
        "value": value,
        "source": clean_text(item.get("source")) or "manual",
        "session_id": clean_text(item.get("session_id")) or None,
        "pinned": safe_bool(item.get("pinned"), False),
        "score": safe_int(item.get("score"), 0),
        "created_at": created_at,
        "updated_at": updated_at,
        "metadata": safe_dict(item.get("metadata")),
        "canonical_value": canonicalize_text(value),
        "token_set": sorted(set(tokenize(value))),
        "preview": preview_text(value),
    }
    return normalized


def choose_better_item(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    kind_rank = {
        "identity": 8,
        "goal": 7,
        "project": 6,
        "workflow": 5,
        "preference": 4,
        "skill": 3,
        "background": 2,
        "note": 1,
    }

    a_score = kind_rank.get(clean_text(a.get("kind")), 0) + (1 if safe_bool(a.get("pinned")) else 0)
    b_score = kind_rank.get(clean_text(b.get("kind")), 0) + (1 if safe_bool(b.get("pinned")) else 0)

    if b_score > a_score:
        winner = dict(b)
        loser = dict(a)
    else:
        winner = dict(a)
        loser = dict(b)

    winner["updated_at"] = max(clean_text(a.get("updated_at")), clean_text(b.get("updated_at"))) or utc_now_iso()
    winner["metadata"] = {
        **safe_dict(loser.get("metadata")),
        **safe_dict(winner.get("metadata")),
    }
    if not winner.get("session_id"):
        winner["session_id"] = loser.get("session_id")
    winner["pinned"] = safe_bool(winner.get("pinned")) or safe_bool(loser.get("pinned"))
    winner["score"] = max(safe_int(a.get("score"), 0), safe_int(b.get("score"), 0))
    return normalize_memory_item(winner)


def dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for raw in safe_list(items):
        item = normalize_memory_item(raw)
        if not item:
            continue

        merged = False
        for idx, existing in enumerate(out):
            same_id = existing.get("id") == item.get("id")
            same_canonical = bool(existing.get("canonical_value")) and existing.get("canonical_value") == item.get("canonical_value")
            same_kind_and_value = existing.get("kind") == item.get("kind") and same_canonical

            if same_id or same_kind_and_value:
                better = choose_better_item(existing, item)
                if better:
                    out[idx] = better
                merged = True
                break

        if not merged:
            out.append(item)

    out.sort(key=lambda x: (not safe_bool(x.get("pinned")), x.get("updated_at", "")))
    pinned = [x for x in out if safe_bool(x.get("pinned"))]
    normal = [x for x in out if not safe_bool(x.get("pinned"))]
    pinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    normal.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    final = pinned + normal
    return final[:MAX_MEMORY_ITEMS]


def normalize_store(store: Dict[str, Any]) -> Dict[str, Any]:
    store = safe_dict(store)
    items = [normalize_memory_item(x) for x in safe_list(store.get("items"))]
    items = [x for x in items if x]
    items = dedupe_items(items)
    return {
        "items": items,
        "updated_at": clean_text(store.get("updated_at")) or utc_now_iso(),
    }


def load_store() -> Dict[str, Any]:
    if not MEMORY_FILE.exists():
        store = default_store()
        atomic_write_json(MEMORY_FILE, store)
        return normalize_store(store)

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("memory file must contain an object")
    except Exception:
        backup_file(MEMORY_FILE)
        fallback = default_store()
        atomic_write_json(MEMORY_FILE, fallback)
        return normalize_store(fallback)

    return normalize_store(raw)


def save_store(store: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_store(store)
    normalized["updated_at"] = utc_now_iso()
    serializable = {
        "items": [strip_internal_fields(item) for item in normalized["items"]],
        "updated_at": normalized["updated_at"],
    }
    atomic_write_json(MEMORY_FILE, serializable)
    return normalize_store(serializable)


# =========================================================
# filtering + extraction
# =========================================================

def is_low_value_memory(value: str) -> bool:
    value = clean_text(value)
    canonical = canonicalize_text(value)

    if not value:
        return True
    if len(value) < 4:
        return True
    if canonical in LOW_SIGNAL_VALUES:
        return True
    if len(value) > MAX_MEMORY_VALUE_CHARS:
        return True

    boring_prefixes = (
        "hello",
        "hi",
        "test",
        "can you",
        "could you",
        "what is",
        "how do",
        "thanks",
        "thank you",
    )
    lowered = value.lower()
    if any(lowered.startswith(prefix) for prefix in boring_prefixes):
        return True

    return False


def infer_memory_kind(value: str) -> str:
    text = clean_text(value).lower()

    if any(x in text for x in ["my name is", "i am ", "i'm "]):
        return "identity"
    if any(x in text for x in ["i want to", "my goal", "my plan", "i plan to"]):
        return "goal"
    if any(x in text for x in ["my project", "i'm building", "i am building", "working on"]):
        return "project"
    if any(x in text for x in ["i prefer", "prefer that", "from now on", "going forward"]):
        return "preference"
    if any(x in text for x in ["workflow", "process", "routine", "always", "never"]):
        return "workflow"
    if any(x in text for x in ["i'm good at", "i am good at", "my skill", "experienced with"]):
        return "skill"

    return "note"


def extract_candidate_memories_from_text(text: str) -> List[Dict[str, Any]]:
    text = clean_text(text)
    if not text:
        return []

    patterns = [
        ("identity", r"\bmy name is\s+([A-Za-z0-9 _.\-]{2,80})"),
        ("goal", r"\bi want to\s+(.{4,180})"),
        ("goal", r"\bmy goal is to\s+(.{4,180})"),
        ("project", r"\bi(?:'m| am)\s+building\s+(.{4,180})"),
        ("project", r"\bi(?:'m| am)\s+working on\s+(.{4,180})"),
        ("preference", r"\bi prefer\s+(.{4,180})"),
        ("workflow", r"\bfrom now on\s+(.{4,180})"),
        ("workflow", r"\bgoing forward\s+(.{4,180})"),
        ("skill", r"\bi(?:'m| am)\s+good at\s+(.{4,180})"),
        ("skill", r"\bi(?:'m| am)\s+experienced with\s+(.{4,180})"),
    ]

    found: List[Dict[str, Any]] = []

    for kind, pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = clean_text(match.group(0))
            if is_low_value_memory(value):
                continue
            found.append(
                {
                    "kind": kind,
                    "value": truncate(value, MAX_MEMORY_VALUE_CHARS),
                    "source": "auto",
                    "score": 1,
                }
            )

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in found:
        key = (item.get("kind"), canonicalize_text(item.get("value")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped[:8]


# =========================================================
# scoring
# =========================================================

def score_memory_item(item: Dict[str, Any], query_text: str = "", session_id: Optional[str] = None) -> int:
    item = normalize_memory_item(item) or {}
    if not item:
        return 0

    score = 0
    kind = clean_text(item.get("kind"))
    value = clean_text(item.get("value"))
    item_tokens = set(safe_list(item.get("token_set")))
    query_tokens = set(tokenize(query_text))

    kind_weights = {
        "identity": 10,
        "goal": 9,
        "project": 8,
        "workflow": 8,
        "preference": 7,
        "skill": 6,
        "background": 5,
        "note": 3,
    }
    score += kind_weights.get(kind, 0)

    if safe_bool(item.get("pinned")):
        score += 10

    if session_id and clean_text(item.get("session_id")) and clean_text(item.get("session_id")) == clean_text(session_id):
        score += 8

    overlap = len(item_tokens & query_tokens)
    score += overlap * 6

    query_text_clean = clean_text(query_text).lower()
    value_clean = value.lower()
    if query_text_clean and value_clean and value_clean in query_text_clean:
        score += 8

    if overlap == 0 and query_text_clean:
        # soft substring signals
        for token in list(item_tokens)[:12]:
            if token and token in query_text_clean:
                score += 2

    updated_at = clean_text(item.get("updated_at"))
    if updated_at:
        score += 1

    score += safe_int(item.get("score"), 0)
    return score


def select_relevant_memories(
    *,
    query_text: str,
    session_id: Optional[str] = None,
    limit: int = MAX_MEMORY_PROMPT_ITEMS,
) -> List[Dict[str, Any]]:
    items = load_store()["items"]

    scored: List[Dict[str, Any]] = []
    for item in items:
        score = score_memory_item(item, query_text=query_text, session_id=session_id)
        enriched = dict(item)
        enriched["relevance_score"] = score
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


# =========================================================
# public CRUD
# =========================================================

def list_memory(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = safe_dict(payload)
    query = truncate(clean_text(payload.get("query")), MAX_MEMORY_QUERY_CHARS)
    kind = clean_text(payload.get("kind")).lower()
    session_id = clean_text(payload.get("session_id")) or None
    limit = max(1, safe_int(payload.get("limit"), 200))

    items = load_store()["items"]

    if kind:
        items = [x for x in items if clean_text(x.get("kind")) == kind]

    if session_id:
        items = [x for x in items if not clean_text(x.get("session_id")) or clean_text(x.get("session_id")) == session_id]

    if query:
        query_tokens = set(tokenize(query))
        filtered = []
        for item in items:
            value = clean_text(item.get("value")).lower()
            tokens = set(safe_list(item.get("token_set")))
            if query.lower() in value or (query_tokens and len(query_tokens & tokens) > 0):
                filtered.append(item)
        items = filtered

    items = [strip_internal_fields(x) for x in items[:limit]]

    return {
        "ok": True,
        "items": items,
        "count": len(items),
        "updated_at": load_store().get("updated_at"),
        "error": None,
    }


def add_memory(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    value = truncate(clean_text(payload.get("value")), MAX_MEMORY_VALUE_CHARS)
    kind = clean_text(payload.get("kind")).lower() or infer_memory_kind(value)

    if not value:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "value is required.",
            },
        }

    if is_low_value_memory(value):
        return {
            "ok": False,
            "error": {
                "code": "low_value_memory",
                "message": "Memory value is too low-signal to store.",
            },
        }

    item = normalize_memory_item(
        {
            "kind": kind,
            "value": value,
            "source": clean_text(payload.get("source")) or "manual",
            "session_id": clean_text(payload.get("session_id")) or None,
            "pinned": safe_bool(payload.get("pinned"), False),
            "score": safe_int(payload.get("score"), 0),
            "metadata": safe_dict(payload.get("metadata")),
        }
    )
    if not item:
        return {
            "ok": False,
            "error": {
                "code": "invalid_memory",
                "message": "Memory could not be normalized.",
            },
        }

    store = load_store()
    store["items"].append(item)
    saved = save_store(store)

    final = next((x for x in saved["items"] if x.get("id") == item["id"]), None)
    if final is None:
        final = next(
            (
                x for x in saved["items"]
                if x.get("kind") == item.get("kind")
                and x.get("canonical_value") == item.get("canonical_value")
            ),
            None,
        )
    final = final or item

    return {
        "ok": True,
        "item": strip_internal_fields(final),
        "error": None,
    }


def delete_memory(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    memory_id = clean_text(payload.get("id") or payload.get("memory_id"))
    if not memory_id:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": "id or memory_id is required.",
            },
        }

    store = load_store()
    kept: List[Dict[str, Any]] = []
    found = False

    for item in store["items"]:
        if clean_text(item.get("id")) == memory_id:
            found = True
            continue
        kept.append(item)

    if not found:
        return {
            "ok": False,
            "error": {
                "code": "not_found",
                "message": "Memory item not found.",
            },
        }

    store["items"] = kept
    save_store(store)

    return {
        "ok": True,
        "deleted_id": memory_id,
        "error": None,
    }


def export_memory(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _ = safe_dict(payload)
    store = load_store()
    items = [strip_internal_fields(x) for x in store["items"]]
    return {
        "ok": True,
        "items": items,
        "count": len(items),
        "updated_at": store.get("updated_at"),
        "error": None,
    }


# =========================================================
# prompt context
# =========================================================

def format_memory_prompt_text(items: List[Dict[str, Any]]) -> str:
    groups: Dict[str, List[str]] = {
        "identity": [],
        "goal": [],
        "project": [],
        "workflow": [],
        "preference": [],
        "skill": [],
        "background": [],
        "note": [],
    }

    for raw in safe_list(items):
        item = safe_dict(raw)
        kind = clean_text(item.get("kind")).lower() or "note"
        value = clean_text(item.get("value"))
        if not value:
            continue
        groups.setdefault(kind, []).append(value)

    lines: List[str] = []
    ordered_kinds = ["identity", "goal", "project", "workflow", "preference", "skill", "background", "note"]

    for kind in ordered_kinds:
        values = groups.get(kind) or []
        if not values:
            continue
        label = kind.capitalize()
        lines.append(f"{label}:")
        for value in values[:4]:
            lines.append(f"- {truncate(value, MAX_MEMORY_VALUE_CHARS)}")

    if not lines:
        return ""

    return "Saved user memory:\n" + "\n".join(lines).strip()


def build_memory_prompt_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)

    content = truncate(clean_text(payload.get("content")), MAX_MEMORY_QUERY_CHARS)
    session_id = clean_text(payload.get("session_id")) or None
    messages = safe_list(payload.get("messages"))

    history_texts: List[str] = []
    for item in messages[-8:]:
        msg = safe_dict(item)
        message_text = clean_text(msg.get("content"))
        if message_text:
            history_texts.append(message_text)

    query_text = "\n".join([x for x in history_texts + [content] if x]).strip()
    selected = select_relevant_memories(
        query_text=query_text,
        session_id=session_id,
        limit=MAX_MEMORY_PROMPT_ITEMS,
    )
    prompt_text = format_memory_prompt_text(selected)

    return {
        "ok": True,
        "items": selected,
        "memory": selected,
        "prompt_text": prompt_text,
        "error": None,
    }


# =========================================================
# optional auto extraction
# =========================================================

def auto_extract_and_store_memory(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    text = clean_text(payload.get("content"))
    session_id = clean_text(payload.get("session_id")) or None

    candidates = extract_candidate_memories_from_text(text)
    stored: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for candidate in candidates:
        result = add_memory(
            {
                **candidate,
                "session_id": session_id,
                "source": "auto",
                "metadata": safe_dict(payload.get("metadata")),
            }
        )
        if result.get("ok"):
            stored.append(safe_dict(result.get("item")))
        else:
            skipped.append(
                {
                    "candidate": candidate,
                    "error": result.get("error"),
                }
            )

    return {
        "ok": True,
        "stored": stored,
        "stored_count": len(stored),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "error": None,
    }


# =========================================================
# diagnostics
# =========================================================

def memory_stats() -> Dict[str, Any]:
    items = load_store()["items"]

    by_kind: Dict[str, int] = {}
    pinned_count = 0

    for item in items:
        kind = clean_text(item.get("kind")) or "note"
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if safe_bool(item.get("pinned")):
            pinned_count += 1

    return {
        "ok": True,
        "count": len(items),
        "pinned_count": pinned_count,
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: kv[0])),
        "file": str(MEMORY_FILE),
        "updated_at": load_store().get("updated_at"),
        "error": None,
    }