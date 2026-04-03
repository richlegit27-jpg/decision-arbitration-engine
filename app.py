import json
import mimetypes
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

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


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

APP_HOST = os.getenv("NOVA_HOST") or os.getenv("APP_HOST") or "127.0.0.1"
APP_PORT = 5001
APP_DEBUG = str(os.getenv("NOVA_DEBUG", "true")).lower() in {"1", "true", "yes", "on"}

ALLOWED_UPLOAD_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "svg",
    "mp4", "mov", "avi", "mkv", "webm", "m4v",
    "pdf", "txt", "log", "md", "json", "csv", "html", "htm", "xml", "yaml", "yml"
}

URL_RE = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    if not path.exists():
        write_json(path, default)
        return deepcopy(default)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return deepcopy(default)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def load_sessions():
    data = read_json(SESSIONS_FILE, [])

    if isinstance(data, list):
        sessions = data
    elif isinstance(data, dict):
        sessions = data.get("sessions", [])
    else:
        sessions = []

    return {"sessions": sessions if isinstance(sessions, list) else []}


def save_sessions(payload):
    if isinstance(payload, dict):
        sessions = payload.get("sessions", [])
    elif isinstance(payload, list):
        sessions = payload
    else:
        sessions = []

    if not isinstance(sessions, list):
        sessions = []

    write_json(SESSIONS_FILE, sessions)


def load_artifacts():
    data = read_json(ARTIFACTS_FILE, [])

    if isinstance(data, list):
        artifacts = data
    elif isinstance(data, dict):
        artifacts = data.get("artifacts", [])
    else:
        artifacts = []

    return {"artifacts": artifacts if isinstance(artifacts, list) else []}


def save_artifacts(payload):
    if isinstance(payload, dict):
        artifacts = payload.get("artifacts", [])
    elif isinstance(payload, list):
        artifacts = payload
    else:
        artifacts = []

    if not isinstance(artifacts, list):
        artifacts = []

    write_json(ARTIFACTS_FILE, artifacts)


def load_memory():
    data = read_json(MEMORY_FILE, [])

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items", [])
    else:
        items = []

    return {"items": items if isinstance(items, list) else []}


def save_memory(payload):
    if isinstance(payload, dict):
        items = payload.get("items", [])
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    if not isinstance(items, list):
        items = []

    write_json(MEMORY_FILE, items)


def ensure_session(session_id: str | None = None):
    sessions_payload = load_sessions()
    sessions = sessions_payload["sessions"]

    if session_id:
        for session in sessions:
            if session.get("id") == session_id:
                return sessions_payload, session

    now = utc_now_iso()
    new_session = {
        "id": uuid.uuid4().hex[:8],
        "title": "New chat",
        "created_at": now,
        "updated_at": now,
        "pinned": False,
        "message_count": 0,
        "last_message_preview": "",
        "messages": [],
    }
    sessions.insert(0, new_session)
    save_sessions(sessions_payload)
    return sessions_payload, new_session


def update_session_summary(session: dict):
    messages = session.get("messages", [])
    preview = ""
    if messages:
        preview = str(messages[-1].get("content", "")).strip().replace("\n", " ")
        preview = preview[:120]
    session["updated_at"] = utc_now_iso()
    session["message_count"] = len(messages)
    session["last_message_preview"] = preview
    if messages:
        first_user = next((m for m in messages if m.get("role") == "user" and m.get("content")), None)
        if first_user:
            title = str(first_user.get("content", "")).strip().splitlines()[0][:48]
            if title:
                session["title"] = title


def append_message(session: dict, role: str, content: str, attachments=None, meta=None):
    attachments = attachments or []
    meta = meta or {}
    session.setdefault("messages", []).append({
        "id": uuid.uuid4().hex,
        "role": role,
        "content": content,
        "attachments": attachments,
        "meta": meta,
        "created_at": utc_now_iso(),
    })
    update_session_summary(session)


