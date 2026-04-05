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

def load_memory_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(MEMORY_FILE, {"items": []})
    items = raw.get("items", []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        items = []
    return {"items": items}


def save_memory_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(MEMORY_FILE, {"items": payload.get("items", [])})


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

    session = None
    session_id = ""
    content = ""
    attachments: list[dict[str, Any]] = []
    route_meta: dict[str, Any] = {"route": "chat", "mode": "general", "reason": "Default conversational route.", "matched_keywords": []}

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

    if route_meta.get("route") == "image":
        prompt = safe_str(content)
        if prompt.lower().startswith("/image"):
            prompt = prompt[6:].strip()

        image_result = generate_image(prompt, safe_str(payload.get("size")))
        image_url = safe_str(image_result.get("image_url"))

        if not regenerate:
            session["messages"].append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "role": "user",
                    "content": content,
                    "created_at": now_iso(),
                    "attachments": attachments,
                    "route_meta": route_meta,
                }
            )

        assistant_text = f"Generated image for: {prompt}" if prompt else "Generated image."

        assistant_attachments = []
        if image_url:
            guessed_name = Path(urlparse(image_url).path).name or "generated.png"
            assistant_attachments.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "name": guessed_name,
                    "filename": guessed_name,
                    "url": image_url,
                    "preview_url": image_url,
                    "path": image_url,
                    "mime_type": "image/png" if image_url.lower().endswith(".png") else "text/plain",
                    "kind": "image" if image_url.lower().endswith(".png") else "file",
                    "size": 0,
                    "uploaded_at": now_iso(),
                }
            )

        assistant_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
            "attachments": assistant_attachments,
            "route_meta": route_meta,
        }
        session["messages"].append(assistant_message)

        artifact = create_artifact(
            session_id=session_id,
            kind="image",
            title="Generated Image",
            content=assistant_text,
            summary=prompt[:220],
            image_url=image_url,
            meta=image_result,
        )

        if safe_str(session.get("title")) in {"", "New Chat"}:
            session["title"] = (prompt[:48].rstrip() if prompt else "New Chat") or "New Chat"

        persist_session(session, assistant_text=assistant_text, fallback_preview=content, make_active=True)

        state_payload = build_state(session_id=session_id)
        return {
            "ok": True,
            "message": assistant_text,
            "assistant_message": assistant_message,
            "assistant_text": assistant_text,
            "session_id": session_id,
            "session": state_payload.get("session"),
            "sessions": state_payload.get("sessions"),
            "messages": state_payload.get("messages"),
            "artifacts": state_payload.get("artifacts"),
            "memory_items": state_payload.get("memory_items"),
            "web_items": state_payload.get("web_items"),
            "memory": state_payload.get("memory"),
            "web": state_payload.get("web"),
            "image_url": image_url,
            "artifact": artifact,
            "route_meta": route_meta,
            "debug": {
                "model": OPENAI_MODEL,
                "image_model": NOVA_IMAGE_MODEL,
                "openai_configured": bool(client),
                "attachment_count": len(attachments),
                "route": route_meta.get("route"),
                "mode": route_meta.get("mode"),
            },
        }

    if not regenerate:
        session["messages"].append(
            {
                "id": uuid.uuid4().hex[:8],
                "role": "user",
                "content": content,
                "created_at": now_iso(),
                "attachments": attachments,
                "route_meta": route_meta,
            }
        )

    safe_reply = fallback_assistant_text(content, attachments)
    model_messages = build_model_messages(
        session=session,
        content=content,
        attachments=attachments,
    )
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

    artifact = create_artifact(
        session_id=session_id,
        kind="chat",
        title="Chat Reply",
        content=assistant_text,
        summary=assistant_text[:220],
    )

    if safe_str(session.get("title")) in {"", "New Chat"}:
        first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
        if first_user:
            session["title"] = first_user["content"][:48].rstrip() or "New Chat"

    persist_session(session, assistant_text=assistant_text, fallback_preview=content, make_active=True)

    state_payload = build_state(session_id=session_id)
    return {
        "ok": True,
        "message": assistant_text,
        "assistant_message": assistant_message,
        "assistant_text": assistant_text,
        "session_id": session_id,
        "session": state_payload.get("session"),
        "sessions": state_payload.get("sessions"),
        "messages": state_payload.get("messages"),
        "artifacts": state_payload.get("artifacts"),
        "memory_items": state_payload.get("memory_items"),
        "web_items": state_payload.get("web_items"),
        "memory": state_payload.get("memory"),
        "web": state_payload.get("web"),
        "artifact": artifact,
        "route_meta": route_meta,
        "debug": {
            "model": OPENAI_MODEL,
            "image_model": NOVA_IMAGE_MODEL,
            "openai_configured": bool(client),
            "attachment_count": len(attachments),
            "route": route_meta.get("route"),
            "mode": route_meta.get("mode"),
        },
    }


# ------------------ ROUTES ------------------

@app.route("/")
def index():
    ensure_storage()
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    ensure_storage()
    return _ok(
        status="ok",
        route_build="session-switch-lock-2026-04-04-001",
        openai_model=OPENAI_MODEL,
        image_model=NOVA_IMAGE_MODEL,
        has_openai_api_key=bool(OPENAI_API_KEY),
        openai_configured=bool(client),
        timestamp=now_iso(),
    )


@app.route("/api/state", methods=["GET"])
def api_state():
    ensure_storage()
    session_id = safe_str(request.args.get("session_id"))
    return jsonify(build_state(session_id=session_id))


