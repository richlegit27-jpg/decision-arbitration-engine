import base64
import json
import mimetypes
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
NOVA_IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1")
NOVA_IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None

URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)


# ------------------ CORE UTILS ------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(x: Any) -> str:
    return str(x or "").strip()


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def ensure_storage() -> None:
    if not SESSIONS_FILE.exists():
        write_json(SESSIONS_FILE, {"active_session_id": "", "sessions": []})
    if not ARTIFACTS_FILE.exists():
        write_json(ARTIFACTS_FILE, {"artifacts": []})
    if not MEMORY_FILE.exists():
        write_json(MEMORY_FILE, {"items": []})


def _ok(**kwargs):
    return jsonify({"ok": True, **kwargs})


def _error(msg: str, status: int = 400):
    return jsonify({"ok": False, "error": msg}), status


def sse_pack(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def normalize_possible_media_url(x: Any) -> str:
    raw = safe_str(x)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("/"):
        return raw
    raw = raw.replace("\\", "/")
    raw = re.sub(r"^uploads/", "", raw)
    return f"/api/uploads/{raw}"


def guess_kind_from_mime(mime_type: str) -> str:
    mt = safe_str(mime_type).lower()
    if mt.startswith("image/"):
        return "image"
    if mt.startswith("video/"):
        return "video"
    if mt.startswith("audio/"):
        return "audio"
    return "file"


def normalize_attachment(x: Any) -> dict[str, Any] | None:
    if not isinstance(x, dict):
        return None

    name = safe_str(x.get("name") or x.get("filename") or x.get("stored_name") or "attachment")
    mime_type = safe_str(x.get("mime_type") or x.get("mime") or x.get("content_type"))
    url = normalize_possible_media_url(x.get("url") or x.get("path") or x.get("preview_url"))
    kind = safe_str(x.get("kind")) or guess_kind_from_mime(mime_type)

    return {
        "id": safe_str(x.get("id") or uuid.uuid4().hex[:8]),
        "name": name,
        "filename": name,
        "stored_name": safe_str(x.get("stored_name")),
        "url": url,
        "preview_url": url,
        "path": url,
        "mime_type": mime_type,
        "kind": kind,
        "size": int(x.get("size") or 0),
        "uploaded_at": safe_str(x.get("uploaded_at") or now_iso()),
    }


def safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


# ------------------ MEMORY ------------------

# ------------------ MEMORY ------------------

MEMORY_PATTERNS = [
    r"^\s*remember\s+that\s+(.+)$",
    r"^\s*remember\s+(.+)$",
    r"^\s*from\s+now\s+on[:,]?\s*(.+)$",
    r"^\s*i\s+prefer\s+(.+)$",
    r"^\s*always\s+(.+)$",
    r"^\s*my\s+project\s+is\s+(.+)$",
    r"^\s*my\s+ports?\s+(?:are|is)\s+(.+)$",
    r"^\s*use\s+this\s+path[:,]?\s*(.+)$",
    r"^\s*keep\s+(.+)$",
]

MEMORY_BAD_SUBSTRINGS = [
    "traceback",
    "error:",
    "exception",
    "stack trace",
    "console.log",
    "uncaught",
    "failed to load",
    "http://127.0.0.1",
    "https://127.0.0.1",
]

MEMORY_CONFLICT_RULES = [
    {
        "name": "response_style_full_file",
        "patterns": [
            r"\bfull file\b",
            r"\bfull files\b",
            r"\bsmff\b",
            r"\bfull file replacements?\b",
        ],
        "kind": "preference",
    },
    {
        "name": "response_style_no_partials",
        "patterns": [
            r"\bno partials?\b",
            r"\bdon't give me partials?\b",
            r"\bnot partials?\b",
            r"\bonly full\b",
        ],
        "kind": "preference",
    },
    {
        "name": "architecture_modular_backend",
        "patterns": [
            r"\bmodular\b",
            r"\bbackend split\b",
            r"\bstay modular\b",
            r"\bsplit modular structure\b",
        ],
        "kind": "project",
    },
    {
        "name": "ports_config",
        "patterns": [
            r"\bports?\b",
            r"\b8744\b",
            r"\b8743\b",
            r"\b5001\b",
        ],
        "kind": "project",
    },
]

def load_memory_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(MEMORY_FILE, {"items": []})
    items = raw.get("items", []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        items = []
    return {"items": items}

def save_memory_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(MEMORY_FILE, {"items": payload.get("items", [])})

def normalize_memory_text(text: str) -> str:
    value = safe_str(text)
    value = re.sub(r"\s+", " ", value).strip(" .,-:\t\r\n")
    return value

def memory_exists(items: list[dict[str, Any]], text: str) -> bool:
    target = normalize_memory_text(text).lower()
    if not target:
        return True

    for item in items:
        existing = normalize_memory_text(item.get("text", "")).lower()
        if existing == target:
            return True

    return False

def classify_memory_text(text: str) -> str:
    lowered = normalize_memory_text(text).lower()

    if any(x in lowered for x in ["prefer", "always", "from now on", "use this path", "keep "]):
        return "preference"

    if any(x in lowered for x in ["project", "ports", "path", "backend", "frontend", "nova"]):
        return "project"

    return "note"

def extract_memory_candidates(content: str) -> list[str]:
    text = safe_str(content)
    if not text:
        return []

    stripped = text.strip()
    lowered = stripped.lower()

    if len(stripped) < 8 or len(stripped) > 220:
        return []

    if "\n" in stripped and len(stripped.splitlines()) > 3:
        return []

    if any(bad in lowered for bad in MEMORY_BAD_SUBSTRINGS):
        return []

    candidates: list[str] = []

    for pattern in MEMORY_PATTERNS:
        match = re.match(pattern, stripped, re.IGNORECASE)
        if match:
            captured = normalize_memory_text(match.group(1))
            if captured:
                candidates.append(captured)

    if not candidates:
        direct_prefixes = [
            "i prefer ",
            "from now on ",
            "my project is ",
            "my ports are ",
            "my port is ",
            "use this path ",
            "always ",
            "keep ",
        ]
        if any(lowered.startswith(prefix) for prefix in direct_prefixes):
            cleaned = normalize_memory_text(stripped)
            if cleaned:
                candidates.append(cleaned)

    deduped: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)

    return deduped[:3]

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def parse_iso_datetime(value: str | None) -> datetime:
    raw = safe_str(value)
    if not raw:
        return utc_now()

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return utc_now()

def memory_conflict_key(text: str, kind: str = "") -> str:
    clean = normalize_memory_text(text).lower()
    clean_kind = safe_str(kind).lower()

    for rule in MEMORY_CONFLICT_RULES:
        rule_kind = safe_str(rule.get("kind"))
        if rule_kind and rule_kind != clean_kind:
            continue

        for pattern in rule.get("patterns", []):
            try:
                if re.search(pattern, clean, re.IGNORECASE):
                    return safe_str(rule.get("name"))
            except re.error:
                continue

    if clean_kind == "preference":
        if clean.startswith("i prefer "):
            return "pref:" + clean.split("i prefer ", 1)[1][:80]
        if clean.startswith("from now on "):
            return "pref:" + clean.split("from now on ", 1)[1][:80]

    if clean_kind == "project":
        if "port" in clean:
            return "project:ports"
        if "path" in clean:
            return "project:path"
        if "backend" in clean and "split" in clean:
            return "project:backend-split"

    return ""

def memory_priority_score(item: dict[str, Any]) -> int:
    text = normalize_memory_text(item.get("text", "")).lower()
    kind = safe_str(item.get("kind")).lower()
    source = safe_str(item.get("source")).lower()

    score = 0

    if kind == "preference":
        score += 100
    elif kind == "project":
        score += 80
    else:
        score += 50

    if source == "manual":
        score += 25
    elif source == "auto":
        score += 10

    if len(text) <= 120:
        score += 10

    if any(x in text for x in ["always", "from now on", "prefer", "must", "only"]):
        score += 20

    if any(x in text for x in ["nova", "backend", "split", "smff", "full file"]):
        score += 15

    age_seconds = max(0, int((utc_now() - parse_iso_datetime(item.get("updated_at"))).total_seconds()))
    age_days = age_seconds // 86400

    if age_days <= 1:
        score += 30
    elif age_days <= 7:
        score += 20
    elif age_days <= 30:
        score += 10

    return score

def replace_conflicting_memory(items: list[dict[str, Any]], new_item: dict[str, Any]) -> list[dict[str, Any]]:
    new_key = memory_conflict_key(new_item.get("text", ""), new_item.get("kind", ""))
    if not new_key:
        return items

    filtered: list[dict[str, Any]] = []
    for item in items:
        old_key = memory_conflict_key(item.get("text", ""), item.get("kind", ""))
        if old_key and old_key == new_key and safe_str(item.get("id")) != safe_str(new_item.get("id")):
            continue
        filtered.append(item)

    return filtered

def save_memory_item_dominant(
    *,
    text: str,
    kind: str = "note",
    source: str = "auto",
    session_id: str = "",
) -> dict[str, Any] | None:
    clean = normalize_memory_text(text)
    if not clean:
        return None

    payload = load_memory_payload()
    items = payload.get("items", [])

    if memory_exists(items, clean):
        return None

    item = {
        "id": uuid.uuid4().hex[:10],
        "text": clean,
        "kind": safe_str(kind) or "note",
        "source": safe_str(source) or "auto",
        "session_id": safe_str(session_id),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "preview": clean[:160],
    }

    items.insert(0, item)
    items = replace_conflicting_memory(items, item)

    items = sorted(
        items,
        key=lambda x: (
            -memory_priority_score(x),
            -int(parse_iso_datetime(x.get("updated_at")).timestamp()),
        ),
    )[:300]

    payload["items"] = items
    save_memory_payload(payload)
    return item

def auto_learn_memory_dominant(content: str, session_id: str = "") -> list[dict[str, Any]]:
    learned: list[dict[str, Any]] = []

    for candidate in extract_memory_candidates(content):
        item = save_memory_item_dominant(
            text=candidate,
            kind=classify_memory_text(candidate),
            source="auto",
            session_id=session_id,
        )
        if item:
            learned.append(item)

    return learned

def get_dominant_memories(limit: int = 8) -> list[dict[str, Any]]:
    payload = load_memory_payload()
    items = payload.get("items", [])

    ranked = sorted(
        items,
        key=lambda x: (
            -memory_priority_score(x),
            -int(parse_iso_datetime(x.get("updated_at")).timestamp()),
        ),
    )

    return ranked[:max(1, limit)]

def build_memory_system_prompt(limit: int = 8) -> str:
    top_items = get_dominant_memories(limit=limit)
    if not top_items:
        return ""

    lines = ["Persistent user memory (highest priority):"]

    for item in top_items:
        kind = safe_str(item.get("kind") or "note").strip()
        text = normalize_memory_text(item.get("text", ""))
        if not text:
            continue
        lines.append(f"- [{kind}] {text}")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)