def normalize_artifact(artifact: dict) -> dict:
    preview = artifact.get("preview") or ""
    content = artifact.get("content") or ""
    viewer = artifact.get("viewer") or {}
    viewer_kind = viewer.get("kind") or artifact.get("kind") or "artifact"

    return {
        "id": artifact.get("id"),
        "kind": artifact.get("kind", "artifact"),
        "title": artifact.get("title") or artifact.get("kind", "Artifact").replace("_", " ").title(),
        "session_id": artifact.get("session_id") or "",
        "created_at": artifact.get("created_at") or utc_now_iso(),
        "preview": preview[:400],
        "content": content,
        "meta": artifact.get("meta") or {},
        "attachments": artifact.get("attachments") or [],
        "viewer": {
            "kind": viewer_kind,
            "content": viewer.get("content", content),
            "html": viewer.get("html", ""),
            "url": viewer.get("url", ""),
            "media": viewer.get("media", []),
            "meta": viewer.get("meta", artifact.get("meta") or {}),
        },
    }


def create_artifact(
    kind: str,
    title: str,
    session_id: str,
    content: str,
    preview: str = "",
    meta: dict | None = None,
    viewer: dict | None = None,
    attachments: list | None = None,
):
    artifacts_payload = load_artifacts()
    artifact = normalize_artifact({
        "id": uuid.uuid4().hex,
        "kind": kind,
        "title": title,
        "session_id": session_id,
        "created_at": utc_now_iso(),
        "content": content,
        "preview": preview or content[:280],
        "meta": meta or {},
        "viewer": viewer or {},
        "attachments": attachments or [],
    })
    artifacts_payload["artifacts"].insert(0, artifact)
    save_artifacts(artifacts_payload)
    return artifact


def get_session_messages_for_reply(session: dict, max_items: int = 10):
    messages = session.get("messages", [])
    trimmed = messages[-max_items:]
    lines = []
    for msg in trimmed:
        role = msg.get("role", "user").upper()
        content = str(msg.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def extract_urls(text: str):
    return [match.group(1).rstrip(".,);]") for match in URL_RE.finditer(text or "")]


def is_allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_UPLOAD_EXTENSIONS


def guess_media_kind(filename: str, content_type: str = "") -> str:
    value = (content_type or "").lower()
    name = (filename or "").lower()

    if value.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")):
        return "image"
    if value.startswith("video/") or name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
        return "video"
    return "file"


def absolutize_url(base_url: str, maybe_url: str) -> str:
    value = str(maybe_url or "").strip()
    if not value:
        return ""
    return urljoin(base_url, value)


def safe_requests_get(url: str):
    if not requests:
        raise RuntimeError("requests is not installed")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Nova/2026",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        return response, {"ssl_fallback_used": False}
    except requests.exceptions.SSLError:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        return response, {"ssl_fallback_used": True}


def summarize_html(url: str):
    response, ssl_meta = safe_requests_get(url)
    response.raise_for_status()

    html = response.text[:1_000_000]
    title = url
    description = ""
    body_text = ""
    media = []

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            title = title_tag.get_text(" ", strip=True)

        meta_description = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", attrs={"property": "og:description"})
            or soup.find("meta", attrs={"name": "twitter:description"})
        )
        if meta_description and meta_description.get("content"):
            description = meta_description.get("content", "").strip()

        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            media.append({
                "type": "image",
                "src": absolutize_url(url, og_image.get("content")),
                "alt": title,
            })

        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            media.append({
                "type": "image",
                "src": absolutize_url(url, twitter_image.get("content")),
                "alt": title,
            })

        og_video = soup.find("meta", attrs={"property": "og:video"})
        if og_video and og_video.get("content"):
            media.append({
                "type": "video",
                "src": absolutize_url(url, og_video.get("content")),
            })

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text_blocks = soup.get_text("\n", strip=True)
        body_text = re.sub(r"\n{2,}", "\n\n", text_blocks).strip()[:6000]

        seen_media = set(
            (m.get("type", ""), m.get("src", ""))
            for m in media
            if m.get("src")
        )

        for img in soup.find_all("img", src=True)[:12]:
            src = absolutize_url(url, img.get("src"))
            key = ("image", src)
            if src and key not in seen_media:
                seen_media.add(key)
                media.append({"type": "image", "src": src, "alt": img.get("alt", "")})

        for video in soup.find_all("video")[:6]:
            src = video.get("src") or ""
            source = video.find("source")
            if source and source.get("src"):
                src = source.get("src")
            src = absolutize_url(url, src)
            key = ("video", src)
            if src and key not in seen_media:
                seen_media.add(key)
                media.append({"type": "video", "src": src})

        for audio in soup.find_all("audio")[:4]:
            src = audio.get("src") or ""
            source = audio.find("source")
            if source and source.get("src"):
                src = source.get("src")
            src = absolutize_url(url, src)
            key = ("audio", src)
            if src and key not in seen_media:
                seen_media.add(key)
                media.append({"type": "audio", "src": src})
    else:
        body_text = re.sub(r"<[^>]+>", " ", html)
        body_text = re.sub(r"\s+", " ", body_text).strip()[:6000]

    snippet_parts = [title]
    if description:
        snippet_parts.append(description)
    if body_text:
        snippet_parts.append(body_text[:1200])

    summary = "\n\n".join(part for part in snippet_parts if part).strip()
    return {
        "ok": True,
        "url": url,
        "title": title,
        "description": description,
        "text": body_text,
        "summary": summary[:5000],
        "media": media[:20],
        "ssl_fallback_used": ssl_meta.get("ssl_fallback_used", False),
        "status_code": response.status_code,
    }


