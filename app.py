# notepad C:\Users\Owner\nova\app.py
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename


# =========================================================
# app setup
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)

app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("NOVA_MAX_REQUEST_BYTES", str(50 * 1024 * 1024)))


# =========================================================
# optional service imports
# =========================================================

try:
    from services.chat_service import (
        coerce_stream_done_event,
        generate_reply,
        generate_reply_stream,
        preview_chat_brain,
        service_status as chat_service_status,
    )
except Exception as exc:  # pragma: no cover
    generate_reply = None  # type: ignore
    generate_reply_stream = None  # type: ignore
    preview_chat_brain = None  # type: ignore
    coerce_stream_done_event = None  # type: ignore
    chat_service_status = None  # type: ignore
    CHAT_IMPORT_ERROR = str(exc)
else:
    CHAT_IMPORT_ERROR = None

try:
    from services.memory_service import (
        add_memory as memory_add,
        delete_memory as memory_delete,
        export_memory as memory_export,
        list_memory as memory_list,
    )
except Exception as exc:  # pragma: no cover
    memory_add = None  # type: ignore
    memory_delete = None  # type: ignore
    memory_export = None  # type: ignore
    memory_list = None  # type: ignore
    MEMORY_IMPORT_ERROR = str(exc)
else:
    MEMORY_IMPORT_ERROR = None

try:
    from services.artifact_service import (
        create_artifact,
        delete_artifact,
        export_artifact,
        get_artifact,
        list_artifacts,
        pin_artifact,
        save_artifact,
        toggle_artifact_pin,
        update_artifact,
    )
except Exception as exc:  # pragma: no cover
    create_artifact = None  # type: ignore
    delete_artifact = None  # type: ignore
    export_artifact = None  # type: ignore
    get_artifact = None  # type: ignore
    list_artifacts = None  # type: ignore
    pin_artifact = None  # type: ignore
    save_artifact = None  # type: ignore
    toggle_artifact_pin = None  # type: ignore
    update_artifact = None  # type: ignore
    ARTIFACT_IMPORT_ERROR = str(exc)
else:
    ARTIFACT_IMPORT_ERROR = None

try:
    from services.attachment_service import (
        attachment_stats,
        cleanup_missing_files,
        delete_attachment,
        list_attachments,
        register_attachment,
        register_attachments,
        save_uploaded_file,
    )
except Exception as exc:  # pragma: no cover
    attachment_stats = None  # type: ignore
    cleanup_missing_files = None  # type: ignore
    delete_attachment = None  # type: ignore
    list_attachments = None  # type: ignore
    register_attachment = None  # type: ignore
    register_attachments = None  # type: ignore
    save_uploaded_file = None  # type: ignore
    ATTACHMENT_IMPORT_ERROR = str(exc)
else:
    ATTACHMENT_IMPORT_ERROR = None

try:
    from services.web_service import (
        fetch_single_url,
        fetch_urls,
        web_preview_from_text,
        web_service_status,
    )
except Exception as exc:  # pragma: no cover
    fetch_single_url = None  # type: ignore
    fetch_urls = None  # type: ignore
    web_preview_from_text = None  # type: ignore
    web_service_status = None  # type: ignore
    WEB_IMPORT_ERROR = str(exc)
else:
    WEB_IMPORT_ERROR = None


# =========================================================
# helpers
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def read_json_request() -> Dict[str, Any]:
    try:
        data = request.get_json(silent=True)
    except Exception:
        data = None
    return safe_dict(data)


def json_ok(data: Optional[Dict[str, Any]] = None, status: int = 200):
    payload = {"ok": True}
    if isinstance(data, dict):
        payload.update(data)
    return jsonify(payload), status


def json_error(message: str, *, code: str = "bad_request", status: int = 400, extra: Optional[Dict[str, Any]] = None):
    payload: Dict[str, Any] = {
        "ok": False,
        "error": {
            "code": code,
            "message": clean_text(message) or "Request failed.",
        },
    }
    if isinstance(extra, dict):
        payload.update(extra)
    return jsonify(payload), status


def ensure_sessions_file() -> None:
    if not SESSIONS_FILE.exists():
        save_sessions([])


