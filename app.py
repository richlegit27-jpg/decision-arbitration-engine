from __future__ import annotations

import json
import mimetypes
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None


# --------------------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

APP_HOST = os.getenv("APP_HOST", os.getenv("NOVA_HOST", "127.0.0.1"))
APP_PORT = int(os.getenv("APP_PORT", os.getenv("NOVA_PORT", "5001")))
APP_DEBUG = os.getenv("NOVA_DEBUG", "1") not in ("0", "false", "False")

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5")
IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")
IMAGE_QUALITY = os.getenv("NOVA_IMAGE_QUALITY", "medium")

MAX_CONTENT_LENGTH = 50 * 1024 * 1024
MAX_MEMORY_ITEMS = 100
MAX_WEB_RESULTS_IN_STATE = 20
MAX_MEMORY_ITEMS_IN_STATE = 25
MAX_SESSION_PREVIEW = 120
MAX_ARTIFACT_PREVIEW = 220
MAX_ANALYSIS_ATTACHMENTS = 4
MAX_INLINE_IMAGE_BYTES = 8 * 1024 * 1024
ROUTE_BUILD = "attachment-image-analysis-artifact-lock-2026-04-02-001"

ALLOWED_UPLOAD_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "pdf", "txt", "log", "md", "json", "csv",
    "html", "htm", "xml", "yaml", "yml",
    "mp4", "mov", "webm", "m4v", "avi",
}


# --------------------------------------------------------------------------------------
# UTILS
# --------------------------------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def summarize_text(text: str, limit: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", safe_str(text)).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def guess_mime_type(filename_or_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(filename_or_path)
    return mime_type or "application/octet-stream"


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_UPLOAD_EXTENSIONS


def normalize_datetime(value: Any) -> str:
    text = safe_str(value).strip()
    return text or utc_now_iso()


def sort_by_updated_desc(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: safe_str(item.get("updated_at") or item.get("created_at") or ""),
        reverse=True,
    )


def attachment_file_path(attachment: dict[str, Any]) -> Path | None:
    stored_filename = safe_str(
        attachment.get("stored_filename")
        or attachment.get("stored_name")
        or attachment.get("filename")
    ).strip()
    if not stored_filename:
        return None
    path = UPLOADS_DIR / stored_filename
    if path.exists() and path.is_file():
        return path
    return None


def attachment_is_image(attachment: dict[str, Any]) -> bool:
    mime_type = safe_str(attachment.get("mime_type")).lower()
    kind = safe_str(attachment.get("type")).lower()
    filename = safe_str(attachment.get("filename") or attachment.get("stored_filename")).lower()
    return (
        mime_type.startswith("image/")
        or kind == "image"
        or filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    )


def attachment_is_video(attachment: dict[str, Any]) -> bool:
    mime_type = safe_str(attachment.get("mime_type")).lower()
    kind = safe_str(attachment.get("type")).lower()
    filename = safe_str(attachment.get("filename") or attachment.get("stored_filename")).lower()
    return (
        mime_type.startswith("video/")
        or kind == "video"
        or filename.endswith((".mp4", ".mov", ".webm", ".m4v", ".avi"))
    )


def has_image_attachments(attachments: list[dict[str, Any]]) -> bool:
    return any(attachment_is_image(a) for a in attachments)


def has_video_attachments(attachments: list[dict[str, Any]]) -> bool:
    return any(attachment_is_video(a) for a in attachments)


def attachment_to_data_url(attachment: dict[str, Any]) -> str:
    import base64

    path = attachment_file_path(attachment)
    if path is None:
        return ""

    try:
        size = path.stat().st_size
    except Exception:
        return ""

    if size <= 0 or size > MAX_INLINE_IMAGE_BYTES:
        return ""

    mime_type = safe_str(attachment.get("mime_type") or guess_mime_type(path.name)).strip() or "application/octet-stream"

    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""

    return f"data:{mime_type};base64,{encoded}"


