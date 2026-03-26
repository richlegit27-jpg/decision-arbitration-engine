from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth_utils import DEV_BYPASS_AUTH, current_user, normalize_username
from nova_context import (
    AGENT_STATE,
    SESSIONS,
    STATE_LOCK,
    ensure_agent_thread,
    get_owned_session_or_404,
    now_iso,
    save_sessions,
)

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")


def _username() -> str:
    if DEV_BYPASS_AUTH:
        return "dev"
    return normalize_username(str(current_user().get("username", "") or ""))


@agent_bp.get("/state")
def get_agent_state():
    return jsonify({"ok": True, "agent": AGENT_STATE})


@agent_bp.post("/enable")
def enable_agent():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "") or "").strip()
    goal = str(data.get("goal", "") or "").strip()
    username = _username()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    session_obj, error = get_owned_session_or_404(session_id, username, jsonify)
    if error:
        return error

    with STATE_LOCK:
        session_obj["agent_enabled"] = True
        session_obj["agent_goal"] = goal
        session_obj["agent_status"] = "idle"
        session_obj["updated_at"] = now_iso()
        AGENT_STATE["enabled"] = True
        save_sessions()

    ensure_agent_thread()
    return jsonify({"ok": True, "session": session_obj, "agent": AGENT_STATE})


@agent_bp.post("/disable")
def disable_agent():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "") or "").strip()
    username = _username()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    session_obj, error = get_owned_session_or_404(session_id, username, jsonify)
    if error:
        return error

    with STATE_LOCK:
        session_obj["agent_enabled"] = False
        session_obj["agent_status"] = "idle"
        session_obj["updated_at"] = now_iso()
        AGENT_STATE["enabled"] = any(s.get("agent_enabled") for s in SESSIONS.values())
        save_sessions()

    return jsonify({"ok": True, "session": session_obj, "agent": AGENT_STATE})