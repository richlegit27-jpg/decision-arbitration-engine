from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth_utils import DEV_BYPASS_AUTH, current_user, normalize_username
from nova_context import (
    SESSIONS,
    STATE_LOCK,
    ensure_session,
    get_owned_session_or_404,
    get_user_sessions,
    now_iso,
    save_sessions,
)

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/session")


def _username() -> str:
    if DEV_BYPASS_AUTH:
        return "dev"
    return normalize_username(str(current_user().get("username", "") or ""))


@sessions_bp.get("/list")
def list_sessions():
    return jsonify({"ok": True, "sessions": get_user_sessions(_username())})


@sessions_bp.post("/new")
def create_session():
    username = _username()
    session_id = ensure_session(None, username)
    with STATE_LOCK:
        session_obj = SESSIONS.get(session_id, {})
    return jsonify({"ok": True, "session": session_obj})


@sessions_bp.post("/delete")
def delete_session():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "") or "").strip()
    username = _username()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    session_obj, error = get_owned_session_or_404(session_id, username, jsonify)
    if error:
        return error

    with STATE_LOCK:
        SESSIONS.pop(session_id, None)
        save_sessions()

    return jsonify({"ok": True, "deleted": session_id})


@sessions_bp.post("/rename")
def rename_session():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "") or "").strip()
    title = str(data.get("title", "") or "").strip()
    username = _username()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400
    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400

    session_obj, error = get_owned_session_or_404(session_id, username, jsonify)
    if error:
        return error

    with STATE_LOCK:
        session_obj["title"] = title[:120]
        session_obj["updated_at"] = now_iso()
        save_sessions()

    return jsonify({"ok": True, "session": session_obj})


@sessions_bp.post("/duplicate")
def duplicate_session():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "") or "").strip()
    username = _username()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    session_obj, error = get_owned_session_or_404(session_id, username, jsonify)
    if error:
        return error

    new_id = ensure_session(None, username)

    with STATE_LOCK:
        source_messages = [dict(msg) for msg in session_obj.get("messages", [])]
        target = SESSIONS[new_id]
        target["title"] = f'{session_obj.get("title", "Chat")} Copy'[:120]
        target["messages"] = source_messages
        target["updated_at"] = now_iso()
        save_sessions()

    return jsonify({"ok": True, "session": SESSIONS[new_id]})


@sessions_bp.post("/pin")
def pin_session():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "") or "").strip()
    pinned = bool(data.get("pinned", True))
    username = _username()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    session_obj, error = get_owned_session_or_404(session_id, username, jsonify)
    if error:
        return error

    with STATE_LOCK:
        session_obj["pinned"] = pinned
        session_obj["updated_at"] = now_iso()
        save_sessions()

    return jsonify({"ok": True, "session": session_obj})