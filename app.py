import base64
import json
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

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
IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5")
IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")
IMAGE_QUALITY = os.getenv("NOVA_IMAGE_QUALITY", "medium")

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None

URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)

ROUTE_INTELLIGENCE_BUILD = "route-intelligence-2026-04-04-chat-fallback-lock-001"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(value: Any) -> str:
    return str(value or "").strip()


def ensure_file(path: Path, default: Any) -> None:
    if path.exists():
        return
    write_json(path, default)


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


def write_json(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)


def _error(message: str, status: int = 400, **kwargs):
    payload = {"ok": False, "error": message}
    payload.update(kwargs)
    return jsonify(payload), status


def ensure_storage() -> None:
    ensure_file(SESSIONS_FILE, {"sessions": []})
    ensure_file(ARTIFACTS_FILE, {"artifacts": []})
    ensure_file(MEMORY_FILE, {"items": []})


def normalize_possible_media_url(value: str) -> str:
    raw = safe_str(value)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("/"):
        return raw
    raw = raw.replace("\\", "/")
    raw = re.sub(r"^uploads/", "", raw)
    return f"/api/uploads/{raw}"


def normalize_session_message(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return None

    role = safe_str(message.get("role") or message.get("sender") or "assistant").lower()
    content = safe_str(message.get("content") or message.get("text") or message.get("message") or "")
    created_at = safe_str(message.get("created_at") or message.get("timestamp") or now_iso())
    attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []
    route_meta = message.get("route_meta") if isinstance(message.get("route_meta"), dict) else {}

    return {
        "id": safe_str(message.get("id") or uuid.uuid4().hex[:8]),
        "role": role or "assistant",
        "content": content,
        "created_at": created_at,
        "attachments": attachments,
        "route_meta": route_meta,
    }


def normalize_session(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    session_id = safe_str(item.get("id") or item.get("session_id"))
    if not session_id:
        session_id = uuid.uuid4().hex[:8]

    messages_raw = item.get("messages") if isinstance(item.get("messages"), list) else []
    messages = [m for m in (normalize_session_message(x) for x in messages_raw) if m]

    updated_at = safe_str(item.get("updated_at") or item.get("created_at") or now_iso())
    created_at = safe_str(item.get("created_at") or updated_at)

    title = safe_str(item.get("title") or item.get("name") or "")
    if not title:
        title = "New Chat"
        for msg in messages:
            if msg["role"] == "user" and msg["content"]:
                title = msg["content"][:48].rstrip()
                break

    last_preview = ""
    for msg in reversed(messages):
        if msg["content"]:
            last_preview = msg["content"][:160]
            break

    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "pinned": bool(item.get("pinned", False)),
        "created_at": created_at,
        "updated_at": updated_at,
        "message_count": len(messages),
        "last_message_preview": safe_str(item.get("last_message_preview") or last_preview),
        "messages": messages,
    }


def load_sessions_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(SESSIONS_FILE, {"sessions": []})

    if isinstance(raw, list):
        sessions_raw = raw
    elif isinstance(raw, dict):
        maybe_sessions = raw.get("sessions", [])
        sessions_raw = maybe_sessions if isinstance(maybe_sessions, list) else []
    else:
        sessions_raw = []

    sessions = [s for s in (normalize_session(x) for x in sessions_raw) if s]
    sessions.sort(key=lambda s: safe_str(s.get("updated_at")), reverse=True)
    sessions.sort(key=lambda s: 1 if s.get("pinned") else 0, reverse=True)
    return {"sessions": sessions}


def save_sessions_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(SESSIONS_FILE, {"sessions": payload.get("sessions", [])})


def get_session(session_id: str) -> dict[str, Any] | None:
    for session in load_sessions_payload()["sessions"]:
        if safe_str(session.get("id")) == safe_str(session_id):
            return session
    return None


def upsert_session(session: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    payload = load_sessions_payload()
    sessions = payload["sessions"]

    existing_index = None
    for i, current in enumerate(sessions):
        if safe_str(current.get("id")) == safe_str(session.get("id")):
            existing_index = i
            break

    if existing_index is None:
        sessions.insert(0, session)
    else:
        sessions[existing_index] = session

    sessions.sort(key=lambda s: safe_str(s.get("updated_at")), reverse=True)
    sessions.sort(key=lambda s: 1 if s.get("pinned") else 0, reverse=True)

    payload["sessions"] = sessions
    save_sessions_payload(payload)
    return payload


def delete_session_by_id(session_id: str) -> tuple[dict[str, list[dict[str, Any]]], str]:
    payload = load_sessions_payload()
    sessions = [s for s in payload["sessions"] if safe_str(s.get("id")) != safe_str(session_id)]
    payload["sessions"] = sessions
    save_sessions_payload(payload)
    next_session_id = safe_str(sessions[0]["id"]) if sessions else ""
    return payload, next_session_id


def create_session(title: str = "New Chat") -> dict[str, Any]:
    ts = now_iso()
    session_id = uuid.uuid4().hex[:8]
    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "pinned": False,
        "created_at": ts,
        "updated_at": ts,
        "message_count": 0,
        "last_message_preview": "",
        "messages": [],
    }


def build_artifact_viewer(
    *,
    kind: str,
    title: str,
    content: str = "",
    image_url: str = "",
    source_url: str = "",
    analysis_text: str = "",
    body: str = "",
) -> dict[str, Any]:
    normalized_image_url = normalize_possible_media_url(image_url)
    normalized_source_url = safe_str(source_url)

    viewer_kind = "artifact"
    if normalized_image_url:
        viewer_kind = "image"
    elif kind in {"web", "web_result", "web_fetch"}:
        viewer_kind = "web"

    return {
        "kind": viewer_kind,
        "title": safe_str(title),
        "body": safe_str(body or content),
        "analysis_text": safe_str(analysis_text or content),
        "image_url": normalized_image_url,
        "source_url": normalized_source_url,
    }


def normalize_artifact(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    artifact_id = safe_str(item.get("id") or item.get("artifact_id"))
    if not artifact_id:
        artifact_id = uuid.uuid4().hex[:10]

    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    web = item.get("web") if isinstance(item.get("web"), dict) else None
    debug = item.get("debug") if isinstance(item.get("debug"), dict) else None
    extra = item.get("extra") if isinstance(item.get("extra"), dict) else None
    viewer = item.get("viewer") if isinstance(item.get("viewer"), dict) else {}

    image_url = safe_str(
        viewer.get("image_url")
        or item.get("image_url")
        or meta.get("image_url")
        or (extra.get("image_url") if isinstance(extra, dict) else "")
        or (
            extra.get("media", [{}])[0].get("url")
            if isinstance(extra, dict) and isinstance(extra.get("media"), list) and extra.get("media")
            else ""
        )
        or (
            meta.get("media", [{}])[0].get("url")
            if isinstance(meta.get("media"), list) and meta.get("media")
            else ""
        )
    )
    image_url = normalize_possible_media_url(image_url)

    source_url = safe_str(
        viewer.get("source_url")
        or item.get("source_url")
        or meta.get("source_url")
        or (web.get("source_url") if isinstance(web, dict) else "")
        or (web.get("url") if isinstance(web, dict) else "")
        or item.get("url")
    )

    title = safe_str(item.get("title") or item.get("name") or item.get("kind") or "Untitled artifact")
    content = safe_str(
        item.get("content") or item.get("text") or item.get("body") or item.get("preview") or item.get("summary") or ""
    )
    kind = safe_str(item.get("kind") or item.get("type") or "artifact")

    normalized_viewer = build_artifact_viewer(
        kind=kind,
        title=title,
        content=content,
        image_url=image_url,
        source_url=source_url,
        analysis_text=safe_str(viewer.get("analysis_text") or content),
        body=safe_str(viewer.get("body") or content),
    )

    return {
        "id": artifact_id,
        "artifact_id": artifact_id,
        "session_id": safe_str(item.get("session_id")),
        "kind": kind,
        "title": title,
        "content": content,
        "summary": safe_str(item.get("summary") or meta.get("summary") or ""),
        "preview": safe_str(item.get("preview") or item.get("content") or item.get("summary") or content)[:220],
        "pinned": bool(item.get("pinned", False)),
        "created_at": safe_str(item.get("created_at") or now_iso()),
        "updated_at": safe_str(item.get("updated_at") or item.get("created_at") or now_iso()),
        "meta": meta,
        "web": web,
        "debug": debug,
        "extra": extra,
        "image_url": image_url,
        "source_url": source_url,
        "viewer": normalized_viewer,
    }


def load_artifacts_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(ARTIFACTS_FILE, {"artifacts": []})

    if isinstance(raw, list):
        items_raw = raw
    elif isinstance(raw, dict):
        maybe_items = raw.get("artifacts", [])
        items_raw = maybe_items if isinstance(maybe_items, list) else []
    else:
        items_raw = []

    items = [a for a in (normalize_artifact(x) for x in items_raw) if a]
    items.sort(key=lambda a: safe_str(a.get("updated_at")), reverse=True)
    items.sort(key=lambda a: 1 if a.get("pinned") else 0, reverse=True)
    return {"artifacts": items}


def save_artifacts_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(ARTIFACTS_FILE, {"artifacts": payload.get("artifacts", [])})


def normalize_memory_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    memory_id = safe_str(item.get("id") or item.get("memory_id"))
    if not memory_id:
        memory_id = uuid.uuid4().hex[:10]

    title = safe_str(item.get("title") or item.get("key") or item.get("label"))
    text = safe_str(item.get("content") or item.get("text") or item.get("value") or item.get("summary"))
    kind = safe_str(item.get("kind") or item.get("type") or item.get("category") or "note").lower()
    source = safe_str(item.get("source") or item.get("origin") or "user").lower()
    created_at = safe_str(item.get("created_at") or item.get("updated_at") or item.get("timestamp") or now_iso())
    updated_at = safe_str(item.get("updated_at") or created_at)
    session_id = safe_str(item.get("session_id") or item.get("chat_id"))

    if not title:
        title = kind or "note"

    return {
        "id": memory_id,
        "memory_id": memory_id,
        "title": title,
        "content": text,
        "text": text,
        "value": text,
        "kind": kind or "note",
        "source": source or "user",
        "session_id": session_id,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def load_memory_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(MEMORY_FILE, {"items": []})

    if isinstance(raw, list):
        items_raw = raw
    elif isinstance(raw, dict):
        maybe_items = raw.get("items", [])
        items_raw = maybe_items if isinstance(maybe_items, list) else []
    else:
        items_raw = []

    items = [m for m in (normalize_memory_item(x) for x in items_raw) if m]
    items.sort(key=lambda m: safe_str(m.get("updated_at")), reverse=True)
    return {"items": items}


def save_memory_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(MEMORY_FILE, {"items": payload.get("items", [])})


def list_memory_items() -> list[dict[str, Any]]:
    return load_memory_payload()["items"]


def add_memory_item(*, title: str, text: str, kind: str = "note", source: str = "user", session_id: str = "") -> dict[str, Any]:
    payload = load_memory_payload()
    ts = now_iso()

    item = normalize_memory_item(
        {
            "id": uuid.uuid4().hex[:10],
            "title": safe_str(title) or safe_str(kind) or "note",
            "content": safe_str(text),
            "kind": safe_str(kind) or "note",
            "source": safe_str(source) or "user",
            "session_id": safe_str(session_id),
            "created_at": ts,
            "updated_at": ts,
        }
    )
    assert item is not None

    items = payload["items"]
    items.insert(0, item)
    save_memory_payload({"items": items})
    return item


def delete_memory_item(memory_id: str) -> tuple[list[dict[str, Any]], str]:
    payload = load_memory_payload()
    items = payload["items"]
    next_items = [m for m in items if safe_str(m.get("id")) != safe_str(memory_id)]
    next_memory_id = safe_str(next_items[0]["id"]) if next_items else ""
    save_memory_payload({"items": next_items})
    return next_items, next_memory_id


def build_state(session_id: str = "") -> dict[str, Any]:
    sessions_payload = load_sessions_payload()
    sessions = sessions_payload["sessions"]

    active_session = None
    if session_id:
        active_session = next((s for s in sessions if safe_str(s.get("id")) == safe_str(session_id)), None)
    if active_session is None and sessions:
        active_session = sessions[0]

    artifacts = load_artifacts_payload()["artifacts"]
    memory_items = list_memory_items()
    session_messages = active_session.get("messages", []) if active_session else []
    web_items = [a for a in artifacts if safe_str(a.get("kind")) in {"web", "web_result", "web_fetch"}]

    return {
        "ok": True,
        "active_session_id": safe_str(active_session.get("id")) if active_session else "",
        "sessions": [
            {
                "id": s["id"],
                "session_id": s["id"],
                "title": s["title"],
                "pinned": s["pinned"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"],
                "message_count": s["message_count"],
                "last_message_preview": s["last_message_preview"],
            }
            for s in sessions
        ],
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
    }


def add_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    content: str,
    meta: dict[str, Any] | None = None,
    web: dict[str, Any] | None = None,
    debug: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    image_url: str = "",
    source_url: str = "",
    viewer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = load_artifacts_payload()
    ts = now_iso()

    normalized_image_url = normalize_possible_media_url(image_url or (meta or {}).get("image_url") or "")
    normalized_source_url = safe_str(source_url or (meta or {}).get("source_url") or (web or {}).get("source_url") or "")

    artifact = {
        "id": uuid.uuid4().hex[:10],
        "artifact_id": "",
        "session_id": safe_str(session_id),
        "kind": safe_str(kind or "artifact"),
        "title": safe_str(title or "Untitled artifact"),
        "content": safe_str(content),
        "summary": safe_str((meta or {}).get("summary") or content)[:220],
        "preview": safe_str((meta or {}).get("preview") or content)[:220],
        "pinned": False,
        "created_at": ts,
        "updated_at": ts,
        "meta": meta or {},
        "web": web or None,
        "debug": debug or None,
        "extra": extra or None,
        "image_url": normalized_image_url,
        "source_url": normalized_source_url,
        "viewer": viewer or build_artifact_viewer(
            kind=safe_str(kind or "artifact"),
            title=safe_str(title or "Untitled artifact"),
            content=safe_str(content),
            image_url=normalized_image_url,
            source_url=normalized_source_url,
            analysis_text=safe_str(content),
            body=safe_str(content),
        ),
    }
    artifact["artifact_id"] = artifact["id"]

    items = payload["artifacts"]
    items.insert(0, artifact)
    save_artifacts_payload({"artifacts": items})
    return normalize_artifact(artifact) or artifact


def _route_meta(route: str, mode: str, reason: str, matched_keywords: list[str] | None = None) -> dict[str, Any]:
    return {
        "route": safe_str(route) or "chat",
        "mode": safe_str(mode) or "general",
        "reason": safe_str(reason),
        "matched_keywords": matched_keywords or [],
        "build": ROUTE_INTELLIGENCE_BUILD,
    }


def route_request(content: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = safe_str(content)
    lowered = text.lower()
    matched: list[str] = []
    attachments = attachments or []

    explicit_web = lowered.startswith("/web ")
    explicit_image = lowered.startswith("/image")
    detected_url = extract_first_url(text)

    if explicit_web or detected_url:
        reason = "Explicit /web command." if explicit_web else "Detected URL in request."
        if explicit_web:
            matched.append("/web")
        if detected_url:
            matched.append("url")
        return _route_meta("web", "analysis", reason, matched)

    if explicit_image:
        return _route_meta("image", "writing", "Explicit /image command.", ["/image"])

    coding_keywords = [
        "python", "javascript", "js", "typescript", "ts", "flask", "fastapi", "react",
        "bug", "debug", "fix", "error", "traceback", "exception", "stack", "route",
        "api", "json", "regex", "function", "class", "refactor", "patch", "code",
        "app.py", "index.html", "css", "html"
    ]
    planning_keywords = [
        "plan", "roadmap", "phase", "next", "architecture", "design", "strategy",
        "system", "workflow", "build order", "milestone", "checkpoint"
    ]
    writing_keywords = [
        "write", "rewrite", "polish", "improve wording", "email", "post", "caption",
        "copy", "bio", "story", "book"
    ]
    analysis_keywords = [
        "analyze", "compare", "why", "reason", "explain", "inspect", "evaluate",
        "review", "break down", "thought process"
    ]

    def _hits(keywords: list[str]) -> list[str]:
        found: list[str] = []
        for keyword in keywords:
            if keyword in lowered:
                found.append(keyword)
        return found

    coding_hits = _hits(coding_keywords)
    planning_hits = _hits(planning_keywords)
    writing_hits = _hits(writing_keywords)
    analysis_hits = _hits(analysis_keywords)

    if coding_hits:
        matched.extend(coding_hits[:6])
        return _route_meta("chat", "coding", "Matched coding/debug request keywords.", matched[:6])

    if planning_hits:
        matched.extend(planning_hits[:6])
        return _route_meta("chat", "planning", "Matched planning/architecture request keywords.", matched[:6])

    if writing_hits:
        matched.extend(writing_hits[:6])
        return _route_meta("chat", "writing", "Matched writing/polish request keywords.", matched[:6])

    if analysis_hits:
        matched.extend(analysis_hits[:6])
        return _route_meta("chat", "analysis", "Matched analysis/explanation request keywords.", matched[:6])

    if attachments:
        attachment_names = [
            safe_str(a.get("name") or a.get("filename") or "")
            for a in attachments
            if isinstance(a, dict)
        ]
        attachment_names = [x for x in attachment_names if x]
        if attachment_names:
            return _route_meta("chat", "analysis", "Attachments detected; favoring analysis mode.", attachment_names[:4])

    return _route_meta("chat", "general", "Default conversational route.", [])


def get_relevant_memory_lines(session_id: str = "", limit: int = 6) -> list[str]:
    lines: list[str] = []
    for item in list_memory_items():
        text = safe_str(item.get("text") or item.get("content") or item.get("value"))
        if not text:
            continue
        item_session_id = safe_str(item.get("session_id"))
        if session_id and item_session_id and item_session_id != safe_str(session_id):
            continue
        lines.append(f"- {text}")
        if len(lines) >= limit:
            break
    return lines


def build_mode_instructions(route_meta: dict[str, Any]) -> str:
    mode = safe_str(route_meta.get("mode") or "general").lower()

    if mode == "coding":
        return (
            "You are Nova in coding mode. Be direct, technical, and solution-first. "
            "Prioritize concrete fixes, implementation details, and debugging clarity."
        )
    if mode == "planning":
        return (
            "You are Nova in planning mode. Organize the response into the best next moves, "
            "phases, priorities, and tradeoffs. Keep it practical."
        )
    if mode == "writing":
        return (
            "You are Nova in writing mode. Improve clarity, tone, and structure while keeping the user's intent."
        )
    if mode == "analysis":
        return (
            "You are Nova in analysis mode. Explain the reasoning clearly, compare options, and make the answer easy to follow."
        )

    return "You are Nova in general mode. Be helpful, concise, and practical."


def build_model_messages(
    *,
    session: dict[str, Any],
    content: str,
    attachments: list[dict[str, Any]] | None,
    route_meta: dict[str, Any],
    session_id: str = "",
) -> list[dict[str, str]]:
    model_messages: list[dict[str, str]] = []

    memory_lines = get_relevant_memory_lines(session_id=session_id, limit=6)
    system_parts = [build_mode_instructions(route_meta)]

    if memory_lines:
        system_parts.append("Relevant memory:\n" + "\n".join(memory_lines))

    model_messages.append(
        {
            "role": "system",
            "content": "\n\n".join(system_parts).strip(),
        }
    )

    for msg in session.get("messages", [])[-12:]:
        role = safe_str(msg.get("role") or "user")
        content_text = safe_str(msg.get("content"))
        if content_text:
            model_messages.append({"role": role, "content": content_text})

    if attachments:
        model_messages.append(
            {
                "role": "user",
                "content": "Attached files:\n" + "\n".join(
                    f"- {safe_str(a.get('name') or a.get('filename') or 'attachment')}"
                    for a in attachments
                    if isinstance(a, dict)
                ),
            }
        )

    model_messages.append({"role": "user", "content": safe_str(content)})
    return model_messages


def fallback_assistant_text(content: str, route_meta: dict[str, Any], attachments: list[dict[str, Any]] | None = None, error_text: str = "") -> str:
    mode = safe_str(route_meta.get("mode") or "general")
    route = safe_str(route_meta.get("route") or "chat")
    attachment_count = len(attachments or [])
    prompt = safe_str(content)

    parts: list[str] = []

    if prompt:
        parts.append(f"Nova safe reply ({mode}/{route})")
        if route == "chat":
            parts.append(f"You said: {prompt[:1200]}")
        else:
            parts.append(prompt[:1200] if prompt else "")
    else:
        parts.append("Nova safe reply")

    if attachment_count:
        parts.append(f"Attachments received: {attachment_count}")

    if error_text:
        parts.append(f"Model fallback used: {error_text[:300]}")

    return "\n\n".join([p for p in parts if p]).strip()


def call_model(messages: list[dict[str, str]], fallback_text: str = "") -> str:
    if not client:
        return safe_str(fallback_text) or "Nova safe reply: backend is live, but no OpenAI key is configured."

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=messages,
        )
        text = getattr(response, "output_text", "") or ""
        text = safe_str(text)
        if text:
            return text
        return safe_str(fallback_text) or "Nova safe reply: model returned an empty response."
    except Exception as exc:
        return safe_str(fallback_text) or f"Nova safe reply: model call failed. {exc}"


def normalize_url(candidate: str) -> str:
    value = safe_str(candidate)
    if not value:
        return ""
    if value.startswith("www."):
        return f"https://{value}"
    return value


def extract_first_url(text: str) -> str:
    match = URL_RE.search(text or "")
    if not match:
        return ""
    return normalize_url(match.group(1))


def display_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


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
        text = unescape(text)

    lines = [collapse_ws(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def readable_body(text: str, max_lines: int = 24, max_chars: int = 5000) -> str:
    output: list[str] = []
    seen: set[str] = set()

    for raw in (text or "").splitlines():
        line = collapse_ws(raw)
        lower = line.lower()
        if not line:
            continue
        if len(line) < 28:
            continue
        if lower in {"privacy", "terms", "cookies", "sign in", "log in"}:
            continue
        if line in seen:
            continue
        seen.add(line)
        output.append(line)
        if len(output) >= max_lines:
            break

    body = "\n\n".join(output).strip()
    return body[:max_chars].strip()


def pick_title(html: str, soup: Any, fallback_domain: str) -> str:
    if soup:
        tag = soup.find("meta", attrs={"property": "og:title"})
        if tag and tag.get("content"):
            title = collapse_ws(tag.get("content"))
            if title:
                return title

        if soup.title and soup.title.string:
            title = collapse_ws(soup.title.string)
            if title:
                return title

        h1 = soup.find("h1")
        if h1:
            title = collapse_ws(h1.get_text(" "))
            if title:
                return title

    match = re.search(r"(?is)<title>(.*?)</title>", html or "")
    if match:
        title = collapse_ws(unescape(match.group(1)))
        if title:
            return title

    return fallback_domain or "Web result"


def pick_description(html: str, soup: Any) -> str:
    if soup:
        for attrs in (
            {"name": "description"},
            {"property": "og:description"},
            {"name": "twitter:description"},
        ):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                text = collapse_ws(tag.get("content"))
                if text:
                    return text

    for pattern in [
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
    ]:
        match = re.search(pattern, html or "")
        if match:
            text = collapse_ws(unescape(match.group(1)))
            if text:
                return text

    return ""


def pick_site_name(soup: Any, domain: str) -> str:
    if soup:
        tag = soup.find("meta", attrs={"property": "og:site_name"})
        if tag and tag.get("content"):
            name = collapse_ws(tag.get("content"))
            if name:
                return name
    return domain


def summarize_text(description: str, body: str) -> tuple[str, list[str]]:
    source = "\n".join(x for x in [description, body] if x).strip()
    if not source:
        return "", []

    sentences = re.split(r"(?<=[.!?])\s+", source)
    sentences = [collapse_ws(s) for s in sentences if collapse_ws(s)]
    summary = " ".join(sentences[:3]).strip()

    bullets: list[str] = []
    for line in body.splitlines():
        clean = collapse_ws(line)
        if clean and clean not in bullets:
            bullets.append(clean)
        if len(bullets) >= 4:
            break

    return summary[:900], bullets


def fetch_web_result(url: str) -> dict[str, Any]:
    target = normalize_url(url)
    if not target:
        raise ValueError("Missing URL.")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    }

    ssl_verified = True
    try:
        response = requests.get(target, timeout=18, headers=headers, allow_redirects=True)
    except requests.exceptions.SSLError:
        ssl_verified = False
        requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]
        response = requests.get(target, timeout=18, headers=headers, allow_redirects=True, verify=False)

    response.raise_for_status()

    final_url = response.url
    html = response.text or ""
    soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
    domain = display_domain(final_url)

    title = pick_title(html, soup, domain)
    description = pick_description(html, soup)
    site_name = pick_site_name(soup, domain)

    raw_text = html_to_text(html)
    body = readable_body(raw_text)
    summary, bullets = summarize_text(description, body)
    preview = description or summary or body[:220]

    return {
        "kind": "web_result",
        "title": title or domain or "Web result",
        "content": body or description or title,
        "summary": summary,
        "preview": preview[:220],
        "web": {
            "title": title or domain or "Web result",
            "site_name": site_name or domain,
            "domain": domain,
            "url": final_url,
            "source_url": final_url,
            "description": description,
            "summary": summary,
            "body": body,
            "bullets": bullets,
            "status_code": response.status_code,
            "ssl_verified": ssl_verified,
            "fetched_at": now_iso(),
        },
        "debug": {
            "route": "web_fetch",
            "ssl_verified": ssl_verified,
            "status_code": response.status_code,
        },
    }


def build_web_assistant_text(web_result: dict[str, Any]) -> str:
    web = web_result.get("web") if isinstance(web_result.get("web"), dict) else {}
    title = safe_str(web.get("title") or web_result.get("title") or "Web result")
    domain = safe_str(web.get("domain"))
    summary = safe_str(web.get("summary") or web.get("description") or web_result.get("summary"))
    body = safe_str(web.get("body") or web_result.get("content"))

    parts = [f"Fetched {title}"]
    if domain:
        parts.append(f"Source: {domain}")
    if summary:
        parts.append(summary)
    elif body:
        parts.append(body[:900])

    if web.get("ssl_verified") is False:
        parts.append("SSL verification failed on the first pass, so fallback fetch was used.")

    return "\n\n".join(parts).strip()


def save_generated_image_from_base64(b64_data: str) -> str:
    binary = base64.b64decode(b64_data)
    filename = f"generated_{uuid.uuid4().hex}.png"
    target = UPLOADS_DIR / filename
    target.write_bytes(binary)
    return f"/api/uploads/{filename}"


def generate_image(prompt: str) -> dict[str, Any]:
    if not client:
        raise RuntimeError("Image generation is not configured because no OpenAI key is available.")

    response = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size=IMAGE_SIZE,
        quality=IMAGE_QUALITY,
    )

    data = getattr(response, "data", None) or []
    if not data:
        raise RuntimeError("Image generation returned no data.")

    first = data[0]
    b64_json = getattr(first, "b64_json", None)
    revised_prompt = getattr(first, "revised_prompt", "") or ""

    if b64_json is None and isinstance(first, dict):
        b64_json = first.get("b64_json")
        revised_prompt = safe_str(first.get("revised_prompt"))

    if not b64_json:
        raise RuntimeError("Image generation returned no image bytes.")

    image_url = save_generated_image_from_base64(b64_json)
    return {
        "image_url": image_url,
        "prompt": prompt,
        "revised_prompt": revised_prompt,
        "preview": prompt[:220],
    }


def sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return _ok(
        status="healthy",
        openai_configured=bool(client),
        openai_model=OPENAI_MODEL,
        image_model=IMAGE_MODEL,
        route_build="REAL-APP-PY-CHAT-FALLBACK-LOCK-2026-04-04-001",
        time=now_iso(),
    )


@app.route("/api/state", methods=["GET"])
def api_state():
    ensure_storage()
    try:
        session_id = safe_str(request.args.get("session_id"))
        return jsonify(build_state(session_id=session_id))
    except Exception as exc:
        return _error(f"Failed to load state: {exc}", status=500)


@app.route("/api/session/new", methods=["POST"])
def api_session_new():
    ensure_storage()
    try:
        session = create_session()
        upsert_session(session)
        return jsonify(build_state(session_id=session["id"]))
    except Exception as exc:
        return _error(f"Failed to create session: {exc}", status=500)


@app.route("/api/session/rename", methods=["POST"])
def api_session_rename():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    session_id = safe_str(data.get("session_id"))
    title = safe_str(data.get("title"))

    if not session_id:
        return _error("Missing session_id.", status=400)

    try:
        session = get_session(session_id)
        if not session:
            return _error("Session not found.", status=404)

        if title:
            session["title"] = title
        session["updated_at"] = now_iso()
        upsert_session(session)
        return jsonify(build_state(session_id=session_id))
    except Exception as exc:
        return _error(f"Rename failed: {exc}", status=500)


@app.route("/api/session/pin", methods=["POST"])
def api_session_pin():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    session_id = safe_str(data.get("session_id"))

    if not session_id:
        return _error("Missing session_id.", status=400)

    try:
        session = get_session(session_id)
        if not session:
            return _error("Session not found.", status=404)

        session["pinned"] = not bool(session.get("pinned"))
        session["updated_at"] = now_iso()
        upsert_session(session)
        return jsonify(build_state(session_id=session_id))
    except Exception as exc:
        return _error(f"Pin failed: {exc}", status=500)


@app.route("/api/session/delete", methods=["POST"])
def api_session_delete():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    session_id = safe_str(data.get("session_id"))

    if not session_id:
        return _error("Missing session_id.", status=400)

    try:
        _, next_session_id = delete_session_by_id(session_id)
        payload = build_state(session_id=next_session_id)
        payload["next_session_id"] = next_session_id
        return jsonify(payload)
    except Exception as exc:
        return _error(f"Delete failed: {exc}", status=500)


@app.route("/api/memory/add", methods=["POST"])
def api_memory_add():
    ensure_storage()
    data = request.get_json(silent=True) or {}

    text = safe_str(data.get("text") or data.get("content") or data.get("value"))
    title = safe_str(data.get("title") or data.get("key") or data.get("label"))
    kind = safe_str(data.get("kind") or "note").lower()
    source = safe_str(data.get("source") or "user").lower()
    session_id = safe_str(data.get("session_id"))

    if not text:
        return _error("Missing memory text.", status=400)

    try:
        item = add_memory_item(
            title=title or kind or "note",
            text=text,
            kind=kind or "note",
            source=source or "user",
            session_id=session_id,
        )
        payload = build_state(session_id=session_id)
        payload["memory_item"] = item
        payload["memory_items"] = list_memory_items()
        payload["memory"] = payload["memory_items"]
        return jsonify(payload)
    except Exception as exc:
        return _error(f"Memory add failed: {exc}", status=500)


@app.route("/api/memory/delete", methods=["POST"])
def api_memory_delete():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    memory_id = safe_str(data.get("memory_id") or data.get("id"))
    session_id = safe_str(data.get("session_id"))

    if not memory_id:
        return _error("Missing memory_id.", status=400)

    try:
        items, next_memory_id = delete_memory_item(memory_id)
        payload = build_state(session_id=session_id)
        payload["next_memory_id"] = next_memory_id
        payload["memory_items"] = items
        payload["memory"] = items
        return jsonify(payload)
    except Exception as exc:
        return _error(f"Memory delete failed: {exc}", status=500)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    ensure_storage()
    try:
        if "files" not in request.files:
            return _error("No files field provided.", status=400)

        uploaded_files = request.files.getlist("files")
        saved: list[dict[str, Any]] = []

        for file in uploaded_files:
            if not file or not file.filename:
                continue

            original_name = Path(file.filename).name
            stored_name = f"{uuid.uuid4().hex}_{original_name}"
            target = UPLOADS_DIR / stored_name
            file.save(target)

            mime_type = file.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
            kind = "file"
            if mime_type.startswith("image/"):
                kind = "image"
            elif mime_type.startswith("video/"):
                kind = "video"
            elif mime_type.startswith("audio/"):
                kind = "audio"

            saved.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "name": original_name,
                    "stored_name": stored_name,
                    "url": f"/api/uploads/{stored_name}",
                    "preview_url": f"/api/uploads/{stored_name}",
                    "size": target.stat().st_size,
                    "mime_type": mime_type,
                    "kind": kind,
                    "uploaded_at": now_iso(),
                }
            )

        return _ok(files=saved)
    except Exception as exc:
        return _error(f"Upload failed: {exc}", status=500)


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.route("/api/web/fetch", methods=["POST"])
def api_web_fetch():
    ensure_storage()
    try:
        payload = request.get_json(silent=True) or {}
        url = safe_str(payload.get("url") or payload.get("content") or payload.get("message") or payload.get("text"))
        session_id = safe_str(payload.get("session_id") or payload.get("sessionId"))

        if not url:
            return _error("Missing URL.", status=400)

        session = get_session(session_id)
        if not session:
            session = create_session()
            session_id = session["id"]

        web_result = fetch_web_result(url)
        assistant_text = build_web_assistant_text(web_result)

        user_msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": url,
            "created_at": now_iso(),
            "attachments": [],
            "route_meta": _route_meta("web", "analysis", "Explicit web fetch route.", ["url"]),
        }
        assistant_msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
            "attachments": [],
            "route_meta": _route_meta("web", "analysis", "Web fetch result.", ["url"]),
        }

        session["messages"].append(user_msg)
        session["messages"].append(assistant_msg)
        session["updated_at"] = now_iso()
        session["message_count"] = len(session["messages"])
        session["last_message_preview"] = assistant_text[:160]

        if safe_str(session.get("title")) in {"", "New Chat"}:
            session["title"] = safe_str(web_result.get("title") or "Web fetch")[:48]

        upsert_session(session)

        artifact = add_artifact(
            session_id=session_id,
            kind="web_result",
            title=safe_str(web_result.get("title") or "Web result"),
            content=assistant_text,
            meta={
                "summary": safe_str(web_result.get("summary")),
                "preview": safe_str(web_result.get("preview")),
                "source_url": safe_str((web_result.get("web") or {}).get("source_url")),
            },
            web=web_result.get("web") if isinstance(web_result.get("web"), dict) else None,
            debug=web_result.get("debug") if isinstance(web_result.get("debug"), dict) else None,
            source_url=safe_str((web_result.get("web") or {}).get("source_url")),
            viewer=build_artifact_viewer(
                kind="web_result",
                title=safe_str(web_result.get("title") or "Web result"),
                content=assistant_text,
                source_url=safe_str((web_result.get("web") or {}).get("source_url")),
                body=safe_str((web_result.get("web") or {}).get("body") or assistant_text),
            ),
        )

        state_payload = build_state(session_id=session_id)
        return _ok(
            assistant_message=assistant_text,
            artifact=artifact,
            session=state_payload.get("session"),
            sessions=state_payload.get("sessions"),
            messages=state_payload.get("messages"),
            artifacts=state_payload.get("artifacts"),
            memory_items=state_payload.get("memory_items"),
            web_items=state_payload.get("web_items"),
            memory=state_payload.get("memory"),
            web=state_payload.get("web"),
            route_meta=_route_meta("web", "analysis", "Explicit web fetch route.", ["url"]),
        )
    except Exception as exc:
        return _error(f"Web fetch failed: {exc}", status=500)


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    ensure_storage()
    try:
        return _ok(artifacts=load_artifacts_payload()["artifacts"])
    except Exception as exc:
        return _error(f"Failed to list artifacts: {exc}", status=500)


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_read(artifact_id: str):
    ensure_storage()
    try:
        items = load_artifacts_payload()["artifacts"]
        item = next((a for a in items if safe_str(a.get("id")) == safe_str(artifact_id)), None)
        if not item:
            return _error("Artifact not found.", status=404)
        return _ok(artifact=item)
    except Exception as exc:
        return _error(f"Failed to read artifact: {exc}", status=500)


