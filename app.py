from __future__ import annotations

import base64
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

APP_HOST = os.getenv("NOVA_HOST", os.getenv("APP_HOST", "127.0.0.1"))
APP_PORT = int(os.getenv("NOVA_PORT", os.getenv("APP_PORT", "5001")))
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5")
IMAGE_SIZE = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")

ALLOWED_UPLOAD_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
    ".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv",
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",
    ".pdf", ".txt", ".log", ".md", ".json", ".csv", ".html", ".htm", ".xml", ".yaml", ".yml"
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_FILE.exists():
        write_json(SESSIONS_FILE, [])
    if not ARTIFACTS_FILE.exists():
        write_json(ARTIFACTS_FILE, [])
    if not MEMORY_FILE.exists():
        write_json(MEMORY_FILE, [])


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def truncate_text(value: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def safe_filename(name: str) -> str:
    cleaned = secure_filename(name or "file")
    return cleaned or f"file-{uuid.uuid4().hex}"


def ext_for_filename(name: str, fallback: str = ".bin") -> str:
    suffix = Path(name or "").suffix.lower()
    return suffix if suffix else fallback


def guess_media_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
        return "image"
    if suffix in {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"}:
        return "video"
    if suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}:
        return "audio"
    return "file"


@dataclass
class JsonStore:
    path: Path

    def load(self, default: Any) -> Any:
        return read_json(self.path, default)

    def save(self, value: Any) -> None:
        write_json(self.path, value)


class ArtifactService:
    def __init__(self, artifacts_file: Path) -> None:
        self.store = JsonStore(artifacts_file)

    def list_artifacts(self) -> list[dict[str, Any]]:
        items = self.store.load([])
        if not isinstance(items, list):
            return []
        items.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return items

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        for item in self.list_artifacts():
            if item.get("id") == artifact_id:
                return item
        return None

    def save_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        items = self.list_artifacts()
        updated = False
        for index, item in enumerate(items):
            if item.get("id") == artifact.get("id"):
                items[index] = artifact
                updated = True
                break
        if not updated:
            items.append(artifact)
        items.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        self.store.save(items)
        return artifact

    def create_artifact(
        self,
        *,
        session_id: str,
        title: str,
        kind: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        meta: dict[str, Any] | None = None,
        pinned: bool = False,
    ) -> dict[str, Any]:
        ts = now_iso()
        artifact = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "title": title,
            "kind": kind,
            "content": content,
            "attachments": attachments or [],
            "created_at": ts,
            "updated_at": ts,
            "pinned": bool(pinned),
            "meta": meta or {},
        }
        return self.save_artifact(artifact)


class SessionService:
    def __init__(self, sessions_file: Path) -> None:
        self.store = JsonStore(sessions_file)

    def list_sessions(self) -> list[dict[str, Any]]:
        items = self.store.load([])
        if not isinstance(items, list):
            return []
        items.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return items

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for item in self.list_sessions():
            if item.get("id") == session_id:
                return item
        return None

    def ensure_session(self, session_id: str | None = None, title: str | None = None) -> dict[str, Any]:
        items = self.list_sessions()
        if session_id:
            for item in items:
                if item.get("id") == session_id:
                    return item

        ts = now_iso()
        session = {
            "id": session_id or str(uuid.uuid4()),
            "title": title or "New Chat",
            "created_at": ts,
            "updated_at": ts,
            "pinned": False,
            "message_count": 0,
            "last_message_preview": "",
            "messages": [],
        }
        items.append(session)
        self.store.save(items)
        return session

    def update_session(self, session: dict[str, Any]) -> dict[str, Any]:
        items = self.list_sessions()
        updated = False
        for index, item in enumerate(items):
            if item.get("id") == session.get("id"):
                items[index] = session
                updated = True
                break
        if not updated:
            items.append(session)
        items.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        self.store.save(items)
        return session

    def append_message(self, session_id: str, message: dict[str, Any]) -> dict[str, Any]:
        session = self.ensure_session(session_id)
        messages = session.get("messages") or []
        if not isinstance(messages, list):
            messages = []
        messages.append(message)
        session["messages"] = messages
        session["message_count"] = len(messages)
        session["updated_at"] = now_iso()
        session["last_message_preview"] = truncate_text(message.get("content", ""))
        if session.get("title") in {"", "New Chat"} and message.get("role") == "user":
            session["title"] = truncate_text(message.get("content", ""), 40) or "New Chat"
        return self.update_session(session)


