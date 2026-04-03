import base64
import json
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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


# =========================================================
# paths / config
# =========================================================

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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()
NOVA_IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5").strip()
NOVA_IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024").strip()
NOVA_IMAGE_QUALITY = os.getenv("NOVA_IMAGE_QUALITY", "high").strip()
NOVA_HOST = os.getenv("APP_HOST") or os.getenv("NOVA_HOST") or "127.0.0.1"
NOVA_PORT = int(os.getenv("APP_PORT") or os.getenv("NOVA_PORT") or "5001")
NOVA_DEBUG = str(os.getenv("NOVA_DEBUG", "true")).lower() in {"1", "true", "yes", "on"}

MAX_CONTENT_LENGTH = 64 * 1024 * 1024
MAX_SESSIONS = 100
MAX_MESSAGES_PER_SESSION = 200

ALLOWED_UPLOAD_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "bmp",
    "pdf", "txt", "log", "md", "json", "csv", "html", "htm",
    "xml", "yaml", "yml", "mp4", "mov", "avi", "mkv", "webm"
}

TEXT_EXTENSIONS = {"txt", "log", "md", "json", "csv", "html", "htm", "xml", "yaml", "yml"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}

URL_RE = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)


# =========================================================
# app
# =========================================================

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

client = OpenAI(api_key=OPENAI_API_KEY) if (OpenAI and OPENAI_API_KEY) else None


# =========================================================
# utilities
# =========================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_file(path: Path, default: Any) -> None:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")