# ------------------ SESSIONS ------------------

def normalize_message(x: Any) -> dict[str, Any] | None:
    if not isinstance(x, dict):
        return None

    attachments_raw = x.get("attachments") if isinstance(x.get("attachments"), list) else []
    attachments = [a for a in (normalize_attachment(v) for v in attachments_raw) if a]

    return {
        "id": safe_str(x.get("id") or uuid.uuid4().hex[:8]),
        "role": safe_str(x.get("role") or "assistant").lower() or "assistant",
        "content": safe_str(x.get("content") or x.get("text") or x.get("message")),
        "created_at": safe_str(x.get("created_at") or now_iso()),
        "attachments": attachments,
        "route_meta": x.get("route_meta") if isinstance(x.get("route_meta"), dict) else {},
    }


def normalize_session(x: Any) -> dict[str, Any] | None:
    if not isinstance(x, dict):
        return None

    messages_raw = x.get("messages") if isinstance(x.get("messages"), list) else []
    messages = [m for m in (normalize_message(v) for v in messages_raw) if m]

    session_id = safe_str(x.get("id") or x.get("session_id") or uuid.uuid4().hex[:8])
    created_at = safe_str(x.get("created_at") or now_iso())
    updated_at = safe_str(x.get("updated_at") or created_at)
    title = safe_str(x.get("title") or x.get("name")) or "New Chat"

    last_preview = safe_str(x.get("last_message_preview"))
    if not last_preview:
        for msg in reversed(messages):
            if safe_str(msg.get("content")):
                last_preview = safe_str(msg.get("content"))[:160]
                break

    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "pinned": bool(x.get("pinned", False)),
        "active": bool(x.get("active", False)),
        "created_at": created_at,
        "updated_at": updated_at,
        "message_count": len(messages),
        "last_message_preview": last_preview,
        "messages": messages,
    }