@app.route("/api/session/new", methods=["POST"])
def api_session_new():
    ensure_storage()
    try:
        payload = request.get_json(silent=True) or {}
        title = safe_str(
            payload.get("title")
            or payload.get("name")
            or payload.get("session_title")
        ) or "New Chat"

        session = create_session(title=title)
        upsert_session(session, make_active=True)

        state_payload = build_state(session_id=session["id"])
        return _ok(
            session_id=session["id"],
            active_session_id=session["id"],
            session=state_payload.get("session"),
            sessions=state_payload.get("sessions"),
            messages=state_payload.get("messages"),
            artifacts=state_payload.get("artifacts"),
            memory_items=state_payload.get("memory_items"),
            web_items=state_payload.get("web_items"),
            memory=state_payload.get("memory"),
            web=state_payload.get("web"),
        )
    except Exception as exc:
        return _error(f"New chat failed: {exc}", status=500)


@app.route("/api/session/switch", methods=["POST"])
def api_session_switch():
    ensure_storage()

    try:
        payload = request.get_json(silent=True) or {}
        session_id = str(
            payload.get("session_id")
            or payload.get("id")
            or payload.get("sessionId")
            or ""
        ).strip()

        if not session_id:
            return jsonify({
                "ok": False,
                "error": "session_id is required"
            }), 400

        store = load_sessions_payload()
        sessions = store.get("sessions") or []

        target = None
        for session in sessions:
            sid = _session_id_of(session)
            if sid == session_id:
                target = session
                break

        if not target:
            return jsonify({
                "ok": False,
                "error": "Session not found",
                "session_id": session_id
            }), 404

        active_session = _mark_active_session(store, session_id)
        save_sessions_payload(store)

        state_payload = build_state(session_id=session_id)
        return jsonify({
            "ok": True,
            "session_id": store.get("active_session_id") or session_id,
            "active_session_id": store.get("active_session_id") or session_id,
            "session": active_session or target,
            "sessions": state_payload.get("sessions"),
            "messages": state_payload.get("messages"),
            "artifacts": state_payload.get("artifacts"),
            "memory_items": state_payload.get("memory_items"),
            "web_items": state_payload.get("web_items"),
            "memory": state_payload.get("memory"),
            "web": state_payload.get("web"),
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    ensure_storage()
    session_id = safe_str(request.args.get("session_id"))
    payload = load_artifacts_payload()
    artifacts = payload["artifacts"]

    if session_id:
        artifacts = [a for a in artifacts if safe_str(a.get("session_id")) == session_id]

    return _ok(artifacts=artifacts, items=artifacts, count=len(artifacts))


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_detail(artifact_id: str):
    ensure_storage()
    artifact = get_artifact(artifact_id)
    if not artifact:
        return _error("Artifact not found.", status=404)
    return _ok(artifact=artifact, item=artifact)


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    ensure_storage()

    if "file" not in request.files:
        return _error("Missing file.", status=400)

    file = request.files["file"]
    original_name = safe_str(file.filename)
    if not original_name:
        return _error("Missing filename.", status=400)

    ext = Path(original_name).suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = UPLOADS_DIR / stored_name
    file.save(str(target))

    mime_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    size = target.stat().st_size if target.exists() else 0
    url = f"/api/uploads/{stored_name}"

    attachment = {
        "id": uuid.uuid4().hex[:8],
        "name": original_name,
        "filename": original_name,
        "stored_name": stored_name,
        "url": url,
        "preview_url": url,
        "path": url,
        "mime_type": mime_type,
        "kind": guess_kind_from_mime(mime_type),
        "size": size,
        "uploaded_at": now_iso(),
    }

    return _ok(
        message="Upload saved.",
        attachment=attachment,
        file=attachment,
        upload=attachment,
        id=attachment["id"],
        filename=original_name,
        url=url,
        path=url,
        mime_type=mime_type,
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        payload = request.get_json(silent=True) or {}
        result = process_chat_payload(payload)
        return jsonify(result)
    except ValueError as exc:
        return _error(str(exc), status=400)
    except Exception as exc:
        return _error(f"Chat failed: {exc}", status=500)


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    payload = request.get_json(silent=True) or {}

    @stream_with_context
    def generate():
        try:
            yield sse_pack("status", {"ok": True, "phase": "start"})
            result = process_chat_payload(payload)

            assistant_text = safe_str(
                (result.get("assistant_message") or {}).get("content")
                or result.get("assistant_text")
                or result.get("message")
            )

            if assistant_text:
                chunk_size = 80
                for i in range(0, len(assistant_text), chunk_size):
                    yield sse_pack("delta", {"text": assistant_text[i:i + chunk_size]})

            yield sse_pack("done", result)
        except ValueError as exc:
            yield sse_pack("error", {"error": str(exc)})
        except Exception as exc:
            yield sse_pack("error", {"error": f"Chat failed: {exc}"})

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return Response(generate(), mimetype="text/event-stream", headers=headers)


@app.route("/api/web/fetch", methods=["POST"])
def api_web_fetch():
    ensure_storage()
    try:
        payload = request.get_json(silent=True) or {}
        url = safe_str(payload.get("url") or payload.get("content") or payload.get("message") or payload.get("text"))
        session_id = safe_str(payload.get("session_id") or payload.get("sessionId"))

        if not url:
            return _error("Missing URL.", status=400)

        result = fetch_web_result(url)

        create_artifact(
            session_id=session_id,
            kind="web",
            title=result.get("title") or "Web Result",
            content=result.get("body") or "",
            summary=result.get("summary") or "",
            source_url=result.get("url") or url,
            meta=result,
        )

        return _ok(web_result=result, session_id=session_id)
    except Exception as exc:
        return _error(f"Web fetch failed: {exc}", status=500)


if __name__ == "__main__":
    ensure_storage()
    app.run(host="127.0.0.1", port=5001, debug=True, threaded=True)