def load_json(path: Path, default: Any) -> Any:
    ensure_file(path, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def guess_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext


def allowed_file(filename: str) -> bool:
    ext = guess_ext(filename)
    return bool(ext) and ext in ALLOWED_UPLOAD_EXTENSIONS


def mime_for_path(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def truncate(text: str, limit: int) -> str:
    text = safe_str(text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def list_sessions() -> List[Dict[str, Any]]:
    return load_json(SESSIONS_FILE, [])


def save_sessions(items: List[Dict[str, Any]]) -> None:
    save_json(SESSIONS_FILE, items[:MAX_SESSIONS])


def list_artifacts() -> List[Dict[str, Any]]:
    return load_json(ARTIFACTS_FILE, [])


def save_artifacts(items: List[Dict[str, Any]]) -> None:
    save_json(ARTIFACTS_FILE, items)


def list_memory() -> List[Dict[str, Any]]:
    return load_json(MEMORY_FILE, [])


def save_memory(items: List[Dict[str, Any]]) -> None:
    save_json(MEMORY_FILE, items)


def get_or_create_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    sessions = list_sessions()

    if session_id:
        for sess in sessions:
            if sess.get("id") == session_id:
                return sess

    new_session = {
        "id": make_id("session"),
        "title": "New chat",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "pinned": False,
        "message_count": 0,
        "last_message_preview": "",
        "messages": [],
    }
    sessions.insert(0, new_session)
    save_sessions(sessions)
    return new_session


def upsert_session(session: Dict[str, Any]) -> Dict[str, Any]:
    sessions = list_sessions()
    found = False
    for i, sess in enumerate(sessions):
        if sess.get("id") == session.get("id"):
            sessions[i] = session
            found = True
            break
    if not found:
        sessions.insert(0, session)

    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    save_sessions(sessions)
    return session


def append_message(
    session: Dict[str, Any],
    role: str,
    content: str,
    kind: str = "chat",
    attachments: Optional[List[Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    msg = {
        "id": make_id("msg"),
        "role": role,
        "content": safe_str(content),
        "kind": kind,
        "attachments": attachments or [],
        "meta": meta or {},
        "created_at": now_iso(),
    }
    session.setdefault("messages", []).append(msg)
    session["messages"] = session["messages"][-MAX_MESSAGES_PER_SESSION:]
    session["updated_at"] = now_iso()
    session["message_count"] = len(session["messages"])
    session["last_message_preview"] = truncate(content, 120)

    if role == "user" and content.strip():
        session["title"] = truncate(content.strip().splitlines()[0], 50)

    upsert_session(session)
    return msg


def normalize_artifact_viewer(artifact: Dict[str, Any]) -> Dict[str, Any]:
    kind = artifact.get("kind", "chat_reply")
    content = safe_str(artifact.get("content", ""))

    viewer = artifact.get("viewer") or {}
    preview = artifact.get("preview") or truncate(content, 400)

    if kind in {"image_generation", "image_analysis"}:
        image_url = artifact.get("file_url") or viewer.get("image_url") or ""
        viewer.setdefault("kind", kind)
        viewer.setdefault("title", artifact.get("title", "Image"))
        viewer.setdefault("image_url", image_url)
        viewer.setdefault("content", content)
    elif kind == "web_result":
        viewer.setdefault("kind", kind)
        viewer.setdefault("title", artifact.get("title", "Web"))
        viewer.setdefault("content", content)
        viewer.setdefault("url", artifact.get("meta", {}).get("url", ""))
    else:
        viewer.setdefault("kind", kind)
        viewer.setdefault("title", artifact.get("title", "Artifact"))
        viewer.setdefault("content", content)

    artifact["preview"] = preview
    artifact["viewer"] = viewer
    return artifact


def create_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    content: str,
    file_path: Optional[Path] = None,
    meta: Optional[Dict[str, Any]] = None,
    viewer: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    artifacts = list_artifacts()

    file_url = ""
    if file_path and file_path.exists():
        file_url = f"/api/uploads/{file_path.name}"

    artifact = {
        "id": make_id("artifact"),
        "session_id": session_id,
        "kind": kind,
        "title": title,
        "content": safe_str(content),
        "preview": truncate(content, 400),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "file_name": file_path.name if file_path else "",
        "file_url": file_url,
        "meta": meta or {},
        "viewer": viewer or {},
    }
    artifact = normalize_artifact_viewer(artifact)
    artifacts.insert(0, artifact)
    save_artifacts(artifacts)
    return artifact


def session_payload(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": session.get("id"),
        "title": session.get("title", "New chat"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned", False)),
        "message_count": int(session.get("message_count", len(session.get("messages", [])))),
        "last_message_preview": session.get("last_message_preview", ""),
        "messages": session.get("messages", []),
    }


def get_memory_context(limit: int = 12) -> str:
    items = list_memory()[:limit]
    if not items:
        return ""
    lines = []
    for item in items:
        text = safe_str(item.get("text")).strip()
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def maybe_save_memory_from_user_text(text: str) -> None:
    lowered = text.lower()
    triggers = [
        "remember that ",
        "remember this ",
        "my name is ",
        "i prefer ",
        "from now on ",
    ]
    if any(t in lowered for t in triggers):
        items = list_memory()
        items.insert(0, {"id": make_id("memory"), "text": text.strip(), "created_at": now_iso()})
        save_memory(items[:200])


def uploaded_file_record(saved_name: str, original_name: str) -> Dict[str, Any]:
    path = UPLOADS_DIR / saved_name
    ext = guess_ext(original_name)
    return {
        "id": make_id("file"),
        "name": original_name,
        "stored_name": saved_name,
        "url": f"/api/uploads/{saved_name}",
        "mime": mime_for_path(path),
        "size": path.stat().st_size if path.exists() else 0,
        "ext": ext,
    }


# =========================================================
# web
# =========================================================

def fetch_web_page(url: str) -> Dict[str, Any]:
    if requests is None:
        return {
            "ok": False,
            "title": "Web fetch failed",
            "content": "Python package 'requests' is not installed.",
            "meta": {"url": url, "used_ssl_fallback": False, "warning": "requests missing"},
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Nova Local App) AppleWebKit/537.36 Chrome Safari"
    }

    used_ssl_fallback = False
    warning = ""
    try:
        res = requests.get(url, timeout=15, headers=headers)
        res.raise_for_status()
    except requests.exceptions.SSLError:
        used_ssl_fallback = True
        warning = "SSL verification fallback was used."
        try:
            res = requests.get(url, timeout=15, headers=headers, verify=False)
            res.raise_for_status()
        except Exception as e:
            return {
                "ok": False,
                "title": "Web fetch failed",
                "content": str(e),
                "meta": {"url": url, "used_ssl_fallback": True, "warning": warning},
            }
    except Exception as e:
        return {
            "ok": False,
            "title": "Web fetch failed",
            "content": str(e),
            "meta": {"url": url, "used_ssl_fallback": used_ssl_fallback, "warning": warning},
        }

    html = res.text or ""
    title = url
    description = ""
    text = ""

    if BeautifulSoup:
        try:
            soup = BeautifulSoup(html, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if desc and desc.get("content"):
                description = desc.get("content").strip()

            for bad in soup(["script", "style", "noscript"]):
                bad.extract()

            text = " ".join(soup.get_text(" ", strip=True).split())
        except Exception:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    else:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()

    summary = text[:3500].strip()
    if description:
        content = f"{description}\n\n{summary}".strip()
    else:
        content = summary

    return {
        "ok": True,
        "title": title or url,
        "content": content or f"Fetched {url}",
        "meta": {
            "url": url,
            "used_ssl_fallback": used_ssl_fallback,
            "warning": warning,
            "description": description,
        },
    }


# =========================================================
# image analysis
# =========================================================

def analyze_image_with_openai(user_prompt: str, image_path: Path) -> Dict[str, Any]:
    if not client:
        return {"ok": False, "content": "OpenAI is not configured."}

    mime = mime_for_path(image_path)
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    data_url = f"data:{mime};base64,{image_b64}"

    system_text = (
        "You are a precise vision assistant inside a local app named Nova. "
        "Describe what is in the image clearly and directly. "
        "If the user asks a specific question, answer that question first."
    )

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_text}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_prompt or "What is in this image?"},
                        {"type": "input_image", "image_url": data_url},
                    ],
                },
            ],
        )
        text = getattr(response, "output_text", "") or "I analyzed the image."
        return {"ok": True, "content": text}
    except Exception as e:
        return {"ok": False, "content": f"Image analysis failed.\n\n{e}"}


# =========================================================
# real /image generation
# =========================================================

def generate_image_with_openai(prompt: str) -> Dict[str, Any]:
    if not client:
        return {
            "ok": False,
            "content": "OpenAI is not configured. Set OPENAI_API_KEY first.",
        }

    clean_prompt = safe_str(prompt).strip()
    if not clean_prompt:
        return {
            "ok": False,
            "content": "Missing image prompt.",
        }

    try:
        result = client.images.generate(
            model=NOVA_IMAGE_MODEL,
            prompt=clean_prompt,
            size=NOVA_IMAGE_SIZE,
            quality=NOVA_IMAGE_QUALITY,
        )

        data = getattr(result, "data", None) or []
        if not data:
            return {
                "ok": False,
                "content": "Image generation returned no data.",
            }

        first = data[0]
        b64_json = getattr(first, "b64_json", None)
        image_url = getattr(first, "url", None)

        if b64_json:
            image_bytes = base64.b64decode(b64_json)
            file_name = f"{uuid.uuid4().hex}.png"
            out_path = UPLOADS_DIR / file_name
            out_path.write_bytes(image_bytes)
            return {
                "ok": True,
                "content": clean_prompt,
                "file_path": out_path,
                "file_url": f"/api/uploads/{file_name}",
                "mime": "image/png",
            }

        if image_url:
            if requests is None:
                return {
                    "ok": False,
                    "content": "Image generation returned a URL, but requests is not installed to download it.",
                }
            img_res = requests.get(image_url, timeout=30)
            img_res.raise_for_status()
            ext = ".png"
            ctype = (img_res.headers.get("content-type") or "").lower()
            if "jpeg" in ctype or "jpg" in ctype:
                ext = ".jpg"
            elif "webp" in ctype:
                ext = ".webp"

            file_name = f"{uuid.uuid4().hex}{ext}"
            out_path = UPLOADS_DIR / file_name
            out_path.write_bytes(img_res.content)
            return {
                "ok": True,
                "content": clean_prompt,
                "file_path": out_path,
                "file_url": f"/api/uploads/{file_name}",
                "mime": ctype or mime_for_path(out_path),
            }

        return {
            "ok": False,
            "content": "Image generation succeeded but returned neither b64_json nor a downloadable URL.",
        }

    except Exception as e:
        return {
            "ok": False,
            "content": f"Image generation failed.\n\n{e}",
        }


# =========================================================
# text chat
# =========================================================

def build_text_reply(user_text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    if not client:
        return {
            "ok": True,
            "content": f"I heard you.\n\n{user_text}",
            "meta": {
                "model": "fallback",
                "memory_used": False,
            },
        }

    memory_context = get_memory_context()
    recent_messages = session.get("messages", [])[-10:]

    input_items: List[Dict[str, Any]] = []
    system_prompt = (
        "You are Nova, a direct helpful assistant inside a local app. "
        "Be concise, useful, and grounded."
    )
    if memory_context:
        system_prompt += f"\n\nUseful remembered context:\n{memory_context}"

    input_items.append({
        "role": "system",
        "content": [{"type": "input_text", "text": system_prompt}],
    })

    for msg in recent_messages:
        role = msg.get("role", "user")
        content = safe_str(msg.get("content", ""))
        if not content.strip():
            continue
        input_items.append({
            "role": "assistant" if role == "assistant" else "user",
            "content": [{"type": "input_text", "text": content}],
        })

    input_items.append({
        "role": "user",
        "content": [{"type": "input_text", "text": user_text}],
    })

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=input_items,
        )
        text = getattr(response, "output_text", "") or "No response."
        return {
            "ok": True,
            "content": text,
            "meta": {
                "model": OPENAI_MODEL,
                "memory_used": bool(memory_context),
            },
        }
    except Exception as e:
        return {
            "ok": False,
            "content": f"Assistant reply failed.\n\n{e}",
            "meta": {
                "model": OPENAI_MODEL,
                "memory_used": bool(memory_context),
            },
        }


# =========================================================
# routes
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "ok": True,
        "status": "healthy",
        "time": now_iso(),
        "openai_configured": bool(client),
        "openai_model": OPENAI_MODEL,
        "image_model": NOVA_IMAGE_MODEL,
    })