def _read_sessions_store() -> dict[str, Any]:
    ensure_storage()

    default_store = {
        "active_session_id": "",
        "sessions": []
    }

    try:
        if not SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_store, f, indent=2, ensure_ascii=False)
            return deepcopy(default_store)

        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return deepcopy(default_store)

    if isinstance(raw, list):
        return {
            "active_session_id": "",
            "sessions": raw
        }

    if not isinstance(raw, dict):
        return deepcopy(default_store)

    sessions = raw.get("sessions")
    if not isinstance(sessions, list):
        sessions = []

    return {
        "active_session_id": str(raw.get("active_session_id") or ""),
        "sessions": sessions
    }


def _write_sessions_store(store: dict[str, Any]) -> None:
    ensure_storage()

    payload = {
        "active_session_id": str((store or {}).get("active_session_id") or ""),
        "sessions": (store or {}).get("sessions") if isinstance((store or {}).get("sessions"), list) else []
    }

    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _session_id_of(session: Any) -> str:
    if not isinstance(session, dict):
        return ""
    return str(
        session.get("id")
        or session.get("session_id")
        or session.get("uuid")
        or ""
    )


def _mark_active_session(store: dict[str, Any], session_id: str) -> dict[str, Any] | None:
    target_id = str(session_id or "").strip()
    sessions = (store or {}).get("sessions") if isinstance((store or {}).get("sessions"), list) else []

    found = None
    for session in sessions:
        sid = _session_id_of(session)
        is_active = bool(target_id and sid == target_id)
        session["active"] = is_active
        if is_active:
            found = session

    if found:
        store["active_session_id"] = target_id
    elif sessions:
        fallback_id = _session_id_of(sessions[0])
        store["active_session_id"] = fallback_id
        for i, session in enumerate(sessions):
            session["active"] = i == 0
        found = sessions[0]
    else:
        store["active_session_id"] = ""
        found = None

    return found