def summarize_attachment_list(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for attachment in attachments:
        path = attachment_file_path(attachment)
        size = 0
        try:
            if path is not None:
                size = path.stat().st_size
        except Exception:
            size = int(attachment.get("size") or 0)

        summary.append({
            "id": safe_str(attachment.get("id")),
            "filename": safe_str(attachment.get("filename") or attachment.get("stored_filename")),
            "stored_filename": safe_str(attachment.get("stored_filename") or attachment.get("stored_name")),
            "mime_type": safe_str(attachment.get("mime_type")),
            "type": safe_str(attachment.get("type")),
            "size": size,
            "url": safe_str(attachment.get("url")),
        })
    return summary


# --------------------------------------------------------------------------------------
# DATA NORMALIZATION
# --------------------------------------------------------------------------------------

def normalize_attachment(item: dict[str, Any]) -> dict[str, Any]:
    attachment = dict(item or {})
    filename = safe_str(
        attachment.get("filename")
        or attachment.get("name")
        or attachment.get("stored_filename")
        or attachment.get("stored_name")
        or "file"
    )
    stored_filename = safe_str(
        attachment.get("stored_filename")
        or attachment.get("stored_name")
        or filename
    )
    mime_type = safe_str(attachment.get("mime_type") or guess_mime_type(filename))
    url = safe_str(attachment.get("url"))
    if not url and stored_filename:
        url = f"/api/uploads/{stored_filename}"

    inferred_type = safe_str(attachment.get("type")).strip().lower()
    if not inferred_type:
        if mime_type.startswith("image/"):
            inferred_type = "image"
        elif mime_type.startswith("video/"):
            inferred_type = "video"
        else:
            inferred_type = "file"

    return {
        "id": safe_str(attachment.get("id") or ""),
        "filename": filename,
        "stored_filename": stored_filename,
        "stored_name": stored_filename,
        "mime_type": mime_type,
        "size": attachment.get("size", 0),
        "type": inferred_type,
        "url": url,
        "title": safe_str(attachment.get("title") or filename),
        "alt": safe_str(attachment.get("alt") or filename),
        "prompt": safe_str(attachment.get("prompt") or ""),
        "source": safe_str(attachment.get("source") or "upload"),
    }


def normalize_message(item: dict[str, Any], session_id: str = "") -> dict[str, Any]:
    msg = dict(item or {})
    content = safe_str(msg.get("content") or msg.get("text") or "")
    attachments = msg.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = []

    return {
        "id": safe_str(msg.get("id") or str(uuid.uuid4())),
        "role": safe_str(msg.get("role") or "assistant"),
        "content": content,
        "created_at": normalize_datetime(msg.get("created_at")),
        "attachments": [normalize_attachment(a) for a in attachments if isinstance(a, dict)],
        "meta": msg.get("meta") if isinstance(msg.get("meta"), dict) else {},
        "kind": safe_str(msg.get("kind") or ""),
        "session_id": safe_str(msg.get("session_id") or session_id),
    }


def normalize_session(item: dict[str, Any]) -> dict[str, Any]:
    session = dict(item or {})
    session_id = safe_str(session.get("id") or str(uuid.uuid4()))
    messages = session.get("messages") or []
    if not isinstance(messages, list):
        messages = []

    normalized_messages = [normalize_message(m, session_id=session_id) for m in messages if isinstance(m, dict)]
    updated_at = normalize_datetime(session.get("updated_at") or session.get("created_at"))
    created_at = normalize_datetime(session.get("created_at") or updated_at)
    last_preview = safe_str(session.get("last_message_preview")).strip()
    if not last_preview and normalized_messages:
        last_preview = summarize_text(normalized_messages[-1].get("content", ""), MAX_SESSION_PREVIEW)

    return {
        "id": session_id,
        "title": safe_str(session.get("title") or "New session"),
        "created_at": created_at,
        "updated_at": updated_at,
        "messages": normalized_messages,
        "message_count": int(session.get("message_count") or len(normalized_messages)),
        "last_message_preview": last_preview,
        "pinned": bool(session.get("pinned", False)),
    }


def normalize_artifact(item: dict[str, Any]) -> dict[str, Any]:
    artifact = dict(item or {})
    content = safe_str(artifact.get("content") or artifact.get("text") or "")
    attachments = artifact.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = []
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    viewer = artifact.get("viewer") if isinstance(artifact.get("viewer"), dict) else {}

    kind = safe_str(artifact.get("kind") or viewer.get("kind") or "artifact")
    title = safe_str(artifact.get("title") or viewer.get("title") or "Untitled artifact")
    session_id = safe_str(
        artifact.get("session_id")
        or artifact.get("sessionId")
        or meta.get("session_id")
        or viewer.get("session_id")
        or ""
    )

    return {
        "id": safe_str(artifact.get("id") or str(uuid.uuid4())),
        "kind": kind,
        "title": title,
        "content": content,
        "created_at": normalize_datetime(artifact.get("created_at")),
        "updated_at": normalize_datetime(artifact.get("updated_at") or artifact.get("created_at")),
        "session_id": session_id,
        "attachments": [normalize_attachment(a) for a in attachments if isinstance(a, dict)],
        "meta": meta,
        "pinned": bool(artifact.get("pinned", False)),
        "viewer": {
            "kind": safe_str(viewer.get("kind") or kind),
            "title": safe_str(viewer.get("title") or title),
            "preview": safe_str(viewer.get("preview") or summarize_text(content, MAX_ARTIFACT_PREVIEW)),
            "content": safe_str(viewer.get("content") or content),
            "session_id": safe_str(viewer.get("session_id") or session_id),
        },
    }


def normalize_memory_item(item: dict[str, Any]) -> dict[str, Any]:
    mem = dict(item or {})
    text = safe_str(mem.get("text") or mem.get("content") or "")
    return {
        "id": safe_str(mem.get("id") or str(uuid.uuid4())),
        "text": text,
        "content": text,
        "created_at": normalize_datetime(mem.get("created_at")),
        "updated_at": normalize_datetime(mem.get("updated_at") or mem.get("created_at")),
        "source": safe_str(mem.get("source") or "system"),
        "session_id": safe_str(mem.get("session_id") or ""),
        "pinned": bool(mem.get("pinned", False)),
    }


# --------------------------------------------------------------------------------------
# STORAGE
# --------------------------------------------------------------------------------------

def read_sessions() -> list[dict[str, Any]]:
    raw = read_json_file(SESSIONS_FILE, [])
    if not isinstance(raw, list):
        return []
    return sort_by_updated_desc([normalize_session(item) for item in raw if isinstance(item, dict)])


def write_sessions(sessions: list[dict[str, Any]]) -> None:
    write_json_file(SESSIONS_FILE, sort_by_updated_desc([normalize_session(s) for s in sessions]))


def read_artifacts() -> list[dict[str, Any]]:
    raw = read_json_file(ARTIFACTS_FILE, [])
    if isinstance(raw, dict) and isinstance(raw.get("artifacts"), list):
        raw = raw.get("artifacts")
    if not isinstance(raw, list):
        return []
    return sort_by_updated_desc([normalize_artifact(item) for item in raw if isinstance(item, dict)])


def write_artifacts(artifacts: list[dict[str, Any]]) -> None:
    write_json_file(ARTIFACTS_FILE, [normalize_artifact(a) for a in sort_by_updated_desc(artifacts)])


def read_memory_items() -> list[dict[str, Any]]:
    raw = read_json_file(MEMORY_FILE, [])
    if isinstance(raw, dict) and isinstance(raw.get("items"), list):
        raw = raw.get("items")
    if not isinstance(raw, list):
        return []
    return sort_by_updated_desc([normalize_memory_item(item) for item in raw if isinstance(item, dict)])


def write_memory_items(items: list[dict[str, Any]]) -> None:
    cleaned = [normalize_memory_item(i) for i in items if isinstance(i, dict)]
    write_json_file(MEMORY_FILE, cleaned[:MAX_MEMORY_ITEMS])


# --------------------------------------------------------------------------------------
# SESSION / ARTIFACT HELPERS
# --------------------------------------------------------------------------------------

def get_session_by_id(session_id: str) -> dict[str, Any] | None:
    clean_id = safe_str(session_id).strip()
    if not clean_id:
        return None
    for session in read_sessions():
        if safe_str(session.get("id")) == clean_id:
            return session
    return None


def ensure_session(session_id: str = "") -> dict[str, Any]:
    existing = get_session_by_id(session_id)
    if existing:
        return existing

    now = utc_now_iso()
    session = normalize_session({
        "id": session_id or str(uuid.uuid4()),
        "title": "New session",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "message_count": 0,
        "last_message_preview": "",
        "pinned": False,
    })
    sessions = read_sessions()
    sessions.insert(0, session)
    write_sessions(sessions)
    return session


def upsert_session(session: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_session(session)
    sessions = read_sessions()
    replaced = False
    for idx, existing in enumerate(sessions):
        if safe_str(existing.get("id")) == safe_str(normalized.get("id")):
            sessions[idx] = normalized
            replaced = True
            break
    if not replaced:
        sessions.insert(0, normalized)
    write_sessions(sessions)
    return normalized


def append_message_to_session(
    session_id: str,
    *,
    role: str,
    content: str,
    attachments: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    kind: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    session = ensure_session(session_id)
    now = utc_now_iso()
    message = normalize_message({
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "created_at": now,
        "attachments": attachments or [],
        "meta": meta or {},
        "kind": kind,
        "session_id": session["id"],
    }, session_id=session["id"])

    messages = list(session.get("messages") or [])
    messages.append(message)
    session["messages"] = messages
    session["updated_at"] = now
    session["message_count"] = len(messages)
    session["last_message_preview"] = summarize_text(content, MAX_SESSION_PREVIEW)

    if role == "user":
        current_title = safe_str(session.get("title")).strip()
        if current_title in ("", "New session", "Untitled session"):
            session["title"] = summarize_text(content or "New session", 48)

    saved_session = upsert_session(session)
    return message, saved_session


def save_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    content: str,
    attachments: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    artifact = normalize_artifact({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "title": title,
        "content": content,
        "attachments": attachments or [],
        "meta": meta or {},
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "viewer": {
            "kind": kind,
            "title": title,
            "preview": summarize_text(content, MAX_ARTIFACT_PREVIEW),
            "content": content,
            "session_id": session_id,
        },
    })
    artifacts = read_artifacts()
    artifacts.insert(0, artifact)
    write_artifacts(artifacts)
    return artifact


def add_memory_item(text: str, *, source: str = "chat", session_id: str = "") -> dict[str, Any]:
    clean = summarize_text(text, 500).strip()
    if not clean:
        return {}
    items = read_memory_items()
    now = utc_now_iso()
    item = normalize_memory_item({
        "id": str(uuid.uuid4()),
        "text": clean,
        "content": clean,
        "created_at": now,
        "updated_at": now,
        "source": source,
        "session_id": session_id,
        "pinned": False,
    })
    items.insert(0, item)
    write_memory_items(items)
    return item


# --------------------------------------------------------------------------------------
# MEMORY / WEB / OPENAI HELPERS
# --------------------------------------------------------------------------------------

def detect_memory_signal(user_text: str) -> str:
    text = safe_str(user_text).strip()
    if not text:
        return ""
    lowered = text.lower()

    triggers = (
        "remember ",
        "remember that ",
        "please remember ",
        "note that ",
        "my name is ",
        "from now on ",
        "going forward ",
    )
    if any(trigger in lowered for trigger in triggers):
        return text
    return ""


def extract_url(text: str) -> str:
    match = re.search(r"https?://\S+", safe_str(text))
    return match.group(0).strip() if match else ""


def fetch_web_content(url: str) -> dict[str, Any]:
    if not url:
        return {"ok": False, "error": "No URL provided.", "url": ""}

    if requests is None:
        return {"ok": False, "error": "requests is not installed.", "url": url}

    try:
        response = requests.get(
            url,
            timeout=(8, 12),
            headers={"User-Agent": "Nova/2026 Local Web Client"},
        )
        response.raise_for_status()
    except Exception as exc:
        return {"ok": False, "error": safe_str(exc), "url": url}

    html = response.text or ""
    title = ""
    description = ""
    site_name = ""
    text_content = ""

    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, "html.parser")
            if soup.title and soup.title.string:
                title = safe_str(soup.title.string).strip()

            meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta_desc:
                description = safe_str(meta_desc.get("content")).strip()

            meta_site = soup.find("meta", attrs={"property": "og:site_name"})
            if meta_site:
                site_name = safe_str(meta_site.get("content")).strip()

            for tag in soup(["script", "style", "noscript"]):
                tag.extract()

            text_content = soup.get_text("\n", strip=True)
        except Exception:
            text_content = re.sub(r"<[^>]+>", " ", html)
    else:
        text_content = re.sub(r"<[^>]+>", " ", html)

    text_content = re.sub(r"\n{2,}", "\n\n", text_content).strip()
    if not description:
        description = summarize_text(text_content, 320)

    return {
        "ok": True,
        "url": url,
        "final_url": safe_str(response.url or url),
        "status_code": response.status_code,
        "title": title or url,
        "description": description,
        "site_name": site_name,
        "preview": summarize_text(description or text_content, 320),
        "content": summarize_text(text_content, 6000),
    }


class AIClient:
    def __init__(self) -> None:
        self.client = None
        if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
            try:
                self.client = OpenAI()
            except Exception:
                self.client = None

    @staticmethod
    def _memory_block(memory_items: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"- {safe_str(item.get('text') or item.get('content'))}"
            for item in memory_items[:8]
            if safe_str(item.get("text") or item.get("content")).strip()
        ) or "No saved memory."

    def chat(self, *, user_text: str, memory_items: list[dict[str, Any]], web_context: dict[str, Any] | None = None) -> str:
        if self.client is None:
            return self._fallback_chat(user_text=user_text, web_context=web_context)

        memory_block = self._memory_block(memory_items)

        web_block = "No web context."
        if web_context and web_context.get("ok"):
            web_block = (
                f"URL: {safe_str(web_context.get('final_url') or web_context.get('url'))}\n"
                f"Title: {safe_str(web_context.get('title'))}\n"
                f"Description: {safe_str(web_context.get('description'))}\n"
                f"Content: {safe_str(web_context.get('content'))}"
            )

        prompt = (
            "You are Nova, a direct local assistant inside a user's custom web app. "
            "Be helpful, concise, and keep answers practical.\n\n"
            f"Saved Memory:\n{memory_block}\n\n"
            f"Web Context:\n{web_block}\n\n"
            f"User Message:\n{user_text}"
        )

        try:
            response = self.client.responses.create(
                model=CHAT_MODEL,
                input=prompt,
            )
            text = safe_str(getattr(response, "output_text", "")).strip()
            if text:
                return text
        except Exception:
            pass

        return self._fallback_chat(user_text=user_text, web_context=web_context)

    def analyze_images(
        self,
        *,
        user_text: str,
        attachments: list[dict[str, Any]],
        memory_items: list[dict[str, Any]],
    ) -> str:
        image_attachments = [a for a in attachments if attachment_is_image(a)][:MAX_ANALYSIS_ATTACHMENTS]
        if not image_attachments:
            return self._fallback_image_analysis(user_text=user_text, attachments=attachments)

        if self.client is None:
            return self._fallback_image_analysis(user_text=user_text, attachments=image_attachments)

        user_prompt = safe_str(user_text).strip() or "What is in this image?"
        memory_block = self._memory_block(memory_items)

        user_content: list[dict[str, Any]] = [{
            "type": "input_text",
            "text": (
                "Analyze the attached image(s) for the user.\n"
                "Be direct, practical, and concise.\n"
                "If the user asks what something is, identify the main visible subject first.\n"
                "Then mention important visible details, uncertainty if any, and useful next steps if relevant.\n\n"
                f"Saved Memory:\n{memory_block}\n\n"
                f"User Prompt:\n{user_prompt}"
            ),
        }]

        added_any_image = False
        for attachment in image_attachments:
            data_url = attachment_to_data_url(attachment)
            if not data_url:
                continue
            user_content.append({
                "type": "input_image",
                "image_url": data_url,
            })
            added_any_image = True

        if not added_any_image:
            return self._fallback_image_analysis(user_text=user_text, attachments=image_attachments)

        try:
            response = self.client.responses.create(
                model=CHAT_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "You are Nova, a direct assistant inside a local app. Analyze images clearly and without fluff.",
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": user_content,
                    },
                ],
            )
            text = safe_str(getattr(response, "output_text", "")).strip()
            if text:
                return text
        except Exception:
            pass

        return self._fallback_image_analysis(user_text=user_text, attachments=image_attachments)

    def analyze_video(
        self,
        *,
        user_text: str,
        attachments: list[dict[str, Any]],
        memory_items: list[dict[str, Any]],
    ) -> str:
        _ = memory_items
        video_attachments = [a for a in attachments if attachment_is_video(a)][:MAX_ANALYSIS_ATTACHMENTS]
        if not video_attachments:
            return "I received the attachment, but I could not identify a video to analyze."

        parts: list[str] = []
        prompt = safe_str(user_text).strip() or "Analyze this video."

        for attachment in video_attachments:
            path = attachment_file_path(attachment)
            size = 0
            if path is not None:
                try:
                    size = path.stat().st_size
                except Exception:
                    size = int(attachment.get("size") or 0)
            else:
                size = int(attachment.get("size") or 0)

            parts.append(
                f"- {safe_str(attachment.get('filename') or attachment.get('stored_filename'))} "
                f"({safe_str(attachment.get('mime_type') or 'video')}, {size} bytes)"
            )

        return (
            "I received your video attachment.\n\n"
            f"Prompt: {prompt}\n\n"
            "First-pass video analysis is active, but deep frame-by-frame vision/video understanding is not wired yet in this build.\n"
            "I saved the video analysis artifact and preserved the uploaded file so the pipeline is locked.\n\n"
            "Received video files:\n"
            + "\n".join(parts)
        )

    def generate_image(self, prompt: str) -> dict[str, Any]:
        if self.client is None:
            return {
                "ok": False,
                "error": "OpenAI image generation is unavailable.",
            }

        try:
            result = self.client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                size=IMAGE_SIZE,
            )
            data = getattr(result, "data", None) or []
            if not data:
                return {"ok": False, "error": "No image data returned."}

            first = data[0]
            image_b64 = getattr(first, "b64_json", None)
            image_url = getattr(first, "url", None)

            if image_b64:
                return {"ok": True, "b64_json": image_b64}
            if image_url:
                return {"ok": True, "remote_url": image_url}

            return {"ok": False, "error": "Unsupported image response format."}
        except Exception as exc:
            return {"ok": False, "error": safe_str(exc)}

    @staticmethod
    def _fallback_chat(*, user_text: str, web_context: dict[str, Any] | None = None) -> str:
        lowered = safe_str(user_text).strip().lower()
        if web_context and web_context.get("ok"):
            return (
                f"Fetched **{safe_str(web_context.get('title'))}**\n\n"
                f"{safe_str(web_context.get('preview'))}\n\n"
                f"Source: {safe_str(web_context.get('final_url') or web_context.get('url'))}"
            )
        if lowered in {"hi", "hello", "hey", "up"}:
            return "Hi! How can I help?"
        return "Hey — I’m up. What do you need?"

    @staticmethod
    def _fallback_image_analysis(*, user_text: str, attachments: list[dict[str, Any]]) -> str:
        names = [
            safe_str(a.get("filename") or a.get("stored_filename") or "image")
            for a in attachments[:MAX_ANALYSIS_ATTACHMENTS]
        ]
        prompt = safe_str(user_text).strip() or "What is this?"
        label = ", ".join(names) if names else "your image"
        return (
            f"I received {label}.\n\n"
            f"Prompt: {prompt}\n\n"
            "Image-analysis routing is active, but live vision analysis is unavailable in this runtime right now. "
            "The upload was preserved and the image_analysis artifact was still saved."
        )


