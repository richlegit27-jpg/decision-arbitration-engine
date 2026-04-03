import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


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

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
IMAGE_MODEL = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5")

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(value: Any) -> str:
    return str(value or "").strip()


def ensure_file(path: Path, default: Any) -> None:
    if path.exists():
      return
    write_json(path, default)


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)


def _error(message: str, status: int = 400, **kwargs):
    payload = {"ok": False, "error": message}
    payload.update(kwargs)
    return jsonify(payload), status


def ensure_storage() -> None:
    ensure_file(SESSIONS_FILE, {"sessions": []})
    ensure_file(ARTIFACTS_FILE, {"artifacts": []})
    ensure_file(MEMORY_FILE, {"items": []})


def normalize_session_message(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return None

    role = safe_str(message.get("role") or message.get("sender") or "assistant").lower()
    content = safe_str(message.get("content") or message.get("text") or message.get("message") or "")
    created_at = safe_str(message.get("created_at") or message.get("timestamp") or now_iso())
    attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []

    return {
        "id": safe_str(message.get("id") or uuid.uuid4().hex[:8]),
        "role": role or "assistant",
        "content": content,
        "created_at": created_at,
        "attachments": attachments,
    }


def normalize_session(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    session_id = safe_str(item.get("id") or item.get("session_id"))
    if not session_id:
        session_id = uuid.uuid4().hex[:8]

    messages_raw = item.get("messages") if isinstance(item.get("messages"), list) else []
    messages = [m for m in (normalize_session_message(x) for x in messages_raw) if m]

    updated_at = safe_str(item.get("updated_at") or item.get("created_at") or now_iso())
    created_at = safe_str(item.get("created_at") or updated_at)

    title = safe_str(item.get("title") or item.get("name") or "")
    if not title:
        title = "New Chat"
        for msg in messages:
            if msg["role"] == "user" and msg["content"]:
                title = msg["content"][:48].rstrip()
                break

    last_preview = ""
    for msg in reversed(messages):
        if msg["content"]:
            last_preview = msg["content"][:160]
            break

    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "pinned": bool(item.get("pinned", False)),
        "created_at": created_at,
        "updated_at": updated_at,
        "message_count": len(messages),
        "last_message_preview": safe_str(item.get("last_message_preview") or last_preview),
        "messages": messages,
    }


def load_sessions_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(SESSIONS_FILE, {"sessions": []})

    if isinstance(raw, list):
        sessions_raw = raw
    elif isinstance(raw, dict):
        maybe_sessions = raw.get("sessions", [])
        sessions_raw = maybe_sessions if isinstance(maybe_sessions, list) else []
    else:
        sessions_raw = []

    sessions = [s for s in (normalize_session(x) for x in sessions_raw) if s]
    sessions.sort(
        key=lambda s: safe_str(s.get("updated_at")),
        reverse=True,
    )
    sessions.sort(
        key=lambda s: 1 if s.get("pinned") else 0,
        reverse=True,
    )

    return {"sessions": sessions}


def save_sessions_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(SESSIONS_FILE, {"sessions": payload.get("sessions", [])})


def get_session(session_id: str) -> dict[str, Any] | None:
    for session in load_sessions_payload()["sessions"]:
        if safe_str(session.get("id")) == safe_str(session_id):
            return session
    return None


def upsert_session(session: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    payload = load_sessions_payload()
    sessions = payload["sessions"]

    existing_index = None
    for i, current in enumerate(sessions):
        if safe_str(current.get("id")) == safe_str(session.get("id")):
            existing_index = i
            break

    if existing_index is None:
        sessions.insert(0, session)
    else:
        sessions[existing_index] = session

    sessions.sort(
        key=lambda s: safe_str(s.get("updated_at")),
        reverse=True,
    )
    sessions.sort(
        key=lambda s: 1 if s.get("pinned") else 0,
        reverse=True,
    )

    payload["sessions"] = sessions
    save_sessions_payload(payload)
    return payload


def delete_session_by_id(session_id: str) -> tuple[dict[str, list[dict[str, Any]]], str]:
    payload = load_sessions_payload()
    sessions = [s for s in payload["sessions"] if safe_str(s.get("id")) != safe_str(session_id)]
    payload["sessions"] = sessions
    save_sessions_payload(payload)
    next_session_id = safe_str(sessions[0]["id"]) if sessions else ""
    return payload, next_session_id


def create_session(title: str = "New Chat") -> dict[str, Any]:
    ts = now_iso()
    session_id = uuid.uuid4().hex[:8]
    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "pinned": False,
        "created_at": ts,
        "updated_at": ts,
        "message_count": 0,
        "last_message_preview": "",
        "messages": [],
    }


def normalize_artifact(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    artifact_id = safe_str(item.get("id") or item.get("artifact_id"))
    if not artifact_id:
        artifact_id = uuid.uuid4().hex[:10]

    return {
        "id": artifact_id,
        "artifact_id": artifact_id,
        "session_id": safe_str(item.get("session_id")),
        "kind": safe_str(item.get("kind") or item.get("type") or "artifact"),
        "title": safe_str(item.get("title") or item.get("name") or item.get("kind") or "Untitled artifact"),
        "content": safe_str(item.get("content") or item.get("text") or item.get("body") or item.get("preview") or ""),
        "summary": safe_str(item.get("summary") or ""),
        "preview": safe_str(item.get("preview") or item.get("content") or item.get("summary") or "")[:220],
        "pinned": bool(item.get("pinned", False)),
        "created_at": safe_str(item.get("created_at") or now_iso()),
        "updated_at": safe_str(item.get("updated_at") or item.get("created_at") or now_iso()),
        "meta": item.get("meta") if isinstance(item.get("meta"), dict) else {},
        "web": item.get("web") if isinstance(item.get("web"), dict) else None,
        "debug": item.get("debug") if isinstance(item.get("debug"), dict) else None,
        "extra": item.get("extra") if isinstance(item.get("extra"), dict) else None,
    }


def load_artifacts_payload() -> dict[str, list[dict[str, Any]]]:
    raw = read_json(ARTIFACTS_FILE, {"artifacts": []})

    if isinstance(raw, list):
        items_raw = raw
    elif isinstance(raw, dict):
        maybe_items = raw.get("artifacts", [])
        items_raw = maybe_items if isinstance(maybe_items, list) else []
    else:
        items_raw = []

    items = [a for a in (normalize_artifact(x) for x in items_raw) if a]
    items.sort(
        key=lambda a: safe_str(a.get("updated_at")),
        reverse=True,
    )
    items.sort(
        key=lambda a: 1 if a.get("pinned") else 0,
        reverse=True,
    )
    return {"artifacts": items}


def save_artifacts_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    write_json(ARTIFACTS_FILE, {"artifacts": payload.get("artifacts", [])})


def list_memory_items() -> list[dict[str, Any]]:
    raw = read_json(MEMORY_FILE, {"items": []})
    if isinstance(raw, list):
        return []
    if not isinstance(raw, dict):
        return []
    items = raw.get("items", [])
    return items if isinstance(items, list) else []


def build_state(session_id: str = "") -> dict[str, Any]:
    sessions_payload = load_sessions_payload()
    sessions = sessions_payload["sessions"]

    active_session = None
    if session_id:
        active_session = next((s for s in sessions if safe_str(s.get("id")) == safe_str(session_id)), None)
    if active_session is None and sessions:
        active_session = sessions[0]

    artifacts = load_artifacts_payload()["artifacts"]
    memory_items = list_memory_items()

    session_messages = active_session.get("messages", []) if active_session else []

    return {
        "ok": True,
        "active_session_id": safe_str(active_session.get("id")) if active_session else "",
        "sessions": [
            {
                "id": s["id"],
                "session_id": s["id"],
                "title": s["title"],
                "pinned": s["pinned"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"],
                "message_count": s["message_count"],
                "last_message_preview": s["last_message_preview"],
            }
            for s in sessions
        ],
        "session": {
            "id": safe_str(active_session.get("id")) if active_session else "",
            "title": safe_str(active_session.get("title")) if active_session else "",
            "messages": session_messages,
        },
        "messages": session_messages,
        "memory_items": memory_items,
        "artifacts": artifacts,
        "web_items": [a for a in artifacts if safe_str(a.get("kind")) == "web"],
    }


def add_artifact(
    *,
    session_id: str,
    kind: str,
    title: str,
    content: str,
    meta: dict[str, Any] | None = None,
    web: dict[str, Any] | None = None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = load_artifacts_payload()
    ts = now_iso()

    artifact = {
        "id": uuid.uuid4().hex[:10],
        "artifact_id": "",
        "session_id": safe_str(session_id),
        "kind": safe_str(kind or "artifact"),
        "title": safe_str(title or "Untitled artifact"),
        "content": safe_str(content),
        "summary": safe_str(content)[:220],
        "preview": safe_str(content)[:220],
        "pinned": False,
        "created_at": ts,
        "updated_at": ts,
        "meta": meta or {},
        "web": web or None,
        "debug": debug or None,
        "extra": None,
    }
    artifact["artifact_id"] = artifact["id"]

    items = payload["artifacts"]
    items.insert(0, artifact)
    save_artifacts_payload({"artifacts": items})
    return artifact


def call_model(messages: list[dict[str, str]]) -> str:
    if not client:
        return "Nova fallback reply: backend is live, but no OpenAI key is configured."

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=messages,
        )
        text = getattr(response, "output_text", "") or ""
        return safe_str(text) or "Nova returned an empty response."
    except Exception as exc:
        return f"Nova fallback reply: model call failed. {exc}"


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return _ok(
        status="healthy",
        openai_configured=bool(client),
        openai_model=OPENAI_MODEL,
        image_model=IMAGE_MODEL,
        time=now_iso(),
    )


@app.route("/api/state", methods=["GET"])
def api_state():
    ensure_storage()
    try:
        session_id = safe_str(request.args.get("session_id"))
        return jsonify(build_state(session_id=session_id))
    except Exception as exc:
        return _error(f"Failed to load state: {exc}", status=500)


@app.route("/api/session/new", methods=["POST"])
def api_session_new():
    ensure_storage()
    try:
        session = create_session()
        upsert_session(session)
        return jsonify(build_state(session_id=session["id"]))
    except Exception as exc:
        return _error(f"Failed to create session: {exc}", status=500)


@app.route("/api/session/rename", methods=["POST"])
def api_session_rename():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    session_id = safe_str(data.get("session_id"))
    title = safe_str(data.get("title"))

    if not session_id:
        return _error("Missing session_id.", status=400)

    try:
        session = get_session(session_id)
        if not session:
            return _error("Session not found.", status=404)

        if title:
            session["title"] = title
        session["updated_at"] = now_iso()
        upsert_session(session)
        return jsonify(build_state(session_id=session_id))
    except Exception as exc:
        return _error(f"Rename failed: {exc}", status=500)


@app.route("/api/session/pin", methods=["POST"])
def api_session_pin():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    session_id = safe_str(data.get("session_id"))

    if not session_id:
        return _error("Missing session_id.", status=400)

    try:
        session = get_session(session_id)
        if not session:
            return _error("Session not found.", status=404)

        session["pinned"] = not bool(session.get("pinned"))
        session["updated_at"] = now_iso()
        upsert_session(session)
        return jsonify(build_state(session_id=session_id))
    except Exception as exc:
        return _error(f"Pin failed: {exc}", status=500)


@app.route("/api/session/delete", methods=["POST"])
def api_session_delete():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    session_id = safe_str(data.get("session_id"))

    if not session_id:
        return _error("Missing session_id.", status=400)

    try:
        _, next_session_id = delete_session_by_id(session_id)
        payload = build_state(session_id=next_session_id)
        payload["next_session_id"] = next_session_id
        return jsonify(payload)
    except Exception as exc:
        return _error(f"Delete failed: {exc}", status=500)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    ensure_storage()
    try:
        if "files" not in request.files:
            return _error("No files field provided.", status=400)

        uploaded_files = request.files.getlist("files")
        saved: list[dict[str, Any]] = []

        for file in uploaded_files:
            if not file or not file.filename:
                continue

            original_name = Path(file.filename).name
            stored_name = f"{uuid.uuid4().hex}_{original_name}"
            target = UPLOADS_DIR / stored_name
            file.save(target)

            mime_type = file.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
            kind = "file"
            if mime_type.startswith("image/"):
                kind = "image"
            elif mime_type.startswith("video/"):
                kind = "video"
            elif mime_type.startswith("audio/"):
                kind = "audio"

            saved.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "name": original_name,
                    "stored_name": stored_name,
                    "url": f"/api/uploads/{stored_name}",
                    "preview_url": f"/api/uploads/{stored_name}",
                    "size": target.stat().st_size,
                    "mime_type": mime_type,
                    "kind": kind,
                    "uploaded_at": now_iso(),
                }
            )

        return _ok(files=saved)
    except Exception as exc:
        return _error(f"Upload failed: {exc}", status=500)


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploads(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    ensure_storage()
    data = request.get_json(silent=True) or {}

    content = safe_str(data.get("content") or data.get("message") or data.get("text"))
    session_id = safe_str(data.get("session_id"))
    attachments = data.get("attachments") if isinstance(data.get("attachments"), list) else []

    if not content and not attachments:
        return _error("Missing content.", status=400)

    try:
        sessions_payload = load_sessions_payload()

        session = None
        if session_id:
            session = next((s for s in sessions_payload["sessions"] if safe_str(s.get("id")) == session_id), None)

        if session is None:
            session = create_session()
            session_id = session["id"]

        user_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": content,
            "created_at": now_iso(),
            "attachments": attachments,
        }
        session["messages"].append(user_message)

        model_messages = []
        for msg in session["messages"][-12:]:
            role = safe_str(msg.get("role") or "user")
            content_text = safe_str(msg.get("content"))
            if content_text:
                model_messages.append({"role": role, "content": content_text})

        if attachments:
            model_messages.append(
                {
                    "role": "user",
                    "content": "Attached files:\n" + "\n".join(
                        f"- {safe_str(a.get('name') or a.get('filename') or 'attachment')}"
                        for a in attachments
                        if isinstance(a, dict)
                    ),
                }
            )

        assistant_text = call_model(model_messages)

        assistant_message = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
            "attachments": [],
        }
        session["messages"].append(assistant_message)

        if not safe_str(session.get("title")) or safe_str(session.get("title")) == "New Chat":
            first_user = next((m for m in session["messages"] if m["role"] == "user" and m["content"]), None)
            if first_user:
                session["title"] = first_user["content"][:48].rstrip() or "New Chat"

        session["updated_at"] = now_iso()
        session["message_count"] = len(session["messages"])
        session["last_message_preview"] = assistant_text[:160] or content[:160]
        upsert_session(session)

        add_artifact(
            session_id=session_id,
            kind="chat",
            title=session["title"],
            content=assistant_text,
            meta={"message_count": session["message_count"]},
            debug={"source": "api_chat"},
        )

        payload = build_state(session_id=session_id)
        payload["message"] = assistant_text
        payload["assistant_message"] = assistant_text
        payload["session"] = {
            "id": session_id,
            "title": session["title"],
            "messages": session["messages"],
        }
        payload["debug"] = {
            "model": OPENAI_MODEL,
            "openai_configured": bool(client),
            "attachment_count": len(attachments),
        }
        return jsonify(payload)
    except Exception as exc:
        return _error(f"Chat failed: {exc}", status=500)


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    ensure_storage()
    try:
        return _ok(artifacts=load_artifacts_payload()["artifacts"])
    except Exception as exc:
        return _error(f"Failed to list artifacts: {exc}", status=500)


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_read(artifact_id: str):
    ensure_storage()
    try:
        items = load_artifacts_payload()["artifacts"]
        item = next((a for a in items if safe_str(a.get("id")) == safe_str(artifact_id)), None)
        if not item:
            return _error("Artifact not found.", status=404)
        return _ok(artifact=item)
    except Exception as exc:
        return _error(f"Failed to read artifact: {exc}", status=500)