def load_sessions_payload() -> dict[str, Any]:
    raw_store = _read_sessions_store()
    items_raw = raw_store.get("sessions", [])
    sessions = [s for s in (normalize_session(x) for x in items_raw) if s]

    active_session_id = safe_str(raw_store.get("active_session_id"))

    sessions.sort(key=lambda s: safe_str(s.get("updated_at")), reverse=True)
    sessions.sort(key=lambda s: 1 if s.get("pinned") else 0, reverse=True)

    normalized_store = {
        "active_session_id": active_session_id,
        "sessions": sessions
    }
    _mark_active_session(normalized_store, active_session_id)
    return normalized_store


def save_sessions_payload(payload: dict[str, Any]) -> None:
    store = {
        "active_session_id": safe_str(payload.get("active_session_id")),
        "sessions": payload.get("sessions", []) if isinstance(payload.get("sessions"), list) else [],
    }
    _mark_active_session(store, store.get("active_session_id", ""))
    _write_sessions_store(store)


def create_session(title: str = "New Chat") -> dict[str, Any]:
    ts = now_iso()
    session_id = uuid.uuid4().hex[:8]
    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "pinned": False,
        "active": False,
        "created_at": ts,
        "updated_at": ts,
        "message_count": 0,
        "last_message_preview": "",
        "messages": [],
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    session_id = safe_str(session_id)
    if not session_id:
        return None
    for session in load_sessions_payload()["sessions"]:
        if safe_str(session.get("id")) == session_id:
            return session
    return None


def upsert_session(session: dict[str, Any], make_active: bool = False) -> dict[str, Any]:
    payload = load_sessions_payload()
    sessions = payload["sessions"]
    sid = safe_str(session.get("id"))

    replaced = False
    for i, current in enumerate(sessions):
        if safe_str(current.get("id")) == sid:
            sessions[i] = session
            replaced = True
            break

    if not replaced:
        sessions.insert(0, session)

    sessions.sort(key=lambda s: safe_str(s.get("updated_at")), reverse=True)
    sessions.sort(key=lambda s: 1 if s.get("pinned") else 0, reverse=True)

    payload["sessions"] = sessions
    if make_active:
        payload["active_session_id"] = sid

    _mark_active_session(payload, payload.get("active_session_id", ""))
    save_sessions_payload(payload)
    return payload