@app.route("/api/state", methods=["GET"])
def api_state():
    sessions = list_sessions()
    artifacts = [normalize_artifact_viewer(a) for a in list_artifacts()]
    memory = list_memory()

    active_session_id = request.args.get("session_id", "").strip()
    active_session = None

    if active_session_id:
        for sess in sessions:
            if sess.get("id") == active_session_id:
                active_session = sess
                break

    if active_session is None:
        active_session = sessions[0] if sessions else get_or_create_session()

    return jsonify({
        "ok": True,
        "sessions": [session_payload(s) for s in sessions],
        "session": session_payload(active_session),
        "memory": memory,
        "artifacts": artifacts,
        "web": [a for a in artifacts if a.get("kind") == "web_result"][:20],
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    files = request.files.getlist("files")
    if not files:
        single = request.files.get("file")
        if single:
            files = [single]

    if not files:
        return jsonify({"ok": False, "error": "No files uploaded."}), 400

    saved: List[Dict[str, Any]] = []
    for file in files:
        if not file or not file.filename:
            continue
        original_name = secure_filename(file.filename)
        if not allowed_file(original_name):
            continue
        ext = Path(original_name).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{ext}"
        out_path = UPLOADS_DIR / stored_name
        file.save(out_path)
        saved.append(uploaded_file_record(stored_name, original_name))

    if not saved:
        return jsonify({"ok": False, "error": "No supported files were uploaded."}), 400

    return jsonify({"ok": True, "files": saved})


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename, as_attachment=False)


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    artifacts = [normalize_artifact_viewer(a) for a in list_artifacts()]
    return jsonify({"ok": True, "artifacts": artifacts})


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_read(artifact_id: str):
    for artifact in list_artifacts():
        if artifact.get("id") == artifact_id:
            return jsonify({"ok": True, "artifact": normalize_artifact_viewer(artifact)})
    return jsonify({"ok": False, "error": "Artifact not found."}), 404


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}

    user_text = (
        payload.get("content")
        or payload.get("message")
        or payload.get("text")
        or ""
    ).strip()

    session_id = payload.get("session_id") or ""
    attachments = payload.get("attachments") or []

    session = get_or_create_session(session_id)
    maybe_save_memory_from_user_text(user_text)

    append_message(
        session,
        "user",
        user_text,
        kind="user_message",
        attachments=attachments,
        meta={"attachment_count": len(attachments)},
    )

    debug: Dict[str, Any] = {
        "latest_user_text": user_text,
        "attachment_count": len(attachments),
        "route": "chat",
        "model": OPENAI_MODEL,
    }

    # -----------------------------------------------------
    # explicit /image real generation
    # -----------------------------------------------------
    if user_text.lower().startswith("/image"):
        prompt = user_text[6:].strip()
        debug["route"] = "image_generation"

        result = generate_image_with_openai(prompt)
        if not result.get("ok"):
            assistant_text = result.get("content", "Image generation failed.")
            append_message(
                session,
                "assistant",
                assistant_text,
                kind="chat_reply",
                meta={"image_generation": False, "prompt": prompt},
            )
            return jsonify({
                "ok": False,
                "assistant_message": assistant_text,
                "message": assistant_text,
                "session": session_payload(session),
                "debug": debug,
            })

        file_path = result["file_path"]
        file_url = result["file_url"]

        assistant_text = f"![generated image]({file_url})\n\n**Prompt:** {prompt}"
        assistant_attachments = [{
            "name": file_path.name,
            "url": file_url,
            "mime": result.get("mime", mime_for_path(file_path)),
            "kind": "image",
        }]

        append_message(
            session,
            "assistant",
            assistant_text,
            kind="chat_reply",
            attachments=assistant_attachments,
            meta={
                "image_generation": True,
                "prompt": prompt,
                "file_url": file_url,
            },
        )

        artifact = create_artifact(
            session_id=session["id"],
            kind="image_generation",
            title=f"Image - {truncate(prompt, 60) or 'Generated image'}",
            content=prompt,
            file_path=file_path,
            meta={
                "prompt": prompt,
                "model": NOVA_IMAGE_MODEL,
                "size": NOVA_IMAGE_SIZE,
                "quality": NOVA_IMAGE_QUALITY,
            },
            viewer={
                "kind": "image_generation",
                "title": f"Image - {truncate(prompt, 60) or 'Generated image'}",
                "image_url": file_url,
                "content": prompt,
            },
        )

        debug["artifact_id"] = artifact["id"]

        return jsonify({
            "ok": True,
            "assistant_message": assistant_text,
            "message": assistant_text,
            "session": session_payload(session),
            "artifact": artifact,
            "debug": debug,
        })

    # -----------------------------------------------------
    # attachment image analysis
    # -----------------------------------------------------
    if attachments:
        first = attachments[0]
        stored_name = first.get("stored_name") or Path(first.get("url", "")).name
        original_name = first.get("name") or stored_name
        ext = guess_ext(original_name)

        if stored_name and ext in IMAGE_EXTENSIONS:
            debug["route"] = "image_analysis"
            image_path = UPLOADS_DIR / stored_name

            prompt = user_text or "What is this image?"
            result = analyze_image_with_openai(prompt, image_path)

            assistant_text = result.get("content", "I analyzed the image.")
            append_message(
                session,
                "assistant",
                assistant_text,
                kind="chat_reply",
                attachments=[{
                    "name": original_name,
                    "url": f"/api/uploads/{stored_name}",
                    "mime": mime_for_path(image_path),
                    "kind": "image",
                }],
                meta={"image_analysis": bool(result.get("ok")), "prompt": prompt},
            )

            artifact = create_artifact(
                session_id=session["id"],
                kind="image_analysis",
                title=f"Image analysis - {truncate(original_name, 60)}",
                content=assistant_text,
                file_path=image_path,
                meta={
                    "prompt": prompt,
                    "source_name": original_name,
                    "model": OPENAI_MODEL,
                },
                viewer={
                    "kind": "image_analysis",
                    "title": f"Image analysis - {truncate(original_name, 60)}",
                    "image_url": f"/api/uploads/{stored_name}",
                    "content": assistant_text,
                },
            )

            debug["artifact_id"] = artifact["id"]

            return jsonify({
                "ok": bool(result.get("ok")),
                "assistant_message": assistant_text,
                "message": assistant_text,
                "session": session_payload(session),
                "artifact": artifact,
                "debug": debug,
            })

        if stored_name and ext in VIDEO_EXTENSIONS:
            debug["route"] = "video_analysis"
            video_url = f"/api/uploads/{stored_name}"
            assistant_text = (
                "Video analysis routing is live at first pass.\n\n"
                f"Attached video: `{original_name}`\n"
                "Next step is deeper frame/audio extraction."
            )
            append_message(
                session,
                "assistant",
                assistant_text,
                kind="chat_reply",
                attachments=[{
                    "name": original_name,
                    "url": video_url,
                    "mime": mime_for_path(UPLOADS_DIR / stored_name),
                    "kind": "video",
                }],
                meta={"video_analysis": True},
            )

            artifact = create_artifact(
                session_id=session["id"],
                kind="video_analysis",
                title=f"Video analysis - {truncate(original_name, 60)}",
                content=assistant_text,
                file_path=UPLOADS_DIR / stored_name,
                meta={"source_name": original_name},
                viewer={
                    "kind": "video_analysis",
                    "title": f"Video analysis - {truncate(original_name, 60)}",
                    "content": assistant_text,
                    "video_url": video_url,
                },
            )

            debug["artifact_id"] = artifact["id"]

            return jsonify({
                "ok": True,
                "assistant_message": assistant_text,
                "message": assistant_text,
                "session": session_payload(session),
                "artifact": artifact,
                "debug": debug,
            })

    # -----------------------------------------------------
    # /web or plain URL auto-route
    # -----------------------------------------------------
    web_url = ""
    if user_text.lower().startswith("/web "):
        web_url = user_text[5:].strip()
    else:
        found_urls = URL_RE.findall(user_text)
        if found_urls:
            web_url = found_urls[0]

    if web_url:
        debug["route"] = "web"

        result = fetch_web_page(web_url)
        assistant_text = result["content"] if result["ok"] else f"{result['title']}.\n\n{result['content']}"

        append_message(
            session,
            "assistant",
            assistant_text,
            kind="chat_reply",
            meta={"web": result.get("meta", {})},
        )

        artifact = create_artifact(
            session_id=session["id"],
            kind="web_result",
            title=result.get("title", "Web"),
            content=assistant_text,
            meta=result.get("meta", {}),
            viewer={
                "kind": "web_result",
                "title": result.get("title", "Web"),
                "content": assistant_text,
                "url": result.get("meta", {}).get("url", ""),
            },
        )

        debug["artifact_id"] = artifact["id"]
        debug["web"] = result.get("meta", {})

        return jsonify({
            "ok": bool(result.get("ok")),
            "assistant_message": assistant_text,
            "message": assistant_text,
            "session": session_payload(session),
            "artifact": artifact,
            "debug": debug,
        })

    # -----------------------------------------------------
    # normal chat
    # -----------------------------------------------------
    result = build_text_reply(user_text, session)
    assistant_text = result.get("content", "No response.")

    append_message(
        session,
        "assistant",
        assistant_text,
        kind="chat_reply",
        meta=result.get("meta", {}),
    )

    artifact = create_artifact(
        session_id=session["id"],
        kind="chat_reply",
        title=f"Chat Reply - {truncate(assistant_text, 50)}",
        content=assistant_text,
        meta=result.get("meta", {}),
        viewer={
            "kind": "chat_reply",
            "title": f"Chat Reply - {truncate(assistant_text, 50)}",
            "content": assistant_text,
        },
    )

    debug["artifact_id"] = artifact["id"]
    debug.update(result.get("meta", {}))

    return jsonify({
        "ok": bool(result.get("ok", True)),
        "assistant_message": assistant_text,
        "message": assistant_text,
        "session": session_payload(session),
        "artifact": artifact,
        "debug": debug,
    })


# =========================================================
# boot defaults
# =========================================================

ensure_file(SESSIONS_FILE, [])
ensure_file(ARTIFACTS_FILE, [])
ensure_file(MEMORY_FILE, [])

if not list_sessions():
    get_or_create_session()


if __name__ == "__main__":
    app.run(host=NOVA_HOST, port=NOVA_PORT, debug=NOVA_DEBUG)