@app.route("/api/artifacts/pin", methods=["POST"])
def api_artifact_pin():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    artifact_id = safe_str(data.get("artifact_id"))

    if not artifact_id:
        return _error("Missing artifact_id.", status=400)

    try:
        payload = load_artifacts_payload()
        items = payload["artifacts"]

        found = None
        for item in items:
            if safe_str(item.get("id")) == artifact_id:
                item["pinned"] = not bool(item.get("pinned"))
                item["updated_at"] = now_iso()
                found = item
                break

        if not found:
            return _error("Artifact not found.", status=404)

        save_artifacts_payload({"artifacts": items})
        return _ok(message="Artifact pin saved.", artifact=found, artifacts=load_artifacts_payload()["artifacts"])
    except Exception as exc:
        return _error(f"Artifact pin failed: {exc}", status=500)


@app.route("/api/artifacts/delete", methods=["POST"])
def api_artifact_delete():
    ensure_storage()
    data = request.get_json(silent=True) or {}
    artifact_id = safe_str(data.get("artifact_id"))

    if not artifact_id:
        return _error("Missing artifact_id.", status=400)

    try:
        payload = load_artifacts_payload()
        items = [a for a in payload["artifacts"] if safe_str(a.get("id")) != artifact_id]
        next_artifact_id = safe_str(items[0]["id"]) if items else ""
        save_artifacts_payload({"artifacts": items})
        return _ok(message="Artifact deleted.", next_artifact_id=next_artifact_id, artifacts=items)
    except Exception as exc:
        return _error(f"Artifact delete failed: {exc}", status=500)


if __name__ == "__main__":
    ensure_storage()
    host = os.getenv("APP_HOST") or os.getenv("NOVA_HOST") or "127.0.0.1"
    port = int(os.getenv("APP_PORT") or os.getenv("NOVA_PORT") or "5001")
    debug = safe_str(os.getenv("NOVA_DEBUG", "1")).lower() not in {"0", "false", "no"}
    app.run(host=host, port=port, debug=debug)