def load_sessions() -> List[Dict[str, Any]]:
    ensure_sessions_file()
    try:
        raw = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        raw = []

    sessions: List[Dict[str, Any]] = []
    for item in safe_list(raw):
        if not isinstance(item, dict):
            continue
        sessions.append(normalize_session(item))
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions


def save_sessions(sessions: List[Dict[str, Any]]) -> None:
    serializable = [normalize_session(x) for x in safe_list(sessions) if isinstance(x, dict)]
    SESSIONS_FILE.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_message(item: Dict[str, Any]) -> Dict[str, Any]:
    item = safe_dict(item)
    role = clean_text(item.get("role")).lower() or "user"
    if role not in {"system", "user", "assistant", "developer", "tool"}:
        role = "user"

    return {
        "id": clean_text(item.get("id")) or f"msg_{uuid.uuid4().hex}",
        "role": role,
        "content": clean_text(item.get("content")),
        "created_at": clean_text(item.get("created_at")) or utc_now_iso(),
        "metadata": safe_dict(item.get("metadata")),
    }


def normalize_session(item: Dict[str, Any]) -> Dict[str, Any]:
    item = safe_dict(item)
    messages = [normalize_message(x) for x in safe_list(item.get("messages")) if isinstance(x, dict)]
    created_at = clean_text(item.get("created_at")) or utc_now_iso()
    updated_at = clean_text(item.get("updated_at")) or created_at
    title = clean_text(item.get("title")) or "New chat"

    return {
        "id": clean_text(item.get("id")) or str(uuid.uuid4()),
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "pinned": bool(item.get("pinned", False)),
        "messages": messages,
        "message_count": len(messages),
        "last_message_preview": clean_text(messages[-1].get("content"))[:180] if messages else "",
        "metadata": safe_dict(item.get("metadata")),
    }


def find_session(session_id: str) -> Optional[Dict[str, Any]]:
    session_id = clean_text(session_id)
    if not session_id:
        return None
    for session in load_sessions():
        if session.get("id") == session_id:
            return session
    return None


def upsert_session(session: Dict[str, Any]) -> Dict[str, Any]:
    target = normalize_session(session)
    sessions = load_sessions()
    replaced = False

    for idx, item in enumerate(sessions):
        if item.get("id") == target.get("id"):
            sessions[idx] = target
            replaced = True
            break

    if not replaced:
        sessions.insert(0, target)

    sessions.sort(key=lambda x: (not x.get("pinned", False), x.get("updated_at", "")), reverse=False)
    pinned = [s for s in sessions if s.get("pinned")]
    unpinned = [s for s in sessions if not s.get("pinned")]
    pinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    unpinned.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    save_sessions(pinned + unpinned)
    return target


def create_session(title: str = "New chat") -> Dict[str, Any]:
    now = utc_now_iso()
    session = {
        "id": str(uuid.uuid4()),
        "title": clean_text(title) or "New chat",
        "created_at": now,
        "updated_at": now,
        "pinned": False,
        "messages": [],
        "metadata": {},
    }
    return upsert_session(session)


def delete_session_by_id(session_id: str) -> bool:
    session_id = clean_text(session_id)
    sessions = load_sessions()
    kept = [x for x in sessions if x.get("id") != session_id]
    if len(kept) == len(sessions):
        return False
    save_sessions(kept)
    return True


def rename_session_by_id(session_id: str, title: str) -> Optional[Dict[str, Any]]:
    sessions = load_sessions()
    target = None
    for idx, session in enumerate(sessions):
        if session.get("id") == clean_text(session_id):
            session["title"] = clean_text(title) or session.get("title") or "New chat"
            session["updated_at"] = utc_now_iso()
            sessions[idx] = normalize_session(session)
            target = sessions[idx]
            break
    if target is None:
        return None
    save_sessions(sessions)
    return target


