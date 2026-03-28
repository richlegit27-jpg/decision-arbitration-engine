# notepad C:\Users\Owner\nova\app.py
from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from services.chat_service import (
    DEFAULT_TITLE,
    get_chat_health,
    get_session_by_id,
    get_session_payload,
    list_sessions,
    now_iso,
    process_chat_request,
    process_chat_stream,
    save_all_sessions,
    upsert_session,
)

# =========================================================
# base paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# optional service imports
# fail-soft everywhere
# =========================================================

try:
    from services.memory_service import (
        add_memory as _memory_add,
        delete_memory as _memory_delete,
        export_memory as _memory_export,
        get_all_memory as _memory_get_all,
        search_memory as _memory_search,
    )
except Exception:
    _memory_add = None
    _memory_delete = None
    _memory_export = None
    _memory_get_all = None
    _memory_search = None

try:
    from services.artifact_service import (
        create_artifact as _artifact_create,
        delete_artifact as _artifact_delete,
        export_artifact as _artifact_export,
        get_artifact as _artifact_get,
        list_artifacts as _artifact_list,
        pin_artifact as _artifact_pin,
        save_artifact as _artifact_save,
        toggle_artifact_pin as _artifact_toggle_pin,
        update_artifact as _artifact_update,
    )
except Exception:
    _artifact_create = None
    _artifact_delete = None
    _artifact_export = None
    _artifact_get = None
    _artifact_list = None
    _artifact_pin = None
    _artifact_save = None
    _artifact_toggle_pin = None
    _artifact_update = None

try:
    from services.web_service import preview_web_request as _web_preview
except Exception:
    _web_preview = None


# =========================================================
# app
# =========================================================

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("NOVA_MAX_CONTENT_LENGTH", str(32 * 1024 * 1024)))

CORS(app, resources={r"/api/*": {"origins": "*"}})

APP_NAME = "Nova"
APP_PORT = int(os.getenv("PORT", os.getenv("NOVA_PORT", "5001")))


# =========================================================
# helpers
# =========================================================

def _json_payload() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _collapse_ws(value: Any) -> str:
    return " ".join(_clean_text(value).split()).strip()


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _json_ok(payload: Dict[str, Any], status: int = 200):
    return jsonify(payload), status


def _json_error(message: str, code: str = "request_failed", status: int = 500, **extra: Any):
    body = {
        "ok": False,
        "error": message,
        "code": code,
    }
    if extra:
        body.update(extra)
    return jsonify(body), status


def _extract_status(payload: Dict[str, Any], fallback: int = 200) -> int:
    status_code = payload.get("status_code")
    if isinstance(status_code, int):
        return status_code
    return fallback


def _session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    messages = _coerce_list(session.get("messages"))
    last_message = messages[-1] if messages else None

    return {
        "id": session.get("id"),
        "title": _clean_text(session.get("title") or DEFAULT_TITLE).strip() or DEFAULT_TITLE,
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned", False)),
        "message_count": len(messages),
        "last_message_preview": _clean_text((last_message or {}).get("content", ""))[:180],
    }


def _all_session_summaries() -> List[Dict[str, Any]]:
    sessions = list_sessions()
    return [_session_summary(session) for session in sessions]


def _replace_session_in_store(updated_session: Dict[str, Any]) -> Dict[str, Any]:
    return upsert_session(updated_session, backup=False)


def _delete_session_by_id(session_id: str) -> bool:
    sessions = list_sessions()
    kept = [session for session in sessions if session.get("id") != session_id]
    if len(kept) == len(sessions):
        return False
    save_all_sessions(kept, backup=False)
    return True


def _duplicate_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    source = get_session_by_id(session_id)
    if not source:
        return None

    duplicated_messages: List[Dict[str, Any]] = []
    for message in _coerce_list(source.get("messages")):
        cloned = dict(message)
        cloned["id"] = _new_id()
        duplicated_messages.append(cloned)

    duplicated = {
        "id": _new_id(),
        "title": f'{_clean_text(source.get("title") or DEFAULT_TITLE).strip() or DEFAULT_TITLE} (copy)',
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "pinned": False,
        "messages": duplicated_messages,
        "meta": dict(_coerce_dict(source.get("meta"))),
    }
    return _replace_session_in_store(duplicated)


def _artifact_service_missing(name: str):
    return _json_error(
        f"Artifact route '{name}' is unavailable because artifact_service is not fully loaded.",
        code="artifact_service_unavailable",
        status=501,
    )


def _memory_service_missing(name: str):
    return _json_error(
        f"Memory route '{name}' is unavailable because memory_service is not fully loaded.",
        code="memory_service_unavailable",
        status=501,
    )


# =========================================================
# static + page routes
# =========================================================

@app.get("/")
def index():
    return send_from_directory(TEMPLATES_DIR, "index.html")


@app.get("/favicon.ico")
def favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return send_from_directory(STATIC_DIR, "favicon.ico")
    return Response(status=204)


# =========================================================
# health + state
# =========================================================

@app.get("/api/health")
def api_health():
    try:
        health = get_chat_health()
        health["ok"] = True
        health["app_name"] = APP_NAME
        health["port"] = APP_PORT
        return _json_ok(health)
    except Exception as exc:
        return _json_error(
            "Health check failed.",
            code="health_failed",
            status=500,
            details=str(exc),
        )


@app.get("/api/state")
def api_state():
    try:
        sessions = list_sessions()
        active_session_id = request.args.get("session_id")

        payload = {
            "ok": True,
            "app": APP_NAME,
            "sessions": [_session_summary(session) for session in sessions],
            "active_session_id": active_session_id,
            "default_model": os.getenv("OPENAI_MODEL", "gpt-5.4"),
            "models": [
                os.getenv("OPENAI_MODEL", "gpt-5.4"),
                "gpt-4.1-mini",
                "gpt-4.1",
                "gpt-4o-mini",
            ],
        }
        return _json_ok(payload)
    except Exception as exc:
        return _json_error(
            "Failed to load app state.",
            code="state_failed",
            status=500,
            details=str(exc),
        )


@app.get("/api/models")
def api_models():
    default_model = os.getenv("OPENAI_MODEL", "gpt-5.4")
    return _json_ok(
        {
            "ok": True,
            "default": default_model,
            "models": [
                default_model,
                "gpt-4.1-mini",
                "gpt-4.1",
                "gpt-4o-mini",
            ],
        }
    )


# =========================================================
# chat routes
# =========================================================

@app.post("/api/chat")
def api_chat():
    try:
        payload = _json_payload()
        result = process_chat_request(payload)
        status = _extract_status(result, 200 if result.get("ok") else 500)
        return jsonify(result), status
    except Exception as exc:
        return _json_error(
            "Chat route failed.",
            code="chat_route_failed",
            status=500,
            details=str(exc),
            traceback=traceback.format_exc(limit=3),
        )


