from __future__ import annotations

import json
import uuid

from flask import Blueprint, jsonify, request


sessions_bp = Blueprint("sessions_bp", __name__)


def _get_ctx():
    from app import STATE_LOCK, SESSIONS, current_user, normalize_username, now_iso, ensure_session, save_sessions

    return {
        "STATE_LOCK": STATE_LOCK,
        "SESSIONS": SESSIONS,
        "current_user": current_user,
        "normalize_username": normalize_username,
        "now_iso": now_iso,
        "ensure_session": ensure_session,
        "save_sessions": save_sessions,
    }


@sessions_bp.route("/api/session/new", methods=["POST"])
def new_session():
    ctx = _get_ctx()
    username = ctx["current_user"]() or "dev"
    sid = str(uuid.uuid4())
    ctx["ensure_session"](sid, username)
    return jsonify({"ok": True, "session_id": sid, "session": ctx["SESSIONS"][sid]})


@sessions_bp.route("/api/session/delete", methods=["POST"])
def delete_session():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"ok": False, "error": "Missing session_id"}), 400

    with ctx["STATE_LOCK"]:
        session_obj = ctx["SESSIONS"].get(session_id)

        if not session_obj:
            return jsonify({"ok": False, "error": "Session not found"}), 404

        from app import DEV_BYPASS_AUTH

        if not DEV_BYPASS_AUTH:
            if ctx["normalize_username"](str(session_obj.get("user", ""))) != ctx["normalize_username"](username):
                return jsonify({"ok": False, "error": "Forbidden"}), 403

        del ctx["SESSIONS"][session_id]
        ctx["save_sessions"]()

    return jsonify({"ok": True})


@sessions_bp.route("/api/session/rename", methods=["POST"])
def rename_session():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    session_id = str(data.get("session_id") or "").strip()
    title = str(data.get("title") or "").strip()

    if not session_id or not title:
        return jsonify({"ok": False, "error": "Missing session_id or title"}), 400

    with ctx["STATE_LOCK"]:
        session_obj = ctx["SESSIONS"].get(session_id)

        if not session_obj:
            return jsonify({"ok": False, "error": "Session not found"}), 404

        from app import DEV_BYPASS_AUTH

        if not DEV_BYPASS_AUTH:
            if ctx["normalize_username"](str(session_obj.get("user", ""))) != ctx["normalize_username"](username):
                return jsonify({"ok": False, "error": "Forbidden"}), 403

        session_obj["title"] = title[:100]
        session_obj["updated_at"] = ctx["now_iso"]()
        ctx["save_sessions"]()

    return jsonify({"ok": True, "session": session_obj})


@sessions_bp.route("/api/session/duplicate", methods=["POST"])
def duplicate_session():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"ok": False, "error": "Missing session_id"}), 400

    with ctx["STATE_LOCK"]:
        original = ctx["SESSIONS"].get(session_id)

        if not original:
            return jsonify({"ok": False, "error": "Session not found"}), 404

        from app import DEV_BYPASS_AUTH

        if not DEV_BYPASS_AUTH:
            if ctx["normalize_username"](str(original.get("user", ""))) != ctx["normalize_username"](username):
                return jsonify({"ok": False, "error": "Forbidden"}), 403

        new_id = str(uuid.uuid4())
        new_messages = json.loads(json.dumps(original.get("messages", [])))

        ctx["SESSIONS"][new_id] = {
            **original,
            "id": new_id,
            "user": ctx["normalize_username"](username),
            "title": f"{str(original.get('title') or 'New Chat')[:80]} (Copy)",
            "messages": new_messages,
            "created_at": ctx["now_iso"](),
            "updated_at": ctx["now_iso"](),
        }

        ctx["save_sessions"]()

    return jsonify({"ok": True, "session_id": new_id, "session": ctx["SESSIONS"][new_id]})


@sessions_bp.route("/api/session/pin", methods=["POST"])
def pin_session():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    session_id = str(data.get("session_id") or "").strip()
    pinned = bool(data.get("pinned", True))

    if not session_id:
        return jsonify({"ok": False, "error": "Missing session_id"}), 400

    with ctx["STATE_LOCK"]:
        session_obj = ctx["SESSIONS"].get(session_id)

        if not session_obj:
            return jsonify({"ok": False, "error": "Session not found"}), 404

        from app import DEV_BYPASS_AUTH

        if not DEV_BYPASS_AUTH:
            if ctx["normalize_username"](str(session_obj.get("user", ""))) != ctx["normalize_username"](username):
                return jsonify({"ok": False, "error": "Forbidden"}), 403

        session_obj["pinned"] = pinned
        session_obj["updated_at"] = ctx["now_iso"]()
        ctx["save_sessions"]()

    return jsonify({"ok": True, "session": session_obj})