def analyze_uploaded_file(file_info: dict, prompt_text: str):
    stored_name = file_info.get("stored_name", "")
    original_name = file_info.get("original_name", "")
    path = UPLOADS_DIR / stored_name
    media_kind = guess_media_kind(original_name, file_info.get("content_type", ""))

    if not path.exists():
        return {
            "ok": False,
            "kind": f"{media_kind}_analysis",
            "title": f"{media_kind.title()} analysis",
            "text": f"Uploaded file not found: {original_name}",
            "preview": f"Uploaded file not found: {original_name}",
            "meta": {"file_missing": True, "original_name": original_name},
        }

    if media_kind == "image":
        text = (
            f"I inspected the image `{original_name}`.\n\n"
            f"First-pass analysis:\n"
            f"- file type: image\n"
            f"- stored file: {stored_name}\n"
            f"- prompt: {prompt_text or 'what is this'}\n\n"
            f"This is the live image-analysis path. If you wire a vision model next, this artifact kind is already locked as `image_analysis`."
        )
        return {
            "ok": True,
            "kind": "image_analysis",
            "title": f"Image Analysis - {original_name}",
            "text": text,
            "preview": text[:280],
            "meta": {
                "document_used": False,
                "analysis_type": "first_pass_image",
                "original_name": original_name,
                "stored_name": stored_name,
            },
            "viewer": {
                "kind": "image_analysis",
                "content": text,
                "media": [{"type": "image", "src": f"/api/uploads/{stored_name}", "alt": original_name}],
                "meta": {"original_name": original_name, "stored_name": stored_name},
            },
            "attachments": [{"name": original_name, "url": f"/api/uploads/{stored_name}", "type": "image"}],
        }

    if media_kind == "video":
        text = (
            f"I inspected the video `{original_name}`.\n\n"
            f"First-pass analysis:\n"
            f"- file type: video\n"
            f"- stored file: {stored_name}\n"
            f"- prompt: {prompt_text or 'analyze this video'}\n\n"
            f"This is the live first-pass video route. You can now persist and reopen real `video_analysis` artifacts."
        )
        return {
            "ok": True,
            "kind": "video_analysis",
            "title": f"Video Analysis - {original_name}",
            "text": text,
            "preview": text[:280],
            "meta": {
                "analysis_type": "first_pass_video",
                "original_name": original_name,
                "stored_name": stored_name,
            },
            "viewer": {
                "kind": "video_analysis",
                "content": text,
                "media": [{"type": "video", "src": f"/api/uploads/{stored_name}"}],
                "meta": {"original_name": original_name, "stored_name": stored_name},
            },
            "attachments": [{"name": original_name, "url": f"/api/uploads/{stored_name}", "type": "video"}],
        }

    text = (
        f"I received the file `{original_name}`.\n\n"
        f"- type: generic file\n"
        f"- prompt: {prompt_text or 'analyze this file'}\n\n"
        f"Attach a real image or video to trigger image/video analysis artifacts."
    )
    return {
        "ok": True,
        "kind": "chat_reply",
        "title": f"Chat Reply - {original_name}",
        "text": text,
        "preview": text[:280],
        "meta": {"original_name": original_name, "stored_name": stored_name},
        "viewer": {"kind": "chat_reply", "content": text, "meta": {"original_name": original_name}},
        "attachments": [],
    }