def append_message_to_session(session_id: str, message: Dict[str, Any], *, title_from_first_user_message: bool = True) -> Dict[str, Any]:
    sessions = load_sessions()
    target = None

    for idx, session in enumerate(sessions):
        if session.get("id") == clean_text(session_id):
            target = normalize_session(session)
            normalized_message = normalize_message(message)
            target["messages"].append(normalized_message)
            target["updated_at"] = utc_now_iso()

            if title_from_first_user_message and target.get("title") == "New chat" and normalized_message.get("role") == "user":
                first_line = clean_text(normalized_message.get("content")).split("\n", 1)[0]
                target["title"] = first_line[:60] or "New chat"

            sessions[idx] = normalize_session(target)
            break

    if target is None:
        target = create_session("New chat")
        return append_message_to_session(target["id"], message, title_from_first_user_message=title_from_first_user_message)

    save_sessions(sessions)
    return normalize_session(target)


def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_route_status() -> Dict[str, Any]:
    return {
        "chat_import_error": CHAT_IMPORT_ERROR,
        "memory_import_error": MEMORY_IMPORT_ERROR,
        "artifact_import_error": ARTIFACT_IMPORT_ERROR,
        "attachment_import_error": ATTACHMENT_IMPORT_ERROR,
        "web_import_error": WEB_IMPORT_ERROR,
    }


# =========================================================
# page routes
# =========================================================

@app.get("/")
def home():
    return render_template("index.html")


@app.get("/favicon.ico")
def favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return send_from_directory(str(STATIC_DIR), "favicon.ico")
    return ("", 204)


# =========================================================
# health + state
# =========================================================

@app.get("/api/health")
def api_health():
    chat_status = chat_service_status() if callable(chat_service_status) else {
        "ok": False,
        "service": "chat_service",
        "error": {"code": "import_failed", "message": CHAT_IMPORT_ERROR or "chat_service unavailable"},
    }

    return jsonify(
        {
            "ok": True,
            "app": "nova",
            "service": "backend",
            "model_connected": bool(safe_dict(chat_status).get("client_available")),
            "model": safe_dict(chat_status).get("model"),
            "chat": chat_status,
            "routes": build_route_status(),
            "sessions_count": len(load_sessions()),
            "updated_at": utc_now_iso(),
        }
    )


@app.get("/api/state")
def api_state():
    sessions = load_sessions()
    return jsonify(
        {
            "ok": True,
            "sessions": sessions,
            "session_count": len(sessions),
            "default_model": os.getenv("OPENAI_MODEL", "gpt-5.4"),
            "updated_at": utc_now_iso(),
        }
    )


@app.get("/api/models")
def api_models():
    env_model = clean_text(os.getenv("OPENAI_MODEL")) or "gpt-5.4"
    models = []
    for model in [env_model, "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"]:
        if model and model not in models:
            models.append(model)

    return jsonify(
        {
            "ok": True,
            "default": env_model,
            "models": models,
        }
    )


# =========================================================
# session routes
# =========================================================

@app.post("/api/session/new")
def api_session_new():
    payload = read_json_request()
    session = create_session(clean_text(payload.get("title")) or "New chat")
    return jsonify({"ok": True, "session": session})


@app.post("/api/session/delete")
def api_session_delete():
    payload = read_json_request()
    session_id = clean_text(payload.get("session_id") or payload.get("id"))
    if not session_id:
        return json_error("session_id is required.", code="invalid_request", status=400)

    deleted = delete_session_by_id(session_id)
    if not deleted:
        return json_error("Session not found.", code="not_found", status=404)

    return jsonify({"ok": True, "deleted_id": session_id})


@app.post("/api/session/rename")
def api_session_rename():
    payload = read_json_request()
    session_id = clean_text(payload.get("session_id") or payload.get("id"))
    title = clean_text(payload.get("title"))

    if not session_id:
        return json_error("session_id is required.", code="invalid_request", status=400)
    if not title:
        return json_error("title is required.", code="invalid_request", status=400)

    session = rename_session_by_id(session_id, title)
    if not session:
        return json_error("Session not found.", code="not_found", status=404)

    return jsonify({"ok": True, "session": session})


@app.get("/api/chat/<session_id>")
def api_chat_get(session_id: str):
    session = find_session(session_id)
    if not session:
        return json_error("Session not found.", code="not_found", status=404)
    return jsonify({"ok": True, "session": session})


# =========================================================
# chat routes
# =========================================================