ai_client = AIClient()


def save_generated_image_from_b64(image_b64: str, *, prompt: str) -> dict[str, Any]:
    import base64

    filename = f"generated_{uuid.uuid4().hex}.png"
    path = UPLOADS_DIR / filename
    path.write_bytes(base64.b64decode(image_b64))

    return normalize_attachment({
        "filename": filename,
        "stored_filename": filename,
        "mime_type": "image/png",
        "size": path.stat().st_size,
        "type": "image",
        "url": f"/api/uploads/{filename}",
        "prompt": prompt,
        "source": "generated",
        "title": filename,
        "alt": "generated image",
    })


def build_state_payload(preferred_session_id: str = "") -> dict[str, Any]:
    sessions = read_sessions()
    artifacts = read_artifacts()
    memory_items = read_memory_items()

    active_session = None
    preferred = safe_str(preferred_session_id).strip()
    if preferred:
        active_session = next((s for s in sessions if safe_str(s.get("id")) == preferred), None)
    if active_session is None and sessions:
        active_session = sessions[0]

    active_session_id = safe_str(active_session.get("id")) if active_session else ""

    web_items = [
        a for a in artifacts
        if safe_str(a.get("kind")) in ("web_result", "web", "web_reply")
    ][:MAX_WEB_RESULTS_IN_STATE]

    return {
        "ok": True,
        "sessions": sessions,
        "session": active_session,
        "messages": list(active_session.get("messages") or []) if active_session else [],
        "memory": {
            "count": len(memory_items),
            "items": memory_items[:MAX_MEMORY_ITEMS_IN_STATE],
        },
        "web": {
            "count": len(web_items),
            "items": web_items,
            "active_session_id": active_session_id,
        },
        "artifacts": {
            "count": len(artifacts),
        },
        "debug": {
            "active_session_id": active_session_id,
            "artifact_count": len(artifacts),
            "memory_count": len(memory_items),
            "session_count": len(sessions),
            "web_count": len(web_items),
        },
    }