def get_last_user_message(session: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    messages = session.get("messages") if isinstance(session.get("messages"), list) else []
    for msg in reversed(messages):
        if safe_str(msg.get("role")).lower() == "user":
            content = safe_str(msg.get("content"))
            attachments = msg.get("attachments") if isinstance(msg.get("attachments"), list) else []
            if content or attachments:
                return content, attachments
    return "", []


def persist_session(session: dict[str, Any], assistant_text: str = "", fallback_preview: str = "", make_active: bool = True) -> None:
    session["updated_at"] = now_iso()
    session["message_count"] = len(session.get("messages", []))
    preview = safe_str(assistant_text) or safe_str(fallback_preview)
    session["last_message_preview"] = preview[:160]
    upsert_session(session, make_active=make_active)


# ------------------ ARTIFACT ENGINE ------------------

def normalize_artifact(x: Any) -> dict[str, Any] | None:
    if not isinstance(x, dict):
        return None

    image_url = normalize_possible_media_url(x.get("image_url"))
    source_url = safe_str(x.get("source_url"))
    kind = safe_str(x.get("kind") or "artifact")
    title = safe_str(x.get("title") or "Artifact")
    content = safe_str(x.get("content"))
    summary = safe_str(x.get("summary"))

    viewer = x.get("viewer") if isinstance(x.get("viewer"), dict) else {}
    meta = x.get("meta") if isinstance(x.get("meta"), dict) else {}

    merged_viewer = {
        "kind": safe_str(viewer.get("kind") or kind),
        "title": safe_str(viewer.get("title") or title),
        "body": safe_str(viewer.get("body") or content),
        "image_url": normalize_possible_media_url(viewer.get("image_url") or image_url),
        "source_url": safe_str(viewer.get("source_url") or source_url),
    }

    return {
        "id": safe_str(x.get("id") or uuid.uuid4().hex[:10]),
        "artifact_id": safe_str(x.get("artifact_id") or x.get("id") or ""),
        "session_id": safe_str(x.get("session_id")),
        "kind": kind,
        "title": title,
        "content": content,
        "summary": summary,
        "preview": safe_str(x.get("preview") or summary or content)[:220],
        "image_url": image_url,
        "source_url": source_url,
        "created_at": safe_str(x.get("created_at") or now_iso()),
        "updated_at": safe_str(x.get("updated_at") or x.get("created_at") or now_iso()),
        "pinned": bool(x.get("pinned", False)),
        "viewer": merged_viewer,
        "meta": meta,
    }


def load_artifacts_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(ARTIFACTS_FILE, {"artifacts": []})

    if isinstance(raw, list):
        items_raw = raw
    elif isinstance(raw, dict):
        items_raw = raw.get("artifacts", [])
        if not isinstance(items_raw, list):
            items_raw = []
    else:
        items_raw = []

    artifacts = [a for a in (normalize_artifact(x) for x in items_raw) if a]
    artifacts.sort(key=lambda a: safe_str(a.get("updated_at")), reverse=True)
    artifacts.sort(key=lambda a: 1 if a.get("pinned") else 0, reverse=True)
    return {"artifacts": artifacts}


def save_artifacts_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(ARTIFACTS_FILE, {"artifacts": payload.get("artifacts", [])})


def get_artifact(artifact_id: str) -> dict[str, Any] | None:
    aid = safe_str(artifact_id)
    if not aid:
        return None

    for artifact in load_artifacts_payload()["artifacts"]:
        if safe_str(artifact.get("id")) == aid or safe_str(artifact.get("artifact_id")) == aid:
            return artifact
    return None


def create_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    content: str = "",
    summary: str = "",
    image_url: str = "",
    source_url: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = load_artifacts_payload()
    ts = now_iso()

    artifact = {
        "id": uuid.uuid4().hex[:10],
        "artifact_id": "",
        "session_id": safe_str(session_id),
        "kind": safe_str(kind or "artifact"),
        "title": safe_str(title or "Artifact"),
        "content": safe_str(content),
        "summary": safe_str(summary),
        "preview": safe_str(summary or content)[:220],
        "image_url": normalize_possible_media_url(image_url),
        "source_url": safe_str(source_url),
        "created_at": ts,
        "updated_at": ts,
        "pinned": False,
        "meta": meta or {},
        "viewer": {
            "kind": safe_str(kind or "artifact"),
            "title": safe_str(title or "Artifact"),
            "body": safe_str(content),
            "image_url": normalize_possible_media_url(image_url),
            "source_url": safe_str(source_url),
        },
    }

    artifact["artifact_id"] = artifact["id"]
    payload["artifacts"].insert(0, artifact)
    save_artifacts_payload(payload)
    return artifact


# ------------------ ROUTING / MODEL ------------------

def route_request(content: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = safe_str(content)
    lowered = text.lower()
    attachments = attachments or []

    if lowered.startswith("/image"):
        return {"route": "image", "mode": "writing", "reason": "Explicit /image command.", "matched_keywords": ["/image"]}

    if URL_RE.search(text):
        return {"route": "web", "mode": "analysis", "reason": "Detected URL in request.", "matched_keywords": ["url"]}

    if attachments:
        return {"route": "chat", "mode": "analysis", "reason": "Attachments detected.", "matched_keywords": []}

    return {"route": "chat", "mode": "general", "reason": "Default conversational route.", "matched_keywords": []}


def build_model_messages(
    *,
    session: dict[str, Any],
    content: str,
    attachments: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "You are Nova. Be helpful, direct, concise, and practical."}
    ]

    for msg in session.get("messages", [])[-12:]:
        text = safe_str(msg.get("content"))
        role = safe_str(msg.get("role") or "user")
        if text:
            messages.append({"role": role, "content": text})

    if attachments:
        names = []
        for a in attachments:
            if isinstance(a, dict):
                names.append(f"- {safe_str(a.get('name') or a.get('filename') or 'attachment')}")
        if names:
            messages.append({"role": "user", "content": "Attached files:\n" + "\n".join(names)})

    messages.append({"role": "user", "content": safe_str(content)})
    return messages


def fallback_assistant_text(content: str, attachments: list[dict[str, Any]] | None = None) -> str:
    prompt = safe_str(content)
    if prompt:
        return f"Nova: {prompt}"
    if attachments:
        return f"Nova: received {len(attachments)} attachment(s)."
    return "Nova: ready."


def call_model(messages: list[dict[str, str]], fallback_text: str = "") -> str:
    if not client:
        return safe_str(fallback_text) or "Nova: backend is live."

    try:
        response = client.responses.create(model=OPENAI_MODEL, input=messages)
        text = safe_str(getattr(response, "output_text", "") or "")
        return text or safe_str(fallback_text) or "Nova: model returned an empty response."
    except Exception:
        return safe_str(fallback_text) or "Nova: model call failed."


# ------------------ WEB ------------------

def normalize_url(value: str) -> str:
    raw = safe_str(value)
    if not raw:
        return ""
    if raw.startswith("www."):
        return f"https://{raw}"
    return raw


def extract_first_url(text: str) -> str:
    match = URL_RE.search(text or "")
    if not match:
        return ""
    return normalize_url(match.group(1))


def collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", safe_str(value)).strip()


def html_to_text(html: str) -> str:
    if not html:
        return ""

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "canvas", "header", "footer", "nav", "form", "aside"]):
            tag.decompose()
        text = soup.get_text("\n")
    else:
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)

    lines = [collapse_ws(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def summarize_text(text: str) -> str:
    lines = [collapse_ws(x) for x in text.splitlines() if collapse_ws(x)]
    return "\n\n".join(lines[:8])[:1000]


def fetch_web_result(url: str) -> dict[str, Any]:
    target = normalize_url(url)
    if not target:
        raise ValueError("Missing URL.")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    response = requests.get(target, timeout=18, headers=headers, allow_redirects=True)
    response.raise_for_status()

    final_url = response.url
    html = response.text or ""

    title = urlparse(final_url).netloc or "Web result"
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            title = collapse_ws(soup.title.string)

    body = summarize_text(html_to_text(html))
    summary = body[:220]

    return {
        "url": final_url,
        "title": title,
        "body": body,
        "summary": summary,
    }


# ------------------ IMAGE ------------------

def decode_base64_image(data: str) -> bytes:
    raw = safe_str(data)
    if "," in raw and raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def save_generated_image_bytes(image_bytes: bytes) -> str:
    filename = f"generated_{uuid.uuid4().hex}.png"
    target = UPLOADS_DIR / filename
    target.write_bytes(image_bytes)
    return f"/api/uploads/{filename}"


def generate_image(prompt: str, size: str = "") -> dict[str, Any]:
    prompt = safe_str(prompt)
    image_size = safe_str(size) or NOVA_IMAGE_SIZE

    if not prompt:
        raise ValueError("Missing image prompt.")

    if not client:
        placeholder_name = f"generated_{uuid.uuid4().hex}.txt"
        placeholder_path = UPLOADS_DIR / placeholder_name
        placeholder_path.write_text(f"Image prompt placeholder:\n\n{prompt}\n", encoding="utf-8")
        return {
            "ok": True,
            "image_url": f"/api/uploads/{placeholder_name}",
            "prompt": prompt,
            "model": NOVA_IMAGE_MODEL,
            "size": image_size,
            "placeholder": True,
        }

    try:
        result = client.images.generate(
            model=NOVA_IMAGE_MODEL,
            prompt=prompt,
            size=image_size,
        )

        data = getattr(result, "data", None) or []
        if not data:
            raise ValueError("No image returned.")

        first = data[0]
        image_b64 = getattr(first, "b64_json", None)
        image_url = getattr(first, "url", None)

        if image_b64:
            image_bytes = decode_base64_image(image_b64)
            saved_url = save_generated_image_bytes(image_bytes)
            return {
                "ok": True,
                "image_url": saved_url,
                "prompt": prompt,
                "model": NOVA_IMAGE_MODEL,
                "size": image_size,
                "placeholder": False,
            }

        if image_url:
            return {
                "ok": True,
                "image_url": image_url,
                "prompt": prompt,
                "model": NOVA_IMAGE_MODEL,
                "size": image_size,
                "placeholder": False,
            }

        raise ValueError("Image response missing usable data.")
    except Exception as exc:
        raise RuntimeError(f"Image generation failed: {exc}") from exc


# ------------------ STATE ------------------

def build_state(session_id: str = "") -> dict[str, Any]:
    store = load_sessions_payload()
    sessions = store["sessions"]
    active_session_id = safe_str(session_id) or safe_str(store.get("active_session_id"))

    active_session = None
    if active_session_id:
        active_session = next((s for s in sessions if safe_str(s.get("id")) == active_session_id), None)
    if active_session is None and sessions:
        active_session = sessions[0]
        active_session_id = safe_str(active_session.get("id"))

    for session in sessions:
        session["active"] = safe_str(session.get("id")) == active_session_id

    artifacts = load_artifacts_payload()["artifacts"]
    memory_items = load_memory_payload()["items"]
    session_messages = active_session.get("messages", []) if active_session else []
    web_items = [a for a in artifacts if safe_str(a.get("kind")) in {"web", "web_result", "web_fetch"}]

    return {
        "ok": True,
        "session_id": active_session_id,
        "active_session_id": active_session_id,
        "sessions": sessions,
        "session": {
            "id": safe_str(active_session.get("id")) if active_session else "",
            "title": safe_str(active_session.get("title")) if active_session else "",
            "messages": session_messages,
        },
        "messages": session_messages,
        "memory_items": memory_items,
        "artifacts": artifacts,
        "web_items": web_items,
        "memory": memory_items,
        "web": web_items,
        "openai_model": OPENAI_MODEL,
        "chat_model": OPENAI_MODEL,
        "model": OPENAI_MODEL,
         }

                  
# ------------------ CHAT CORE ------------------


def process_chat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_storage()

    content = (
        safe_str(payload.get("content"))
        or safe_str(payload.get("message"))
        or safe_str(payload.get("user_text"))
        or safe_str(payload.get("text"))
    )

    session_id = safe_str(payload.get("session_id") or payload.get("sessionId"))
    attachments_raw = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
    attachments = [a for a in (normalize_attachment(x) for x in attachments_raw) if a]
    regenerate = bool(payload.get("regenerate"))

    session = get_session(session_id)
    if not session:
        session = create_session()
        upsert_session(session, make_active=True)
        session_id = session["id"]

    if regenerate:
        content, attachments = get_last_user_message(session)

    if not content and not attachments:
        raise ValueError("Missing content.")

    route_meta = route_request(content, attachments)

    learned_memory_items = []
    if not regenerate and route_meta.get("route") == "chat":
        learned_memory_items = auto_learn_memory_dominant(content, session_id=session_id)

    if route_meta.get("route") == "image":
        prompt = safe_str(content)
        if prompt.lower().startswith("/image"):
            prompt = prompt[6:].strip()

        image_result = generate_image(prompt, safe_str(payload.get("size")))
        image_url = safe_str(image_result.get("image_url"))

        if not regenerate:
            session["messages"].append({
                "id": uuid.uuid4().hex[:8],
                "role": "user",
                "content": content,
                "created_at": now_iso(),
                "attachments": attachments,
                "route_meta": route_meta,
            })

        assistant_text = f"Generated image for: {prompt}" if prompt else "Generated image."

        assistant_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
            "attachments": [],
            "route_meta": route_meta,
        }

        session["messages"].append(assistant_message)

        persist_session(session, assistant_text=assistant_text, fallback_preview=content, make_active=True)

        return {
            "ok": True,
            "assistant_message": assistant_message,
            "assistant_text": assistant_text,
            "session_id": session_id,
            "learned_memory_items": learned_memory_items,
            "dominant_memory": get_dominant_memories(limit=8),
        }

    if not regenerate:
        session["messages"].append({
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": content,
            "created_at": now_iso(),
            "attachments": attachments,
            "route_meta": route_meta,
        })

    fallback = fallback_assistant_text(content, attachments)

    model_messages = build_model_messages(
        session=session,
        content=content,
        attachments=attachments,
    )

    memory_prompt = build_memory_system_prompt(limit=8)
    if memory_prompt:
        model_messages.insert(0, {
            "role": "system",
            "content": memory_prompt
        })

    assistant_text = call_model(model_messages, fallback_text=fallback)

    assistant_message = {
        "id": uuid.uuid4().hex[:8],
        "role": "assistant",
        "content": assistant_text,
        "created_at": now_iso(),
        "attachments": [],
        "route_meta": route_meta,
    }

    session["messages"].append(assistant_message)

    create_artifact(
        session_id=session_id,
        kind="chat",
        title="Chat Reply",
        content=assistant_text,
        summary=assistant_text[:220],
    )

    if safe_str(session.get("title")) in {"", "New Chat"}:
        session["title"] = content[:48].rstrip() or "New Chat"

    persist_session(session, assistant_text=assistant_text, fallback_preview=content, make_active=True)

    state = build_state(session_id=session_id)

    return {
        "ok": True,
        "assistant_message": assistant_message,
        "assistant_text": assistant_text,
        "session_id": session_id,
        "session": state.get("session"),
        "sessions": state.get("sessions"),
        "messages": state.get("messages"),
        "artifacts": state.get("artifacts"),
        "memory_items": state.get("memory_items"),
        "web_items": state.get("web_items"),
        "learned_memory_items": learned_memory_items,
        "dominant_memory": get_dominant_memories(limit=8),
    }


# ------------------ ROUTES ------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "ok": True,
        "chat_model": OPENAI_MODEL,
        "model": OPENAI_MODEL,
    })