@app.post("/api/chat")
def api_chat():
    if not callable(generate_reply):
        return json_error(
            CHAT_IMPORT_ERROR or "chat_service unavailable",
            code="service_unavailable",
            status=500,
        )

    payload = read_json_request()
    content = clean_text(payload.get("content"))
    session_id = clean_text(payload.get("session_id"))

    if not content:
        return json_error("content is required.", code="invalid_request", status=400)

    if not session_id:
        session = create_session("New chat")
        session_id = session["id"]

    user_message = {
        "id": f"user_{uuid.uuid4().hex}",
        "role": "user",
        "content": content,
        "created_at": utc_now_iso(),
        "metadata": {},
    }
    append_message_to_session(session_id, user_message)

    service_payload = {
        **payload,
        "content": content,
        "session_id": session_id,
        "messages": find_session(session_id).get("messages", [])[:-1] if find_session(session_id) else [],
        "stream": False,
    }

    result = safe_dict(generate_reply(service_payload))
    assistant_message = safe_dict(result.get("assistant_message") or result.get("message"))

    if clean_text(assistant_message.get("content")):
        assistant_message["session_id"] = session_id
        append_message_to_session(session_id, assistant_message)

    session = find_session(session_id)

    return jsonify(
        {
            "ok": bool(result.get("ok", True)),
            "message": assistant_message,
            "assistant_message": assistant_message,
            "session": session,
            "session_id": session_id,
            "model": result.get("model"),
            "debug": result.get("debug"),
            "error": result.get("error"),
        }
    )


@app.post("/api/chat/stream")
def api_chat_stream():
    if not callable(generate_reply_stream):
        return json_error(
            CHAT_IMPORT_ERROR or "chat_service unavailable",
            code="service_unavailable",
            status=500,
        )

    payload = read_json_request()
    content = clean_text(payload.get("content"))
    session_id = clean_text(payload.get("session_id"))

    if not content:
        return json_error("content is required.", code="invalid_request", status=400)

    if not session_id:
        session = create_session("New chat")
        session_id = session["id"]

    user_message = {
        "id": f"user_{uuid.uuid4().hex}",
        "role": "user",
        "content": content,
        "created_at": utc_now_iso(),
        "metadata": {},
    }
    append_message_to_session(session_id, user_message)

    existing_session = find_session(session_id)
    history = safe_list(existing_session.get("messages"))[:-1] if existing_session else []

    service_payload = {
        **payload,
        "content": content,
        "session_id": session_id,
        "messages": history,
        "stream": True,
    }

    try:
        stream_iter, debug = generate_reply_stream(service_payload)
    except Exception as exc:
        return json_error(str(exc), code="stream_init_failed", status=500)

    def event_stream():
        yield sse_event(
            "start",
            {
                "ok": True,
                "session_id": session_id,
                "debug": debug,
                "created_at": utc_now_iso(),
            },
        )

        final_done: Optional[Dict[str, Any]] = None

        try:
            for raw_event in stream_iter:
                event = safe_dict(raw_event)
                event_type = clean_text(event.get("type")) or "message"

                if event_type == "done" and callable(coerce_stream_done_event):
                    event = safe_dict(coerce_stream_done_event(event))

                if event_type == "done":
                    final_done = event

                yield sse_event(event_type, event)

        except Exception as exc:
            yield sse_event(
                "error",
                {
                    "ok": False,
                    "error": {
                        "code": "stream_failed",
                        "message": str(exc),
                    },
                },
            )
            return

        if final_done:
            assistant_message = safe_dict(final_done.get("assistant_message") or final_done.get("message"))
            if clean_text(assistant_message.get("content")):
                assistant_message["session_id"] = session_id
                append_message_to_session(session_id, assistant_message)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/debug/brain")
def api_debug_brain():
    if not callable(preview_chat_brain):
        return json_error(
            CHAT_IMPORT_ERROR or "chat_service unavailable",
            code="service_unavailable",
            status=500,
        )

    payload = read_json_request()
    result = safe_dict(preview_chat_brain(payload))
    return jsonify(result)


# =========================================================
# memory routes
# =========================================================