class ChatEngine:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if (OpenAI and os.getenv("OPENAI_API_KEY")) else None

    def _assistant_text(self, user_text: str, attachments: list[dict[str, Any]]) -> str:
        if not self.client:
            if user_text.strip().startswith("/image "):
                prompt = user_text.strip()[7:].strip()
                return f"Generated image requested for: {prompt}"
            return "Nova is running. Set OPENAI_API_KEY for real model replies."

        if user_text.strip().startswith("/image "):
            prompt = user_text.strip()[7:].strip()
            return f"Generated image requested for: {prompt}"

        prompt = user_text.strip() or "Hello"
        attachment_lines: list[str] = []
        for item in attachments:
            attachment_lines.append(
                f"- {item.get('filename','attachment')} ({item.get('mime_type') or item.get('type') or 'file'})"
            )

        system = (
            "You are Nova, a direct helpful local assistant inside a web app. "
            "Be concise, clear, and practical. "
            "If attachments are present, acknowledge them naturally."
        )
        user = prompt
        if attachment_lines:
            user += "\n\nAttachments:\n" + "\n".join(attachment_lines)

        try:
            resp = self.client.responses.create(
                model=CHAT_MODEL,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = getattr(resp, "output_text", "") or ""
            return text.strip() or "Done."
        except Exception as exc:
            return f"Nova hit an API error: {exc}"

    def generate_image(self, prompt: str) -> dict[str, Any]:
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("Image prompt is required.")

        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        try:
            result = self.client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                size=IMAGE_SIZE,
            )
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

        data = getattr(result, "data", None) or []
        if not data:
            raise RuntimeError("No image data returned.")

        item = data[0]
        b64 = getattr(item, "b64_json", None)
        image_url = getattr(item, "url", None)

        if b64:
            raw = base64.b64decode(b64)
            filename = f"generated_{uuid.uuid4().hex}.png"
            path = UPLOADS_DIR / filename
            path.write_bytes(raw)
            return {
                "type": "image",
                "filename": filename,
                "url": f"/api/uploads/{filename}",
                "mime_type": "image/png",
                "size": len(raw),
                "prompt": prompt,
            }

        if image_url:
            return {
                "type": "image",
                "filename": "",
                "url": image_url,
                "mime_type": "image/png",
                "size": 0,
                "prompt": prompt,
            }

        raise RuntimeError("No supported image payload returned.")


