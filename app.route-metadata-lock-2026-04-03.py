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
from flask import Flask, jsonify, render_template, request, send_from_directory

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


def normalize_session_message(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return None

    role = safe_str(message.get("role") or message.get("sender") or "assistant").lower()
    content = safe_str(message.get("content") or message.get("text") or message.get("message") or "")
    created_at = safe_str(message.get("created_at") or message.get("timestamp") or now_iso())
    attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []

    return {
        "id": safe_str(message.get("id") or uuid.uuid4().hex[:8]),
        "role": role or "assistant",
        "content": content,
        "created_at": created_at,
        "attachments": attachments,
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

    image_url = safe_str(
        item.get("image_url")
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

    return {
        "id": artifact_id,
        "artifact_id": artifact_id,
        "session_id": safe_str(item.get("session_id")),
        "kind": safe_str(item.get("kind") or item.get("type") or "artifact"),
        "title": safe_str(item.get("title") or item.get("name") or item.get("kind") or "Untitled artifact"),
        "content": safe_str(item.get("content") or item.get("text") or item.get("body") or item.get("preview") or ""),
        "summary": safe_str(item.get("summary") or meta.get("summary") or ""),
        "preview": safe_str(item.get("preview") or item.get("content") or item.get("summary") or "")[:220],
        "pinned": bool(item.get("pinned", False)),
        "created_at": safe_str(item.get("created_at") or now_iso()),
        "updated_at": safe_str(item.get("updated_at") or item.get("created_at") or now_iso()),
        "meta": meta,
        "web": web,
        "debug": debug,
        "extra": extra,
        "image_url": image_url,
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
        "web_items": [a for a in artifacts if safe_str(a.get("kind")) in {"web", "web_result"}],
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
) -> dict[str, Any]:
    payload = load_artifacts_payload()
    ts = now_iso()

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
        "image_url": safe_str(image_url),
    }
    artifact["artifact_id"] = artifact["id"]

    items = payload["artifacts"]
    items.insert(0, artifact)
    save_artifacts_payload({"artifacts": items})
    return artifact


def call_model(messages: list[dict[str, str]]) -> str:
    if not client:
        return "Nova fallback reply: backend is live, but no OpenAI key is configured."

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=messages,
        )
        text = getattr(response, "output_text", "") or ""
        return safe_str(text) or "Nova returned an empty response."
    except Exception as exc:
        return f"Nova fallback reply: model call failed. {exc}"


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
        "kind": "web",
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
        route_build="REAL-APP-PY-MEMORY-MANAGER-LOCK-2026-04-03-005",
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


@app.route("/api/chat", methods=["POST"])
def api_chat():
    ensure_storage()
    data = request.get_json(silent=True) or {}

    content = safe_str(data.get("content") or data.get("message") or data.get("text"))
    session_id = safe_str(data.get("session_id"))
    attachments = data.get("attachments") if isinstance(data.get("attachments"), list) else []

    if not content and not attachments:
        return _error("Missing content.", status=400)

    try:
        sessions_payload = load_sessions_payload()

        session = None
        if session_id:
            session = next((s for s in sessions_payload["sessions"] if safe_str(s.get("id")) == session_id), None)

        if session is None:
            session = create_session()
            session_id = session["id"]

        user_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": content,
            "created_at": now_iso(),
            "attachments": attachments,
        }
        session["messages"].append(user_message)

        route = "chat"
        stripped = content.strip()
        lowered = stripped.lower()
        explicit_web = lowered.startswith("/web ")
        explicit_image = lowered.startswith("/image ")
        detected_url = extract_first_url(stripped)

        if explicit_web or detected_url:
            route = "web"
            target_url = normalize_url(stripped[5:].strip()) if explicit_web else detected_url
            web_result = fetch_web_result(target_url)
            assistant_text = build_web_assistant_text(web_result)

            assistant_message = {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant",
                "content": assistant_text,
                "created_at": now_iso(),
                "attachments": [],
            }
            session["messages"].append(assistant_message)

            if not safe_str(session.get("title")) or safe_str(session.get("title")) == "New Chat":
                first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
                if first_user:
                    session["title"] = first_user["content"][:48].rstrip() or "New Chat"

            session["updated_at"] = now_iso()
            session["message_count"] = len(session["messages"])
            session["last_message_preview"] = assistant_text[:160] or content[:160]
            upsert_session(session)

            add_artifact(
                session_id=session_id,
                kind="web",
                title=web_result["title"],
                content=web_result["content"],
                meta={
                    "summary": web_result["summary"],
                    "preview": web_result["preview"],
                    "title": web_result["title"],
                    "source_url": safe_str(web_result["web"].get("source_url")),
                    "domain": safe_str(web_result["web"].get("domain")),
                    "site_name": safe_str(web_result["web"].get("site_name")),
                    "body": safe_str(web_result["web"].get("body")),
                    "bullets": web_result["web"].get("bullets", []),
                },
                web=web_result["web"],
                debug=web_result["debug"],
            )

            payload = build_state(session_id=session_id)
            payload["message"] = assistant_text
            payload["assistant_message"] = assistant_text
            payload["session"] = {
                "id": session_id,
                "title": session["title"],
                "messages": session["messages"],
            }
            payload["debug"] = {
                "model": OPENAI_MODEL,
                "openai_configured": bool(client),
                "attachment_count": len(attachments),
                "route": route,
            }
            return jsonify(payload)

        if explicit_image:
            route = "image"
            prompt = safe_str(stripped[7:].strip())
            if not prompt:
                return _error("Missing image prompt.", status=400)

            image_result = generate_image(prompt)
            image_url = safe_str(image_result["image_url"])
            assistant_text = f"![generated image]({image_url})\n\nGenerated from prompt: {prompt}"

            assistant_message = {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant",
                "content": assistant_text,
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
            }
            session["messages"].append(assistant_message)

            if not safe_str(session.get("title")) or safe_str(session.get("title")) == "New Chat":
                first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
                if first_user:
                    session["title"] = first_user["content"][:48].rstrip() or "New Chat"

            session["updated_at"] = now_iso()
            session["message_count"] = len(session["messages"])
            session["last_message_preview"] = f"Generated image: {prompt[:120]}"
            upsert_session(session)

            add_artifact(
                session_id=session_id,
                kind="generated_image",
                title=f"Generated Image - {prompt[:80]}",
                content=assistant_text,
                meta={
                    "prompt": prompt,
                    "image_url": image_url,
                    "preview": f"Generated from prompt: {prompt}"[:220],
                    "summary": f"Generated from prompt: {prompt}"[:220],
                    "media": [
                        {
                            "filename": Path(image_url).name,
                            "mime_type": "image/png",
                            "prompt": prompt,
                            "type": "image",
                            "url": image_url,
                        }
                    ],
                },
                debug={
                    "source": "api_chat",
                    "route": route,
                    "image_model": IMAGE_MODEL,
                },
                extra={
                    "image_url": image_url,
                    "prompt": prompt,
                    "media": [
                        {
                            "filename": Path(image_url).name,
                            "mime_type": "image/png",
                            "prompt": prompt,
                            "type": "image",
                            "url": image_url,
                        }
                    ],
                },
                image_url=image_url,
            )

            payload = build_state(session_id=session_id)
            payload["message"] = assistant_text
            payload["assistant_message"] = assistant_text
            payload["session"] = {
                "id": session_id,
                "title": session["title"],
                "messages": session["messages"],
            }
            payload["debug"] = {
                "model": OPENAI_MODEL,
                "openai_configured": bool(client),
                "attachment_count": len(attachments),
                "route": route,
                "image_model": IMAGE_MODEL,
            }
            return jsonify(payload)

        model_messages = []
        for msg in session["messages"][-12:]:
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

        assistant_text = call_model(model_messages)

        assistant_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
            "attachments": [],
        }
        session["messages"].append(assistant_message)

        if not safe_str(session.get("title")) or safe_str(session.get("title")) == "New Chat":
            first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
            if first_user:
                session["title"] = first_user["content"][:48].rstrip() or "New Chat"

        session["updated_at"] = now_iso()
        session["message_count"] = len(session["messages"])
        session["last_message_preview"] = assistant_text[:160] or content[:160]
        upsert_session(session)

        add_artifact(
            session_id=session_id,
            kind="chat",
            title=session["title"],
            content=assistant_text,
            meta={"message_count": session["message_count"]},
            debug={"source": "api_chat", "route": route},
        )

        payload = build_state(session_id=session_id)
        payload["message"] = assistant_text
        payload["assistant_message"] = assistant_text
        payload["session"] = {
            "id": session_id,
            "title": session["title"],
            "messages": session["messages"],
        }
        payload["debug"] = {
            "model": OPENAI_MODEL,
            "openai_configured": bool(client),
            "attachment_count": len(attachments),
            "route": route,
        }
        return jsonify(payload)
    except Exception as exc:
        return _error(f"Chat failed: {exc}", status=500)


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
                found = item
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
        return _ok(message="Artifact deleted.", next_artifact_id=next_artifact_id, artifacts=items)
    except Exception as exc:
        return _error(f"Artifact delete failed: {exc}", status=500)


if __name__ == "__main__":
    ensure_storage()
    host = os.getenv("APP_HOST") or os.getenv("NOVA_HOST") or "127.0.0.1"
    port = int(os.getenv("APP_PORT") or os.getenv("NOVA_PORT") or "5001")
    debug = safe_str(os.getenv("NOVA_DEBUG", "1")).lower() not in {"0", "false", "no"}
    app.run(host=host, port=port, debug=debug)