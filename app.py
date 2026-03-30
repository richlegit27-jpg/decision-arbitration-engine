from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_PATH = DATA_DIR / "nova_sessions.json"
MEMORY_PATH = DATA_DIR / "nova_memory.json"
ARTIFACTS_PATH = DATA_DIR / "nova_artifacts.json"

ALLOWED_UPLOAD_EXTENSIONS = {
    "txt", "md", "log", "json", "csv", "pdf",
    "png", "jpg", "jpeg", "gif", "webp", "bmp"
}

MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "200"))
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "100"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_json_file(path: Path, default: Any) -> None:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")


def load_json(path: Path, default: Any) -> Any:
    ensure_json_file(path, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, value: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.move(str(tmp_path), str(path))


def guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def is_allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_UPLOAD_EXTENSIONS


def truncate_text(value: str, limit: int) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def load_sessions() -> list[dict[str, Any]]:
    data = load_json(SESSIONS_PATH, [])
    return data if isinstance(data, list) else []


def save_sessions(sessions: list[dict[str, Any]]) -> None:
    save_json(SESSIONS_PATH, sessions[:MAX_SESSIONS])


def load_memory() -> list[dict[str, Any]]:
    data = load_json(MEMORY_PATH, [])
    return data if isinstance(data, list) else []


def save_memory(items: list[dict[str, Any]]) -> None:
    save_json(MEMORY_PATH, items)


def load_artifacts() -> list[dict[str, Any]]:
    data = load_json(ARTIFACTS_PATH, [])
    return data if isinstance(data, list) else []


def save_artifacts(items: list[dict[str, Any]]) -> None:
    save_json(ARTIFACTS_PATH, items)


def find_session(session_id: str) -> dict[str, Any]:
    sessions = load_sessions()
    for session in sessions:
        if session.get("id") == session_id:
            session.setdefault("messages", [])
            session.setdefault("title", "Nova Chat")
            session.setdefault("created_at", now_iso())
            session.setdefault("updated_at", now_iso())
            return session

    session = {
        "id": session_id,
        "title": "Nova Chat",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "messages": [],
        "pinned": False,
        "message_count": 0,
        "last_message_preview": "",
    }
    sessions.insert(0, session)
    save_sessions(sessions)
    return session


def upsert_session(updated_session: dict[str, Any]) -> dict[str, Any]:
    sessions = load_sessions()
    replaced = False

    for idx, session in enumerate(sessions):
        if session.get("id") == updated_session.get("id"):
            sessions[idx] = updated_session
            replaced = True
            break

    if not replaced:
        sessions.insert(0, updated_session)

    sessions = sorted(
        sessions,
        key=lambda x: x.get("updated_at", ""),
        reverse=True,
    )[:MAX_SESSIONS]

    save_sessions(sessions)
    return updated_session


def append_session_message(
    session_id: str,
    role: str,
    content: str,
    attachments: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    session = find_session(session_id)
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content or "",
        "created_at": now_iso(),
        "attachments": attachments or [],
        "meta": meta or {},
    }

    messages = safe_list(session.get("messages"))
    messages.append(message)
    if len(messages) > MAX_MESSAGES_PER_SESSION:
        messages = messages[-MAX_MESSAGES_PER_SESSION:]

    session["messages"] = messages
    session["updated_at"] = now_iso()
    session["message_count"] = len(messages)
    session["last_message_preview"] = truncate_text(content or "", 120)

    if not session.get("title") or session.get("title") == "Nova Chat":
        if role == "user" and content:
            session["title"] = truncate_text(content.strip(), 40) or "Nova Chat"

    upsert_session(session)
    return session, message


def summarize_session(session: dict[str, Any]) -> dict[str, Any]:
    messages = safe_list(session.get("messages"))
    return {
        "id": session.get("id", ""),
        "title": session.get("title", "Nova Chat"),
        "created_at": session.get("created_at", ""),
        "updated_at": session.get("updated_at", ""),
        "pinned": bool(session.get("pinned", False)),
        "message_count": len(messages),
        "last_message_preview": session.get("last_message_preview", ""),
    }


def build_attachment_record(saved_name: str, original_name: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": original_name,
        "filename": original_name,
        "stored_name": saved_name,
        "url": f"/uploads/{saved_name}",
        "file_url": f"/uploads/{saved_name}",
        "mime_type": guess_mime(original_name),
        "created_at": now_iso(),
    }


def score_artifact(query: str, artifact: dict[str, Any]) -> int:
    query_terms = [t for t in re.findall(r"[a-zA-Z0-9_]+", (query or "").lower()) if t]
    if not query_terms:
        return 0

    haystack = " ".join([
        str(artifact.get("title", "")),
        str(artifact.get("content", "")),
        str(artifact.get("kind", "")),
        " ".join(str(t) for t in safe_list(artifact.get("tags"))),
    ]).lower()

    score = 0
    for term in query_terms:
        if term in haystack:
            score += 1
    if artifact.get("pinned"):
        score += 1
    return score


def get_relevant_artifacts(query: str, limit: int = 5) -> list[dict[str, Any]]:
    artifacts = load_artifacts()
    ranked = []
    for artifact in artifacts:
        score = score_artifact(query, artifact)
        if score > 0:
            ranked.append((score, artifact))

    ranked.sort(
        key=lambda x: (
            x[0],
            x[1].get("updated_at", x[1].get("created_at", "")),
        ),
        reverse=True,
    )
    return [item for _, item in ranked[:limit]]


def build_local_reply(
    user_text: str,
    attachments: list[dict[str, Any]],
    relevant_artifacts: list[dict[str, Any]],
) -> str:
    user_text = (user_text or "").strip()

    if attachments and not user_text:
        return "I see your uploaded attachment(s). Tell me what you want me to do with them, or ask me to describe or summarize them."

    if attachments and user_text:
        return f"I received your message and {len(attachments)} attachment(s). You said: {user_text}"

    if relevant_artifacts and user_text:
        titles = [a.get("title", "Untitled") for a in relevant_artifacts[:3]]
        joined = ", ".join(titles)
        return f"You said: {user_text}\n\nI also found relevant saved artifacts: {joined}"

    if user_text:
        return f"You said: {user_text}"

    return "Hey — I’m here."


def maybe_autosave_artifact(
    session_id: str,
    assistant_content: str,
    assistant_meta: dict[str, Any],
) -> tuple[bool, str]:
    content = (assistant_content or "").strip()
    if not content:
        return False, "empty_content"

    lowered = content.lower().strip()
    junk_prefixes = [
        "...",
        "thinking...",
    ]
    if lowered in junk_prefixes:
        return False, "pending_placeholder"

    artifacts = load_artifacts()

    artifact = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "title": truncate_text(content.splitlines()[0], 60) or "Chat Reply",
        "kind": "chat",
        "content": content,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "pinned": False,
        "tags": [],
        "meta": assistant_meta or {},
    }

    artifacts.insert(0, artifact)
    save_artifacts(artifacts)
    return True, "saved"


