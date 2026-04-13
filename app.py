from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

import uuid
from werkzeug.utils import secure_filename

from nova_backend.config import (
    BASE_DIR,
    DATA_DIR,
    UPLOADS_DIR,
    SESSIONS_FILE,
    ARTIFACTS_FILE,
    MEMORY_FILE,
    WEB_TIMEOUT,
    RECON_TIMEOUT,
)
from nova_backend.services.session_service import SessionService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.web_service import WebService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.chat_service import ChatService
from nova_backend.utils.file_utils import ensure_dir


# -----------------------
# APP SETUP
# -----------------------

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
CORS(app)

ensure_dir(DATA_DIR)
ensure_dir(UPLOADS_DIR)

app.config["UPLOAD_FOLDER"] = str(UPLOADS_DIR)


# -----------------------
# SERVICES
# -----------------------

session_service = SessionService(str(SESSIONS_FILE))
artifact_service = ArtifactService(str(ARTIFACTS_FILE))
memory_service = MemoryService(str(MEMORY_FILE))
web_service = WebService(timeout=WEB_TIMEOUT)
recon_service = ReconService(timeout=RECON_TIMEOUT)

chat_service = ChatService(
    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service,
    web_service=web_service,
    recon_service=recon_service,
)


# -----------------------
# HELPERS
# -----------------------

def json_ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)


def json_error(message: str, status: int = 400, **kwargs):
    payload = {"ok": False, "error": str(message)}
    payload.update(kwargs)
    return jsonify(payload), status


def request_json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# -----------------------
# PAGE ROUTES
# -----------------------

@app.get("/")
def index():
    return render_template("index.html")


# -----------------------
# HEALTH
# -----------------------

@app.get("/api/health")
def api_health():
    return json_ok(
        status="ready",
        app="nova",
        cwd=os.getcwd(),
        base_dir=str(BASE_DIR),
        uploads_dir=str(UPLOADS_DIR),
        sessions_file=str(SESSIONS_FILE),
        artifacts_file=str(ARTIFACTS_FILE),
        memory_file=str(MEMORY_FILE),
        route_build="backend-split-cleanup-002",
    )


# -----------------------
# STATE
# -----------------------

@app.get("/api/state")
def api_state():
    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )


# -----------------------
# CHAT
# -----------------------

@app.post("/api/chat")
def api_chat():
    data = request_json()

    user_text = str(data.get("user_text") or "").strip()
    session_id = str(data.get("session_id") or "").strip()
    attachments = data.get("attachments") if isinstance(data.get("attachments"), list) else []

    if not session_id:
        active = session_service.get_active()
        if active:
            session_id = str(active.get("id") or "").strip()

    if not session_id:
        created = session_service.create("New Chat")
        session_id = created["id"]

    if not user_text and not attachments:
        return json_error("Missing user_text or attachments", 400)

    try:
        result = chat_service.handle(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )
        return jsonify(result)
    except Exception as exc:
        return json_error(str(exc), 500)


# -----------------------
# SESSIONS
# -----------------------

@app.get("/api/sessions")
def api_sessions():
    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
    )


