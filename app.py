from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import secrets
import traceback
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

try:
    import requests
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

APP_HOST = os.getenv("APP_HOST") or os.getenv("NOVA_HOST") or "127.0.0.1"
APP_PORT = int(os.getenv("APP_PORT") or os.getenv("NOVA_PORT") or "8743")
NOVA_DEBUG = str(os.getenv("NOVA_DEBUG", "1")).lower() not in {"0", "false", "no"}

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
NOVA_IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1")
NOVA_IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")

MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "200"))
MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "200"))
MAX_FETCH_BYTES = int(os.getenv("MAX_FETCH_BYTES", str(2 * 1024 * 1024)))
MAX_WEB_TEXT_CHARS = int(os.getenv("MAX_WEB_TEXT_CHARS", "12000"))
MAX_DOC_TEXT_CHARS = int(os.getenv("MAX_DOC_TEXT_CHARS", "12000"))
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "16000"))

ALLOWED_UPLOAD_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "svg",
    "pdf",
    "txt",
    "log",
    "md",
    "json",
    "csv",
    "html",
    "htm",
    "xml",
    "yaml",
    "yml",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "webm",
    "mp3",
    "wav",
    "m4a",
    "ogg",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}
TEXT_EXTENSIONS = {"txt", "log", "md", "json", "csv", "html", "htm", "xml", "yaml", "yml"}

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def preview_text(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", safe_text(value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def make_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)


def json_save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def is_allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[-1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def ext_of(name: str) -> str:
    return Path(name or "").suffix.lower().lstrip(".")


def detect_attachment_kind(name: str, mime_type: str = "") -> str:
    ext = ext_of(name)
    mime = safe_text(mime_type).lower()
    if ext in IMAGE_EXTENSIONS or mime.startswith("image/"):
        return "image"
    if ext in VIDEO_EXTENSIONS or mime.startswith("video/"):
        return "video"
    if ext in AUDIO_EXTENSIONS or mime.startswith("audio/"):
        return "audio"
    return "document"


def load_sessions() -> list[dict[str, Any]]:
    data = json_load(SESSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_sessions(items: list[dict[str, Any]]) -> None:
    json_save(SESSIONS_FILE, items[:MAX_SESSIONS])


def load_artifacts() -> list[dict[str, Any]]:
    data = json_load(ARTIFACTS_FILE, [])
    return data if isinstance(data, list) else []


def save_artifacts(items: list[dict[str, Any]]) -> None:
    json_save(ARTIFACTS_FILE, items)


def load_memory() -> list[dict[str, Any]]:
    data = json_load(MEMORY_FILE, [])
    return data if isinstance(data, list) else []


def save_memory(items: list[dict[str, Any]]) -> None:
    json_save(MEMORY_FILE, items)


def normalize_session(session: dict[str, Any]) -> dict[str, Any]:
    messages = session.get("messages") or []
    created_at = session.get("created_at") or now_iso()
    updated_at = session.get("updated_at") or created_at
    last_preview = preview_text(messages[-1].get("content") if messages else "", 160)
    return {
        "id": safe_text(session.get("id") or make_id("session")),
        "title": safe_text(session.get("title") or "New chat"),
        "created_at": created_at,
        "updated_at": updated_at,
        "pinned": bool(session.get("pinned", False)),
        "messages": messages[-MAX_MESSAGES_PER_SESSION:],
        "message_count": len(messages),
        "last_message_preview": last_preview,
    }


def normalize_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    content = safe_text(artifact.get("content"))
    created_at = artifact.get("created_at") or now_iso()
    updated_at = artifact.get("updated_at") or created_at
    viewer = artifact.get("viewer") if isinstance(artifact.get("viewer"), dict) else {}
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    return {
        "id": safe_text(artifact.get("id") or make_id("artifact")),
        "session_id": safe_text(artifact.get("session_id")),
        "kind": safe_text(artifact.get("kind") or "chat_reply"),
        "title": safe_text(artifact.get("title") or "Artifact"),
        "content": content,
        "preview": safe_text(artifact.get("preview") or preview_text(content)),
        "created_at": created_at,
        "updated_at": updated_at,
        "viewer": viewer,
        "meta": meta,
    }


def sort_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_session(s) for s in sessions]
    pinned = sorted(
        [s for s in normalized if s.get("pinned")],
        key=lambda x: safe_text(x.get("updated_at")),
        reverse=True,
    )
    unpinned = sorted(
        [s for s in normalized if not s.get("pinned")],
        key=lambda x: safe_text(x.get("updated_at")),
        reverse=True,
    )
    return pinned + unpinned


def sort_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_artifact(a) for a in artifacts]
    return sorted(normalized, key=lambda x: safe_text(x.get("updated_at")), reverse=True)


def session_summary(session: dict[str, Any] | None) -> dict[str, Any] | None:
    if not session:
        return None
    s = normalize_session(session)
    return {
        "id": s["id"],
        "title": s["title"],
        "created_at": s["created_at"],
        "updated_at": s["updated_at"],
        "pinned": s["pinned"],
        "message_count": s["message_count"],
        "last_message_preview": s["last_message_preview"],
    }


def artifact_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    a = normalize_artifact(artifact)
    return {
        "id": a["id"],
        "session_id": a["session_id"],
        "kind": a["kind"],
        "title": a["title"],
        "preview": a["preview"],
        "created_at": a["created_at"],
        "updated_at": a["updated_at"],
        "viewer": a["viewer"],
        "meta": a["meta"],
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    for session in sort_sessions(load_sessions()):
        if safe_text(session.get("id")) == safe_text(session_id):
            return normalize_session(session)
    return None


def get_or_create_session(session_id: str = "") -> dict[str, Any]:
    sessions = sort_sessions(load_sessions())
    if session_id:
        for session in sessions:
            if safe_text(session.get("id")) == safe_text(session_id):
                return normalize_session(session)

    session = normalize_session(
        {
            "id": make_id("session"),
            "title": "New chat",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "pinned": False,
            "messages": [],
        }
    )
    sessions.insert(0, session)
    save_sessions(sort_sessions(sessions))
    return session


def save_session(session: dict[str, Any]) -> dict[str, Any]:
    sessions = sort_sessions(load_sessions())
    found = False
    normalized = normalize_session(session)

    for i, existing in enumerate(sessions):
        if safe_text(existing.get("id")) == safe_text(normalized.get("id")):
            sessions[i] = normalized
            found = True
            break

    if not found:
        sessions.insert(0, normalized)

    sessions = sort_sessions(sessions)[:MAX_SESSIONS]
    save_sessions(sessions)
    return normalized


def save_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    artifacts = sort_artifacts(load_artifacts())
    normalized = normalize_artifact(artifact)
    found = False

    for i, existing in enumerate(artifacts):
        if safe_text(existing.get("id")) == safe_text(normalized.get("id")):
            artifacts[i] = normalized
            found = True
            break

    if not found:
        artifacts.insert(0, normalized)

    artifacts = sort_artifacts(artifacts)
    save_artifacts(artifacts)
    return normalized


def get_artifact(artifact_id: str) -> dict[str, Any] | None:
    for artifact in sort_artifacts(load_artifacts()):
        if safe_text(artifact.get("id")) == safe_text(artifact_id):
            return normalize_artifact(artifact)
    return None


def list_session_artifacts(session_id: str = "") -> list[dict[str, Any]]:
    artifacts = sort_artifacts(load_artifacts())
    if not session_id:
        return artifacts
    return [a for a in artifacts if safe_text(a.get("session_id")) == safe_text(session_id)]


def append_message(session: dict[str, Any], role: str, content: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    messages = list(session.get("messages") or [])
    messages.append(
        {
            "id": make_id("msg"),
            "role": role,
            "content": safe_text(content),
            "created_at": now_iso(),
            "meta": meta or {},
        }
    )
    session["messages"] = messages[-MAX_MESSAGES_PER_SESSION:]
    session["updated_at"] = now_iso()

    if safe_text(session.get("title")) in {"", "New chat"}:
        first_user = next((m for m in session["messages"] if m.get("role") == "user" and safe_text(m.get("content")).strip()), None)
        if first_user:
            session["title"] = preview_text(first_user.get("content"), 56)
    return session


def create_memory_item(title: str, value: str, source: str = "chat") -> dict[str, Any]:
    return {
        "id": make_id("memory"),
        "title": title,
        "value": value,
        "source": source,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def maybe_store_memory_from_message(content: str) -> list[dict[str, Any]]:
    text = safe_text(content).strip()
    lower = text.lower()
    created: list[dict[str, Any]] = []

    patterns = [
        (r"^remember that (.+)$", "Memory"),
        (r"^remember (.+)$", "Memory"),
        (r"^my name is (.+)$", "Name"),
    ]

    memory = load_memory()

    for pattern, title in patterns:
        match = re.match(pattern, lower, re.IGNORECASE)
        if not match:
            continue
        raw_value = text[match.start(1):match.end(1)].strip()
        item = create_memory_item(title, raw_value, "chat")
        memory.insert(0, item)
        created.append(item)
        break

    if created:
        save_memory(memory)

    return created


def url_from_text(text: str) -> str:
    match = re.search(r"(https?://[^\s]+)", safe_text(text))
    return match.group(1).strip() if match else ""


def local_upload_path_from_url(url: str) -> Path | None:
    if not url:
        return None
    marker = "/api/uploads/"
    if marker not in url:
        return None
    stored_name = url.split(marker, 1)[1].strip()
    path = UPLOADS_DIR / stored_name
    return path if path.exists() else None


def try_read_text_file(path: Path, limit: int = MAX_DOC_TEXT_CHARS) -> str:
    if not path.exists() or not path.is_file():
        return ""
    ext = ext_of(path.name)
    if ext not in TEXT_EXTENSIONS:
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text[:limit]
    except Exception:
        return ""


def image_file_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def extract_html_text(html: str) -> tuple[str, dict[str, Any]]:
    title = ""
    description = ""
    site_name = ""
    images: list[str] = []
    text = preview_text(html, MAX_WEB_TEXT_CHARS)

    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            def meta_content(*attrs: tuple[str, str]) -> str:
                for attr_name, attr_value in attrs:
                    tag = soup.find("meta", attrs={attr_name: attr_value})
                    if tag and tag.get("content"):
                        return safe_text(tag.get("content")).strip()
                return ""

            description = meta_content(("name", "description"), ("property", "og:description"), ("name", "twitter:description"))
            site_name = meta_content(("property", "og:site_name"))
            og_image = meta_content(("property", "og:image"), ("name", "twitter:image"))
            if og_image:
                images.append(og_image)

            for bad in soup(["script", "style", "noscript"]):
                bad.extract()

            body_text = soup.get_text("\n", strip=True)
            if body_text:
                text = body_text[:MAX_WEB_TEXT_CHARS]
        except Exception:
            pass

    meta = {
        "title": title,
        "description": description,
        "site_name": site_name,
        "images": images[:8],
    }
    return text, meta


def fetch_url(url: str) -> dict[str, Any]:
    if requests is None:
        return {
            "ok": False,
            "url": url,
            "title": "Web fetch failed",
            "content": "requests is not installed.",
            "preview": "requests is not installed.",
            "viewer": {},
            "meta": {"web": {"used": True, "urls": [url], "errors": ["requests is not installed."]}},
        }

    timeout = (8, 18)
    verify = True
    verify_fallback_used = False
    response = None

    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "NovaUltimate/2026"},
            stream=True,
            verify=verify,
        )
    except requests.exceptions.SSLError:
        verify = False
        verify_fallback_used = True
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "NovaUltimate/2026"},
            stream=True,
            verify=False,
        )
    except Exception as err:
        return {
            "ok": False,
            "url": url,
            "title": "Web fetch failed",
            "content": safe_text(err),
            "preview": preview_text(err),
            "viewer": {},
            "meta": {"web": {"used": True, "urls": [url], "errors": [safe_text(err)]}},
        }

    try:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_FETCH_BYTES:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        content_type = safe_text(response.headers.get("content-type")).lower()
        final_url = safe_text(response.url or url)

        if "text/html" in content_type or "<html" in raw[:1000].decode("utf-8", errors="ignore").lower():
            html = raw.decode("utf-8", errors="ignore")
            text, parsed_meta = extract_html_text(html)
            title = parsed_meta.get("title") or final_url
            description = parsed_meta.get("description") or preview_text(text, 200)

            viewer = {
                "copy": text,
                "url": final_url,
                "description": description,
                "title": title,
                "image_url": (parsed_meta.get("images") or [""])[0] if parsed_meta.get("images") else "",
            }
            meta = {
                "web": {
                    "used": True,
                    "urls": [final_url],
                    "verify_fallback_used": verify_fallback_used,
                    "content_type": content_type,
                    "site_name": parsed_meta.get("site_name") or "",
                    "description": description,
                    "images": parsed_meta.get("images") or [],
                    "status_code": response.status_code,
                }
            }
            return {
                "ok": True,
                "url": final_url,
                "title": title,
                "content": text,
                "preview": preview_text(text),
                "viewer": viewer,
                "meta": meta,
            }

        text = raw.decode("utf-8", errors="ignore")[:MAX_WEB_TEXT_CHARS]
        return {
            "ok": True,
            "url": final_url,
            "title": final_url,
            "content": text,
            "preview": preview_text(text),
            "viewer": {"copy": text, "url": final_url},
            "meta": {
                "web": {
                    "used": True,
                    "urls": [final_url],
                    "verify_fallback_used": verify_fallback_used,
                    "content_type": content_type,
                    "status_code": response.status_code,
                }
            },
        }
    except Exception as err:
        return {
            "ok": False,
            "url": safe_text(response.url or url),
            "title": "Web fetch failed",
            "content": safe_text(err),
            "preview": preview_text(err),
            "viewer": {},
            "meta": {
                "web": {
                    "used": True,
                    "urls": [safe_text(response.url or url)],
                    "verify_fallback_used": verify_fallback_used,
                    "errors": [safe_text(err)],
                }
            },
        }