def normalize_chat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    content = payload.get("content")
    if content is None:
        content = payload.get("message")
    if content is None:
        content = payload.get("text")

    session_id = payload.get("session_id") or payload.get("sessionId") or "default-session"
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []

    return {
        "content": str(content or "").strip(),
        "session_id": str(session_id),
        "attachments": attachments,
    }


def stable_chat_response(
    *,
    ok: bool,
    session: dict[str, Any],
    assistant_message: dict[str, Any],
    debug: dict[str, Any],
    status_code: int = 200,
):
    response = {
        "ok": ok,
        "session": summarize_session(session),
        "assistant_message": {
            "id": assistant_message.get("id", ""),
            "role": "assistant",
            "content": assistant_message.get("content", "") or "",
            "created_at": assistant_message.get("created_at", now_iso()),
            "attachments": safe_list(assistant_message.get("attachments")),
            "meta": assistant_message.get("meta", {}) if isinstance(assistant_message.get("meta"), dict) else {},
        },
        "message": assistant_message.get("content", "") or "",
        "debug": debug,
    }
    return jsonify(response), status_code


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    return jsonify({
        "ok": True,
        "status": "healthy",
        "time": now_iso(),
    })


@app.get("/api/state")
def api_state():
    sessions = load_sessions()
    memory = load_memory()
    artifacts = load_artifacts()

    current_session_id = request.args.get("session_id") or "default-session"
    current_session = find_session(current_session_id)

    return jsonify({
        "ok": True,
        "session": summarize_session(current_session),
        "sessions": [summarize_session(s) for s in sessions],
        "memory": memory,
        "artifacts": artifacts,
    })