def basic_assistant_reply(user_text: str, session: dict):
    cleaned = (user_text or "").strip()
    if not cleaned:
        return "Say something and I’ll help."

    lower = cleaned.lower()

    if lower.startswith("/image "):
        prompt = cleaned[7:].strip()
        if not prompt:
            prompt = "high detail subject"
        return (
            f"Here’s your image prompt:\n\n"
            f"{prompt}\n\n"
            f"This request is now saved as a real `image_generation` artifact so it can be reopened from the artifact rail."
        )

    if "hello" in lower or lower == "hi":
        return "Hi. Nova is up. Send a prompt, a URL, or upload an image/video."

    history = get_session_messages_for_reply(session, max_items=8)
    if history:
        return f"Working from the current session context, here’s the next move:\n\n{cleaned}"
    return cleaned


def current_web_results(session_id: str = ""):
    artifacts = load_artifacts()["artifacts"]
    results = []

    for artifact in artifacts:
        if artifact.get("kind") != "web_result":
            continue
        if session_id and artifact.get("session_id") != session_id:
            continue

        results.append({
            "id": artifact.get("id"),
            "title": artifact.get("title"),
            "url": artifact.get("viewer", {}).get("url") or artifact.get("meta", {}).get("url", ""),
            "preview": artifact.get("preview", ""),
            "created_at": artifact.get("created_at"),
            "ssl_fallback_used": bool(artifact.get("meta", {}).get("ssl_fallback_used")),
        })

    return results[:20]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "status": "healthy", "time": utc_now_iso()})


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.route("/api/upload", methods=["POST"])
def upload():
    incoming_files = request.files.getlist("files")
    saved = []

    for incoming in incoming_files:
        if not incoming or not incoming.filename:
            continue

        filename = secure_filename(incoming.filename)
        if not filename or not is_allowed_file(filename):
            continue

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        stored_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        save_path = UPLOADS_DIR / stored_name
        incoming.save(save_path)

        content_type = incoming.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        saved.append({
            "id": uuid.uuid4().hex,
            "original_name": filename,
            "stored_name": stored_name,
            "url": f"/api/uploads/{stored_name}",
            "content_type": content_type,
            "kind": guess_media_kind(filename, content_type),
            "size": save_path.stat().st_size if save_path.exists() else 0,
            "created_at": utc_now_iso(),
        })

    return jsonify({"ok": True, "files": saved})