@app.route("/api/state", methods=["GET"])
def api_state():
    ensure_storage()
    state = build_state()
    return jsonify({"ok": True, **state})


# ------------------ SESSION FAMILY ------------------

@app.route("/api/session/new", methods=["POST"])
def api_session_new():
    ensure_storage()
    session = create_session()
    upsert_session(session, make_active=True)
    state = build_state(session_id=session["id"])
    return jsonify({"ok": True, **state})


@app.route("/api/session/switch", methods=["POST"])
def api_session_switch():
    payload = request.get_json(silent=True) or {}
    session_id = safe_str(payload.get("session_id"))

    if not session_id:
        return jsonify({"ok": False, "error": "session_id required"}), 400

    store = load_sessions_payload()
    _mark_active_session(store, session_id)
    save_sessions_payload(store)

    state = build_state(session_id=session_id)
    return jsonify({"ok": True, **state})


@app.route("/api/session/rename", methods=["POST"])
def api_session_rename():
    payload = request.get_json(silent=True) or {}
    session_id = safe_str(payload.get("session_id"))
    title = safe_str(payload.get("title"))

    store = load_sessions_payload()

    for s in store["sessions"]:
        if safe_str(s["id"]) == session_id:
            s["title"] = title
            s["updated_at"] = now_iso()

    save_sessions_payload(store)

    state = build_state(session_id=session_id)
    return jsonify({"ok": True, **state})