@app.get("/api/artifacts")
def api_artifacts():
    return jsonify({
        "ok": True,
        "artifacts": load_artifacts(),
    })


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_get(artifact_id: str):
    artifacts = load_artifacts()
    artifact = next((a for a in artifacts if a.get("id") == artifact_id), None)
    if not artifact:
        return jsonify({"ok": False, "error": "Artifact not found"}), 404
    return jsonify({"ok": True, "artifact": artifact})


@app.patch("/api/artifacts/<artifact_id>")
def api_artifact_patch(artifact_id: str):
    payload = request.get_json(silent=True) or {}
    artifacts = load_artifacts()

    for artifact in artifacts:
        if artifact.get("id") == artifact_id:
            if "pinned" in payload:
                artifact["pinned"] = bool(payload.get("pinned"))
            if "title" in payload:
                artifact["title"] = str(payload.get("title") or artifact.get("title", "Untitled"))
            artifact["updated_at"] = now_iso()
            save_artifacts(artifacts)
            return jsonify({"ok": True, "artifact": artifact})

    return jsonify({"ok": False, "error": "Artifact not found"}), 404


@app.delete("/api/artifacts/<artifact_id>")
def api_artifact_delete(artifact_id: str):
    artifacts = load_artifacts()
    before = len(artifacts)
    artifacts = [a for a in artifacts if a.get("id") != artifact_id]
    save_artifacts(artifacts)
    return jsonify({
        "ok": True,
        "deleted": before != len(artifacts),
    })


@app.post("/api/artifacts/delete")
def api_artifact_delete_post():
    payload = request.get_json(silent=True) or {}
    artifact_id = str(payload.get("artifact_id") or "")
    artifacts = load_artifacts()
    before = len(artifacts)
    artifacts = [a for a in artifacts if a.get("id") != artifact_id]
    save_artifacts(artifacts)
    return jsonify({
        "ok": True,
        "deleted": before != len(artifacts),
    })


@app.post("/api/artifacts/pin")
def api_artifact_pin():
    payload = request.get_json(silent=True) or {}
    artifact_id = str(payload.get("artifact_id") or "")
    pinned = bool(payload.get("pinned", True))
    artifacts = load_artifacts()

    for artifact in artifacts:
        if artifact.get("id") == artifact_id:
            artifact["pinned"] = pinned
            artifact["updated_at"] = now_iso()
            save_artifacts(artifacts)
            return jsonify({"ok": True, "artifact": artifact})

    return jsonify({"ok": False, "error": "Artifact not found"}), 404


@app.post("/api/artifacts/admin/cleanup")
def api_artifacts_admin_cleanup():
    artifacts = load_artifacts()
    cleaned = []
    removed_count = 0

    junk_patterns = [
        "nova local fallback reply: ...",
        "thinking...",
        "...",
    ]

    for artifact in artifacts:
        content = str(artifact.get("content", "")).strip().lower()
        if not content:
            removed_count += 1
            continue
        if content in junk_patterns:
            removed_count += 1
            continue
        cleaned.append(artifact)

    save_artifacts(cleaned)
    return jsonify({
        "ok": True,
        "removed_count": removed_count,
        "artifacts": cleaned,
    })