@app.route("/api/state", methods=["GET"])
def state():
    requested_session_id = str(request.args.get("session_id") or "").strip()
    sessions_payload = load_sessions()
    sessions = sessions_payload["sessions"]

    active_session = None
    if requested_session_id:
        active_session = next((s for s in sessions if s.get("id") == requested_session_id), None)
    if not active_session:
        active_session = sessions[0] if sessions else None

    active_session_id = active_session.get("id", "") if active_session else ""

    state_payload = {
        "ok": True,
        "sessions": [
            {
                "id": session.get("id"),
                "title": session.get("title"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "pinned": bool(session.get("pinned")),
                "message_count": session.get("message_count", len(session.get("messages", []))),
                "last_message_preview": session.get("last_message_preview", ""),
            }
            for session in sessions
        ],
        "session": active_session,
        "active_session_id": active_session_id,
        "memory": load_memory().get("items", []),
        "web_results": current_web_results(active_session_id),
        "web_items": current_web_results(active_session_id),
    }
    return jsonify(state_payload)


@app.route("/api/artifacts", methods=["GET"])
def artifacts():
    artifacts_payload = load_artifacts()
    session_id = request.args.get("session_id", "").strip()

    artifacts_list = artifacts_payload["artifacts"]
    if session_id:
        artifacts_list = [a for a in artifacts_list if a.get("session_id") == session_id]

    return jsonify({"ok": True, "artifacts": artifacts_list})


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def artifact_read(artifact_id):
    artifacts_payload = load_artifacts()
    artifact = next((a for a in artifacts_payload["artifacts"] if a.get("id") == artifact_id), None)
    if not artifact:
        return jsonify({"ok": False, "error": "Artifact not found"}), 404
    return jsonify({"ok": True, "artifact": artifact})


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_text = str(payload.get("content") or payload.get("message") or "").strip()
    requested_session_id = str(payload.get("session_id") or "").strip()
    staged_files = payload.get("attachments") or payload.get("files") or []

    sessions_payload, session = ensure_session(requested_session_id)

    user_attachments = []
    for item in staged_files:
        if not isinstance(item, dict):
            continue
        user_attachments.append({
            "name": item.get("original_name") or item.get("name") or "file",
            "url": item.get("url") or "",
            "type": item.get("kind") or item.get("type") or "file",
            "stored_name": item.get("stored_name") or "",
            "content_type": item.get("content_type") or "",
            "original_name": item.get("original_name") or item.get("name") or "",
        })

    append_message(
        session,
        "user",
        user_text,
        attachments=user_attachments,
        meta={"has_urls": bool(extract_urls(user_text))}
    )
    save_sessions(sessions_payload)

    artifact = None
    assistant_text = ""

    debug = {
        "mode": "auto",
        "has_urls": False,
        "attachment_count": len(user_attachments),
        "artifact_created": False,
        "artifact_kind": "",
    }

    urls = extract_urls(user_text)
    debug["has_urls"] = bool(urls)

    try:
        if user_attachments:
            first = user_attachments[0]
            kind = guess_media_kind(first.get("original_name", ""), first.get("content_type", ""))
            debug["mode"] = f"{kind}_analysis"

            analysis = analyze_uploaded_file(first, user_text)
            assistant_text = analysis["text"]

            artifact = create_artifact(
                kind=analysis["kind"],
                title=analysis["title"],
                session_id=session["id"],
                content=analysis["text"],
                preview=analysis["preview"],
                meta=analysis["meta"],
                viewer=analysis["viewer"],
                attachments=analysis.get("attachments", []),
            )

        elif urls:
            debug["mode"] = "web_auto"

            url = urls[0]
            web_data = summarize_html(url)
            assistant_text = web_data["summary"] or web_data["title"] or url

            artifact = create_artifact(
                kind="web_result",
                title=f"Fetched {web_data['title'][:80]}",
                session_id=session["id"],
                content=assistant_text,
                preview=assistant_text[:280],
                meta={
                    "url": web_data["url"],
                    "title": web_data["title"],
                    "description": web_data["description"],
                    "ssl_fallback_used": web_data["ssl_fallback_used"],
                },
                viewer={
                    "kind": "web_result",
                    "content": assistant_text,
                    "url": web_data["url"],
                    "media": web_data["media"],
                    "meta": web_data,
                },
            )

        elif user_text.lower().startswith("/image "):
            debug["mode"] = "image_generation"

            prompt = user_text[7:].strip() or "high detail subject"
            assistant_text = f"Image prompt locked:\n\n{prompt}"

            artifact = create_artifact(
                kind="image_generation",
                title=f"Image Prompt - {prompt[:60]}",
                session_id=session["id"],
                content=assistant_text,
                preview=prompt[:280],
                meta={"prompt": prompt},
                viewer={
                    "kind": "image_generation",
                    "content": assistant_text,
                    "meta": {"prompt": prompt},
                },
            )

        else:
            debug["mode"] = "chat"
            assistant_text = basic_assistant_reply(user_text, session)

        if not artifact:
            artifact = create_artifact(
                kind="chat_reply",
                title=f"Chat Reply - {assistant_text[:40] or 'Reply'}",
                session_id=session["id"],
                content=assistant_text,
                preview=assistant_text[:280],
                meta={"reply_chars": len(assistant_text)},
                viewer={
                    "kind": "chat_reply",
                    "content": assistant_text,
                    "meta": {"reply_chars": len(assistant_text)},
                },
            )

        debug["artifact_created"] = True
        debug["artifact_kind"] = artifact.get("kind")

    except Exception as exc:
        assistant_text = f"Request failed:\n\n{exc}"

        artifact = create_artifact(
            kind="chat_reply",
            title="Chat Reply - Error",
            session_id=session["id"],
            content=assistant_text,
            preview=assistant_text[:280],
            meta={"error": str(exc)},
            viewer={
                "kind": "chat_reply",
                "content": assistant_text,
            },
        )

    append_message(
        session,
        "assistant",
        assistant_text,
        attachments=artifact.get("attachments", []),
        meta={
            "artifact_id": artifact.get("id"),
            "artifact_kind": artifact.get("kind"),
            "debug": debug,
        },
    )

    save_sessions(sessions_payload)

    return jsonify({
        "ok": True,
        "assistant_message": assistant_text,
        "session": session,
        "debug": debug,
        "web_results": current_web_results(session["id"]),
    })


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)