ensure_dirs()
artifact_service = ArtifactService(ARTIFACTS_FILE)
session_service = SessionService(SESSIONS_FILE)
chat_engine = ChatEngine()


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "debug": {
                    "cwd": str(BASE_DIR),
                    "chat_model": CHAT_MODEL,
                    "image_model": IMAGE_MODEL,
                    "image_size": IMAGE_SIZE,
                    "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
                    "route_build": "artifact-image-reuse-lock-2026-04-02-001",
                    "timestamp": now_iso(),
                },
            }
        )

    @app.get("/api/uploads/<path:filename>")
    def uploaded_file(filename: str):
        return send_from_directory(UPLOADS_DIR, filename)

    @app.get("/api/state")
    def api_state():
        sessions = session_service.list_sessions()
        return jsonify(
            {
                "ok": True,
                "sessions": sessions,
                "memory": read_json(MEMORY_FILE, []),
                "debug": {
                    "session_count": len(sessions),
                    "artifact_count": len(artifact_service.list_artifacts()),
                },
            }
        )

    @app.get("/api/artifacts")
    def api_artifacts():
        artifacts = artifact_service.list_artifacts()
        media_count = 0
        for artifact in artifacts:
            for item in ((artifact.get("meta") or {}).get("media") or []):
                if isinstance(item, dict) and item.get("type") in {"image", "video", "audio"}:
                    media_count += 1
        return jsonify(
            {
                "ok": True,
                "artifacts": artifacts,
                "debug": {
                    "count": len(artifacts),
                    "media_count": media_count,
                },
            }
        )

    @app.get("/api/artifacts/<artifact_id>")
    def api_artifact_read(artifact_id: str):
        artifact = artifact_service.get_artifact(artifact_id)
        if not artifact:
            return jsonify({"ok": False, "error": "Artifact not found."}), 404
        return jsonify({"ok": True, "artifact": artifact})

    @app.post("/api/upload")
    def api_upload():
        files = request.files.getlist("files")
        saved: list[dict[str, Any]] = []

        for file in files:
            if not file or not file.filename:
                continue
            original_name = file.filename
            suffix = Path(original_name).suffix.lower()
            if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
                continue

            filename = f"{uuid.uuid4().hex}{suffix}"
            path = UPLOADS_DIR / filename
            file.save(path)

            saved.append(
                {
                    "id": str(uuid.uuid4()),
                    "filename": original_name,
                    "stored_filename": filename,
                    "url": f"/api/uploads/{filename}",
                    "mime_type": file.mimetype or "",
                    "size": path.stat().st_size,
                    "type": guess_media_type(original_name),
                }
            )

        return jsonify({"ok": True, "files": saved, "count": len(saved)})

    @app.post("/api/chat")
    def api_chat():
        payload = request.get_json(silent=True) or {}
        content = str(payload.get("content") or payload.get("message") or "").strip()
        session_id = str(payload.get("session_id") or "").strip() or str(uuid.uuid4())
        incoming_attachments = payload.get("attachments") or []
        attachments = incoming_attachments if isinstance(incoming_attachments, list) else []

        session = session_service.ensure_session(session_id)

        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": content,
            "attachments": attachments,
            "created_at": now_iso(),
        }
        session_service.append_message(session["id"], user_message)

        generated_media: list[dict[str, Any]] = []
        assistant_text = ""

        if content.startswith("/image "):
            prompt = content[7:].strip()
            try:
                image_item = chat_engine.generate_image(prompt)
                generated_media.append(image_item)
                assistant_text = f"![generated image]({image_item['url']})\n\nGenerated from prompt: {prompt}"
            except Exception as exc:
                assistant_text = f"Image generation failed: {exc}"
        else:
            assistant_text = chat_engine._assistant_text(content, attachments)

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_text,
            "attachments": generated_media,
            "created_at": now_iso(),
        }
        session = session_service.append_message(session["id"], assistant_message)

        artifact_meta: dict[str, Any] = {
            "role": "assistant",
            "message_id": assistant_message["id"],
            "model": CHAT_MODEL,
            "artifact_source": "chat_service_autosave",
            "attachments_count": len(generated_media),
        }
        if generated_media:
            artifact_meta["media"] = generated_media
            artifact_meta["document_used"] = False
            artifact_meta["web"] = {"used": False}

        artifact_kind = "generated_image" if generated_media else "chat_reply"
        artifact_title = (
            f"Generated Image - {truncate_text(content[7:].strip(), 64)}"
            if generated_media
            else f"Chat Reply - {truncate_text(assistant_text, 64) or 'Assistant'}"
        )

        artifact = artifact_service.create_artifact(
            session_id=session["id"],
            title=artifact_title,
            kind=artifact_kind,
            content=assistant_text,
            attachments=generated_media,
            meta=artifact_meta,
        )

        return jsonify(
            {
                "ok": True,
                "message": assistant_message,
                "assistant_message": assistant_message,
                "session": session,
                "artifacts": artifact_service.list_artifacts(),
                "debug": {
                    "generated_media_count": len(generated_media),
                    "artifact_id": artifact["id"],
                    "route_build": "artifact-image-reuse-lock-2026-04-02-001",
                },
            }
        )

    return app


app = create_app()

if __name__ == "__main__":
    print(f"Nova running on http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=False, use_reloader=False)