@app.get("/api/memory")
def api_memory_list():
    if not callable(memory_list):
        return json_error(
            MEMORY_IMPORT_ERROR or "memory_service unavailable",
            code="service_unavailable",
            status=500,
        )
    payload = {
        "session_id": request.args.get("session_id"),
        "kind": request.args.get("kind"),
        "query": request.args.get("query"),
        "limit": request.args.get("limit"),
    }
    result = safe_dict(memory_list(payload))
    return jsonify(result)


@app.post("/api/memory/add")
def api_memory_add():
    if not callable(memory_add):
        return json_error(
            MEMORY_IMPORT_ERROR or "memory_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(memory_add(read_json_request()))
    return jsonify(result)


@app.post("/api/memory/delete")
def api_memory_delete():
    if not callable(memory_delete):
        return json_error(
            MEMORY_IMPORT_ERROR or "memory_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(memory_delete(read_json_request()))
    return jsonify(result)


@app.get("/api/memory/export")
def api_memory_export():
    if not callable(memory_export):
        return json_error(
            MEMORY_IMPORT_ERROR or "memory_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(memory_export({}))
    return jsonify(result)


# =========================================================
# artifact routes
# =========================================================

@app.get("/api/artifacts")
def api_artifacts_list():
    if not callable(list_artifacts):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )

    payload = {
        "session_id": request.args.get("session_id"),
        "q": request.args.get("q"),
        "kind": request.args.get("kind"),
        "limit": request.args.get("limit"),
    }
    result = safe_dict(list_artifacts(payload))
    return jsonify(result)


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_get(artifact_id: str):
    if not callable(get_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(get_artifact({"id": artifact_id}))
    return jsonify(result)


@app.post("/api/artifacts/create")
def api_artifact_create():
    if not callable(create_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(create_artifact(read_json_request()))
    return jsonify(result)


@app.post("/api/artifacts/save")
def api_artifact_save():
    if not callable(save_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(save_artifact(read_json_request()))
    return jsonify(result)


@app.post("/api/artifacts/update")
def api_artifact_update():
    if not callable(update_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(update_artifact(read_json_request()))
    return jsonify(result)


@app.post("/api/artifacts/delete")
def api_artifact_delete():
    if not callable(delete_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(delete_artifact(read_json_request()))
    return jsonify(result)


@app.post("/api/artifacts/pin")
def api_artifact_pin():
    if not callable(pin_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(pin_artifact(read_json_request()))
    return jsonify(result)


@app.post("/api/artifacts/toggle-pin")
def api_artifact_toggle_pin():
    if not callable(toggle_artifact_pin):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(toggle_artifact_pin(read_json_request()))
    return jsonify(result)


@app.get("/api/artifacts/export")
def api_artifact_export():
    if not callable(export_artifact):
        return json_error(
            ARTIFACT_IMPORT_ERROR or "artifact_service unavailable",
            code="service_unavailable",
            status=500,
        )
    payload = {
        "id": request.args.get("id"),
        "artifact_id": request.args.get("artifact_id"),
    }
    result = safe_dict(export_artifact(payload))
    return jsonify(result)


# =========================================================
# attachment routes
# =========================================================

@app.get("/api/attachments")
def api_attachments_list():
    if not callable(list_attachments):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )

    payload = {
        "session_id": request.args.get("session_id"),
        "kind": request.args.get("kind"),
        "limit": request.args.get("limit"),
    }
    result = list_attachments(payload)
    return jsonify({"ok": True, "attachments": result, "count": len(result)})


@app.post("/api/attachments/register")
def api_attachment_register():
    if not callable(register_attachment):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(register_attachment(read_json_request()))
    return jsonify(result)


@app.post("/api/attachments/register-many")
def api_attachments_register_many():
    if not callable(register_attachments):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )
    payload = read_json_request()
    result = safe_dict(register_attachments(safe_list(payload.get("attachments"))))
    return jsonify(result)


@app.post("/api/attachments/delete")
def api_attachment_delete():
    if not callable(delete_attachment):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(delete_attachment(read_json_request()))
    return jsonify(result)


@app.post("/api/attachments/cleanup")
def api_attachments_cleanup():
    if not callable(cleanup_missing_files):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(cleanup_missing_files())
    return jsonify(result)


@app.get("/api/attachments/stats")
def api_attachments_stats():
    if not callable(attachment_stats):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(attachment_stats())
    return jsonify(result)


@app.post("/api/attachments/upload")
def api_attachment_upload():
    if not callable(save_uploaded_file):
        return json_error(
            ATTACHMENT_IMPORT_ERROR or "attachment_service unavailable",
            code="service_unavailable",
            status=500,
        )

    if "file" not in request.files:
        return json_error("file is required.", code="invalid_request", status=400)

    uploaded = request.files["file"]
    filename = secure_filename(uploaded.filename or "")
    if not filename:
        return json_error("Uploaded file must have a filename.", code="invalid_request", status=400)

    content_bytes = uploaded.read()
    session_id = clean_text(request.form.get("session_id"))
    message_id = clean_text(request.form.get("message_id"))
    mime_type = clean_text(uploaded.mimetype)

    metadata: Dict[str, Any] = {}
    raw_metadata = clean_text(request.form.get("metadata"))
    if raw_metadata:
        try:
            parsed = json.loads(raw_metadata)
            if isinstance(parsed, dict):
                metadata = parsed
        except Exception:
            metadata = {}

    result = safe_dict(
        save_uploaded_file(
            filename=filename,
            content_bytes=content_bytes,
            session_id=session_id or None,
            message_id=message_id or None,
            mime_type=mime_type or None,
            metadata=metadata,
        )
    )
    return jsonify(result)


# =========================================================
# web routes
# =========================================================

@app.post("/api/debug/web_preview")
def api_debug_web_preview():
    if not callable(web_preview_from_text):
        return json_error(
            WEB_IMPORT_ERROR or "web_service unavailable",
            code="service_unavailable",
            status=500,
        )
    payload = read_json_request()
    text = clean_text(payload.get("text"))
    if not text:
        return json_error("text is required.", code="invalid_request", status=400)
    result = safe_dict(web_preview_from_text(text))
    return jsonify(result)


@app.post("/api/web/fetch")
def api_web_fetch():
    if not callable(fetch_single_url):
        return json_error(
            WEB_IMPORT_ERROR or "web_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(fetch_single_url(read_json_request()))
    return jsonify(result)


@app.post("/api/web/fetch-many")
def api_web_fetch_many():
    if not callable(fetch_urls):
        return json_error(
            WEB_IMPORT_ERROR or "web_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(fetch_urls(read_json_request()))
    return jsonify(result)


@app.get("/api/web/status")
def api_web_status():
    if not callable(web_service_status):
        return json_error(
            WEB_IMPORT_ERROR or "web_service unavailable",
            code="service_unavailable",
            status=500,
        )
    result = safe_dict(web_service_status())
    return jsonify(result)


# =========================================================
# error handlers
# =========================================================

@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return json_error("Not Found", code="not_found", status=404)
    return ("Not Found", 404)


@app.errorhandler(405)
def method_not_allowed(_error):
    if request.path.startswith("/api/"):
        return json_error("Method Not Allowed", code="method_not_allowed", status=405)
    return ("Method Not Allowed", 405)


@app.errorhandler(413)
def payload_too_large(_error):
    return json_error("Uploaded payload too large.", code="payload_too_large", status=413)


@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith("/api/"):
        return json_error(str(error), code="internal_error", status=500)
    return ("Internal Server Error", 500)


# =========================================================
# main
# =========================================================

if __name__ == "__main__":
    host = os.getenv("NOVA_HOST", "127.0.0.1")
    port = int(os.getenv("NOVA_PORT", "5001"))
    debug = os.getenv("NOVA_DEBUG", "true").lower() in {"1", "true", "yes", "on"}

    print(f"[NOVA] starting Flask app on http://{host}:{port}")
    print(f"[NOVA] templates: {TEMPLATES_DIR}")
    print(f"[NOVA] static: {STATIC_DIR}")
    print(f"[NOVA] sessions file: {SESSIONS_FILE}")
    print(f"[NOVA] openai model: {os.getenv('OPENAI_MODEL', 'gpt-5.4')}")

    app.run(host=host, port=port, debug=debug)