@app.post("/api/upload")
def api_upload():
    uploaded_files = request.files.getlist("files")
    session_id = request.form.get("session_id", "default-session")

    results: list[dict[str, Any]] = []

    for file in uploaded_files:
        if not file or not file.filename:
            continue

        original_name = file.filename
        if not is_allowed_file(original_name):
            continue

        safe_name = secure_filename(original_name)
        ext = Path(safe_name).suffix
        unique_name = f"{Path(safe_name).stem}_{uuid.uuid4().hex}{ext}"
        target = UPLOADS_DIR / unique_name
        file.save(target)

        results.append(build_attachment_record(unique_name, original_name))

    return jsonify({
        "ok": True,
        "session_id": session_id,
        "files": results,
        "attachments": results,
    })


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(silent=True) or {}
    normalized = normalize_chat_payload(payload)

    session_id = normalized["session_id"]
    user_text = normalized["content"]
    incoming_attachments = normalized["attachments"]

    debug: dict[str, Any] = {
        "route": "/api/chat",
        "used_fallback": True,
        "fallback_reason": "local_contract_stable_reply",
        "history_count": 0,
        "attachments_count": len(incoming_attachments),
        "memory_used": False,
        "memory_selected_count": 0,
        "memory_titles": [],
        "artifact_saved": False,
        "artifact_save_reason": "not_attempted",
        "model": "local-fallback",
    }

    try:
        session = find_session(session_id)
        history = safe_list(session.get("messages"))
        debug["history_count"] = len(history)

        # save user message first
        session, _ = append_session_message(
            session_id=session_id,
            role="user",
            content=user_text or "Describe or use the uploaded attachment(s).",
            attachments=incoming_attachments,
            meta={
                "attachments_count": len(incoming_attachments),
            },
        )

        relevant_artifacts = get_relevant_artifacts(user_text, limit=5)
        debug["memory_used"] = len(relevant_artifacts) > 0
        debug["memory_selected_count"] = len(relevant_artifacts)
        debug["memory_titles"] = [a.get("title", "Untitled") for a in relevant_artifacts]
        debug["memory_artifact_ids"] = [a.get("id", "") for a in relevant_artifacts]
        debug["memory_pinned_count"] = sum(1 for a in relevant_artifacts if a.get("pinned"))

        assistant_content = build_local_reply(
            user_text=user_text,
            attachments=incoming_attachments,
            relevant_artifacts=relevant_artifacts,
        )

        assistant_meta = {
            "used_fallback": True,
            "fallback_reason": debug["fallback_reason"],
            "attachments_count": len(incoming_attachments),
            "memory_used": debug["memory_used"],
            "memory_selected_count": debug["memory_selected_count"],
            "memory_titles": debug["memory_titles"],
            "model": debug["model"],
        }

        session, assistant_message = append_session_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            attachments=[],
            meta=assistant_meta,
        )

        artifact_saved, artifact_save_reason = maybe_autosave_artifact(
            session_id=session_id,
            assistant_content=assistant_content,
            assistant_meta=assistant_meta,
        )

        debug["artifact_saved"] = artifact_saved
        debug["artifact_save_reason"] = artifact_save_reason

        return stable_chat_response(
            ok=True,
            session=session,
            assistant_message=assistant_message,
            debug=debug,
            status_code=200,
        )

    except Exception as exc:
        error_text = f"Error: {exc}"

        try:
            session = find_session(session_id)
        except Exception:
            session = {
                "id": session_id,
                "title": "Nova Chat",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "messages": [],
            }

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": error_text,
            "created_at": now_iso(),
            "attachments": [],
            "meta": {
                "failed": True,
                "exception": str(exc),
                "used_fallback": True,
            },
        }

        debug["failed"] = True
        debug["exception"] = str(exc)
        debug["artifact_saved"] = False
        debug["artifact_save_reason"] = "error_path"

        return stable_chat_response(
            ok=False,
            session=session,
            assistant_message=assistant_message,
            debug=debug,
            status_code=500,
        )


if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", os.getenv("NOVA_PORT", "5001")))
    host = os.getenv("APP_HOST", os.getenv("NOVA_HOST", "127.0.0.1"))
    debug_mode = os.getenv("NOVA_DEBUG", "true").lower() in {"1", "true", "yes", "on"}

    ensure_json_file(SESSIONS_PATH, [])
    ensure_json_file(MEMORY_PATH, [])
    ensure_json_file(ARTIFACTS_PATH, [])

    app.run(host=host, port=port, debug=debug_mode)