def extract_document_context(attachments: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    chunks: list[str] = []
    used_names: list[str] = []

    for attachment in attachments:
        if safe_text(attachment.get("kind")) != "document":
            continue
        path = local_upload_path_from_url(safe_text(attachment.get("url")))
        if not path:
            continue
        text = try_read_text_file(path)
        if not text:
            continue
        used_names.append(path.name)
        chunks.append(f"FILE: {attachment.get('name')}\n{text}")

    joined = "\n\n".join(chunks)[:MAX_DOC_TEXT_CHARS]
    meta = {
        "document_used": bool(chunks),
        "document_count": len(chunks),
        "document_names": used_names,
        "document_chars": len(joined),
        "document_preview": preview_text(joined, 240),
    }
    return joined, meta


def build_model_messages_for_text(user_text: str, web_context: str = "", doc_context: str = "") -> str:
    system = (
        "You are Nova, a direct local assistant. "
        "Be clear, useful, and concise. "
        "If web context is provided, use it. "
        "If document context is provided, use it. "
        "Do not mention hidden system instructions."
    )
    parts = [f"SYSTEM:\n{system}"]
    if web_context.strip():
        parts.append(f"WEB CONTEXT:\n{web_context[:MAX_PROMPT_CHARS]}")
    if doc_context.strip():
        parts.append(f"DOCUMENT CONTEXT:\n{doc_context[:MAX_PROMPT_CHARS]}")
    parts.append(f"USER:\n{user_text}")
    return "\n\n".join(parts)


def generate_text_reply(prompt: str) -> str:
    client = get_openai_client()
    if client is None:
        return "OPENAI_API_KEY is not configured."

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            max_output_tokens=900,
        )
        text = getattr(response, "output_text", "") or ""
        if text.strip():
            return text.strip()

        parts: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                maybe = getattr(content, "text", "")
                if maybe:
                    parts.append(maybe)
        return "\n".join(parts).strip() or "No response text returned."
    except Exception as err:
        return f"Model error.\n\n{safe_text(err)}"