@app.route("/api/artifacts/pin", methods=["POST"])
def api_artifact_pin():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    artifact_id = safe_str(data.get("artifact_id"))

    if not artifact_id:
        return _error("Missing artifact_id.", status=400)

    try:
        payload = load_artifacts_payload()
        items = payload["artifacts"]

        found = None
        for item in items:
            if safe_str(item.get("id")) == artifact_id:
                item["pinned"] = not bool(item.get("pinned"))
                item["updated_at"] = now_iso()
                found = normalize_artifact(item)
                break

        if not found:
            return _error("Artifact not found.", status=404)

        save_artifacts_payload({"artifacts": items})
        return _ok(message="Artifact pin saved.", artifact=found, artifacts=load_artifacts_payload()["artifacts"])
    except Exception as exc:
        return _error(f"Artifact pin failed: {exc}", status=500)


@app.route("/api/artifacts/delete", methods=["POST"])
def api_artifact_delete():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    artifact_id = safe_str(data.get("artifact_id"))

    if not artifact_id:
        return _error("Missing artifact_id.", status=400)

    try:
        payload = load_artifacts_payload()
        items = [a for a in payload["artifacts"] if safe_str(a.get("id")) != artifact_id]
        next_artifact_id = safe_str(items[0]["id"]) if items else ""
        save_artifacts_payload({"artifacts": items})
        return _ok(message="Artifact deleted.", next_artifact_id=next_artifact_id, artifacts=load_artifacts_payload()["artifacts"])
    except Exception as exc:
        return _error(f"Artifact delete failed: {exc}", status=500)


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    try:
        payload = request.get_json(silent=True) or {}

        content = (
            safe_str(payload.get("content"))
            or safe_str(payload.get("message"))
            or safe_str(payload.get("user_text"))
            or safe_str(payload.get("text"))
        )

        session_id = safe_str(payload.get("session_id") or payload.get("sessionId"))
        attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
        route_meta = payload.get("route_meta") or payload.get("routeMeta") or {}

        if not content and not attachments:
            return _error("Missing content.", status=400)

        ensure_storage()

        session = get_session(session_id)
        if not session:
            session = create_session()
            session_id = session["id"]

        user_msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": content,
            "created_at": now_iso(),
            "attachments": attachments,
            "route_meta": route_meta if isinstance(route_meta, dict) else {},
        }
        session["messages"].append(user_msg)

        if not route_meta:
            route_meta = route_request(content, attachments)

        def generate():
            try:
                yield sse_pack("status", {"ok": True})

                if safe_str(route_meta.get("route")) == "image":
                    prompt = content.replace("/image", "", 1).strip() or "image"
                    image_result = generate_image(prompt)
                    image_url = safe_str(image_result.get("image_url"))
                    revised_prompt = safe_str(image_result.get("revised_prompt"))
                    final_prompt = revised_prompt or prompt
                    reply_text = f"![Generated image]({image_url})"

                    artifact = add_artifact(
                        session_id=session_id,
                        kind="image_generation",
                        title=final_prompt[:60] or "Generated image",
                        content=final_prompt,
                        meta={
                            "image_url": image_url,
                            "summary": final_prompt[:220],
                            "preview": final_prompt[:220],
                        },
                        image_url=image_url,
                        viewer=build_artifact_viewer(
                            kind="image_generation",
                            title=final_prompt[:60] or "Generated image",
                            content=final_prompt,
                            image_url=image_url,
                            body=final_prompt,
                        ),
                    )

                    yield sse_pack("delta", {"text": reply_text})

                    assistant_msg = {
                        "id": uuid.uuid4().hex[:8],
                        "role": "assistant",
                        "content": reply_text,
                        "created_at": now_iso(),
                        "attachments": [],
                        "route_meta": route_meta,
                    }

                    session["messages"].append(assistant_msg)
                    session["updated_at"] = now_iso()
                    session["message_count"] = len(session["messages"])
                    session["last_message_preview"] = final_prompt[:160]

                    if safe_str(session.get("title")) in {"", "New Chat"}:
                        session["title"] = final_prompt[:48] or "Image"

                    upsert_session(session)

                    state_payload = build_state(session_id=session_id)
                    yield sse_pack("done", {
                        "ok": True,
                        "assistant_message": assistant_msg,
                        "image_url": image_url,
                        "artifact": artifact,
                        "session": state_payload.get("session"),
                        "sessions": state_payload.get("sessions"),
                        "messages": state_payload.get("messages"),
                        "artifacts": state_payload.get("artifacts"),
                        "memory_items": state_payload.get("memory_items"),
                        "web_items": state_payload.get("web_items"),
                        "memory": state_payload.get("memory"),
                        "web": state_payload.get("web"),
                        "route_meta": route_meta,
                    })
                    return

                if safe_str(route_meta.get("route")) == "web":
                    target_url = extract_first_url(content)
                    if not target_url and content.lower().startswith("/web "):
                        target_url = normalize_url(content[5:].strip())
                    if not target_url:
                        raise ValueError("No URL detected for web fetch.")

                    web_result = fetch_web_result(target_url)
                    reply_text = build_web_assistant_text(web_result)

                    chunk_size = 80
                    for i in range(0, len(reply_text), chunk_size):
                        yield sse_pack("delta", {"text": reply_text[i:i + chunk_size]})

                    artifact = add_artifact(
                        session_id=session_id,
                        kind="web_result",
                        title=safe_str(web_result.get("title") or "Web result"),
                        content=reply_text,
                        meta={
                            "summary": safe_str(web_result.get("summary")),
                            "preview": safe_str(web_result.get("preview")),
                            "source_url": safe_str((web_result.get("web") or {}).get("source_url")),
                        },
                        web=web_result.get("web") if isinstance(web_result.get("web"), dict) else None,
                        debug=web_result.get("debug") if isinstance(web_result.get("debug"), dict) else None,
                        source_url=safe_str((web_result.get("web") or {}).get("source_url")),
                        viewer=build_artifact_viewer(
                            kind="web_result",
                            title=safe_str(web_result.get("title") or "Web result"),
                            content=reply_text,
                            source_url=safe_str((web_result.get("web") or {}).get("source_url")),
                            body=safe_str((web_result.get("web") or {}).get("body") or reply_text),
                        ),
                    )

                    assistant_msg = {
                        "id": uuid.uuid4().hex[:8],
                        "role": "assistant",
                        "content": reply_text,
                        "created_at": now_iso(),
                        "attachments": [],
                        "route_meta": route_meta,
                    }

                    session["messages"].append(assistant_msg)
                    session["updated_at"] = now_iso()
                    session["message_count"] = len(session["messages"])
                    session["last_message_preview"] = reply_text[:160]

                    if safe_str(session.get("title")) in {"", "New Chat"}:
                        session["title"] = safe_str(web_result.get("title") or "Web fetch")[:48]

                    upsert_session(session)

                    state_payload = build_state(session_id=session_id)
                    yield sse_pack("done", {
                        "ok": True,
                        "assistant_message": assistant_msg,
                        "artifact": artifact,
                        "session": state_payload.get("session"),
                        "sessions": state_payload.get("sessions"),
                        "messages": state_payload.get("messages"),
                        "artifacts": state_payload.get("artifacts"),
                        "memory_items": state_payload.get("memory_items"),
                        "web_items": state_payload.get("web_items"),
                        "memory": state_payload.get("memory"),
                        "web": state_payload.get("web"),
                        "route_meta": route_meta,
                    })
                    return

                model_messages = build_model_messages(
                    session=session,
                    content=content,
                    attachments=attachments,
                    route_meta=route_meta,
                    session_id=session_id,
                )

                safe_reply = fallback_assistant_text(content, route_meta, attachments)
                reply_text = call_model(model_messages, fallback_text=safe_reply)

                chunk_size = 80
                for i in range(0, len(reply_text), chunk_size):
                    yield sse_pack("delta", {"text": reply_text[i:i + chunk_size]})

                assistant_msg = {
                    "id": uuid.uuid4().hex[:8],
                    "role": "assistant",
                    "content": reply_text,
                    "created_at": now_iso(),
                    "attachments": [],
                    "route_meta": route_meta,
                }

                session["messages"].append(assistant_msg)
                session["updated_at"] = now_iso()
                session["message_count"] = len(session["messages"])
                session["last_message_preview"] = reply_text[:160]

                if safe_str(session.get("title")) in {"", "New Chat"}:
                    for msg in session["messages"]:
                        if safe_str(msg.get("role")) == "user" and safe_str(msg.get("content")):
                            session["title"] = safe_str(msg.get("content"))[:48]
                            break

                upsert_session(session)

                artifact = add_artifact(
                    session_id=session_id,
                    kind="chat",
                    title=session["title"],
                    content=reply_text,
                    meta={"message_count": session["message_count"]},
                    debug={"source": "api_chat_stream", "route": "chat", "route_meta": route_meta},
                    viewer=build_artifact_viewer(
                        kind="chat",
                        title=session["title"],
                        content=reply_text,
                        body=reply_text,
                    ),
                )

                state_payload = build_state(session_id=session_id)
                yield sse_pack("done", {
                    "ok": True,
                    "assistant_message": assistant_msg,
                    "artifact": artifact,
                    "session": state_payload.get("session"),
                    "sessions": state_payload.get("sessions"),
                    "messages": state_payload.get("messages"),
                    "artifacts": state_payload.get("artifacts"),
                    "memory_items": state_payload.get("memory_items"),
                    "web_items": state_payload.get("web_items"),
                    "memory": state_payload.get("memory"),
                    "web": state_payload.get("web"),
                    "route_meta": route_meta,
                })
            except Exception as exc:
                safe_reply = fallback_assistant_text(content, route_meta if isinstance(route_meta, dict) else {}, attachments, error_text=str(exc))
                yield sse_pack("delta", {"text": safe_reply})

                assistant_msg = {
                    "id": uuid.uuid4().hex[:8],
                    "role": "assistant",
                    "content": safe_reply,
                    "created_at": now_iso(),
                    "attachments": [],
                    "route_meta": route_meta if isinstance(route_meta, dict) else {},
                }

                session["messages"].append(assistant_msg)
                session["updated_at"] = now_iso()
                session["message_count"] = len(session["messages"])
                session["last_message_preview"] = safe_reply[:160]

                if safe_str(session.get("title")) in {"", "New Chat"}:
                    for msg in session["messages"]:
                        if safe_str(msg.get("role")) == "user" and safe_str(msg.get("content")):
                            session["title"] = safe_str(msg.get("content"))[:48]
                            break

                upsert_session(session)

                artifact = add_artifact(
                    session_id=session_id,
                    kind="chat",
                    title=session["title"],
                    content=safe_reply,
                    meta={"message_count": session["message_count"]},
                    debug={"source": "api_chat_stream", "route": "chat-fallback", "error": str(exc)},
                    viewer=build_artifact_viewer(
                        kind="chat",
                        title=session["title"],
                        content=safe_reply,
                        body=safe_reply,
                    ),
                )

                state_payload = build_state(session_id=session_id)
                yield sse_pack("done", {
                    "ok": True,
                    "assistant_message": assistant_msg,
                    "artifact": artifact,
                    "session": state_payload.get("session"),
                    "sessions": state_payload.get("sessions"),
                    "messages": state_payload.get("messages"),
                    "artifacts": state_payload.get("artifacts"),
                    "memory_items": state_payload.get("memory_items"),
                    "web_items": state_payload.get("web_items"),
                    "memory": state_payload.get("memory"),
                    "web": state_payload.get("web"),
                    "route_meta": route_meta if isinstance(route_meta, dict) else {},
                    "debug": {"stream_fallback_error": str(exc)},
                })

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        return _error(f"Streaming failed: {exc}", status=500)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        payload = request.get_json(silent=True) or {}

        content = (
            safe_str(payload.get("content"))
            or safe_str(payload.get("message"))
            or safe_str(payload.get("user_text"))
            or safe_str(payload.get("text"))
        )

        session_id = safe_str(payload.get("session_id") or payload.get("sessionId"))
        attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
        route_meta = payload.get("route_meta") or payload.get("routeMeta") or {}

        if not content and not attachments:
            return _error("Missing content.", status=400)

        ensure_storage()

        session = get_session(session_id)
        if not session:
            session = create_session()
            session_id = session["id"]

        if not route_meta:
            route_meta = route_request(content, attachments)

        user_msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": content,
            "created_at": now_iso(),
            "attachments": attachments,
            "route_meta": route_meta if isinstance(route_meta, dict) else {},
        }
        session["messages"].append(user_msg)

        route_name = safe_str(route_meta.get("route"))

        if route_name == "image":
            prompt = content.replace("/image", "", 1).strip() or "image"
            image_result = generate_image(prompt)
            image_url = safe_str(image_result.get("image_url"))
            revised_prompt = safe_str(image_result.get("revised_prompt"))
            final_prompt = revised_prompt or prompt
            reply_text = f"![Generated image]({image_url})"

            assistant_msg = {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant",
                "content": reply_text,
                "created_at": now_iso(),
                "attachments": [
                    {
                        "id": uuid.uuid4().hex[:8],
                        "name": Path(image_url).name,
                        "url": image_url,
                        "preview_url": image_url,
                        "mime_type": "image/png",
                        "kind": "image",
                        "uploaded_at": now_iso(),
                    }
                ],
                "route_meta": route_meta,
            }

            session["messages"].append(assistant_msg)
            session["updated_at"] = now_iso()
            session["message_count"] = len(session["messages"])
            session["last_message_preview"] = f"Generated image: {final_prompt[:120]}"

            if safe_str(session.get("title")) in {"", "New Chat"}:
                for msg in session["messages"]:
                    if safe_str(msg.get("role")) == "user" and safe_str(msg.get("content")):
                        session["title"] = safe_str(msg.get("content"))[:48].rstrip() or "New Chat"
                        break

            upsert_session(session)

            artifact = add_artifact(
                session_id=session_id,
                kind="generated_image",
                title=f"Generated Image - {final_prompt[:80]}",
                content=reply_text,
                meta={
                    "prompt": final_prompt,
                    "image_url": image_url,
                    "preview": f"Generated from prompt: {final_prompt}"[:220],
                    "summary": f"Generated from prompt: {final_prompt}"[:220],
                    "media": [
                        {
                            "filename": Path(image_url).name,
                            "mime_type": "image/png",
                            "prompt": final_prompt,
                            "type": "image",
                            "url": image_url,
                        }
                    ],
                },
                debug={
                    "source": "api_chat",
                    "route": route_name,
                    "image_model": IMAGE_MODEL,
                },
                extra={
                    "image_url": image_url,
                    "prompt": final_prompt,
                    "media": [
                        {
                            "filename": Path(image_url).name,
                            "mime_type": "image/png",
                            "prompt": final_prompt,
                            "type": "image",
                            "url": image_url,
                        }
                    ],
                },
                image_url=image_url,
                viewer=build_artifact_viewer(
                    kind="generated_image",
                    title=f"Generated Image - {final_prompt[:80]}",
                    content=reply_text,
                    image_url=image_url,
                    body=f"Generated from prompt: {final_prompt}",
                ),
            )

            state_payload = build_state(session_id=session_id)
            return _ok(
                message=reply_text,
                assistant_message=reply_text,
                image_url=image_url,
                artifact=artifact,
                session=state_payload.get("session"),
                sessions=state_payload.get("sessions"),
                messages=state_payload.get("messages"),
                artifacts=state_payload.get("artifacts"),
                memory_items=state_payload.get("memory_items"),
                web_items=state_payload.get("web_items"),
                memory=state_payload.get("memory"),
                web=state_payload.get("web"),
                debug={
                    "model": OPENAI_MODEL,
                    "openai_configured": bool(client),
                    "attachment_count": len(attachments),
                    "route": route_name,
                    "image_model": IMAGE_MODEL,
                },
                route_meta=route_meta,
            )

        if route_name == "web":
            target_url = extract_first_url(content)
            if not target_url and content.lower().startswith("/web "):
                target_url = normalize_url(content[5:].strip())
            if not target_url:
                return _error("No URL detected for web fetch.", status=400)

            web_result = fetch_web_result(target_url)
            reply_text = build_web_assistant_text(web_result)

            assistant_msg = {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant",
                "content": reply_text,
                "created_at": now_iso(),
                "attachments": [],
                "route_meta": route_meta,
            }

            session["messages"].append(assistant_msg)
            session["updated_at"] = now_iso()
            session["message_count"] = len(session["messages"])
            session["last_message_preview"] = reply_text[:160]

            if safe_str(session.get("title")) in {"", "New Chat"}:
                for msg in session["messages"]:
                    if safe_str(msg.get("role")) == "user" and safe_str(msg.get("content")):
                        session["title"] = safe_str(msg.get("content"))[:48].rstrip() or "New Chat"
                        break

            upsert_session(session)

            artifact = add_artifact(
                session_id=session_id,
                kind="web_result",
                title=safe_str(web_result.get("title") or "Web result"),
                content=reply_text,
                meta={
                    "summary": safe_str(web_result.get("summary")),
                    "preview": safe_str(web_result.get("preview")),
                    "source_url": safe_str((web_result.get("web") or {}).get("source_url")),
                },
                web=web_result.get("web") if isinstance(web_result.get("web"), dict) else None,
                debug=web_result.get("debug") if isinstance(web_result.get("debug"), dict) else None,
                source_url=safe_str((web_result.get("web") or {}).get("source_url")),
                viewer=build_artifact_viewer(
                    kind="web_result",
                    title=safe_str(web_result.get("title") or "Web result"),
                    content=reply_text,
                    source_url=safe_str((web_result.get("web") or {}).get("source_url")),
                    body=safe_str((web_result.get("web") or {}).get("body") or reply_text),
                ),
            )

            state_payload = build_state(session_id=session_id)
            return _ok(
                message=reply_text,
                assistant_message=reply_text,
                artifact=artifact,
                session=state_payload.get("session"),
                sessions=state_payload.get("sessions"),
                messages=state_payload.get("messages"),
                artifacts=state_payload.get("artifacts"),
                memory_items=state_payload.get("memory_items"),
                web_items=state_payload.get("web_items"),
                memory=state_payload.get("memory"),
                web=state_payload.get("web"),
                debug={
                    "model": OPENAI_MODEL,
                    "openai_configured": bool(client),
                    "attachment_count": len(attachments),
                    "route": route_name,
                },
                route_meta=route_meta,
            )

        model_messages = build_model_messages(
            session=session,
            content=content,
            attachments=attachments,
            route_meta=route_meta,
            session_id=session_id,
        )

        safe_reply = fallback_assistant_text(content, route_meta, attachments)
        assistant_text = call_model(model_messages, fallback_text=safe_reply)

        assistant_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
            "attachments": [],
            "route_meta": route_meta,
        }
        session["messages"].append(assistant_message)

        if safe_str(session.get("title")) in {"", "New Chat"}:
            first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
            if first_user:
                session["title"] = first_user["content"][:48].rstrip() or "New Chat"

        session["updated_at"] = now_iso()
        session["message_count"] = len(session["messages"])
        session["last_message_preview"] = assistant_text[:160] or content[:160]
        upsert_session(session)

        artifact = add_artifact(
            session_id=session_id,
            kind="chat",
            title=session["title"],
            content=assistant_text,
            meta={"message_count": session["message_count"]},
            debug={"source": "api_chat", "route": "chat", "route_meta": route_meta},
            viewer=build_artifact_viewer(
                kind="chat",
                title=session["title"],
                content=assistant_text,
                body=assistant_text,
            ),
        )

        state_payload = build_state(session_id=session_id)
        return _ok(
            message=assistant_text,
            assistant_message=assistant_text,
            artifact=artifact,
            session=state_payload.get("session"),
            sessions=state_payload.get("sessions"),
            messages=state_payload.get("messages"),
            artifacts=state_payload.get("artifacts"),
            memory_items=state_payload.get("memory_items"),
            web_items=state_payload.get("web_items"),
            memory=state_payload.get("memory"),
            web=state_payload.get("web"),
            debug={
                "model": OPENAI_MODEL,
                "openai_configured": bool(client),
                "attachment_count": len(attachments),
                "route": "chat",
            },
            route_meta=route_meta,
        )
    except Exception as exc:
        try:
            ensure_storage()

            payload = request.get_json(silent=True) or {}
            content = (
                safe_str(payload.get("content"))
                or safe_str(payload.get("message"))
                or safe_str(payload.get("user_text"))
                or safe_str(payload.get("text"))
            )
            session_id = safe_str(payload.get("session_id") or payload.get("sessionId"))
            attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
            route_meta = payload.get("route_meta") or payload.get("routeMeta") or {}
            if not route_meta:
                route_meta = _route_meta("chat", "general", "Safe exception fallback.", [])

            session = get_session(session_id)
            if not session:
                session = create_session()
                session_id = session["id"]

            if not session.get("messages") or not (
                session["messages"]
                and safe_str(session["messages"][-1].get("role")) == "user"
                and safe_str(session["messages"][-1].get("content")) == safe_str(content)
            ):
                session["messages"].append(
                    {
                        "id": uuid.uuid4().hex[:8],
                        "role": "user",
                        "content": content,
                        "created_at": now_iso(),
                        "attachments": attachments,
                        "route_meta": route_meta if isinstance(route_meta, dict) else {},
                    }
                )

            safe_reply = fallback_assistant_text(content, route_meta if isinstance(route_meta, dict) else {}, attachments, error_text=str(exc))

            assistant_message = {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant",
                "content": safe_reply,
                "created_at": now_iso(),
                "attachments": [],
                "route_meta": route_meta if isinstance(route_meta, dict) else {},
            }
            session["messages"].append(assistant_message)

            if safe_str(session.get("title")) in {"", "New Chat"}:
                first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
                if first_user:
                    session["title"] = first_user["content"][:48].rstrip() or "New Chat"

            session["updated_at"] = now_iso()
            session["message_count"] = len(session["messages"])
            session["last_message_preview"] = safe_reply[:160]
            upsert_session(session)

            artifact = add_artifact(
                session_id=session_id,
                kind="chat",
                title=session["title"],
                content=safe_reply,
                meta={"message_count": session["message_count"]},
                debug={"source": "api_chat_exception", "route": "chat-fallback", "error": str(exc)},
                viewer=build_artifact_viewer(
                    kind="chat",
                    title=session["title"],
                    content=safe_reply,
                    body=safe_reply,
                ),
            )

            state_payload = build_state(session_id=session_id)
            return _ok(
                message=safe_reply,
                assistant_message=safe_reply,
                artifact=artifact,
                session=state_payload.get("session"),
                sessions=state_payload.get("sessions"),
                messages=state_payload.get("messages"),
                artifacts=state_payload.get("artifacts"),
                memory_items=state_payload.get("memory_items"),
                web_items=state_payload.get("web_items"),
                memory=state_payload.get("memory"),
                web=state_payload.get("web"),
                debug={
                    "model": OPENAI_MODEL,
                    "openai_configured": bool(client),
                    "route": "chat-fallback",
                    "error": str(exc),
                },
                route_meta=route_meta if isinstance(route_meta, dict) else {},
            )
        except Exception as fallback_exc:
            return _error(f"Chat failed: {exc}; fallback failed: {fallback_exc}", status=500)


if __name__ == "__main__":
    ensure_storage()
    app.run(host="127.0.0.1", port=5001, debug=True)