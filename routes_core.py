from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from auth_utils import DEV_BYPASS_AUTH, current_user
from nova_context import AGENT_STATE, DEFAULT_MODEL, get_user_sessions

core_bp = Blueprint("core", __name__)


@core_bp.get("/")
def index():
    username = ""
    if not DEV_BYPASS_AUTH:
        try:
            user = current_user()
            username = str(user.get("username", "") or "")
        except Exception:
            username = ""

    return render_template("index.html", username=username)


@core_bp.get("/api/state")
def api_state():
    username = "dev"
    if not DEV_BYPASS_AUTH:
        try:
            username = str(current_user().get("username", "") or "").strip() or "dev"
        except Exception:
            username = "dev"

    sessions = get_user_sessions(username)
    active_session_id = sessions[0]["id"] if sessions else None

    return jsonify(
        {
            "ok": True,
            "sessions": sessions,
            "active_session_id": active_session_id,
            "agent_enabled": bool(AGENT_STATE.get("enabled", False)),
            "session_count": len(sessions),
        }
    )


@core_bp.get("/api/models")
def api_models():
    return jsonify(
        {
            "ok": True,
            "default": DEFAULT_MODEL,
            "models": [DEFAULT_MODEL, "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
        }
    )