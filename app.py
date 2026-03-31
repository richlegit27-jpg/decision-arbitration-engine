from __future__ import annotations

import json
import mimetypes
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

from services.artifact_service import ArtifactService
from services.chat_service import ChatService
from services.memory_service import MemoryService


# =========================
# PATHS / FILES
# =========================
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
CRASH_LOG_FILE = DATA_DIR / "nova_crash.log"

MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB


# =========================
# UTILS
# =========================
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def write_crash_log(label: str, exc: Exception) -> str:
    tb = traceback.format_exc()

    log_block = (
        "\n" + "=" * 100 + "\n"
        f"[{utc_now()}] {label}\n"
        f"{type(exc).__name__}: {exc}\n\n"
        f"{tb}\n"
    )

    try:
        CRASH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CRASH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_block)
    except Exception:
        pass

    print(log_block)
    return tb


# =========================
# APP FACTORY
# =========================
def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
    )

    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # =========================
    # SERVICES
    # =========================
    chat_service = ChatService(SESSIONS_FILE, ARTIFACTS_FILE, MEMORY_FILE)
    memory_service = MemoryService(MEMORY_FILE)
    artifact_service = ArtifactService(ARTIFACTS_FILE)

    # =========================
    # ROUTES
    # =========================
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "message": "healthy",
                "debug": {
                    "timestamp": utc_now(),
                    "cwd": str(BASE_DIR),
                    "sessions_file": str(SESSIONS_FILE),
                    "memory_file": str(MEMORY_FILE),
                    "artifacts_file": str(ARTIFACTS_FILE),
                    "route_build": "no-debug-no-reloader-crash-logging-2026-03-31",
                },
            }
        )

    # =========================
    # CHAT (HARDENED)
    # =========================
    @app.route("/api/chat", methods=["POST"])
    def chat():
        try:
            payload = request.get_json(silent=True) or {}
            content = str(payload.get("content", "")).strip()
            session_id = str(payload.get("session_id", "")).strip() or "default-session"

            if not content:
                return jsonify(
                    {
                        "ok": False,
                        "assistant_message": None,
                        "session": None,
                        "debug": {
                            "error": "empty_content",
                        },
                    }
                ), 400

            result = chat_service.send_message(
                content=content,
                session_id=session_id,
                attachments=payload.get("attachments") or [],
            )

            return jsonify(result)

        except Exception as exc:
            tb = write_crash_log("CHAT ROUTE CRASH", exc)

            # HARD fallback — NEVER crash connection
            fallback_text = "Nova fallback: backend recovered from error."

            safe_session = {
                "id": "crash-session",
                "title": "Recovered Session",
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "messages": [],
                "pinned": False,
            }

            return jsonify(
                {
                    "ok": True,
                    "assistant_message": {
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": fallback_text,
                        "created_at": utc_now(),
                        "attachments": [],
                        "meta": {
                            "fallback": True,
                            "fallback_reason": "server_exception",
                        },
                    },
                    "session": safe_session,
                    "debug": {
                        "fallback": True,
                        "fallback_reason": "server_exception",
                        "trace": tb[-1000:],  # last part only
                    },
                }
            ), 200

    # =========================
    # SESSIONS
    # =========================
    @app.route("/api/sessions", methods=["GET"])
    def list_sessions():
        return jsonify({"ok": True, "sessions": chat_service.list_sessions()})

    @app.route("/api/sessions", methods=["POST"])
    def create_session():
        data = request.get_json(silent=True) or {}
        title = data.get("title") or "New Session"
        session = chat_service.create_session(title)
        return jsonify({"ok": True, "session": session})

    @app.route("/api/sessions/<session_id>", methods=["GET"])
    def get_session(session_id: str):
        session = chat_service.get_session(session_id)
        return jsonify({"ok": True, "session": session})

    @app.route("/api/sessions/<session_id>", methods=["PATCH"])
    def update_session(session_id: str):
        data = request.get_json(silent=True) or {}
        session = chat_service.update_session(session_id, data)
        return jsonify({"ok": True, "session": session})

    @app.route("/api/sessions/<session_id>", methods=["DELETE"])
    def delete_session(session_id: str):
        chat_service.delete_session(session_id)
        return jsonify({"ok": True})

    # =========================
    # ARTIFACTS
    # =========================
    @app.route("/api/artifacts", methods=["GET"])
    def list_artifacts():
        return jsonify({"ok": True, "artifacts": artifact_service.list_artifacts()})

    @app.route("/api/artifacts/<artifact_id>", methods=["GET"])
    def get_artifact(artifact_id: str):
        artifact = artifact_service.get_artifact(artifact_id)
        return jsonify({"ok": True, "artifact": artifact})

    @app.route("/api/artifacts/clean-junk", methods=["POST"])
    def clean_artifacts():
        result = artifact_service.clean_junk()
        return jsonify({"ok": True, "result": result})

    # =========================
    # UPLOADS
    # =========================
    @app.route("/api/upload", methods=["POST"])
    def upload():
        if "files" not in request.files:
            return jsonify({"ok": False, "error": "no_files"}), 400

        files = request.files.getlist("files")
        saved = []

        for file in files:
            filename = file.filename or f"upload-{uuid.uuid4().hex}"
            path = UPLOADS_DIR / filename
            file.save(path)

            saved.append(
                {
                    "filename": filename,
                    "url": f"/api/uploads/{filename}",
                    "mime": mimetypes.guess_type(filename)[0] or "application/octet-stream",
                }
            )

        return jsonify({"ok": True, "files": saved})

    @app.route("/api/uploads/<path:filename>")
    def serve_upload(filename: str):
        return send_from_directory(UPLOADS_DIR, filename)

    return app


# =========================
# ENTRYPOINT (LOCKED)
# =========================
if __name__ == "__main__":
    app = create_app()

    host = "127.0.0.1"
    port = 5001

    print("\n" + "=" * 80)
    print("Nova backend starting (LOCKED MODE)")
    print(f"URL: http://{host}:{port}")
    print("Debug: OFF | Reloader: OFF")
    print("=" * 80 + "\n")

    # 🔒 CRITICAL: no debug, no reloader (prevents silent resets)
    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )