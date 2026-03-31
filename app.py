from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_UPLOAD_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "svg",
    "pdf",
    "txt",
    "log",
    "md",
    "json",
    "csv",
    "html",
    "htm",
    "xml",
    "yaml",
    "yml",
}

ROUTE_BUILD = "clean-chat-pipeline-2026-03-31-006"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["JSON_SORT_KEYS"] = False
app.config["PROPAGATE_EXCEPTIONS"] = False


ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
SESSIONS_FILE = DATA_DIR / "nova_sessions.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_trace(label: str, exc: BaseException) -> str:
    tb = traceback.format_exc()
    print("\n" + "=" * 80)
    print(f"[{utc_now_iso()}] {label}")
    print(f"{type(exc).__name__}: {exc}")
    print(tb)
    print("=" * 80 + "\n")
    return tb


def safe_error_response(
    *,
    route: str,
    exc: BaseException,
    status_code: int = 500,
    extra_debug: dict[str, Any] | None = None,
):
    tb = print_trace(f"ROUTE CRASH {route}", exc)
    debug = {
        "route": route,
        "exception_type": type(exc).__name__,
        "traceback": tb,
        "timestamp": utc_now_iso(),
        "route_build": ROUTE_BUILD,
    }
    if extra_debug:
        debug.update(extra_debug)

    return (
        jsonify(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "message": f"{type(exc).__name__}: {exc}",
                "debug": debug,
            }
        ),
        status_code,
    )


def normalize_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


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


def write_json_file(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_data_files_exist() -> None:
    if not SESSIONS_FILE.exists():
        write_json_file(SESSIONS_FILE, [])
    if not MEMORY_FILE.exists():
        write_json_file(MEMORY_FILE, [])
    if not ARTIFACTS_FILE.exists():
        write_json_file(ARTIFACTS_FILE, [])


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def normalize_response(result: Any, session_id: str, content: str) -> dict[str, Any]:
    fallback_message = normalize_text(content, "").strip()
    if fallback_message:
        fallback_message = f"You said: {fallback_message}"
    else:
        fallback_message = "Nova fallback is active."

    base = {
        "ok": True,
        "message": fallback_message,
        "assistant_message": {
            "id": None,
            "role": "assistant",
            "content": fallback_message,
            "created_at": utc_now_iso(),
            "meta": {},
            "attachments": [],
        },
        "session_id": session_id or "default-session",
        "debug": {},
    }

    if isinstance(result, dict):
        merged = dict(base)
        merged.update(result)

        assistant_message = merged.get("assistant_message")
        if not isinstance(assistant_message, dict):
            assistant_message = dict(base["assistant_message"])
        else:
            fixed_assistant = dict(base["assistant_message"])
            fixed_assistant.update(assistant_message)
            assistant_message = fixed_assistant

        if not isinstance(assistant_message.get("meta"), dict):
            assistant_message["meta"] = {}

        if not isinstance(assistant_message.get("attachments"), list):
            assistant_message["attachments"] = []

        if not normalize_text(assistant_message.get("role"), "").strip():
            assistant_message["role"] = "assistant"

        if not normalize_text(assistant_message.get("content"), "").strip():
            assistant_message["content"] = normalize_text(
                merged.get("message"),
                fallback_message,
            )

        if not normalize_text(assistant_message.get("created_at"), "").strip():
            assistant_message["created_at"] = utc_now_iso()

        merged["assistant_message"] = assistant_message

        if not isinstance(merged.get("debug"), dict):
            merged["debug"] = {}

        if not normalize_text(merged.get("message"), "").strip():
            merged["message"] = normalize_text(
                merged["assistant_message"].get("content"),
                fallback_message,
            )

        if not normalize_text(merged.get("session_id"), "").strip():
            merged["session_id"] = session_id or "default-session"

        ok_value = merged.get("ok")
        if not isinstance(ok_value, bool):
            merged["ok"] = True

        return merged

    text_result = normalize_text(result, "").strip() or fallback_message

    return {
        "ok": True,
        "message": text_result,
        "assistant_message": {
            "id": None,
            "role": "assistant",
            "content": text_result,
            "created_at": utc_now_iso(),
            "meta": {},
            "attachments": [],
        },
        "session_id": session_id or "default-session",
        "debug": {},
    }


def get_chat_service():
    from services.chat_service import ChatService

    service = ChatService()
    if not callable(getattr(service, "send_message", None)):
        raise RuntimeError("ChatService instance missing callable send_message")
    return service


def get_chat_service_debug() -> dict[str, Any]:
    try:
        module = __import__(
            "services.chat_service",
            fromlist=[
                "ChatService",
                "CHAT_SERVICE_VERSION",
                "MODEL_STAGE_REAL",
                "MODEL_STAGE_FALLBACK",
            ],
        )
        service = module.ChatService()

        return {
            "chat_service_class": service.__class__.__name__,
            "chat_service_module": service.__class__.__module__,
            "chat_service_version": getattr(module, "CHAT_SERVICE_VERSION", None),
            "loaded_chat_service_version": getattr(module, "CHAT_SERVICE_VERSION", None),
            "loaded_model_stage_real": getattr(module, "MODEL_STAGE_REAL", None),
            "loaded_model_stage_fallback": getattr(module, "MODEL_STAGE_FALLBACK", None),
            "client_ready": bool(getattr(service, "client", None)),
            "api_key_present": bool(getattr(service, "api_key", "")),
            "model": getattr(service, "model", None),
        }
    except Exception as exc:
        return {
            "chat_service_probe_error": f"{type(exc).__name__}: {exc}",
        }


def call_send_message(
    service: Any,
    *,
    content: str,
    session_id: str,
    attachments: list[Any],
    raw_payload: dict[str, Any],
):
    send_fn = getattr(service, "send_message", None)
    if not callable(send_fn):
        raise RuntimeError("ChatService instance missing callable send_message")

    return send_fn(
        content=content,
        session_id=session_id,
        attachments=attachments,
        payload=raw_payload,
    )


def normalize_message_for_session(message: Any, *, role_fallback: str) -> dict[str, Any]:
    msg = message if isinstance(message, dict) else {}
    content = normalize_text(msg.get("content"), "").strip()

    return {
        "id": normalize_text(msg.get("id"), "") or str(uuid.uuid4()),
        "role": normalize_text(msg.get("role"), role_fallback) or role_fallback,
        "content": content,
        "created_at": normalize_text(msg.get("created_at"), "") or utc_now_iso(),
        "attachments": msg.get("attachments", []) if isinstance(msg.get("attachments"), list) else [],
        "meta": msg.get("meta", {}) if isinstance(msg.get("meta"), dict) else {},
    }


def load_sessions() -> list[dict[str, Any]]:
    ensure_data_files_exist()
    sessions = read_json_file(SESSIONS_FILE, [])
    return sessions if isinstance(sessions, list) else []


def save_sessions(sessions: list[dict[str, Any]]) -> None:
    ensure_data_files_exist()
    write_json_file(SESSIONS_FILE, sessions)


def build_session_title(user_content: str, existing_title: str = "") -> str:
    existing = normalize_text(existing_title, "").strip()
    if existing:
        return existing
    seed = normalize_text(user_content, "").strip()
    return (seed[:60] or "New Chat").strip()


def ensure_session_record(session_id: str, title_seed: str = "") -> dict[str, Any]:
    sessions = load_sessions()
    now = utc_now_iso()

    for session in sessions:
        if normalize_text(session.get("id"), "") == session_id:
            if not isinstance(session.get("messages"), list):
                session["messages"] = []
            if not normalize_text(session.get("title"), "").strip():
                session["title"] = build_session_title(title_seed)
            session["message_count"] = len(session["messages"])
            session["updated_at"] = now
            save_sessions(sessions)
            return session

    new_session = {
        "id": session_id,
        "title": build_session_title(title_seed),
        "created_at": now,
        "updated_at": now,
        "pinned": False,
        "message_count": 0,
        "last_message_preview": "",
        "messages": [],
    }
    sessions.append(new_session)
    save_sessions(sessions)
    return new_session


def get_session_by_id(session_id: str) -> dict[str, Any] | None:
    sessions = load_sessions()
    for session in sessions:
        if normalize_text(session.get("id"), "") == session_id:
            return session
    return None


def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    session = get_session_by_id(session_id)
    if not session:
        return []
    messages = session.get("messages", [])
    return messages if isinstance(messages, list) else []


def persist_chat_exchange(
    session_id: str,
    user_content: str,
    assistant_message: dict[str, Any],
    attachments: list[Any] | None = None,
) -> dict[str, Any]:
    sessions = load_sessions()
    now = utc_now_iso()
    target_session: dict[str, Any] | None = None

    for session in sessions:
        if normalize_text(session.get("id"), "") == session_id:
            target_session = session
            break

    if target_session is None:
        target_session = {
            "id": session_id,
            "title": build_session_title(user_content),
            "created_at": now,
            "updated_at": now,
            "pinned": False,
            "message_count": 0,
            "last_message_preview": "",
            "messages": [],
        }
        sessions.append(target_session)

    if not isinstance(target_session.get("messages"), list):
        target_session["messages"] = []

    normalized_user_attachments = attachments if isinstance(attachments, list) else []

    user_message = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": normalize_text(user_content, ""),
        "created_at": now,
        "attachments": normalized_user_attachments,
        "meta": {
            "attachments_count": len(normalized_user_attachments),
            "document_used": False,
            "document_count": 0,
            "document_names": [],
        },
    }

    assistant_normalized = normalize_message_for_session(
        assistant_message,
        role_fallback="assistant",
    )

    messages: list[dict[str, Any]] = target_session["messages"]

    should_add_user = True
    if messages:
        last = messages[-1]
        if (
            normalize_text(last.get("role"), "") == "user"
            and normalize_text(last.get("content"), "") == normalize_text(user_content, "")
        ):
            should_add_user = False

    if should_add_user and normalize_text(user_content, ""):
        messages.append(user_message)

    should_add_assistant = True
    if messages:
        last = messages[-1]
        if (
            normalize_text(last.get("role"), "") == "assistant"
            and normalize_text(last.get("content"), "") == normalize_text(assistant_normalized.get("content"), "")
        ):
            should_add_assistant = False

    if should_add_assistant and normalize_text(assistant_normalized.get("content"), ""):
        messages.append(assistant_normalized)

    target_session["title"] = build_session_title(
        user_content,
        normalize_text(target_session.get("title"), ""),
    )
    target_session["updated_at"] = now
    target_session["message_count"] = len(messages)
    target_session["last_message_preview"] = normalize_text(
        assistant_normalized.get("content"),
        user_content,
    )[:160]

    save_sessions(sessions)
    return target_session


def try_get_state(active_session_id: str = "") -> dict[str, Any]:
    ensure_data_files_exist()

    sessions = load_sessions()
    memory = read_json_file(MEMORY_FILE, [])
    artifacts = read_json_file(ARTIFACTS_FILE, [])

    active_session_id = normalize_text(active_session_id, "").strip()
    active_messages = get_session_messages(active_session_id) if active_session_id else []

    return {
        "ok": True,
        "sessions": sessions if isinstance(sessions, list) else [],
        "memory": memory if isinstance(memory, list) else [],
        "artifacts": artifacts if isinstance(artifacts, list) else [],
        "active_session_id": active_session_id or None,
        "active_messages": active_messages,
        "debug": {
            "sessions_file": str(SESSIONS_FILE),
            "memory_file": str(MEMORY_FILE),
            "artifacts_file": str(ARTIFACTS_FILE),
            "sessions_count": len(sessions) if isinstance(sessions, list) else 0,
            "memory_count": len(memory) if isinstance(memory, list) else 0,
            "artifacts_count": len(artifacts) if isinstance(artifacts, list) else 0,
            "active_session_id": active_session_id or None,
            "active_messages_count": len(active_messages),
            "route_build": ROUTE_BUILD,
        },
    }


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    return safe_error_response(route="global", exc=exc, status_code=500)