@app.route("/api/session/delete", methods=["POST"])
def api_session_delete():
    payload = request.get_json(silent=True) or {}
    session_id = safe_str(payload.get("session_id"))

    store = load_sessions_payload()
    store["sessions"] = [s for s in store["sessions"] if safe_str(s["id"]) != session_id]

    save_sessions_payload(store)

    state = build_state()
    return jsonify({"ok": True, **state})


# ------------------ CHAT ------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    result = process_chat_payload(payload)
    return jsonify(result)


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    data = request.get_json(silent=True) or {}
    user_text = (
        data.get("message")
        or data.get("content")
        or data.get("user_text")
        or ""
    ).strip()
    session_id = str(data.get("session_id") or "").strip()
    attachments = data.get("attachments") or []

    if not user_text and not attachments:
        return jsonify({"ok": False, "error": "Message required."}), 400

    def sse(event):
        return f"data: {json.dumps(event)}\n\n"

    def generate():
        assistant_text = ""
        assistant_message = None

        try:
            route_meta = {}
            try:
                if "route_request" in globals():
                    route_meta = route_request(user_text=user_text, attachments=attachments) or {}
            except Exception:
                route_meta = {}

            yield sse({
                "ok": True,
                "phase": "start",
                "session_id": session_id,
                "route_meta": route_meta,
            })

            current_session = None
            try:
                if "chat_service" in globals() and hasattr(chat_service, "ensure_session"):
                    current_session = chat_service.ensure_session(session_id=session_id)
                elif "ensure_session" in globals():
                    current_session = ensure_session(session_id)
            except Exception:
                current_session = None

            if isinstance(current_session, dict):
                session_id_local = str(
                    current_session.get("id")
                    or current_session.get("session_id")
                    or session_id
                    or ""
                )
            else:
                session_id_local = session_id

            try:
                if "chat_service" in globals() and hasattr(chat_service, "append_message"):
                    chat_service.append_message(
                        session_id=session_id_local,
                        role="user",
                        content=user_text,
                        attachments=attachments,
                    )
                elif "append_message" in globals():
                    append_message(session_id_local, {
                        "role": "user",
                        "content": user_text,
                        "attachments": attachments,
                    })
            except Exception:
                pass

            if OpenAI is None:
                assistant_text = "Streaming unavailable: OpenAI SDK not loaded."
                yield sse({"delta": assistant_text})
            else:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                model_name = os.getenv("OPENAI_MODEL", "gpt-5.4")

                messages = [
                    {"role": "system", "content": "You are Nova. Be helpful, direct, and concise."},
                    {"role": "user", "content": user_text},
                ]

                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                )

                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta.content or ""
                    except Exception:
                        delta = ""

                    if not delta:
                        continue

                    assistant_text += delta
                    yield sse({"delta": delta})

            try:
                if "chat_service" in globals() and hasattr(chat_service, "append_message"):
                    assistant_message = chat_service.append_message(
                        session_id=session_id_local,
                        role="assistant",
                        content=assistant_text,
                    )
                elif "append_message" in globals():
                    assistant_message = append_message(session_id_local, {
                        "role": "assistant",
                        "content": assistant_text,
                    })
            except Exception:
                assistant_message = {
                    "role": "assistant",
                    "content": assistant_text,
                }

            payload = {
                "ok": True,
                "done": True,
                "assistant_message": assistant_message or {
                    "role": "assistant",
                    "content": assistant_text,
                },
                "session_id": session_id_local,
                "route_meta": route_meta,
            }

            try:
                if "build_state_payload" in globals():
                    state_payload = build_state_payload(session_id_local)
                    if isinstance(state_payload, dict):
                        payload.update(state_payload)
                elif "chat_service" in globals() and hasattr(chat_service, "build_state_payload"):
                    state_payload = chat_service.build_state_payload(session_id_local)
                    if isinstance(state_payload, dict):
                        payload.update(state_payload)
            except Exception:
                pass

            yield sse(payload)

        except Exception as exc:
            yield sse({
                "ok": False,
                "error": str(exc),
                "done": True,
            })

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


# ------------------ WEB ------------------

@app.route("/api/web/fetch", methods=["POST"])
def api_web_fetch():
    payload = request.get_json(silent=True) or {}
    url = safe_str(payload.get("url"))

    result = fetch_web_result(url)

    create_artifact(
        session_id=safe_str(payload.get("session_id")),
        kind="web",
        title=result.get("title"),
        content=result.get("body"),
        summary=result.get("summary"),
        source_url=result.get("url"),
        meta=result,
    )

    return jsonify({"ok": True, "web_result": result})


# ------------------ UPLOADS ------------------

@app.route("/api/upload", methods=["POST"])
def api_upload():
    ensure_storage()

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file"}), 400

    file = request.files["file"]
    filename = uuid.uuid4().hex + "_" + file.filename
    path = UPLOADS_DIR / filename
    file.save(path)

    return jsonify({
        "ok": True,
        "file": {
            "name": filename,
            "url": f"/uploads/{filename}",
            "path": str(path),
        }
    })


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)


# ------------------ RUN ------------------

if __name__ == "__main__":
    ensure_storage()
    app.run(host="127.0.0.1", port=5001, debug=True, threaded=True)