@app.get("/api/sessions/<session_id>")
def api_session_by_id(session_id: str):
    session = session_service.get_by_id(session_id)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session,
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/new")
def api_sessions_new():
    data = request_json()
    title = str(data.get("title") or "New Chat").strip() or "New Chat"

    session = session_service.create(title)
    return json_ok(
        session=session,
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/switch")
def api_sessions_switch():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.set_active(session_id)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session,
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/rename")
def api_sessions_rename():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    title = str(data.get("title") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    if not session_service.rename(session_id, title or "New Chat"):
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_by_id(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/delete")
def api_sessions_delete():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    if not session_service.delete(session_id):
        return json_error("Session not found", 404)

    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )


@app.post("/api/sessions/pin")
def api_sessions_pin():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    if not session_service.pin(session_id):
        return json_error("Session not found", 404)

    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
    )


# -----------------------
# ARTIFACTS
# -----------------------

@app.get("/api/artifacts")
def api_artifacts():
    return json_ok(
        artifacts=artifact_service.build_list_payload(),
    )


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_view(artifact_id: str):
    payload = artifact_service.build_view_payload(artifact_id)
    if not payload:
        return json_error("Artifact not found", 404)

    return json_ok(
        artifact=payload,
    )


# -----------------------
# MEMORY
# -----------------------

@app.get("/api/memory")
def api_memory():
    return json_ok(
        memory=memory_service.build_list_payload(),
    )


@app.post("/api/memory/add")
def api_memory_add():
    data = request_json()

    text = str(data.get("text") or "").strip()
    kind = str(data.get("kind") or "note").strip() or "note"
    source = str(data.get("source") or "manual").strip() or "manual"
    session_id = str(data.get("session_id") or "").strip()

    if not text:
        return json_error("Missing text", 400)

    item = memory_service.add(
        text=text,
        kind=kind,
        source=source,
        session_id=session_id,
    )

    return json_ok(
        item=item,
        memory=memory_service.build_list_payload(),
    )


@app.post("/api/memory/delete")
def api_memory_delete():
    data = request_json()
    memory_id = str(data.get("memory_id") or data.get("id") or "").strip()

    if not memory_id:
        return json_error("Missing memory_id", 400)

    if not memory_service.delete(memory_id):
        return json_error("Memory not found", 404)

    return json_ok(
        memory=memory_service.build_list_payload(),
    )

@app.post("/api/memory/cleanup")
def api_memory_cleanup():
    result = memory_service.cleanup_memories()
    return jsonify({
        "ok": True,
        **result,
    })

@app.post("/api/memory/promote")
def api_memory_promote():
    result = memory_service.promote_memories()
    return jsonify({
        "ok": True,
        **result,
    })


@app.post("/api/memory/cleanup-promote")
def api_memory_cleanup_promote():
    result = memory_service.cleanup_and_promote_memories()
    return jsonify(result)

# -----------------------
# WEB
# -----------------------

@app.post("/api/web/fetch")
def api_web_fetch():
    data = request_json()
    url = str(data.get("url") or "").strip()

    if not url:
        return json_error("Missing url", 400)

    result = web_service.fetch(url)
    if not result.get("ok"):
        return json_error(result.get("error") or "Fetch failed", 500, result=result)

    return json_ok(
        result=result,
        artifact=web_service.build_artifact_payload(result),
    )


# -----------------------
# RECON
# -----------------------

@app.post("/api/recon/analyze")
def api_recon_analyze():
    data = request_json()
    url = str(data.get("url") or "").strip()

    if not url:
        return json_error("Missing url", 400)

    result = recon_service.analyze_target(url)
    if not result.get("ok"):
        return json_error(result.get("error") or "Recon failed", 500, result=result)

    return json_ok(
        result=result,
        artifact=recon_service.build_artifact_payload(result),
    )


# -----------------------
# UPLOADS
# -----------------------

@app.get("/api/uploads/<path:filename>")
def api_uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)

@app.post("/api/upload")
def api_upload():
    try:
        if "file" not in request.files:
            return jsonify({
                "ok": False,
                "error": "No file provided.",
            }), 400

        file = request.files["file"]
        if not file or not getattr(file, "filename", ""):
            return jsonify({
                "ok": False,
                "error": "Empty file.",
            }), 400

        original_name = os.path.basename(str(file.filename))
        safe_name = secure_filename(original_name) or "upload.bin"

        base, ext = os.path.splitext(safe_name)
        ext = ext or ""
        final_name = f"{base}_{uuid.uuid4().hex}{ext}"

        save_path = UPLOADS_DIR / final_name
        file.save(str(save_path))

        mime_type = getattr(file, "mimetype", None) or "application/octet-stream"
        size = save_path.stat().st_size if save_path.exists() else 0

        return jsonify({
            "ok": True,
            "filename": final_name,
            "original_filename": original_name,
            "file_url": f"/api/uploads/{final_name}",
            "url": f"/api/uploads/{final_name}",
            "mime_type": mime_type,
            "size": size,
        })
    except Exception as e:
        app.logger.exception("api_upload failed")
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500

# -----------------------
# MAIN
# -----------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
    )