@app.post("/api/chat/stream")
def api_chat_stream():
    try:
        payload = _json_payload()

        return Response(
            process_chat_stream(payload),
            status=200,
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        error_payload = {
            "ok": False,
            "error": "Chat stream route failed.",
            "code": "chat_stream_route_failed",
            "details": str(exc),
        }
        body = f"event: error\ndata: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        return Response(body, status=500, mimetype="text/event-stream")


@app.get("/api/chat/<session_id>")
def api_chat_get_session(session_id: str):
    try:
        payload = get_session_payload(session_id)
        status = _extract_status(payload, 200 if payload.get("ok") else 404)
        return jsonify(payload), status
    except Exception as exc:
        return _json_error(
            "Failed to load session.",
            code="session_load_failed",
            status=500,
            details=str(exc),
        )


# =========================================================
# session routes
# =========================================================

@app.post("/api/session/new")
def api_session_new():
    try:
        payload = _json_payload()
        title = _collapse_ws(payload.get("title")) or DEFAULT_TITLE

        session = {
            "id": _new_id(),
            "title": title,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "pinned": False,
            "messages": [],
            "meta": _coerce_dict(payload.get("meta")),
        }
        session = _replace_session_in_store(session)

        return _json_ok(
            {
                "ok": True,
                "session": session,
                "sessions": _all_session_summaries(),
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to create session.",
            code="session_create_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/session/delete")
def api_session_delete():
    try:
        payload = _json_payload()
        session_id = _clean_text(payload.get("session_id")).strip()

        if not session_id:
            return _json_error("session_id is required.", code="invalid_request", status=400)

        deleted = _delete_session_by_id(session_id)
        if not deleted:
            return _json_error("Session not found.", code="not_found", status=404)

        return _json_ok(
            {
                "ok": True,
                "deleted_session_id": session_id,
                "sessions": _all_session_summaries(),
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to delete session.",
            code="session_delete_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/session/rename")
def api_session_rename():
    try:
        payload = _json_payload()
        session_id = _clean_text(payload.get("session_id")).strip()
        title = _collapse_ws(payload.get("title"))

        if not session_id:
            return _json_error("session_id is required.", code="invalid_request", status=400)
        if not title:
            return _json_error("title is required.", code="invalid_request", status=400)

        session = get_session_by_id(session_id)
        if not session:
            return _json_error("Session not found.", code="not_found", status=404)

        session["title"] = title
        session["updated_at"] = _now_iso()
        session = _replace_session_in_store(session)

        return _json_ok(
            {
                "ok": True,
                "session": session,
                "sessions": _all_session_summaries(),
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to rename session.",
            code="session_rename_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/session/duplicate")
def api_session_duplicate():
    try:
        payload = _json_payload()
        session_id = _clean_text(payload.get("session_id")).strip()

        if not session_id:
            return _json_error("session_id is required.", code="invalid_request", status=400)

        duplicated = _duplicate_session_by_id(session_id)
        if not duplicated:
            return _json_error("Session not found.", code="not_found", status=404)

        return _json_ok(
            {
                "ok": True,
                "session": duplicated,
                "sessions": _all_session_summaries(),
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to duplicate session.",
            code="session_duplicate_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/session/pin")
def api_session_pin():
    try:
        payload = _json_payload()
        session_id = _clean_text(payload.get("session_id")).strip()
        pinned = bool(payload.get("pinned", True))

        if not session_id:
            return _json_error("session_id is required.", code="invalid_request", status=400)

        session = get_session_by_id(session_id)
        if not session:
            return _json_error("Session not found.", code="not_found", status=404)

        session["pinned"] = pinned
        session["updated_at"] = _now_iso()
        session = _replace_session_in_store(session)

        return _json_ok(
            {
                "ok": True,
                "session": session,
                "sessions": _all_session_summaries(),
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to pin session.",
            code="session_pin_failed",
            status=500,
            details=str(exc),
        )


# =========================================================
# memory routes
# =========================================================

@app.get("/api/memory")
def api_memory_list():
    if not _memory_get_all:
        return _memory_service_missing("list")

    try:
        query = _clean_text(request.args.get("q")).strip()
        if query and _memory_search:
            items = _memory_search(query)
        else:
            items = _memory_get_all()

        return _json_ok(
            {
                "ok": True,
                "items": items if isinstance(items, list) else [],
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to load memory.",
            code="memory_list_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/memory/add")
def api_memory_add():
    if not _memory_add:
        return _memory_service_missing("add")

    try:
        payload = _json_payload()
        result = _memory_add(
            kind=_clean_text(payload.get("kind")).strip(),
            value=_clean_text(payload.get("value")).strip(),
        )
        return _json_ok({"ok": True, "item": result})
    except Exception as exc:
        return _json_error(
            "Failed to add memory.",
            code="memory_add_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/memory/delete")
def api_memory_delete():
    if not _memory_delete:
        return _memory_service_missing("delete")

    try:
        payload = _json_payload()
        memory_id = _clean_text(payload.get("id")).strip()
        if not memory_id:
            return _json_error("id is required.", code="invalid_request", status=400)

        result = _memory_delete(memory_id)
        return _json_ok({"ok": True, "deleted": bool(result), "id": memory_id})
    except Exception as exc:
        return _json_error(
            "Failed to delete memory.",
            code="memory_delete_failed",
            status=500,
            details=str(exc),
        )


@app.get("/api/memory/export")
def api_memory_export():
    if not _memory_export:
        return _memory_service_missing("export")

    try:
        payload = _memory_export()
        return _json_ok({"ok": True, "export": payload})
    except Exception as exc:
        return _json_error(
            "Failed to export memory.",
            code="memory_export_failed",
            status=500,
            details=str(exc),
        )


# =========================================================
# artifact routes
# =========================================================

@app.get("/api/artifacts")
def api_artifacts_list():
    if not _artifact_list:
        return _artifact_service_missing("list")

    try:
        q = _clean_text(request.args.get("q")).strip()
        session_id = _clean_text(request.args.get("session_id")).strip() or None
        pinned_only = request.args.get("pinned") in {"1", "true", "True"}

        items = _artifact_list(query=q, session_id=session_id, pinned_only=pinned_only)
        return _json_ok({"ok": True, "artifacts": items if isinstance(items, list) else []})
    except TypeError:
        try:
            items = _artifact_list()
            return _json_ok({"ok": True, "artifacts": items if isinstance(items, list) else []})
        except Exception as exc:
            return _json_error(
                "Failed to list artifacts.",
                code="artifact_list_failed",
                status=500,
                details=str(exc),
            )
    except Exception as exc:
        return _json_error(
            "Failed to list artifacts.",
            code="artifact_list_failed",
            status=500,
            details=str(exc),
        )


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_get(artifact_id: str):
    if not _artifact_get:
        return _artifact_service_missing("get")

    try:
        artifact = _artifact_get(artifact_id)
        if not artifact:
            return _json_error("Artifact not found.", code="not_found", status=404)
        return _json_ok({"ok": True, "artifact": artifact})
    except Exception as exc:
        return _json_error(
            "Failed to load artifact.",
            code="artifact_get_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/artifacts/create")
def api_artifact_create():
    if not _artifact_create:
        return _artifact_service_missing("create")

    try:
        payload = _json_payload()
        artifact = _artifact_create(payload)
        return _json_ok({"ok": True, "artifact": artifact})
    except Exception as exc:
        return _json_error(
            "Failed to create artifact.",
            code="artifact_create_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/artifacts/save")
def api_artifact_save():
    if not _artifact_save:
        return _artifact_service_missing("save")

    try:
        payload = _json_payload()
        artifact = _artifact_save(payload)
        return _json_ok({"ok": True, "artifact": artifact})
    except Exception as exc:
        return _json_error(
            "Failed to save artifact.",
            code="artifact_save_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/artifacts/update")
def api_artifact_update():
    if not _artifact_update:
        return _artifact_service_missing("update")

    try:
        payload = _json_payload()
        artifact = _artifact_update(payload)
        return _json_ok({"ok": True, "artifact": artifact})
    except Exception as exc:
        return _json_error(
            "Failed to update artifact.",
            code="artifact_update_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/artifacts/delete")
def api_artifact_delete():
    if not _artifact_delete:
        return _artifact_service_missing("delete")

    try:
        payload = _json_payload()
        artifact_id = _clean_text(payload.get("id") or payload.get("artifact_id")).strip()
        if not artifact_id:
            return _json_error("artifact id is required.", code="invalid_request", status=400)

        result = _artifact_delete(artifact_id)
        return _json_ok({"ok": True, "deleted": bool(result), "id": artifact_id})
    except Exception as exc:
        return _json_error(
            "Failed to delete artifact.",
            code="artifact_delete_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/artifacts/pin")
def api_artifact_pin():
    if not _artifact_pin:
        return _artifact_service_missing("pin")

    try:
        payload = _json_payload()
        artifact_id = _clean_text(payload.get("id") or payload.get("artifact_id")).strip()
        pinned = bool(payload.get("pinned", True))

        if not artifact_id:
            return _json_error("artifact id is required.", code="invalid_request", status=400)

        artifact = _artifact_pin(artifact_id, pinned=pinned)
        return _json_ok({"ok": True, "artifact": artifact})
    except TypeError:
        try:
            payload = _json_payload()
            artifact_id = _clean_text(payload.get("id") or payload.get("artifact_id")).strip()
            artifact = _artifact_pin(artifact_id)
            return _json_ok({"ok": True, "artifact": artifact})
        except Exception as exc:
            return _json_error(
                "Failed to pin artifact.",
                code="artifact_pin_failed",
                status=500,
                details=str(exc),
            )
    except Exception as exc:
        return _json_error(
            "Failed to pin artifact.",
            code="artifact_pin_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/artifacts/toggle-pin")
def api_artifact_toggle_pin():
    if not _artifact_toggle_pin:
        return _artifact_service_missing("toggle-pin")

    try:
        payload = _json_payload()
        artifact_id = _clean_text(payload.get("id") or payload.get("artifact_id")).strip()
        if not artifact_id:
            return _json_error("artifact id is required.", code="invalid_request", status=400)

        artifact = _artifact_toggle_pin(artifact_id)
        return _json_ok({"ok": True, "artifact": artifact})
    except Exception as exc:
        return _json_error(
            "Failed to toggle artifact pin.",
            code="artifact_toggle_pin_failed",
            status=500,
            details=str(exc),
        )


@app.get("/api/artifacts/export")
def api_artifact_export():
    if not _artifact_export:
        return _artifact_service_missing("export")

    try:
        artifact_id = _clean_text(request.args.get("id") or request.args.get("artifact_id")).strip()
        if not artifact_id:
            return _json_error("artifact id is required.", code="invalid_request", status=400)

        exported = _artifact_export(artifact_id)
        return _json_ok({"ok": True, "export": exported})
    except Exception as exc:
        return _json_error(
            "Failed to export artifact.",
            code="artifact_export_failed",
            status=500,
            details=str(exc),
        )


# =========================================================
# debug routes
# =========================================================

@app.post("/api/debug/web_preview")
def api_debug_web_preview():
    if not _web_preview:
        return _json_ok(
            {
                "ok": True,
                "preview": {
                    "enabled": False,
                    "items": [],
                    "prompt_context": "",
                    "errors": ["web preview service unavailable"],
                },
            }
        )

    try:
        payload = _json_payload()
        text = _clean_text(payload.get("text")).strip()
        meta = _coerce_dict(payload.get("meta"))

        preview = _web_preview(text=text, meta=meta)
        return _json_ok({"ok": True, "preview": preview})
    except TypeError:
        try:
            payload = _json_payload()
            text = _clean_text(payload.get("text")).strip()
            preview = _web_preview(text)
            return _json_ok({"ok": True, "preview": preview})
        except Exception as exc:
            return _json_error(
                "Failed to build web preview.",
                code="web_preview_failed",
                status=500,
                details=str(exc),
            )
    except Exception as exc:
        return _json_error(
            "Failed to build web preview.",
            code="web_preview_failed",
            status=500,
            details=str(exc),
        )


@app.post("/api/debug/brain")
def api_debug_brain():
    try:
        payload = _json_payload()
        result = process_chat_request(payload)

        if not result.get("ok"):
            status = _extract_status(result, 500)
            return jsonify(result), status

        debug = result.get("debug", {})
        session = result.get("session", {})
        message = result.get("message", {})
        assistant = result.get("assistant", {})

        return _json_ok(
            {
                "ok": True,
                "debug": debug,
                "message_count": len(_coerce_list(session.get("messages"))),
                "messages_preview": [
                    {
                        "role": message.get("role"),
                        "content": _clean_text(message.get("content"))[:280],
                    },
                    {
                        "role": assistant.get("role"),
                        "content": _clean_text(assistant.get("content"))[:280],
                    },
                ],
            }
        )
    except Exception as exc:
        return _json_error(
            "Failed to build debug brain output.",
            code="debug_brain_failed",
            status=500,
            details=str(exc),
        )


# =========================================================
# global error handlers
# =========================================================

@app.errorhandler(404)
def handle_404(_error):
    return _json_error("Not Found", code="not_found", status=404)


@app.errorhandler(405)
def handle_405(_error):
    return _json_error("Method Not Allowed", code="method_not_allowed", status=405)


@app.errorhandler(413)
def handle_413(_error):
    return _json_error("Payload too large.", code="payload_too_large", status=413)


@app.errorhandler(500)
def handle_500(error):
    return _json_error(
        "Internal server error.",
        code="internal_server_error",
        status=500,
        details=str(error),
    )


# =========================================================
# main
# =========================================================

if __name__ == "__main__":
    print(
        f"[{APP_NAME}] starting on http://127.0.0.1:{APP_PORT} "
        f"| model={os.getenv('OPENAI_MODEL', 'gpt-5.4')}"
    )
    app.run(host="127.0.0.1", port=APP_PORT, debug=True, threaded=True)