# --------------------------------------------------------------------------------------
# FLASK APP
# --------------------------------------------------------------------------------------

ensure_dirs()

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.route("/", methods=["GET"])
def index() -> Any:
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health() -> Any:
    return jsonify({
        "ok": True,
        "debug": {
            "chat_model": CHAT_MODEL,
            "cwd": str(BASE_DIR),
            "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "image_model": IMAGE_MODEL,
            "image_quality": IMAGE_QUALITY,
            "image_size": IMAGE_SIZE,
            "requests_available": requests is not None,
            "route_build": ROUTE_BUILD,
            "timestamp": utc_now_iso(),
        },
    })


@app.route("/api/state", methods=["GET"])
def api_state() -> Any:
    session_id = safe_str(request.args.get("session_id")).strip()
    return jsonify(build_state_payload(preferred_session_id=session_id))


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts() -> Any:
    artifacts = read_artifacts()
    media_count = sum(1 for artifact in artifacts if artifact.get("attachments"))
    return jsonify({
        "ok": True,
        "artifacts": artifacts,
        "debug": {
            "count": len(artifacts),
            "media_count": media_count,
        },
    })


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_read(artifact_id: str) -> Any:
    artifact = next((a for a in read_artifacts() if safe_str(a.get("id")) == safe_str(artifact_id)), None)
    if artifact is None:
        return jsonify({"ok": False, "error": "Artifact not found."}), 404
    return jsonify({"ok": True, "artifact": artifact})