@app.errorhandler(404)
def handle_404(_exc):
    return (
        jsonify(
            {
                "ok": False,
                "error": "Not found",
                "message": "Not found",
                "debug": {
                    "route": request.path,
                    "method": request.method,
                    "status_code": 404,
                    "route_build": ROUTE_BUILD,
                },
            }
        ),
        404,
    )


@app.errorhandler(405)
def handle_405(_exc):
    return (
        jsonify(
            {
                "ok": False,
                "error": "Method not allowed",
                "message": "Method not allowed",
                "debug": {
                    "route": request.path,
                    "method": request.method,
                    "status_code": 405,
                    "route_build": ROUTE_BUILD,
                },
            }
        ),
        405,
    )


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    ensure_data_files_exist()
    service_debug = get_chat_service_debug()
    return jsonify(
        {
            "ok": True,
            "message": "healthy",
            "debug": {
                "timestamp": utc_now_iso(),
                "cwd": str(BASE_DIR),
                "uploads_dir": str(UPLOADS_DIR),
                "data_dir": str(DATA_DIR),
                "sessions_file": str(SESSIONS_FILE),
                "memory_file": str(MEMORY_FILE),
                "artifacts_file": str(ARTIFACTS_FILE),
                "route_build": ROUTE_BUILD,
                **service_debug,
            },
        }
    )


@app.get("/api/state")
def api_state():
    try:
        session_id = normalize_text(request.args.get("session_id"), "").strip()
        if session_id:
            ensure_session_record(session_id)
        state = try_get_state(session_id)
        return jsonify(state)
    except Exception as exc:
        return safe_error_response(route="/api/state", exc=exc)


@app.get("/api/artifacts")
def api_artifacts():
    try:
        ensure_data_files_exist()
        artifacts = read_json_file(ARTIFACTS_FILE, [])
        if not isinstance(artifacts, list):
            artifacts = []

        return jsonify(
            {
                "ok": True,
                "artifacts": artifacts,
                "debug": {
                    "count": len(artifacts),
                    "source": str(ARTIFACTS_FILE),
                    "route_build": ROUTE_BUILD,
                },
            }
        )
    except Exception as exc:
        return safe_error_response(route="/api/artifacts", exc=exc)


@app.post("/api/upload")
def api_upload():
    try:
        files = request.files.getlist("files")
        saved = []

        for file in files:
            if not file or not file.filename:
                continue
            if not allowed_file(file.filename):
                continue

            filename = secure_filename(file.filename)
            target = UPLOADS_DIR / filename

            if target.exists():
                stem = target.stem
                suffix = target.suffix
                counter = 1
                while True:
                    alt = UPLOADS_DIR / f"{stem}_{counter}{suffix}"
                    if not alt.exists():
                        target = alt
                        break
                    counter += 1

            file.save(target)
            saved.append(
                {
                    "name": target.name,
                    "url": f"/uploads/{target.name}",
                    "path": str(target),
                    "size": target.stat().st_size if target.exists() else 0,
                }
            )

        return jsonify(
            {
                "ok": True,
                "files": saved,
                "debug": {
                    "saved_count": len(saved),
                    "route_build": ROUTE_BUILD,
                },
            }
        )
    except Exception as exc:
        return safe_error_response(route="/api/upload", exc=exc)


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.post("/api/chat")
def api_chat():
    payload: dict[str, Any] = {}
    content = ""
    session_id = "default-session"
    attachments: list[Any] = []

    try:
        ensure_data_files_exist()

        payload = request.get_json(silent=True) or {}

        if not isinstance(payload, dict):
            payload = {}

        content = normalize_text(
            payload.get("content")
            or payload.get("message")
            or payload.get("text")
            or payload.get("prompt"),
            "",
        ).strip()

        session_id = normalize_text(
            payload.get("session_id"),
            "default-session",
        ).strip() or "default-session"

        raw_attachments = payload.get("attachments", [])
        attachments = raw_attachments if isinstance(raw_attachments, list) else []

        ensure_session_record(session_id, title_seed=content)

        if "history" not in payload or not isinstance(payload.get("history"), list) or not payload.get("history"):
            existing_messages = get_session_messages(session_id)
            payload["history"] = existing_messages[-12:] if isinstance(existing_messages, list) else []

        debug_in = {
            "route": "/api/chat",
            "request_content_type": request.content_type,
            "payload_keys": sorted(list(payload.keys())),
            "content_chars": len(content),
            "session_id": session_id,
            "attachments_count": len(attachments),
            "history_count_in": len(payload.get("history", [])) if isinstance(payload.get("history"), list) else 0,
            "timestamp": utc_now_iso(),
            "route_build": ROUTE_BUILD,
        }

        service = get_chat_service()
        result = call_send_message(
            service,
            content=content,
            session_id=session_id,
            attachments=attachments,
            raw_payload=payload,
        )

        response_payload = normalize_response(result, session_id, content)

        if not isinstance(response_payload.get("debug"), dict):
            response_payload["debug"] = {}

        if not isinstance(response_payload.get("assistant_message"), dict):
            response_payload["assistant_message"] = {
                "id": None,
                "role": "assistant",
                "content": normalize_text(response_payload.get("message"), ""),
                "created_at": utc_now_iso(),
                "meta": {},
                "attachments": [],
            }

        if not isinstance(response_payload["assistant_message"].get("meta"), dict):
            response_payload["assistant_message"]["meta"] = {}

        if not isinstance(response_payload["assistant_message"].get("attachments"), list):
            response_payload["assistant_message"]["attachments"] = []

        saved_session = persist_chat_exchange(
            session_id=session_id,
            user_content=content,
            assistant_message=response_payload["assistant_message"],
            attachments=attachments,
        )

        active_messages = get_session_messages(session_id)

        response_payload["session_id"] = session_id
        response_payload["debug"]["request_debug"] = debug_in
        response_payload["debug"]["route_shielded"] = True
        response_payload["debug"]["route_build"] = ROUTE_BUILD
        response_payload["debug"]["sessions_file"] = str(SESSIONS_FILE)
        response_payload["debug"]["persisted_session_id"] = session_id
        response_payload["debug"]["persisted_session_title"] = normalize_text(saved_session.get("title"), "")
        response_payload["debug"]["persisted_session_message_count"] = len(
            saved_session.get("messages", []) if isinstance(saved_session.get("messages"), list) else []
        )
        response_payload["debug"]["active_messages_count"] = len(active_messages)
        response_payload["assistant_message"]["meta"]["route_build"] = ROUTE_BUILD

        return jsonify(response_payload), 200

    except Exception as exc:
        return safe_error_response(
            route="/api/chat",
            exc=exc,
            status_code=500,
            extra_debug={
                "payload": payload,
                "content_preview": content[:300],
                "content_chars": len(content or ""),
                "session_id": session_id,
                "attachments_count": len(attachments or []),
                "request_content_type": request.content_type,
                "route_shielded": True,
                "route_build": ROUTE_BUILD,
                "sessions_file": str(SESSIONS_FILE),
            },
        )


if __name__ == "__main__":
    ensure_data_files_exist()
    port = int(os.getenv("APP_PORT", os.getenv("NOVA_PORT", "5001")))
    app.run(
        host="127.0.0.1",
        port=port,
        debug=True,
        threaded=True,
        use_reloader=False,
    )