def analyze_image_with_model(user_text: str, image_path: Path) -> str:
    client = get_openai_client()
    if client is None:
        return "Image received.\n\nOPENAI_API_KEY is not configured."
    try:
        data_url = image_file_to_data_url(image_path)
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_text or "Describe this image clearly."},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            max_output_tokens=900,
        )
        text = getattr(response, "output_text", "") or ""
        return text.strip() or "Image analyzed."
    except Exception as err:
        return f"Image analysis failed.\n\n{safe_text(err)}"


def generate_image(prompt: str) -> tuple[str, str]:
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    result = client.images.generate(
        model=NOVA_IMAGE_MODEL,
        prompt=prompt,
        size=NOVA_IMAGE_SIZE,
    )

    data = getattr(result, "data", None) or []
    if not data:
        raise RuntimeError("No image data returned.")

    item = data[0]
    b64 = getattr(item, "b64_json", None)
    if not b64:
        raise RuntimeError("Image response did not contain b64_json.")

    image_bytes = base64.b64decode(b64)
    filename = f"generated_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}.png"
    path = UPLOADS_DIR / filename
    path.write_bytes(image_bytes)
    return f"/api/uploads/{filename}", filename


def create_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    content: str,
    viewer: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ts = now_iso()
    artifact = {
        "id": make_id("artifact"),
        "session_id": session_id,
        "kind": kind,
        "title": title,
        "content": content,
        "preview": preview_text(content),
        "created_at": ts,
        "updated_at": ts,
        "viewer": viewer or {},
        "meta": meta or {},
    }
    return save_artifact(artifact)