@app.route("/api/upload", methods=["POST"])
def api_upload() -> Any:
    files = request.files.getlist("files")
    saved_files: list[dict[str, Any]] = []

    for uploaded in files:
        if not uploaded or not uploaded.filename:
            continue

        original_name = secure_filename(uploaded.filename)
        if not original_name or not allowed_file(original_name):
            continue

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        target_path = UPLOADS_DIR / stored_name
        uploaded.save(target_path)

        guessed_mime = guess_mime_type(original_name)
        inferred_type = "file"
        if guessed_mime.startswith("image/"):
            inferred_type = "image"
        elif guessed_mime.startswith("video/"):
            inferred_type = "video"

        saved_files.append(normalize_attachment({
            "id": str(uuid.uuid4()),
            "filename": original_name,
            "stored_filename": stored_name,
            "mime_type": guessed_mime,
            "size": target_path.stat().st_size,
            "type": inferred_type,
            "url": f"/api/uploads/{stored_name}",
            "title": original_name,
            "alt": original_name,
            "source": "upload",
        }))

    return jsonify({
        "ok": True,
        "files": saved_files,
        "debug": {
            "count": len(saved_files),
        },
    })


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploads(filename: str) -> Any:
    return send_from_directory(str(UPLOADS_DIR), filename, as_attachment=False)


