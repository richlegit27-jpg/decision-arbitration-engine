# C:\Users\Owner\nova\routes_agent.py

from __future__ import annotations

from flask import Blueprint, jsonify, request


agent_bp = Blueprint("agent_bp", __name__)


def _get_ctx():
    from app import (
        AGENT_STATE,
        SESSIONS,
        STATE_LOCK,
        current_user,
        ensure_agent_thread,
        ensure_session,
        now_iso,
        run_agent_step_for_session,
        save_sessions,
    )

    return {
        "AGENT_STATE": AGENT_STATE,
        "SESSIONS": SESSIONS,
        "STATE_LOCK": STATE_LOCK,
        "current_user": current_user,
        "ensure_agent_thread": ensure_agent_thread,
        "ensure_session": ensure_session,
        "now_iso": now_iso,
        "run_agent_step_for_session": run_agent_step_for_session,
        "save_sessions": save_sessions,
    }


@agent_bp.route("/api/agent/status", methods=["GET"])
def agent_status():
    ctx = _get_ctx()
    return jsonify({"ok": True, "agent": ctx["AGENT_STATE"]})


@agent_bp.route("/api/agent/start", methods=["POST"])
def agent_start():
    ctx = _get_ctx()
    ctx["ensure_agent_thread"]()

    data = request.get_json(silent=True) or {}
    interval = int(data.get("interval_seconds") or ctx["AGENT_STATE"].get("interval_seconds") or 20)
    ctx["AGENT_STATE"]["interval_seconds"] = max(3, interval)
    ctx["AGENT_STATE"]["enabled"] = True
    ctx["AGENT_STATE"]["last_error"] = ""

    return jsonify({"ok": True, "agent": ctx["AGENT_STATE"]})


@agent_bp.route("/api/agent/stop", methods=["POST"])
def agent_stop():
    ctx = _get_ctx()
    ctx["AGENT_STATE"]["enabled"] = False
    return jsonify({"ok": True, "agent": ctx["AGENT_STATE"]})


@agent_bp.route("/api/agent/session/config", methods=["POST"])
def agent_session_config():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    session_id = ctx["ensure_session"](data.get("session_id"), username)
    enabled = bool(data.get("enabled", True))
    goal = str(data.get("goal") or "").strip()

    with ctx["STATE_LOCK"]:
        ctx["SESSIONS"][session_id]["agent_enabled"] = enabled
        ctx["SESSIONS"][session_id]["agent_goal"] = goal
        ctx["SESSIONS"][session_id]["agent_status"] = "idle"
        ctx["SESSIONS"][session_id]["updated_at"] = ctx["now_iso"]()
        ctx["save_sessions"]()

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "session": ctx["SESSIONS"][session_id],
        }
    )


@agent_bp.route("/api/agent/session/run_once", methods=["POST"])
def agent_run_once():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    session_id = ctx["ensure_session"](data.get("session_id"), username)
    output = ctx["run_agent_step_for_session"](session_id)

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "output": output,
            "session": ctx["SESSIONS"][session_id],
        }
    )