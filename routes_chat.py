# C:\Users\Owner\nova\routes_chat.py

from __future__ import annotations

import json
import time

from flask import Blueprint, Response, jsonify, request, stream_with_context


chat_bp = Blueprint("chat_bp", __name__)


def _get_ctx():
    from app import (
        LAST_ROUTER_META,
        MEMORY_ITEMS,
        SESSIONS,
        add_message,
        current_user,
        ensure_session,
        extract_memory,
        generate_reply,
        get_owned_session_or_404,
        normalize_username,
        save_memory,
    )

    return {
        "LAST_ROUTER_META": LAST_ROUTER_META,
        "MEMORY_ITEMS": MEMORY_ITEMS,
        "SESSIONS": SESSIONS,
        "add_message": add_message,
        "current_user": current_user,
        "ensure_session": ensure_session,
        "extract_memory": extract_memory,
        "generate_reply": generate_reply,
        "get_owned_session_or_404": get_owned_session_or_404,
        "normalize_username": normalize_username,
        "save_memory": save_memory,
    }


@chat_bp.route("/api/chat/<session_id>", methods=["GET"])
def get_session(session_id: str):
    ctx = _get_ctx()
    username = ctx["current_user"]() or "dev"
    session_obj, error = ctx["get_owned_session_or_404"](session_id, username)
    if error:
        return error

    return jsonify(
        {
            "ok": True,
            "session": session_obj,
            "messages": session_obj.get("messages", []),
            "router": session_obj.get("router_meta", ctx["LAST_ROUTER_META"]),
            "router_meta": session_obj.get("router_meta", ctx["LAST_ROUTER_META"]),
            "last_router_meta": session_obj.get("router_meta", ctx["LAST_ROUTER_META"]),
        }
    )


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"

    msg = data.get("message") or data.get("content") or ""
    session_id = ctx["ensure_session"](data.get("session_id"), username)

    ctx["add_message"](session_id, "user", msg)

    mem = ctx["extract_memory"](msg)
    if mem:
        mem["user"] = ctx["normalize_username"](username)
        ctx["MEMORY_ITEMS"].insert(0, mem)
        ctx["save_memory"]()

    reply, results, provider = ctx["generate_reply"](username, msg, session_id)
    ctx["add_message"](session_id, "assistant", reply, web_results=results, web_provider=provider)

    return jsonify(
        {
            "ok": True,
            "reply": reply,
            "web_results": results,
            "web_provider": provider,
            "session_id": session_id,
            "messages": ctx["SESSIONS"][session_id]["messages"],
            "session": ctx["SESSIONS"][session_id],
        }
    )


@chat_bp.route("/api/chat/stream", methods=["POST"])
def stream():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"

    msg = data.get("message") or data.get("content") or ""
    session_id = ctx["ensure_session"](data.get("session_id"), username)

    ctx["add_message"](session_id, "user", msg)

    mem = ctx["extract_memory"](msg)
    if mem:
        mem["user"] = ctx["normalize_username"](username)
        ctx["MEMORY_ITEMS"].insert(0, mem)
        ctx["save_memory"]()

    def gen():
        try:
            yield f"event: start\ndata: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"

            reply, results, provider = ctx["generate_reply"](username, msg, session_id)

            ctx["add_message"](
                session_id,
                "assistant",
                reply,
                web_results=results,
                web_provider=provider,
            )

            for i in range(0, len(reply), 3):
                chunk = reply[i:i + 3]
                yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'delta': chunk, 'session_id': session_id})}\n\n"
                time.sleep(0.01)

            yield (
                f"event: done\ndata: {json.dumps({'type': 'done', 'content': reply, 'response': reply, "
                f"'session_id': session_id, 'web_results': results or [], 'web_provider': provider or ''})}\n\n"
            )

        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(exc), 'session_id': session_id})}\n\n"
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'content': '', 'response': '', 'session_id': session_id, 'web_results': [], 'web_provider': ''})}\n\n"

    return Response(
        stream_with_context(gen()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )