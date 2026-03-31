from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

from services.artifact_service import ArtifactService

try:
    from services.chat_service import ChatService
except Exception:
    ChatService = None


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ROUTE_BUILD = "clean-chat-pipeline-2026-03-31-011"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

artifact_service = ArtifactService(artifacts_file=ARTIFACTS_FILE, sessions_file=SESSIONS_FILE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


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


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_trace(label: str, exc: Exception) -> str:
    tb = traceback.format_exc()
    print("\n" + "=" * 80)
    print(f"[{utc_now()}] APP ERROR: {label}")
    print(f"{type(exc).__name__}: {exc}")
    print(tb)
    print("=" * 80 + "\n")
    return tb


def success_payload(message: str, **extra: Any):
    return jsonify({
        "ok": True,
        "message": message,
        **extra,
    })


def error_payload(message: str, status: int = 400, debug: dict[str, Any] | None = None):
    return jsonify({
        "ok": False,
        "message": message,
        "error": message,
        "debug": {
            "timestamp": utc_now(),
            "route_build": ROUTE_BUILD,
            **(debug or {}),
        },
    }), status


def get_request_json() -> dict[str, Any]:
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


def get_session_id_from_request(default: str = "default-session") -> str:
    body = get_request_json()
    session_id = (
        body.get("session_id")
        or request.args.get("session_id")
        or request.form.get("session_id")
        or default
    )
    return str(session_id).strip() or default


def read_sessions_payload() -> dict[str, Any]:
    data = read_json_file(SESSIONS_FILE, {})
    if isinstance(data, list):
        return {"sessions": data, "active_session_id": "default-session"}
    if isinstance(data, dict):
        data.setdefault("sessions", [])
        data.setdefault("active_session_id", "default-session")
        return data
    return {"sessions": [], "active_session_id": "default-session"}


def write_sessions_payload(payload: dict[str, Any]) -> None:
    payload.setdefault("sessions", [])
    payload.setdefault("active_session_id", "default-session")
    write_json_file(SESSIONS_FILE, payload)


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    msg = dict(message or {})
    msg.setdefault("id", new_id("msg"))
    msg.setdefault("role", "assistant")
    msg.setdefault("content", "")
    msg.setdefault("created_at", utc_now())
    msg.setdefault("attachments", [])
    msg.setdefault("meta", {})
    return msg


def normalize_session_record(session: dict[str, Any]) -> dict[str, Any]:
    session = dict(session or {})
    created_at = session.get("created_at") or utc_now()

    session.setdefault("id", "default-session")
    session.setdefault("title", "New Chat")
    session.setdefault("created_at", created_at)
    session.setdefault("updated_at", created_at)
    session.setdefault("pinned", False)

    raw_messages = session.get("messages") or []
    if not isinstance(raw_messages, list):
        raw_messages = []

    messages = [normalize_message(item) for item in raw_messages if isinstance(item, dict)]
    session["messages"] = messages
    session["message_count"] = len(messages)

    if messages:
        preview = str(messages[-1].get("content") or "").strip().replace("\n", " ")
        session["last_message_preview"] = preview[:120]
    else:
        session["last_message_preview"] = ""

    return session


def sort_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_session_record(item) for item in sessions if isinstance(item, dict)]

    pinned = [item for item in normalized if item.get("pinned")]
    unpinned = [item for item in normalized if not item.get("pinned")]

    pinned = sorted(
        pinned,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    unpinned = sorted(
        unpinned,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return pinned + unpinned


def ensure_default_session(payload: dict[str, Any]) -> dict[str, Any]:
    sessions = payload.get("sessions", [])
    if sessions:
        payload["sessions"] = sort_sessions(sessions)
        if not payload.get("active_session_id"):
            payload["active_session_id"] = payload["sessions"][0]["id"]
        return payload

    default_session = normalize_session_record({
        "id": "default-session",
        "title": "New Chat",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "pinned": False,
        "messages": [],
    })
    payload["sessions"] = [default_session]
    payload["active_session_id"] = "default-session"
    write_sessions_payload(payload)
    return payload


def get_or_create_session(session_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = ensure_default_session(read_sessions_payload())
    sessions = payload.get("sessions", [])

    for idx, raw_session in enumerate(sessions):
        if str(raw_session.get("id")) == session_id:
            normalized = normalize_session_record(raw_session)
            sessions[idx] = normalized
            payload["sessions"] = sort_sessions(sessions)
            payload["active_session_id"] = normalized["id"]
            write_sessions_payload(payload)
            return normalized, payload

    new_session = normalize_session_record({
        "id": session_id,
        "title": "New Chat",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "pinned": False,
        "messages": [],
    })
    sessions.insert(0, new_session)
    payload["sessions"] = sort_sessions(sessions)
    payload["active_session_id"] = new_session["id"]
    write_sessions_payload(payload)
    return new_session, payload


def save_session(session: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = ensure_default_session(payload or read_sessions_payload())
    sessions = data.get("sessions", [])
    normalized = normalize_session_record(session)

    replaced = False
    for idx, item in enumerate(sessions):
        if str(item.get("id")) == str(normalized.get("id")):
            sessions[idx] = normalized
            replaced = True
            break

    if not replaced:
        sessions.insert(0, normalized)

    data["sessions"] = sort_sessions(sessions)
    data["active_session_id"] = normalized["id"]
    write_sessions_payload(data)
    return normalized


def delete_session_record(session_id: str) -> tuple[bool, str]:
    payload = ensure_default_session(read_sessions_payload())
    sessions = payload.get("sessions", [])

    kept = [item for item in sessions if str(item.get("id")) != session_id]
    removed = len(kept) != len(sessions)

    if not removed:
        return False, payload.get("active_session_id") or "default-session"

    if not kept:
        fallback = normalize_session_record({
            "id": "default-session",
            "title": "New Chat",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "pinned": False,
            "messages": [],
        })
        kept = [fallback]

    payload["sessions"] = sort_sessions(kept)
    payload["active_session_id"] = payload["sessions"][0]["id"]
    write_sessions_payload(payload)

    next_session_id = payload["active_session_id"]
    return True, next_session_id


def session_summary(session: dict[str, Any]) -> dict[str, Any]:
    session = normalize_session_record(session)
    return {
        "id": session.get("id"),
        "title": session.get("title"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned")),
        "message_count": session.get("message_count", 0),
        "last_message_preview": session.get("last_message_preview", ""),
    }


def all_session_summaries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sessions = payload.get("sessions", [])
    sessions = sort_sessions(sessions)
    return [session_summary(item) for item in sessions]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/uploads/<path:filename>")
def uploads(filename: str):
    return send_from_directory(UPLOADS_DIR, filename)


@app.get("/api/health")
def api_health():
    return success_payload(
        "healthy",
        debug={
            "timestamp": utc_now(),
            "cwd": str(BASE_DIR),
            "uploads_dir": str(UPLOADS_DIR),
            "data_dir": str(DATA_DIR),
            "sessions_file": str(SESSIONS_FILE),
            "memory_file": str(MEMORY_FILE),
            "artifacts_file": str(ARTIFACTS_FILE),
            "route_build": ROUTE_BUILD,
            "chat_service_class": getattr(ChatService, "__name__", None),
            "chat_service_module": getattr(ChatService, "__module__", None),
        },
    )


@app.get("/api/state")
def api_state():
    try:
        session_id = get_session_id_from_request()
        session, payload = get_or_create_session(session_id)

        memory_items = read_json_file(MEMORY_FILE, [])
        if not isinstance(memory_items, list):
            memory_items = []

        return success_payload(
            "State loaded",
            session=session,
            sessions=all_session_summaries(payload),
            active_session_id=payload.get("active_session_id", session_id),
            memory_items=memory_items,
            debug={
                "route_build": ROUTE_BUILD,
                "session_id": session_id,
                "session_count": len(payload.get("sessions", [])),
                "memory_count": len(memory_items),
            },
        )
    except Exception as exc:
        tb = safe_trace("api_state", exc)
        return error_payload("Failed to load state", 500, {"traceback": tb})


@app.post("/api/sessions/new")
def api_sessions_new():
    try:
        session_id = new_id("session")
        payload = ensure_default_session(read_sessions_payload())

        session = normalize_session_record({
            "id": session_id,
            "title": "New Chat",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "pinned": False,
            "messages": [],
        })

        sessions = payload.get("sessions", [])
        sessions.insert(0, session)
        payload["sessions"] = sort_sessions(sessions)
        payload["active_session_id"] = session_id
        write_sessions_payload(payload)

        return success_payload(
            "Session created",
            session=session_summary(session),
            sessions=all_session_summaries(payload),
            active_session_id=session_id,
            debug={
                "route_build": ROUTE_BUILD,
                "session_id": session_id,
            },
        )
    except Exception as exc:
        tb = safe_trace("api_sessions_new", exc)
        return error_payload("Failed to create session", 500, {"traceback": tb})


@app.post("/api/sessions/rename")
def api_sessions_rename():
    try:
        body = get_request_json()
        session_id = str(body.get("session_id") or "").strip()
        title = str(body.get("title") or "").strip()

        if not session_id:
            return error_payload("session_id is required", 400)

        if not title:
            return error_payload("title is required", 400)

        payload = ensure_default_session(read_sessions_payload())
        sessions = payload.get("sessions", [])
        updated = None

        for idx, item in enumerate(sessions):
            if str(item.get("id")) == session_id:
                item = normalize_session_record(item)
                item["title"] = title
                item["updated_at"] = utc_now()
                sessions[idx] = item
                updated = item
                break

        if updated is None:
            return error_payload("Session not found", 404, {"session_id": session_id})

        payload["sessions"] = sort_sessions(sessions)
        payload["active_session_id"] = session_id
        write_sessions_payload(payload)

        return success_payload(
            "Session renamed",
            session=session_summary(updated),
            sessions=all_session_summaries(payload),
            active_session_id=session_id,
            debug={
                "route_build": ROUTE_BUILD,
                "session_id": session_id,
            },
        )
    except Exception as exc:
        tb = safe_trace("api_sessions_rename", exc)
        return error_payload("Failed to rename session", 500, {"traceback": tb})


@app.post("/api/sessions/pin")
def api_sessions_pin():
    try:
        body = get_request_json()
        session_id = str(body.get("session_id") or "").strip()
        pinned = bool(body.get("pinned"))

        if not session_id:
            return error_payload("session_id is required", 400)

        payload = ensure_default_session(read_sessions_payload())
        sessions = payload.get("sessions", [])
        updated = None

        for idx, item in enumerate(sessions):
            if str(item.get("id")) == session_id:
                item = normalize_session_record(item)
                item["pinned"] = pinned
                item["updated_at"] = utc_now()
                sessions[idx] = item
                updated = item
                break

        if updated is None:
            return error_payload("Session not found", 404, {"session_id": session_id})

        payload["sessions"] = sort_sessions(sessions)
        payload["active_session_id"] = session_id
        write_sessions_payload(payload)

        return success_payload(
            "Session pin updated",
            session=session_summary(updated),
            sessions=all_session_summaries(payload),
            active_session_id=session_id,
            debug={
                "route_build": ROUTE_BUILD,
                "session_id": session_id,
                "pinned": pinned,
            },
        )
    except Exception as exc:
        tb = safe_trace("api_sessions_pin", exc)
        return error_payload("Failed to update session pin", 500, {"traceback": tb})


@app.post("/api/sessions/delete")
def api_sessions_delete():
    try:
        body = get_request_json()
        session_id = str(body.get("session_id") or "").strip()

        if not session_id:
            return error_payload("session_id is required", 400)

        deleted, next_session_id = delete_session_record(session_id)
        if not deleted:
            return error_payload("Session not found", 404, {"session_id": session_id})

        artifact_service.purge_session_artifacts(session_id)

        payload = ensure_default_session(read_sessions_payload())

        return success_payload(
            "Session deleted",
            deleted_session_id=session_id,
            next_session_id=next_session_id,
            active_session_id=next_session_id,
            sessions=all_session_summaries(payload),
            debug={
                "route_build": ROUTE_BUILD,
                "deleted_session_id": session_id,
                "next_session_id": next_session_id,
            },
        )
    except Exception as exc:
        tb = safe_trace("api_sessions_delete", exc)
        return error_payload("Failed to delete session", 500, {"traceback": tb})


@app.get("/api/artifacts")
def api_artifacts():
    try:
        session_id = get_session_id_from_request()
        artifacts = artifact_service.list_artifacts(session_id=session_id)

        return success_payload(
            "Artifacts loaded",
            artifacts=artifacts,
            debug={
                "route_build": ROUTE_BUILD,
                "session_id": session_id,
                "artifact_count": len(artifacts),
                "ordering": "pinned_first_then_newest",
                "session_scoped": True,
            },
        )
    except Exception as exc:
        tb = safe_trace("api_artifacts", exc)
        return error_payload("Failed to load artifacts", 500, {"traceback": tb})


@app.post("/api/artifacts/pin")
def api_artifacts_pin():
    try:
        body = get_request_json()
        artifact_id = str(body.get("artifact_id") or "").strip()
        pinned = bool(body.get("pinned"))

        if not artifact_id:
            return error_payload("artifact_id is required", 400)

        updated = artifact_service.set_pinned(artifact_id=artifact_id, pinned=pinned)
        if not updated:
            return error_payload("Artifact not found", 404, {"artifact_id": artifact_id})

        return success_payload(
            "Artifact pin updated",
            artifact=updated,
            debug={
                "route_build": ROUTE_BUILD,
                "artifact_id": artifact_id,
                "pinned": pinned,
                "session_id": updated.get("session_id"),
            },
        )
    except Exception as exc:
        tb = safe_trace("api_artifacts_pin", exc)
        return error_payload("Failed to update artifact pin", 500, {"traceback": tb})


@app.post("/api/artifacts/delete")
def api_artifacts_delete():
    try:
        body = get_request_json()
        artifact_id = str(body.get("artifact_id") or "").strip()

        if not artifact_id:
            return error_payload("artifact_id is required", 400)

        deleted = artifact_service.delete_artifact(artifact_id=artifact_id)
        if not deleted:
            return error_payload("Artifact not found", 404, {"artifact_id": artifact_id})

        return success_payload(
            "Artifact deleted",
            artifact_id=artifact_id,
            debug={
                "route_build": ROUTE_BUILD,
                "artifact_id": artifact_id,
            },
        )
    except Exception as exc:
        tb = safe_trace("api_artifacts_delete", exc)
        return error_payload("Failed to delete artifact", 500, {"traceback": tb})


@app.post("/api/chat")
def api_chat():
    try:
        body = get_request_json()
        session_id = str(body.get("session_id") or "default-session").strip() or "default-session"
        content = str(body.get("content") or "").strip()
        history = body.get("history") or []

        if not content:
            return error_payload("content is required", 400)

        session, payload = get_or_create_session(session_id)
        user_message = {
            "id": new_id("user"),
            "role": "user",
            "content": content,
            "created_at": utc_now(),
            "attachments": [],
            "meta": {},
        }

        session_messages = list(session.get("messages") or [])
        session_messages.append(user_message)

        assistant_message = None
        debug = {
            "route_build": ROUTE_BUILD,
            "history_count": len(history) if isinstance(history, list) else 0,
            "used_fallback": False,
        }

        if ChatService is not None:
            try:
                chat_service = ChatService()
                result = chat_service.send_message(
                    content=content,
                    session_id=session_id,
                    history=history,
                )

                if isinstance(result, dict):
                    assistant_message = result.get("assistant_message")
                    debug.update(result.get("debug") or {})
                else:
                    assistant_message = None
            except Exception as exc:
                debug["used_fallback"] = True
                debug["fallback_reason"] = f"{type(exc).__name__}: {exc}"
        else:
            debug["used_fallback"] = True
            debug["fallback_reason"] = "ChatService unavailable"

        if not assistant_message:
            assistant_message = {
                "id": new_id("assistant"),
                "role": "assistant",
                "content": f"You said: {content}",
                "created_at": utc_now(),
                "attachments": [],
                "meta": {},
            }

        assistant_message = normalize_message(assistant_message)

        session_messages.append(assistant_message)
        session["messages"] = session_messages
        session["updated_at"] = utc_now()
        session = save_session(session, payload)

        assistant_text = str(assistant_message.get("content") or "").strip()
        artifact_saved = False
        artifact_save_reason = "empty_content"

        if assistant_text:
            artifact = artifact_service.create_artifact(
                session_id=session_id,
                title="Chat Reply",
                content=assistant_text,
                kind="chat_reply",
                meta={
                    "source": "api_chat",
                    "role": "assistant",
                    "route_build": ROUTE_BUILD,
                },
            )
            artifact_saved = artifact is not None
            artifact_save_reason = "saved" if artifact_saved else "not_saved"

        debug["artifact_saved"] = artifact_saved
        debug["artifact_save_reason"] = artifact_save_reason

        return success_payload(
            assistant_message.get("content") or "",
            assistant_message=assistant_message,
            session=session_summary(session),
            sessions=all_session_summaries(read_sessions_payload()),
            active_session_id=session.get("id"),
            debug=debug,
        )
    except Exception as exc:
        tb = safe_trace("api_chat", exc)
        return error_payload("Chat failed", 500, {"traceback": tb})


if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)