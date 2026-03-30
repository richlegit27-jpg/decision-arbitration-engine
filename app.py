from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request, send_from_directory

from services.artifact_service import ArtifactService
from services.chat_service import ChatService


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

artifact_service = ArtifactService(str(DATA_DIR))
chat_service = ChatService(str(DATA_DIR), artifact_service=artifact_service)


def json_ok(payload: Dict[str, Any], status: int = 200):
    return jsonify(payload), status


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return json_ok(
        {
            "ok": True,
            "service": "nova",
            "port": int(os.getenv("APP_PORT", "5001")),
            "cwd": str(BASE_DIR),
        }
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        content = (data.get("content") or "").strip()
        session_id = (data.get("session_id") or "default-session").strip()
        attachments = data.get("attachments") or []

        result = chat_service.send_message(
            content=content,
            session_id=session_id,
            attachments=attachments,
        )
        return json_ok(result)
    except ValueError as e:
        return json_ok({"ok": False, "error": str(e)}, 400)
    except Exception as e:
        return json_ok({"ok": False, "error": f"Chat failed: {e}"}, 500)


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    try:
        session_id = request.args.get("session_id", "").strip() or None
        items = artifact_service.list_artifacts(session_id=session_id)
        return json_ok({"ok": True, "items": items})
    except Exception as e:
        return json_ok({"ok": False, "error": f"Artifacts load failed: {e}"}, 500)


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_get(artifact_id: str):
    try:
        item = artifact_service.get_artifact(artifact_id)
        if not item:
            return json_ok({"ok": False, "error": "Artifact not found"}, 404)
        return json_ok({"ok": True, "artifact": item})
    except Exception as e:
        return json_ok({"ok": False, "error": f"Artifact read failed: {e}"}, 500)


@app.route("/api/artifacts/save", methods=["POST"])
def api_artifact_save():
    try:
        data = request.get_json(force=True, silent=True) or {}
        item = artifact_service.save_artifact(
            title=data.get("title") or "Untitled artifact",
            content=data.get("content") or "",
            kind=data.get("kind") or "chat",
            session_id=data.get("session_id") or "default-session",
            tags=data.get("tags") or [],
            meta=data.get("meta") or {},
            pinned=bool(data.get("pinned", False)),
        )
        return json_ok({"ok": True, "artifact": item})
    except Exception as e:
        return json_ok({"ok": False, "error": f"Artifact save failed: {e}"}, 500)


@app.route("/api/artifacts/search", methods=["POST"])
def api_artifacts_search():
    try:
        data = request.get_json(force=True, silent=True) or {}
        query = (data.get("query") or "").strip()
        session_id = (data.get("session_id") or "").strip() or None
        limit = int(data.get("limit") or 5)

        items = artifact_service.search_artifacts(
            query,
            session_id=session_id,
            limit=limit,
        )
        return json_ok({"ok": True, "items": items})
    except Exception as e:
        return json_ok({"ok": False, "error": f"Artifact search failed: {e}"}, 500)


@app.route("/api/state", methods=["GET"])
def api_state():
    try:
        session_id = request.args.get("session_id", "default-session").strip()
        session = chat_service.get_session(session_id)
        artifacts = artifact_service.list_artifacts(session_id=session_id, limit=50)
        return json_ok(
            {
                "ok": True,
                "session": session,
                "artifacts": artifacts,
            }
        )
    except Exception as e:
        return json_ok({"ok": False, "error": f"State failed: {e}"}, 500)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    try:
        uploaded = request.files.getlist("files")
        if not uploaded:
            return json_ok({"ok": False, "error": "No files uploaded"}, 400)

        saved: List[Dict[str, Any]] = []
        for file in uploaded:
            if not file or not file.filename:
                continue

            filename = Path(file.filename).name
            target = UPLOADS_DIR / filename
            stem = target.stem
            suffix = target.suffix
            counter = 1

            while target.exists():
                target = UPLOADS_DIR / f"{stem}_{counter}{suffix}"
                counter += 1

            file.save(target)
            saved.append(
                {
                    "name": target.name,
                    "url": f"/api/uploads/{target.name}",
                    "size": target.stat().st_size,
                }
            )

        return json_ok({"ok": True, "files": saved})
    except Exception as e:
        return json_ok({"ok": False, "error": f"Upload failed: {e}"}, 500)


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploaded_file(filename: str):
    return send_from_directory(UPLOADS_DIR, filename)


if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)