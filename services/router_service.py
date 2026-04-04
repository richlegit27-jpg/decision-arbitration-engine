import base64
import json
import mimetypes
import os
import re
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, render_template, request, send_from_directory

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

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if OpenAI and os.getenv("OPENAI_API_KEY") else None
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
VISION_MODEL = os.getenv("NOVA_VISION_MODEL", "gpt-4.1-mini")
IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5")
IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")
IMAGE_QUALITY = os.getenv("NOVA_IMAGE_QUALITY", "medium")

ROUTE_BUILD = "route-request-hardened-2026-04-03-002"


# --------------------------------------------------
# core utils
# --------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def safe_write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def truncate(text: str, limit: int = 180) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def ensure_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    if re.match(r"^https?://", value, re.I):
        return value
    if re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}([/?#].*)?$", value):
        return f"https://{value}"
    return value


def extract_first_url(text: str) -> Optional[str]:
    value = (text or "").strip()
    if not value:
        return None
    match = re.search(r"(https?://[^\s]+|www\.[^\s]+|[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)", value)
    if not match:
        return None
    return normalize_url(match.group(1).rstrip(").,]}>"))


def is_probable_url_only(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    value = value.replace("\n", " ").strip()
    return bool(re.fullmatch(r"(https?://[^\s]+|www\.[^\s]+|[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)", value))


def slugify_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "file")
    cleaned = cleaned.strip("._") or "file"
    return cleaned


def guess_kind_from_mime(mime: str) -> str:
    value = mime or ""
    if value.startswith("image/"):
        return "image"
    if value.startswith("video/"):
        return "video"
    if value.startswith("audio/"):
        return "audio"
    if value == "application/pdf":
        return "pdf"
    return "file"


def parse_json_body() -> Dict[str, Any]:
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            return payload
    return {}


# --------------------------------------------------
# persistence
# --------------------------------------------------
def normalize_sessions_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, list):
        sessions = payload
        active_session_id = sessions[0].get("id") if sessions else None
        return {"sessions": sessions, "active_session_id": active_session_id}

    if isinstance(payload, dict):
        sessions = payload.get("sessions", [])
        if not isinstance(sessions, list):
            sessions = []
        active_session_id = payload.get("active_session_id")
        if not active_session_id and sessions:
            active_session_id = sessions[0].get("id")
        return {"sessions": sessions, "active_session_id": active_session_id}

    return {"sessions": [], "active_session_id": None}


def load_sessions_store() -> Dict[str, Any]:
    payload = normalize_sessions_payload(
        safe_read_json(SESSIONS_FILE, {"sessions": [], "active_session_id": None})
    )
    sessions = payload.get("sessions", [])
    changed = False

    for session in sessions:
        if not isinstance(session, dict):
            continue

        if "id" not in session:
            session["id"] = new_id("session")
            changed = True

        session.setdefault("title", "New chat")
        session.setdefault("created_at", utc_now())
        session.setdefault("updated_at", session["created_at"])
        session.setdefault("pinned", False)
        session.setdefault("messages", [])
        session.setdefault("last_message_preview", "")
        session.setdefault("message_count", len(session.get("messages", [])))

        if not isinstance(session.get("messages"), list):
            session["messages"] = []
            changed = True

        for msg in session["messages"]:
            if not isinstance(msg, dict):
                continue
            if "id" not in msg:
                msg["id"] = new_id("msg")
                changed = True
            msg.setdefault("role", "assistant")
            msg.setdefault("content", "")
            msg.setdefault("created_at", utc_now())
            msg.setdefault("attachments", [])
            msg.setdefault("meta", {})

    if not payload.get("active_session_id") and sessions:
        payload["active_session_id"] = sessions[0].get("id")
        changed = True

    if changed:
        save_sessions_store(payload)

    return payload


def save_sessions_store(store: Dict[str, Any]) -> None:
    safe_write_json(SESSIONS_FILE, store)


def load_artifacts() -> List[Dict[str, Any]]:
    raw = safe_read_json(ARTIFACTS_FILE, [])
    if isinstance(raw, dict):
        raw = raw.get("artifacts", [])
    if not isinstance(raw, list):
        raw = []

    items: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        item.setdefault("id", new_id("artifact"))
        item.setdefault("kind", "chat_reply")
        item.setdefault("title", "Artifact")
        item.setdefault("body", item.get("content") or "")
        item.setdefault("content", item.get("body") or "")
        item.setdefault("preview", "")
        item.setdefault("meta", {})
        item.setdefault("viewer", {})
        item.setdefault("session_id", "")
        item.setdefault("created_at", utc_now())
        item.setdefault("updated_at", item["created_at"])
        items.append(item)
    return items


def save_artifacts(items: List[Dict[str, Any]]) -> None:
    safe_write_json(ARTIFACTS_FILE, items)


def load_memory() -> List[Dict[str, Any]]:
    raw = safe_read_json(MEMORY_FILE, [])
    if isinstance(raw, dict):
        raw = raw.get("items", [])
    if not isinstance(raw, list):
        raw = []

    items: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        item.setdefault("id", new_id("memory"))
        item.setdefault("text", "")
        item.setdefault("kind", "note")
        item.setdefault("source", "assistant")
        item.setdefault("session_id", "")
        item.setdefault("created_at", utc_now())
        item.setdefault("updated_at", item["created_at"])
        item["preview"] = truncate(item.get("text", ""), 140)
        items.append(item)
    return items


def save_memory(items: List[Dict[str, Any]]) -> None:
    safe_write_json(MEMORY_FILE, items)


# --------------------------------------------------
# session helpers
# --------------------------------------------------
def make_session(title: str = "New chat") -> Dict[str, Any]:
    now = utc_now()
    return {
        "id": new_id("session"),
        "title": title,
        "created_at": now,
        "updated_at": now,
        "pinned": False,
        "messages": [],
        "last_message_preview": "",
        "message_count": 0,
    }


def find_session(store: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    for session in store.get("sessions", []):
        if session.get("id") == session_id:
            return session
    return None


def get_active_session_id() -> Optional[str]:
    return load_sessions_store().get("active_session_id")


def update_session_derived_fields(session: Dict[str, Any]) -> None:
    messages = ensure_list(session.get("messages"))
    session["message_count"] = len(messages)
    session["updated_at"] = utc_now()

    preview = ""
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        content = (msg.get("content") or "").strip()
        if content:
            preview = truncate(content, 140)
            break
    session["last_message_preview"] = preview

    title = (session.get("title") or "").strip()
    if not title or title == "New chat":
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "user":
                content = (msg.get("content") or "").strip()
                if content:
                    session["title"] = truncate(content, 48)
                    break


def append_message(
    session: Dict[str, Any],
    role: str,
    content: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    msg = {
        "id": new_id("msg"),
        "role": role,
        "content": content or "",
        "created_at": utc_now(),
        "attachments": attachments or [],
        "meta": meta or {},
    }
    session.setdefault("messages", []).append(msg)
    update_session_derived_fields(session)
    return msg


def choose_fallback_session_id(store: Dict[str, Any]) -> Optional[str]:
    sessions = ensure_list(store.get("sessions"))
    if not sessions:
        return None

    pinned = [s for s in sessions if s.get("pinned")]
    if pinned:
        pinned.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return pinned[0].get("id")

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions[0].get("id")


# --------------------------------------------------
# artifact helpers
# --------------------------------------------------
def build_artifact_viewer(item: Dict[str, Any]) -> Dict[str, Any]:
    viewer = dict(item.get("viewer") or {})
    meta = dict(item.get("meta") or {})

    viewer.setdefault("kind", item.get("kind", "chat_reply"))
    viewer.setdefault("title", item.get("title", "Artifact"))
    viewer.setdefault("body", item.get("body") or item.get("content") or "")
    viewer.setdefault("source_url", meta.get("source_url") or item.get("source_url"))
    viewer.setdefault("image_url", meta.get("image_url") or item.get("image_url"))
    viewer.setdefault("video_url", meta.get("video_url") or item.get("video_url"))
    viewer.setdefault("audio_url", meta.get("audio_url") or item.get("audio_url"))
    viewer.setdefault("analysis_text", meta.get("analysis_text") or item.get("analysis_text") or "")
    viewer.setdefault("bullets", ensure_list(meta.get("bullets") or viewer.get("bullets")))
    return viewer


def create_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    body: str = "",
    preview: str = "",
    meta: Optional[Dict[str, Any]] = None,
    viewer: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = utc_now()
    item = {
        "id": new_id("artifact"),
        "session_id": session_id,
        "kind": kind or "chat_reply",
        "title": title or "Artifact",
        "body": body or "",
        "content": body or "",
        "preview": preview or truncate(body or "", 180),
        "meta": meta or {},
        "viewer": viewer or {},
        "created_at": now,
        "updated_at": now,
    }
    item["viewer"] = build_artifact_viewer(item)

    artifacts = load_artifacts()
    artifacts.insert(0, item)
    save_artifacts(artifacts)
    return item


def serialize_artifact(item: Dict[str, Any]) -> Dict[str, Any]:
    output = dict(item)
    output["viewer"] = build_artifact_viewer(output)
    return output


# --------------------------------------------------
# upload helpers
# --------------------------------------------------
def save_uploaded_file(file_storage) -> Dict[str, Any]:
    original_name = file_storage.filename or "upload"
    safe_name = slugify_filename(original_name)
    ext = Path(safe_name).suffix
    stem = Path(safe_name).stem or "upload"
    disk_name = f"{stem}_{uuid.uuid4().hex}{ext}"
    destination = UPLOADS_DIR / disk_name
    file_storage.save(destination)

    mime = file_storage.mimetype or mimetypes.guess_type(destination.name)[0] or "application/octet-stream"
    url = f"/uploads/{destination.name}"

    return {
        "id": new_id("upload"),
        "name": original_name,
        "filename": destination.name,
        "path": str(destination),
        "url": url,
        "mime_type": mime,
        "kind": guess_kind_from_mime(mime),
        "size": destination.stat().st_size if destination.exists() else 0,
        "created_at": utc_now(),
    }


def read_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def attachment_to_input_block(att: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mime = att.get("mime_type") or ""
    filename = att.get("filename") or ""
    path = UPLOADS_DIR / filename

    if not path.exists():
        return None

    try:
        data_b64 = read_file_base64(path)
    except Exception:
        return None

    if mime.startswith("image/"):
        return {
            "type": "input_image",
            "image_url": f"data:{mime};base64,{data_b64}",
        }

    return {
        "type": "input_text",
        "text": f"Attachment available: {att.get('name') or filename} ({mime})",
    }


# --------------------------------------------------
# web fetch
# --------------------------------------------------
def strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html or "")
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_meta(html: str, patterns: List[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, html or "", re.I | re.S)
        if match:
            return (match.group(1) or "").strip()
    return ""


def fetch_web_page(url: str) -> Dict[str, Any]:
    target = normalize_url(url)
    if not target:
        raise ValueError("Missing URL")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Nova/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    response = None
    ssl_verified = True

    try:
        response = requests.get(target, timeout=20, headers=headers)
        response.raise_for_status()
    except requests.exceptions.SSLError:
        ssl_verified = False
        response = requests.get(target, timeout=20, headers=headers, verify=False)
        response.raise_for_status()

    html = response.text or ""
    title = first_meta(html, [r"<title[^>]*>(.*?)</title>", r'property="og:title"\s+content="(.*?)"'])
    description = first_meta(
        html,
        [
            r'<meta[^>]+name="description"[^>]+content="(.*?)"',
            r'<meta[^>]+property="og:description"[^>]+content="(.*?)"',
        ],
    )
    site_name = first_meta(html, [r'<meta[^>]+property="og:site_name"[^>]+content="(.*?)"'])
    content = strip_html(html)
    summary = truncate(content, 1200)
    preview = truncate(description or summary or title or target, 180)
    parsed = urlparse(target)

    return {
        "ok": True,
        "url": target,
        "domain": parsed.netloc,
        "title": title or parsed.netloc or target,
        "description": description or "",
        "site_name": site_name or parsed.netloc,
        "content": summary,
        "preview": preview,
        "summary": summary,
        "status_code": response.status_code if response is not None else 200,
        "ssl_verified": ssl_verified,
        "fetched_at": utc_now(),
    }


# --------------------------------------------------
# routing / mode system
# --------------------------------------------------
MODE_KEYWORDS: Dict[str, List[str]] = {
    "coding": [
        "code",
        "bug",
        "fix",
        "error",
        "traceback",
        "flask",
        "python",
        "javascript",
        "js",
        "css",
        "html",
        "sql",
        "api",
        "endpoint",
        "route",
        "function",
        "class",
        "refactor",
        "smff",
        "full file",
        "app.py",
        "index.html",
        "backend",
        "frontend",
        "json",
    ],
    "planning": [
        "plan",
        "roadmap",
        "phase",
        "next step",
        "next steps",
        "sequence",
        "strategy",
        "milestone",
        "architecture",
        "organize",
        "timeline",
        "break this down",
        "what should we do next",
    ],
    "writing": [
        "write",
        "rewrite",
        "edit",
        "book",
        "chapter",
        "email",
        "bio",
        "story",
        "post",
        "caption",
        "script",
        "poem",
        "essay",
        "copy",
    ],
    "analysis": [
        "analyze",
        "analyse",
        "why",
        "compare",
        "review",
        "inspect",
        "debug",
        "root cause",
        "explain",
        "what happened",
        "investigate",
        "evaluate",
        "pros and cons",
    ],
}

MODE_INSTRUCTIONS: Dict[str, str] = {
    "coding": (
        "You are in CODING mode. Be implementation-first, exact, and practical. "
        "Prefer concrete fixes, direct reasoning, and working code. "
        "If something is broken, identify the cause briefly and then solve it cleanly."
    ),
    "planning": (
        "You are in PLANNING mode. Be structured and ordered. "
        "Break work into phases, dependencies, and execution steps. "
        "Optimize for the most reliable path forward."
    ),
    "writing": (
        "You are in WRITING mode. Preserve the user's voice. "
        "Keep phrasing natural, non-generic, and human. "
        "Favor clarity, rhythm, and intention."
    ),
    "analysis": (
        "You are in ANALYSIS mode. Focus on careful reasoning, tradeoffs, evidence from the prompt, "
        "and concise explanation of what is happening and why."
    ),
    "general": (
        "You are in GENERAL mode. Be direct, helpful, grounded, and concise."
    ),
}


def base_system_prompt() -> str:
    return (
        "You are Nova, a fast local AI workspace assistant. "
        "Be direct, useful, and execution-focused. "
        "Preserve working behavior unless the user explicitly asks to change it. "
        "When the user is working on code, prioritize concrete implementation over vague advice."
    )


def detect_intent_signals(user_text: str, attachments: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = (user_text or "").strip()
    lowered = text.lower()

    has_url = bool(is_probable_url_only(text) or extract_first_url(text))
    has_image_attachment = any((att.get("mime_type") or "").startswith("image/") for att in attachments)
    has_video_attachment = any((att.get("mime_type") or "").startswith("video/") for att in attachments)
    starts_image_command = lowered.startswith("/image")
    starts_web_command = lowered.startswith("/web ")

    return {
        "has_url": has_url,
        "has_image_attachment": has_image_attachment,
        "has_video_attachment": has_video_attachment,
        "starts_image_command": starts_image_command,
        "starts_web_command": starts_web_command,
    }


def route_request(user_text: str, attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    text = (user_text or "").strip()
    lowered = text.lower()
    attachment_list = attachments or []
    signals = detect_intent_signals(text, attachment_list)

    scores: Dict[str, int] = {
        "general": 0,
        "coding": 0,
        "planning": 0,
        "writing": 0,
        "analysis": 0,
    }

    matched_keywords: Dict[str, List[str]] = {
        "coding": [],
        "planning": [],
        "writing": [],
        "analysis": [],
    }

    for mode, keywords in MODE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[mode] += 2
                matched_keywords[mode].append(keyword)

    if attachment_list:
        scores["analysis"] += 1

    if signals["has_image_attachment"]:
        scores["analysis"] += 2

    if signals["has_video_attachment"]:
        scores["analysis"] += 2

    if signals["starts_image_command"]:
        return {
            "mode": "general",
            "reason": "image command",
            "matched_keywords": [],
            "scores": scores,
            "signals": signals,
        }

    if signals["starts_web_command"] or signals["has_url"]:
        return {
            "mode": "general",
            "reason": "web route detected",
            "matched_keywords": [],
            "scores": scores,
            "signals": signals,
        }

    mode = max(scores.keys(), key=lambda key: scores[key])
    if scores.get(mode, 0) <= 0:
        mode = "general"

    if mode == "general":
        reason = "default general route"
    else:
        found = matched_keywords.get(mode, [])
        reason = f"matched {mode} keywords" if found else f"{mode} score won"

    return {
        "mode": mode,
        "reason": reason,
        "matched_keywords": matched_keywords.get(mode, []),
        "scores": scores,
        "signals": signals,
    }


def mode_instruction_for(mode: str) -> str:
    return MODE_INSTRUCTIONS.get(mode or "general", MODE_INSTRUCTIONS["general"])


def build_route_meta(route: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "mode": route.get("mode", "general"),
        "reason": route.get("reason", "default"),
        "matched_keywords": ensure_list(route.get("matched_keywords")),
        "scores": route.get("scores", {}),
        "signals": route.get("signals", {}),
        "build": ROUTE_BUILD,
        "timestamp": utc_now(),
    }


# --------------------------------------------------
# model helpers
# --------------------------------------------------
def build_response_input(
    session: Dict[str, Any],
    user_text: str,
    attachments: List[Dict[str, Any]],
    mode: str,
) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = [
        {"role": "system", "content": base_system_prompt()},
        {"role": "system", "content": mode_instruction_for(mode)},
    ]

    history = ensure_list(session.get("messages"))
    for msg in history[-16:]:
        if not isinstance(msg, dict):
            continue
        role = "assistant" if msg.get("role") == "assistant" else "user"
        content = msg.get("content") or ""
        if content:
            payload.append({"role": role, "content": content})

    user_blocks: List[Dict[str, Any]] = [{"type": "input_text", "text": user_text or ""}]
    for att in attachments:
        block = attachment_to_input_block(att)
        if block:
            user_blocks.append(block)

    payload.append({"role": "user", "content": user_blocks})
    return payload


def call_chat_model(
    session: Dict[str, Any],
    user_text: str,
    attachments: List[Dict[str, Any]],
    mode: str,
) -> str:
    if not client:
        return (
            "Nova is live, but no OpenAI API key is configured on the backend yet. "
            "Set OPENAI_API_KEY and retry."
        )

    model_name = VISION_MODEL if any((att.get("mime_type") or "").startswith("image/") for att in attachments) else CHAT_MODEL
    input_payload = build_response_input(session, user_text, attachments, mode)

    try:
        response = client.responses.create(
            model=model_name,
            input=input_payload,
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()

        fragments: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    fragments.append(getattr(content, "text", ""))
        return "\n".join([part for part in fragments if part]).strip() or "No response text returned."
    except Exception as exc:
        return f"Model error: {exc}"


def generate_image(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    if not client:
        return None, "No OpenAI API key configured."

    try:
        result = client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
        )
        data = getattr(result, "data", None) or []
        if not data:
            return None, "No image data returned."

        first = data[0]
        b64 = getattr(first, "b64_json", None)
        if not b64:
            return None, "No image b64 returned."

        raw = base64.b64decode(b64)
        filename = f"generated_{uuid.uuid4().hex}.png"
        path = UPLOADS_DIR / filename
        path.write_bytes(raw)
        return f"/uploads/{filename}", None
    except Exception as exc:
        return None, str(exc)


# --------------------------------------------------
# memory helpers
# --------------------------------------------------
MEMORY_PATTERNS = [
    re.compile(r"\bremember that\b(.*)", re.I),
    re.compile(r"\bnote that\b(.*)", re.I),
    re.compile(r"\bfrom now on\b(.*)", re.I),
    re.compile(r"\bi prefer\b(.*)", re.I),
    re.compile(r"\bmy project is\b(.*)", re.I),
]


def maybe_store_memory(user_text: str, session_id: str) -> Optional[Dict[str, Any]]:
    text = (user_text or "").strip()
    if not text:
        return None

    for pattern in MEMORY_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        candidate = match.group(0).strip()
        if not candidate:
            continue

        item = {
            "id": new_id("memory"),
            "text": candidate,
            "kind": "note",
            "source": "assistant",
            "session_id": session_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "preview": truncate(candidate, 140),
        }
        memory = load_memory()
        memory.insert(0, item)
        save_memory(memory)
        return item

    return None


# --------------------------------------------------
# serializers / state
# --------------------------------------------------
def serialize_session(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": session.get("id"),
        "title": session.get("title", "New chat"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned")),
        "message_count": int(session.get("message_count", len(session.get("messages", [])))),
        "last_message_preview": session.get("last_message_preview", ""),
        "messages": ensure_list(session.get("messages")),
    }


def build_state_payload(active_session_id: Optional[str] = None) -> Dict[str, Any]:
    store = load_sessions_store()
    sessions = ensure_list(store.get("sessions"))
    current_id = active_session_id or store.get("active_session_id")

    if not current_id and sessions:
        current_id = sessions[0].get("id")

    active_session = find_session(store, current_id) if current_id else None
    artifacts = [serialize_artifact(item) for item in load_artifacts()]
    memory_items = load_memory()
    web_items = [item for item in artifacts if item.get("kind") in {"web_result", "web_fetch"}]

    return {
        "ok": True,
        "route_build": ROUTE_BUILD,
        "session_id": current_id or "",
        "active_session": serialize_session(active_session) if active_session else None,
        "sessions": [serialize_session(s) for s in sessions],
        "messages": ensure_list(active_session.get("messages")) if active_session else [],
        "artifacts": artifacts,
        "memory": memory_items,
        "memoryItems": memory_items,
        "web": web_items,
        "webItems": web_items,
        "models": {
            "chat_model": CHAT_MODEL,
            "vision_model": VISION_MODEL,
            "image_model": IMAGE_MODEL,
        },
    }


# --------------------------------------------------
# routes
# --------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/uploads/<path:filename>")
def uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.get("/api/health")
def api_health():
    return jsonify(
        {
            "ok": True,
            "status": "healthy",
            "time": utc_now(),
            "route_build": ROUTE_BUILD,
            "openai_configured": bool(client),
            "openai_model": CHAT_MODEL,
            "chat_model": CHAT_MODEL,
            "vision_model": VISION_MODEL,
            "image_model": IMAGE_MODEL,
            "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        }
    )


@app.get("/api/state")
def api_state():
    return jsonify(build_state_payload())


@app.get("/api/sessions")
def api_sessions():
    store = load_sessions_store()
    return jsonify(
        {
            "ok": True,
            "sessions": [serialize_session(s) for s in ensure_list(store.get("sessions"))],
            "active_session_id": store.get("active_session_id"),
        }
    )


@app.post("/api/session/new")
def api_session_new():
    data = parse_json_body()
    title = (data.get("title") or "New chat").strip() or "New chat"

    store = load_sessions_store()
    session = make_session(title)
    store["sessions"].insert(0, session)
    store["active_session_id"] = session["id"]
    save_sessions_store(store)

    return jsonify(
        {
            "ok": True,
            "session_id": session["id"],
            "session": serialize_session(session),
            **build_state_payload(session["id"]),
        }
    )


@app.post("/api/session/switch")
def api_session_switch():
    data = parse_json_body()
    session_id = (data.get("session_id") or "").strip()

    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404

    store["active_session_id"] = session_id
    save_sessions_store(store)
    return jsonify({"ok": True, **build_state_payload(session_id)})


@app.post("/api/session/rename")
def api_session_rename():
    data = parse_json_body()
    session_id = (data.get("session_id") or "").strip()
    title = (data.get("title") or "").strip()

    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404

    if title:
        session["title"] = title
        session["updated_at"] = utc_now()
        save_sessions_store(store)

    return jsonify({"ok": True, **build_state_payload(session_id)})


@app.post("/api/session/pin")
def api_session_pin():
    data = parse_json_body()
    session_id = (data.get("session_id") or "").strip()

    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404

    session["pinned"] = not bool(session.get("pinned"))
    session["updated_at"] = utc_now()
    save_sessions_store(store)

    return jsonify({"ok": True, **build_state_payload(session_id)})


@app.post("/api/session/delete")
def api_session_delete():
    data = parse_json_body()
    session_id = (data.get("session_id") or "").strip()

    store = load_sessions_store()
    sessions = ensure_list(store.get("sessions"))
    remaining = [s for s in sessions if s.get("id") != session_id]

    if len(remaining) == len(sessions):
        return jsonify({"ok": False, "error": "Session not found"}), 404

    store["sessions"] = remaining
    next_session_id = store.get("active_session_id")

    if next_session_id == session_id:
        next_session_id = choose_fallback_session_id(store)

    if not next_session_id and not remaining:
        new_session = make_session("New chat")
        remaining.insert(0, new_session)
        next_session_id = new_session["id"]

    store["active_session_id"] = next_session_id
    save_sessions_store(store)

    return jsonify({"ok": True, "next_session_id": next_session_id, **build_state_payload(next_session_id)})


@app.post("/api/upload")
def api_upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    file_storage = request.files["file"]
    if not file_storage or not file_storage.filename:
        return jsonify({"ok": False, "error": "Invalid file"}), 400

    saved = save_uploaded_file(file_storage)
    return jsonify({"ok": True, "upload": saved})


@app.get("/api/memory")
def api_memory():
    items = load_memory()
    return jsonify({"ok": True, "items": items, "memory_count": len(items)})


@app.post("/api/memory/create")
def api_memory_create():
    data = parse_json_body()
    text = (data.get("text") or "").strip()
    kind = (data.get("kind") or "note").strip() or "note"
    session_id = (data.get("session_id") or "").strip()

    if not text:
        return jsonify({"ok": False, "error": "Missing text"}), 400

    item = {
        "id": new_id("memory"),
        "text": text,
        "kind": kind,
        "source": "manual",
        "session_id": session_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "preview": truncate(text, 140),
    }

    items = load_memory()
    items.insert(0, item)
    save_memory(items)

    return jsonify({"ok": True, "item": item, **build_state_payload(session_id or get_active_session_id())})


@app.post("/api/memory/delete")
def api_memory_delete():
    data = parse_json_body()
    memory_id = (data.get("id") or "").strip()
    session_id = (data.get("session_id") or "").strip()

    items = load_memory()
    next_items = [item for item in items if item.get("id") != memory_id]

    if len(next_items) == len(items):
        return jsonify({"ok": False, "error": "Memory item not found"}), 404

    save_memory(next_items)
    return jsonify({"ok": True, **build_state_payload(session_id or get_active_session_id())})


@app.get("/api/artifacts")
def api_artifacts():
    return jsonify({"ok": True, "artifacts": [serialize_artifact(item) for item in load_artifacts()]})


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_read(artifact_id: str):
    for item in load_artifacts():
        if item.get("id") == artifact_id:
            return jsonify({"ok": True, "artifact": serialize_artifact(item)})
    return jsonify({"ok": False, "error": "Artifact not found"}), 404


@app.post("/api/web/fetch")
def api_web_fetch():
    data = parse_json_body()
    session_id = (data.get("session_id") or get_active_session_id() or "").strip()
    url = normalize_url(data.get("url") or data.get("text") or "")

    if not url:
        return jsonify({"ok": False, "error": "Missing URL"}), 400

    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        session = make_session("New chat")
        store["sessions"].insert(0, session)
        store["active_session_id"] = session["id"]
        session_id = session["id"]

    route_meta = build_route_meta(
        {
            "mode": "general",
            "reason": "explicit web fetch",
            "matched_keywords": [],
            "scores": {},
            "signals": {"starts_web_command": True},
        }
    )

    result = fetch_web_page(url)

    append_message(
        session,
        "user",
        url,
        meta={"route": route_meta},
    )

    assistant_text = result.get("summary") or result.get("preview") or result.get("title") or url
    assistant_msg = append_message(
        session,
        "assistant",
        assistant_text,
        meta={
            "route": route_meta,
            "web_result": result,
        },
    )

    artifact = create_artifact(
        session_id=session_id,
        kind="web_result",
        title=result.get("title") or "Web result",
        body=assistant_text,
        preview=result.get("preview") or truncate(assistant_text, 180),
        meta={
            "source_url": result.get("url"),
            "bullets": [result.get("description")] if result.get("description") else [],
            "route": route_meta,
        },
        viewer={
            "kind": "web_result",
            "title": result.get("title") or "Web result",
            "body": assistant_text,
            "source_url": result.get("url"),
            "bullets": [result.get("description")] if result.get("description") else [],
        },
    )

    save_sessions_store(store)

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "assistant_message": assistant_msg,
            "artifact": serialize_artifact(artifact),
            "web_result": result,
            "debug": {"route": route_meta},
            **build_state_payload(session_id),
        }
    )


@app.post("/api/chat")
def api_chat():
    try:
        data = parse_json_body()
        session_id = (data.get("session_id") or get_active_session_id() or "").strip()
        user_text = (data.get("message") or data.get("text") or data.get("user_text") or "").strip()
        attachments = ensure_list(data.get("attachments"))

        if not user_text and not attachments:
            return jsonify({"ok": False, "error": "Missing message"}), 400

        store = load_sessions_store()
        session = find_session(store, session_id)

        if not session:
            session = make_session("New chat")
            store["sessions"].insert(0, session)
            store["active_session_id"] = session["id"]
            session_id = session["id"]

        route = route_request(user_text, attachments)
        route_meta = build_route_meta(route)

        user_msg = append_message(
            session,
            "user",
            user_text,
            attachments=attachments,
            meta={"route": route_meta},
        )

        lowered = user_text.lower()

        # /image
        if lowered.startswith("/image"):
            prompt = user_text[len("/image"):].strip() or "Generate an image."
            image_url, image_error = generate_image(prompt)

            if image_error:
                assistant_text = f"Image generation failed: {image_error}"
                assistant_msg = append_message(
                    session,
                    "assistant",
                    assistant_text,
                    meta={"route": route_meta, "image_error": image_error},
                )
                save_sessions_store(store)
                return jsonify(
                    {
                        "ok": True,
                        "session_id": session_id,
                        "assistant_message": assistant_msg,
                        "debug": {"route": route_meta},
                        **build_state_payload(session_id),
                    }
                )

            generated_attachment = {
                "id": new_id("generated"),
                "name": Path(image_url).name,
                "filename": Path(image_url).name,
                "url": image_url,
                "mime_type": "image/png",
                "kind": "image",
                "created_at": utc_now(),
            }

            assistant_text = f"Generated image for: {prompt}"
            assistant_msg = append_message(
                session,
                "assistant",
                assistant_text,
                attachments=[generated_attachment],
                meta={"route": route_meta, "image_url": image_url, "prompt": prompt},
            )

            artifact = create_artifact(
                session_id=session_id,
                kind="image_generation",
                title="Generated image",
                body=assistant_text,
                preview=truncate(prompt, 180),
                meta={
                    "image_url": image_url,
                    "prompt": prompt,
                    "route": route_meta,
                },
                viewer={
                    "kind": "image_generation",
                    "title": "Generated image",
                    "body": assistant_text,
                    "image_url": image_url,
                    "bullets": [prompt],
                },
            )

            maybe_store_memory(user_text, session_id)
            save_sessions_store(store)

            return jsonify(
                {
                    "ok": True,
                    "session_id": session_id,
                    "assistant_message": assistant_msg,
                    "artifact": serialize_artifact(artifact),
                    "debug": {"route": route_meta},
                    **build_state_payload(session_id),
                }
            )

        # /web or raw url auto-route
        detected_url = extract_first_url(user_text)
        if lowered.startswith("/web ") or is_probable_url_only(user_text) or detected_url:
            url = normalize_url(user_text[5:].strip() if lowered.startswith("/web ") else (detected_url or user_text))
            result = fetch_web_page(url)

            assistant_text = result.get("summary") or result.get("preview") or result.get("title") or url
            assistant_msg = append_message(
                session,
                "assistant",
                assistant_text,
                meta={
                    "route": route_meta,
                    "web_result": result,
                },
            )

            artifact = create_artifact(
                session_id=session_id,
                kind="web_result",
                title=result.get("title") or "Web result",
                body=assistant_text,
                preview=result.get("preview") or truncate(assistant_text, 180),
                meta={
                    "source_url": result.get("url"),
                    "bullets": [result.get("description")] if result.get("description") else [],
                    "route": route_meta,
                },
                viewer={
                    "kind": "web_result",
                    "title": result.get("title") or "Web result",
                    "body": assistant_text,
                    "source_url": result.get("url"),
                    "bullets": [result.get("description")] if result.get("description") else [],
                },
            )

            maybe_store_memory(user_text, session_id)
            save_sessions_store(store)

            return jsonify(
                {
                    "ok": True,
                    "session_id": session_id,
                    "assistant_message": assistant_msg,
                    "artifact": serialize_artifact(artifact),
                    "web_result": result,
                    "debug": {"route": route_meta},
                    **build_state_payload(session_id),
                }
            )

        # image analysis
        has_image_attachment = any((att.get("mime_type") or "").startswith("image/") for att in attachments)
        if has_image_attachment:
            assistant_text = call_chat_model(session, user_text or "Describe this image.", attachments, "analysis")

            assistant_msg = append_message(
                session,
                "assistant",
                assistant_text,
                meta={
                    "route": route_meta,
                    "analysis_type": "image",
                },
            )

            artifact = create_artifact(
                session_id=session_id,
                kind="image_analysis",
                title="Image analysis",
                body=assistant_text,
                preview=truncate(assistant_text, 180),
                meta={
                    "analysis_text": assistant_text,
                    "image_url": attachments[0].get("url") if attachments else None,
                    "route": route_meta,
                },
                viewer={
                    "kind": "image_analysis",
                    "title": "Image analysis",
                    "body": assistant_text,
                    "image_url": attachments[0].get("url") if attachments else None,
                    "analysis_text": assistant_text,
                },
            )

            maybe_store_memory(user_text, session_id)
            save_sessions_store(store)

            return jsonify(
                {
                    "ok": True,
                    "session_id": session_id,
                    "assistant_message": assistant_msg,
                    "artifact": serialize_artifact(artifact),
                    "debug": {"route": route_meta},
                    **build_state_payload(session_id),
                }
            )

        # normal chat with mode instruction
        assistant_text = call_chat_model(session, user_text, attachments, route_meta["mode"])

        assistant_msg = append_message(
            session,
            "assistant",
            assistant_text,
            meta={"route": route_meta},
        )

        artifact = create_artifact(
            session_id=session_id,
            kind="chat_reply",
            title="Chat reply",
            body=assistant_text,
            preview=truncate(assistant_text, 180),
            meta={"route": route_meta},
            viewer={
                "kind": "chat_reply",
                "title": "Chat reply",
                "body": assistant_text,
            },
        )

        maybe_store_memory(user_text, session_id)
        save_sessions_store(store)

        return jsonify(
            {
                "ok": True,
                "session_id": session_id,
                "assistant_message": assistant_msg,
                "artifact": serialize_artifact(artifact),
                "debug": {
                    "route": route_meta,
                    "user_message_id": user_msg.get("id"),
                },
                **build_state_payload(session_id),
            }
        )

    except Exception as exc:
        return jsonify(
            {
                "ok": False,
                "error": str(exc),
                "trace": traceback.format_exc(),
                "route_build": ROUTE_BUILD,
            }
        ), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)