@app.route("/api/chat", methods=["POST"])
def api_chat() -> Any:
    payload = request.get_json(silent=True) or {}
    user_text = safe_str(payload.get("content")).strip()
    session_id = safe_str(payload.get("session_id")).strip()
    raw_attachments = payload.get("attachments") or []
    if not isinstance(raw_attachments, list):
        raw_attachments = []
    attachments = [normalize_attachment(a) for a in raw_attachments if isinstance(a, dict)]

    session = ensure_session(session_id)
    session_id = safe_str(session.get("id"))

    user_message = None
    if user_text or attachments:
        user_message, session = append_message_to_session(
            session_id,
            role="user",
            content=user_text or "(attachment)",
            attachments=attachments,
            meta={
                "route_meta": {
                    "attachments_count": len(attachments),
                    "attachments_types": [safe_str(a.get("type")) for a in attachments],
                    "source": "nova-composer-bundle",
                    "timestamp": utc_now_iso(),
                }
            },
            kind="user_message",
        )

    memory_saved = {}
    memory_signal = detect_memory_signal(user_text)
    if memory_signal:
        memory_saved = add_memory_item(memory_signal, source="user", session_id=session_id)

    assistant_text = ""
    assistant_attachments: list[dict[str, Any]] = []
    assistant_kind = "chat_reply"
    web_result: dict[str, Any] | None = None
    special_artifact_already_saved = False

    lowered = user_text.lower()

    if lowered.startswith("/image"):
        prompt = user_text[6:].strip()
        if not prompt:
            assistant_text = "Error\n\nProvide an image prompt after /image."
            assistant_kind = "error"
        else:
            image_result = ai_client.generate_image(prompt)
            if image_result.get("ok") and image_result.get("b64_json"):
                generated_attachment = save_generated_image_from_b64(image_result["b64_json"], prompt=prompt)
                assistant_attachments = [generated_attachment]
                assistant_kind = "generated_image"
                assistant_text = (
                    f"![generated image]({generated_attachment['url']})\n\n"
                    f"Generated from prompt: {prompt}"
                )

                save_artifact(
                    session_id=session_id,
                    kind="generated_image",
                    title=f"Generated Image - {summarize_text(prompt, 60)}",
                    content=assistant_text,
                    attachments=assistant_attachments,
                    meta={
                        "artifact_source": "chat_service_autosave",
                        "attachments_count": len(assistant_attachments),
                        "document_used": False,
                        "media": assistant_attachments,
                        "model": IMAGE_MODEL,
                        "role": "assistant",
                        "prompt": prompt,
                        "web": {"used": False},
                    },
                )
                special_artifact_already_saved = True
            else:
                assistant_kind = "error"
                assistant_text = f"Error\n\n{safe_str(image_result.get('error') or 'Image generation failed.')}"
    elif lowered.startswith("/web"):
        url = extract_url(user_text)
        web_result = fetch_web_content(url)
        if web_result.get("ok"):
            assistant_text = (
                f"Fetched **{safe_str(web_result.get('title'))}**\n\n"
                f"{safe_str(web_result.get('preview'))}"
            )
            assistant_kind = "web_result"

            save_artifact(
                session_id=session_id,
                kind="web_result",
                title=f"Web - {summarize_text(safe_str(web_result.get('title')), 80)}",
                content=(
                    f"URL: {safe_str(web_result.get('final_url') or web_result.get('url'))}\n\n"
                    f"{safe_str(web_result.get('content'))}"
                ),
                attachments=[],
                meta={
                    "artifact_source": "web_fetch",
                    "web": web_result,
                    "model": CHAT_MODEL,
                    "role": "assistant",
                },
            )
            special_artifact_already_saved = True
        else:
            assistant_kind = "error"
            assistant_text = f"Web fetch failed.\n\n{safe_str(web_result.get('error') or 'Unknown web error.')}"
    elif has_image_attachments(attachments):
        memory_items = read_memory_items()[:12]
        assistant_text = ai_client.analyze_images(
            user_text=user_text,
            attachments=attachments,
            memory_items=memory_items,
        )
        assistant_kind = "image_analysis"

        save_artifact(
            session_id=session_id,
            kind="image_analysis",
            title=f"Image Analysis - {summarize_text(user_text or 'Attachment analysis', 60)}",
            content=assistant_text,
            attachments=attachments,
            meta={
                "artifact_source": "attachment_analysis",
                "analysis_type": "image",
                "attachments_count": len(attachments),
                "attachments": summarize_attachment_list(attachments),
                "model": CHAT_MODEL,
                "role": "assistant",
                "user_prompt": user_text,
            },
        )
        special_artifact_already_saved = True
    elif has_video_attachments(attachments):
        memory_items = read_memory_items()[:12]
        assistant_text = ai_client.analyze_video(
            user_text=user_text,
            attachments=attachments,
            memory_items=memory_items,
        )
        assistant_kind = "video_analysis"

        save_artifact(
            session_id=session_id,
            kind="video_analysis",
            title=f"Video Analysis - {summarize_text(user_text or 'Video attachment', 60)}",
            content=assistant_text,
            attachments=attachments,
            meta={
                "artifact_source": "attachment_analysis",
                "analysis_type": "video",
                "attachments_count": len(attachments),
                "attachments": summarize_attachment_list(attachments),
                "model": CHAT_MODEL,
                "role": "assistant",
                "user_prompt": user_text,
                "first_pass_only": True,
            },
        )
        special_artifact_already_saved = True
    else:
        memory_items = read_memory_items()[:12]
        assistant_text = ai_client.chat(
            user_text=user_text,
            memory_items=memory_items,
            web_context=None,
        )
        assistant_kind = "chat_reply"

    assistant_message, session = append_message_to_session(
        session_id,
        role="assistant",
        content=assistant_text,
        attachments=assistant_attachments,
        meta={
            "model": CHAT_MODEL if assistant_kind != "generated_image" else IMAGE_MODEL,
            "provider": "openai" if os.getenv("OPENAI_API_KEY") else "fallback",
        },
        kind=assistant_kind,
    )

    if not special_artifact_already_saved:
        save_artifact(
            session_id=session_id,
            kind="chat_reply" if assistant_kind != "generated_image" else assistant_kind,
            title=f"{'Chat Reply' if assistant_kind != 'generated_image' else 'Generated Image'} - {summarize_text(assistant_text, 60) or 'Reply'}",
            content=assistant_text,
            attachments=assistant_attachments,
            meta={
                "artifact_source": "chat_service_autosave",
                "attachments_count": len(assistant_attachments),
                "message_id": safe_str(assistant_message.get("id")),
                "model": CHAT_MODEL if assistant_kind != "generated_image" else IMAGE_MODEL,
                "role": "assistant",
                "memory_saved": bool(memory_saved),
                "web": {
                    "used": bool(web_result and web_result.get("ok")),
                    "url": safe_str((web_result or {}).get("final_url") or (web_result or {}).get("url")),
                },
            },
        )

    refreshed_session = get_session_by_id(session_id) or session

    return jsonify({
        "ok": True,
        "message": user_message,
        "assistant_message": assistant_message,
        "session": refreshed_session,
        "debug": {
            "route_build": ROUTE_BUILD,
            "memory_saved": bool(memory_saved),
            "web_used": bool(web_result and web_result.get("ok")),
            "web_ok": bool(web_result and web_result.get("ok")),
            "web_error": safe_str((web_result or {}).get("error")),
            "attachment_count": len(attachments),
            "assistant_attachment_count": len(assistant_attachments),
            "assistant_kind": assistant_kind,
            "special_artifact_saved": special_artifact_already_saved,
            "image_analysis_used": assistant_kind == "image_analysis",
            "video_analysis_used": assistant_kind == "video_analysis",
        },
    })


if __name__ == "__main__":
    ensure_dirs()
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)