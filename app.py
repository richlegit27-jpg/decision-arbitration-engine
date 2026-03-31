from __future__ import annotations

import json
import mimetypes
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from services.artifact_service import ArtifactService
from services.chat_service import ChatService
from services.memory_service import MemoryService


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"

MAX_CONTENT_LENGTH = 64 * 1024 * 1024

ALLOWED_UPLOAD_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "svg",
    "mp4", "webm", "mov", "m4v", "avi", "mkv",
    "mp3", "wav", "m4a", "ogg", "flac", "aac",
    "pdf", "txt", "log", "md", "json", "csv", "html", "htm", "xml", "yaml", "yml",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_trace(label: str, exc: Exception) -> str:
    tb = traceback.format_exc()
    print("\n" + "=" * 100)
    print(f"[{utc_now()}] APP ERROR: {label}")
    print(f"{type(exc).__name__}: {exc}")
    print(tb)
    print("=" * 100 + "\n")
    return tb


def read_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[-1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def guess_attachment_type(filename: str = "", mime_type: str = "") -> str:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()

    if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")):
        return "image"
    if mime.startswith("video/") or name.endswith((".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv")):
        return "video"
    if mime.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac")):
        return "audio"
    return "file"


def build_upload_url(stored_name: str) -> str:
    return f"/api/uploads/{stored_name}"


def normalize_attachment(raw: Any, source: str = "unknown") -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    filename = str(raw.get("filename") or raw.get("name") or raw.get("title") or "")
    stored_name = str(raw.get("stored_name") or raw.get("stored_filename") or raw.get("path") or "")
    mime_type = str(raw.get("mime_type") or raw.get("content_type") or raw.get("mime") or "")
    url = str(raw.get("url") or raw.get("src") or raw.get("href") or "")

    if not mime_type and filename:
        guessed, _ = mimetypes.guess_type(filename)
        mime_type = guessed or ""

    att_type = str(raw.get("type") or raw.get("kind") or guess_attachment_type(filename, mime_type)).lower()
    if att_type not in {"image", "video", "audio", "file"}:
        att_type = guess_attachment_type(filename, mime_type)

    if not url and stored_name:
        url = stored_name if stored_name.startswith(("http://", "https://", "/api/")) else build_upload_url(stored_name)

    item = {
        "id": str(raw.get("id") or uuid.uuid4()),
        "type": att_type,
        "filename": filename,
        "stored_name": stored_name,
        "mime_type": mime_type,
        "url": url,
        "size": raw.get("size"),
        "source": str(raw.get("source") or source),
        "title": raw.get("title") or filename or att_type.title(),
        "alt": raw.get("alt") or raw.get("caption") or filename or att_type.title(),
    }

    if not item["url"] and not item["filename"]:
        return None
    return item


def normalize_attachments(value: Any, source: str = "unknown") -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []

    out: list[dict[str, Any]] = []
    for raw in value:
        item = normalize_attachment(raw, source=source)
        if item:
            out.append(item)
    return out


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    item = dict(message or {})
    item["attachments"] = normalize_attachments(item.get("attachments"), source="message")
    item["meta"] = item.get("meta") or {}
    return item


def normalize_session(session: dict[str, Any] | None) -> dict[str, Any] | None:
    if not session:
        return None
    item = dict(session)
    item["messages"] = [normalize_message(m) for m in (item.get("messages") or []) if isinstance(m, dict)]
    return item


def normalize_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    item = dict(artifact or {})
    item["attachments"] = normalize_attachments(item.get("attachments"), source="artifact")
    item["meta"] = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    return item


def list_artifacts_raw() -> list[dict[str, Any]]:
    data = read_json_file(ARTIFACTS_FILE, [])
    return data if isinstance(data, list) else []


def write_artifacts_raw(items: list[dict[str, Any]]) -> None:
    write_json_file(ARTIFACTS_FILE, items)


def list_memory_raw() -> list[dict[str, Any]]:
    data = read_json_file(MEMORY_FILE, [])
    return data if isinstance(data, list) else []


def build_frontend_session_payload(session: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_session(session) or {}
    messages = normalized.get("messages") or []
    return {
        "id": normalized.get("id"),
        "title": normalized.get("title") or "New Chat",
        "created_at": normalized.get("created_at"),
        "updated_at": normalized.get("updated_at"),
        "pinned": bool(normalized.get("pinned", False)),
        "message_count": int(normalized.get("message_count", len(messages))),
        "last_message_preview": normalized.get("last_message_preview") or "",
        "messages": messages,
    }


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
    )
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    chat_service = ChatService(SESSIONS_FILE, ARTIFACTS_FILE, MEMORY_FILE)
    memory_service = MemoryService(MEMORY_FILE)
    artifact_service = ArtifactService(ARTIFACTS_FILE)

    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def api_health():
        return jsonify(
            {
                "ok": True,
                "message": "healthy",
                "debug": {
                    "timestamp": utc_now(),
                    "cwd": str(BASE_DIR),
                    "uploads_dir": str(UPLOADS_DIR),
                    "data_dir": str(DATA_DIR),
                    "sessions_file": str(SESSIONS_FILE),
                    "memory_file": str(MEMORY_FILE),
                    "artifacts_file": str(ARTIFACTS_FILE),
                    "route_build": "chat-failure-hardening-2026-03-31-001",
                    "chat_service_class": chat_service.__class__.__name__,
                    "chat_service_module": chat_service.__class__.__module__,
                },
            }
        )

    @app.get("/api/state")
    def api_state():
        try:
            sessions = [build_frontend_session_payload(s) for s in chat_service.list_sessions()]
            artifacts = [normalize_artifact(a) for a in list_artifacts_raw()]
            memory = list_memory_raw()
            return jsonify(
                {
                    "ok": True,
                    "sessions": sessions,
                    "artifacts": artifacts,
                    "memory": memory,
                    "debug": {
                        "sessions_count": len(sessions),
                        "artifacts_count": len(artifacts),
                        "memory_count": len(memory),
                    },
                }
            )
        except Exception as exc:
            trace = safe_trace("api_state", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.get("/api/uploads/<path:filename>")
    def api_uploads(filename: str):
        return send_from_directory(UPLOADS_DIR, filename, as_attachment=False)

    @app.post("/api/upload")
    def api_upload():
        try:
            uploaded_files = request.files.getlist("files")
            if not uploaded_files:
                maybe_one = request.files.get("file")
                if maybe_one:
                    uploaded_files = [maybe_one]

            if not uploaded_files:
                return jsonify({"ok": False, "message": "No files uploaded"}), 400

            saved: list[dict[str, Any]] = []

            for file in uploaded_files:
                if not file or not file.filename:
                    continue

                original_name = secure_filename(file.filename)
                if not original_name:
                    continue

                if not allowed_file(original_name):
                    return jsonify({"ok": False, "message": f"File type not allowed: {original_name}"}), 400

                stored_name = f"{uuid.uuid4().hex}_{original_name}"
                target = UPLOADS_DIR / stored_name
                file.save(target)

                mime_type = file.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
                item = {
                    "id": str(uuid.uuid4()),
                    "type": guess_attachment_type(original_name, mime_type),
                    "filename": original_name,
                    "stored_name": stored_name,
                    "mime_type": mime_type,
                    "url": build_upload_url(stored_name),
                    "size": target.stat().st_size if target.exists() else None,
                    "source": "upload",
                    "title": original_name,
                    "alt": original_name,
                }
                saved.append(item)

            if not saved:
                return jsonify({"ok": False, "message": "No valid files uploaded"}), 400

            return jsonify(
                {
                    "ok": True,
                    "files": saved,
                    "attachments": saved,
                    "debug": {
                        "uploaded_count": len(saved),
                        "types": [x.get("type") for x in saved],
                    },
                }
            )
        except Exception as exc:
            trace = safe_trace("api_upload", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.post("/api/chat")
    def api_chat():
        try:
            payload = request.get_json(silent=True) or {}
            content = str(payload.get("content") or payload.get("message") or payload.get("text") or "").strip()
            session_id = payload.get("session_id") or payload.get("sessionId")
            attachments = payload.get("attachments") or []
            route_meta = payload.get("route_meta") or payload.get("routeMeta") or {}

            if not content and not attachments:
                return jsonify(
                    {
                        "ok": False,
                        "message": "Message content or attachments required",
                        "assistant_message": None,
                        "session": None,
                        "debug": {"route_contract": "ok-assistant_message-session-debug"},
                    }
                ), 400

            result = chat_service.send_message(
                content=content,
                session_id=session_id,
                attachments=attachments,
                route_meta=route_meta,
            )

            assistant_message = normalize_message(result.get("assistant_message") or {})
            session = build_frontend_session_payload(result.get("session") or {})
            debug = result.get("debug") or {}

            return jsonify(
                {
                    "ok": True,
                    "assistant_message": assistant_message,
                    "session": session,
                    "debug": {
                        **debug,
                        "route_contract": "ok-assistant_message-session-debug",
                    },
                }
            )
        except Exception as exc:
            trace = safe_trace("api_chat", exc)
            return jsonify(
                {
                    "ok": False,
                    "message": str(exc),
                    "assistant_message": None,
                    "session": None,
                    "debug": {
                        "trace": trace,
                        "route_contract": "ok-assistant_message-session-debug",
                    },
                }
            ), 500

    @app.get("/api/sessions")
    def api_sessions_list():
        try:
            sessions = [build_frontend_session_payload(s) for s in chat_service.list_sessions()]
            return jsonify({"ok": True, "sessions": sessions})
        except Exception as exc:
            trace = safe_trace("api_sessions_list", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.post("/api/sessions")
    def api_sessions_create():
        try:
            payload = request.get_json(silent=True) or {}
            title = payload.get("title") or "New Chat"
            session = chat_service.create_session(title=title)
            return jsonify({"ok": True, "session": build_frontend_session_payload(session)})
        except Exception as exc:
            trace = safe_trace("api_sessions_create", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.get("/api/sessions/<session_id>")
    def api_sessions_read(session_id: str):
        try:
            session = chat_service.get_session(session_id)
            if not session:
                return jsonify({"ok": False, "message": "Session not found"}), 404
            return jsonify({"ok": True, "session": build_frontend_session_payload(session)})
        except Exception as exc:
            trace = safe_trace("api_sessions_read", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.patch("/api/sessions/<session_id>")
    def api_sessions_update(session_id: str):
        try:
            payload = request.get_json(silent=True) or {}
            changes: dict[str, Any] = {}
            if "title" in payload:
                changes["title"] = payload.get("title")
            if "pinned" in payload:
                changes["pinned"] = payload.get("pinned")

            session = chat_service.update_session(session_id, **changes)
            if not session:
                return jsonify({"ok": False, "message": "Session not found"}), 404

            session = chat_service.get_session(session_id)
            return jsonify({"ok": True, "session": build_frontend_session_payload(session)})
        except Exception as exc:
            trace = safe_trace("api_sessions_update", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.delete("/api/sessions/<session_id>")
    def api_sessions_delete(session_id: str):
        try:
            ok = chat_service.delete_session(session_id)
            if not ok:
                return jsonify({"ok": False, "message": "Session not found"}), 404
            sessions = [build_frontend_session_payload(s) for s in chat_service.list_sessions()]
            return jsonify({"ok": True, "deleted": True, "sessions": sessions})
        except Exception as exc:
            trace = safe_trace("api_sessions_delete", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.get("/api/artifacts")
    def api_artifacts_list():
        try:
            artifacts = [normalize_artifact(a) for a in list_artifacts_raw()]
            artifacts.sort(key=lambda x: (bool(x.get("pinned")), x.get("updated_at") or x.get("created_at") or ""), reverse=True)
            return jsonify(
                {
                    "ok": True,
                    "artifacts": artifacts,
                    "debug": {
                        "count": len(artifacts),
                        "media_count": sum(1 for a in artifacts if a.get("attachments")),
                    },
                }
            )
        except Exception as exc:
            trace = safe_trace("api_artifacts_list", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.get("/api/artifacts/<artifact_id>")
    def api_artifacts_read(artifact_id: str):
        try:
            artifact = next((a for a in list_artifacts_raw() if str(a.get("id")) == artifact_id), None)
            if not artifact:
                return jsonify({"ok": False, "message": "Artifact not found"}), 404
            return jsonify({"ok": True, "artifact": normalize_artifact(artifact)})
        except Exception as exc:
            trace = safe_trace("api_artifacts_read", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.get("/api/memory")
    def api_memory_list():
        try:
            items = list_memory_raw()
            return jsonify({"ok": True, "memory": items, "count": len(items)})
        except Exception as exc:
            trace = safe_trace("api_memory_list", exc)
            return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    @app.errorhandler(413)
    def handle_too_large(_exc):
        return jsonify({"ok": False, "message": "Upload too large"}), 413

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        trace = safe_trace("unhandled_exception", exc)
        return jsonify({"ok": False, "message": str(exc), "debug": {"trace": trace}}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("NOVA_HOST") or os.getenv("APP_HOST") or "127.0.0.1"
    port = 5001
    app.run(host=host, port=port, debug=False, use_reloader=False)