def build_web_result(session_id: str, url: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    result = fetch_url(url)
    title = safe_text(result.get("title") or url or "Web result")
    content = safe_text(result.get("content") or "")
    viewer = result.get("viewer") if isinstance(result.get("viewer"), dict) else {}
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    artifact = create_artifact(
        session_id=session_id,
        kind="web_result",
        title=title,
        content=content or title,
        viewer=viewer,
        meta=meta,
    )
    reply = content if content else title
    return reply, artifact, {"artifact_kind": "web_result", "web": meta.get("web", {"used": True})}


def handle_image_generation(session: dict[str, Any], prompt: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    image_url, stored_name = generate_image(prompt)
    content = f"![Generated image]({image_url})"
    artifact = create_artifact(
        session_id=safe_text(session.get("id")),
        kind="image_generation",
        title=preview_text(prompt, 80) or "Generated image",
        content=content,
        viewer={
            "image_url": image_url,
            "media_url": image_url,
            "prompt": prompt,
            "copy": content,
        },
        meta={"prompt": prompt, "stored_name": stored_name},
    )
    reply = f"{prompt}\n\n![Generated image]({image_url})"
    meta = {"artifact_kind": "image_generation", "image_used": True}
    return reply, artifact, meta


def handle_image_analysis(session: dict[str, Any], user_text: str, attachments: list[dict[str, Any]]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    image_attachment = next((a for a in attachments if safe_text(a.get("kind")) == "image"), None)
    if not image_attachment:
        raise RuntimeError("No image attachment found.")
    image_path = local_upload_path_from_url(safe_text(image_attachment.get("url")))
    if not image_path:
        raise RuntimeError("Uploaded image file not found.")
    reply = analyze_image_with_model(user_text or "Describe this image clearly.", image_path)
    artifact = create_artifact(
        session_id=safe_text(session.get("id")),
        kind="image_analysis",
        title=safe_text(image_attachment.get("name") or "Image analysis"),
        content=reply,
        viewer={
            "media_url": safe_text(image_attachment.get("url")),
            "image_url": safe_text(image_attachment.get("url")),
            "copy": reply,
            "prompt": user_text,
        },
        meta={
            "prompt": user_text,
            "attachment_name": image_attachment.get("name"),
            "image_used": True,
        },
    )
    return reply, artifact, {"artifact_kind": "image_analysis", "image_used": True}


def handle_video_analysis(session: dict[str, Any], user_text: str, attachments: list[dict[str, Any]]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    video_attachment = next((a for a in attachments if safe_text(a.get("kind")) == "video"), None)
    if not video_attachment:
        raise RuntimeError("No video attachment found.")

    lines = [
        "Video received.",
        "",
        f"Name: {safe_text(video_attachment.get('name'))}",
        f"MIME: {safe_text(video_attachment.get('mime_type'))}",
    ]
    if user_text.strip():
        lines += ["", f"Prompt: {user_text.strip()}"]

    reply = "\n".join(lines)
    artifact = create_artifact(
        session_id=safe_text(session.get("id")),
        kind="video_analysis",
        title=safe_text(video_attachment.get("name") or "Video analysis"),
        content=reply,
        viewer={
            "media_url": safe_text(video_attachment.get("url")),
            "copy": reply,
            "prompt": user_text,
        },
        meta={
            "prompt": user_text,
            "attachment_name": video_attachment.get("name"),
        },
    )
    return reply, artifact, {"artifact_kind": "video_analysis"}


def handle_standard_chat(session: dict[str, Any], user_text: str, attachments: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None, dict[str, Any]]:
    web_url = ""
    text = user_text.strip()

    if text.lower().startswith("/web "):
        web_url = text[5:].strip()
    else:
        web_url = url_from_text(text)

    if web_url:
        return build_web_result(safe_text(session.get("id")), web_url)

    doc_context, doc_meta = extract_document_context(attachments)
    prompt = build_model_messages_for_text(user_text, "", doc_context)
    reply = generate_text_reply(prompt)
    meta = {"artifact_kind": "chat_reply"}
    meta.update(doc_meta)

    memory_created = maybe_store_memory_from_message(user_text)
    if memory_created:
        meta["memory_saved"] = True

    artifact = create_artifact(
        session_id=safe_text(session.get("id")),
        kind="chat_reply",
        title="Nova reply",
        content=reply,
        viewer={"copy": reply},
        meta=meta,
    )
    return reply, artifact, meta


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify(
        {
            "ok": True,
            "status": "healthy",
            "time": now_iso(),
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "openai_model": OPENAI_MODEL,
            "image_model": NOVA_IMAGE_MODEL,
            "requests_available": requests is not None,
            "bs4_available": BeautifulSoup is not None,
        }
    )


@app.route("/api/state", methods=["GET"])
def api_state():
    requested_session_id = safe_text(request.args.get("session_id")).strip()
    sessions = sort_sessions(load_sessions())
    active_session = None

    if requested_session_id:
        active_session = next((s for s in sessions if safe_text(s.get("id")) == requested_session_id), None)

    if active_session is None and sessions:
        active_session = sessions[0]

    active_session_id = safe_text(active_session.get("id")) if active_session else ""

    return jsonify(
        {
            "ok": True,
            "active_session_id": active_session_id,
            "session": session_summary(active_session),
            "messages": list(active_session.get("messages") or []) if active_session else [],
            "sessions": [session_summary(s) for s in sessions],
            "artifacts": [artifact_summary(a) for a in list_session_artifacts(active_session_id)],
            "memory": load_memory(),
        }
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    user_text = safe_text(payload.get("content")).strip()
    session_id = safe_text(payload.get("session_id")).strip()
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []

    session = get_or_create_session(session_id)
    session = append_message(
        session,
        "user",
        user_text,
        {"attachments": attachments},
    )

    artifact: dict[str, Any] | None = None
    assistant_meta: dict[str, Any] = {"artifact_kind": "chat_reply"}

    try:
        if user_text.lower().startswith("/image "):
            prompt = user_text[7:].strip()
            reply, artifact, assistant_meta = handle_image_generation(session, prompt)
        elif any(safe_text(a.get("kind")) == "image" for a in attachments):
            reply, artifact, assistant_meta = handle_image_analysis(session, user_text, attachments)
        elif any(safe_text(a.get("kind")) == "video" for a in attachments):
            reply, artifact, assistant_meta = handle_video_analysis(session, user_text, attachments)
        else:
            reply, artifact, assistant_meta = handle_standard_chat(session, user_text, attachments)
    except Exception as err:
        reply = f"Request failed.\n\n{safe_text(err)}"
        assistant_meta = {
            "artifact_kind": "chat_reply",
            "error": safe_text(err),
            "traceback": traceback.format_exc(limit=3),
        }
        artifact = create_artifact(
            session_id=safe_text(session.get("id")),
            kind="chat_reply",
            title="Nova reply",
            content=reply,
            viewer={"copy": reply},
            meta=assistant_meta,
        )

    session = append_message(session, "assistant", reply, assistant_meta)
    saved_session = save_session(session)

    assistant_message = saved_session["messages"][-1]

    return jsonify(
        {
            "ok": True,
            "assistant_message": assistant_message,
            "session": session_summary(saved_session),
            "artifact": artifact_summary(artifact) if artifact else None,
            "debug": {
                "mode": "real" if bool(os.getenv("OPENAI_API_KEY")) else "local-fallback",
                "model": OPENAI_MODEL,
                "artifact_kind": safe_text((artifact or {}).get("kind")),
                "attachment_count": len(attachments),
                "has_urls": bool(url_from_text(user_text) or user_text.lower().startswith("/web ")),
                "image_used": any(safe_text(a.get("kind")) == "image" for a in attachments) or user_text.lower().startswith("/image "),
                "latest_user_text": preview_text(user_text, 120),
                "message_count": len(saved_session.get("messages") or []),
            },
        }
    )


@app.route("/api/upload", methods=["POST"])
def api_upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"ok": False, "error": "No files uploaded."}), 400

    uploaded: list[dict[str, Any]] = []
    for file in files:
        original_name = secure_filename(file.filename or "")
        if not original_name or not is_allowed_file(original_name):
            continue

        ext = Path(original_name).suffix.lower()
        stored_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}{ext}"
        path = UPLOADS_DIR / stored_name
        file.save(path)

        mime_type = file.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        uploaded.append(
            {
                "id": make_id("upload"),
                "name": original_name,
                "stored_name": stored_name,
                "url": f"/api/uploads/{stored_name}",
                "mime_type": mime_type,
                "kind": detect_attachment_kind(original_name, mime_type),
                "created_at": now_iso(),
            }
        )

    if not uploaded:
        return jsonify({"ok": False, "error": "No valid files uploaded."}), 400

    return jsonify({"ok": True, "files": uploaded})


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    session_id = safe_text(request.args.get("session_id")).strip()
    artifacts = list_session_artifacts(session_id)
    return jsonify({"ok": True, "artifacts": [artifact_summary(a) for a in artifacts]})


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_read(artifact_id: str):
    artifact = get_artifact(artifact_id)
    if not artifact:
        return jsonify({"ok": False, "error": "Artifact not found."}), 404
    return jsonify({"ok": True, "artifact": artifact})


@app.route("/api/artifacts/<artifact_id>", methods=["DELETE"])
def api_artifact_delete(artifact_id: str):
    artifacts = sort_artifacts(load_artifacts())
    before = len(artifacts)

    deleted: dict[str, Any] | None = None
    kept: list[dict[str, Any]] = []

    for artifact in artifacts:
        if safe_text(artifact.get("id")) == safe_text(artifact_id):
            deleted = artifact
        else:
            kept.append(artifact)

    if deleted is None:
        return jsonify({"ok": False, "error": "Artifact not found."}), 404

    save_artifacts(kept)

    return jsonify(
        {
            "ok": True,
            "deleted_id": artifact_id,
            "deleted_kind": safe_text(deleted.get("kind")),
            "deleted_session_id": safe_text(deleted.get("session_id")),
            "artifact_count_before": before,
            "artifact_count_after": len(kept),
        }
    )


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_session_delete(session_id: str):
    sessions = sort_sessions(load_sessions())
    artifacts = sort_artifacts(load_artifacts())

    before_sessions = len(sessions)
    before_artifacts = len(artifacts)

    deleted_session: dict[str, Any] | None = None
    kept_sessions: list[dict[str, Any]] = []

    for session in sessions:
        if safe_text(session.get("id")) == safe_text(session_id):
            deleted_session = session
        else:
            kept_sessions.append(session)

    if deleted_session is None:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    kept_artifacts = [a for a in artifacts if safe_text(a.get("session_id")) != safe_text(session_id)]

    save_sessions(kept_sessions)
    save_artifacts(kept_artifacts)

    next_session_id = safe_text(kept_sessions[0].get("id")) if kept_sessions else ""

    return jsonify(
        {
            "ok": True,
            "deleted_id": session_id,
            "deleted_title": safe_text(deleted_session.get("title") or "New chat"),
            "session_count_before": before_sessions,
            "session_count_after": len(kept_sessions),
            "artifact_count_before": before_artifacts,
            "artifact_count_after": len(kept_artifacts),
            "next_session_id": next_session_id,
        }
    )


@app.route("/api/sessions/<session_id>/rename", methods=["POST"])
def api_session_rename(session_id: str):
    payload = request.get_json(silent=True) or {}
    title = safe_text(payload.get("title")).strip()

    if not title:
        return jsonify({"ok": False, "error": "Title is required."}), 400

    title = title[:120]

    sessions = sort_sessions(load_sessions())
    updated: dict[str, Any] | None = None

    for i, session in enumerate(sessions):
        if safe_text(session.get("id")) == safe_text(session_id):
            session["title"] = title
            session["updated_at"] = now_iso()
            updated = normalize_session(session)
            sessions[i] = updated
            break

    if updated is None:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    save_sessions(sort_sessions(sessions))

    return jsonify(
        {
            "ok": True,
            "session": session_summary(updated),
        }
    )


@app.route("/api/sessions/<session_id>/pin", methods=["POST"])
def api_session_pin(session_id: str):
    payload = request.get_json(silent=True) or {}
    pin_value = payload.get("pinned")

    sessions = sort_sessions(load_sessions())
    updated: dict[str, Any] | None = None

    for i, session in enumerate(sessions):
        if safe_text(session.get("id")) == safe_text(session_id):
            current = bool(session.get("pinned", False))
            new_value = (not current) if pin_value is None else bool(pin_value)
            session["pinned"] = new_value
            session["updated_at"] = now_iso()
            updated = normalize_session(session)
            sessions[i] = updated
            break

    if updated is None:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    save_sessions(sort_sessions(sessions))

    return jsonify(
        {
            "ok": True,
            "session": session_summary(updated),
        }
    )


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=NOVA_DEBUG)