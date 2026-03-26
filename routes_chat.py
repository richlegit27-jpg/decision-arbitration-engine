from __future__ import annotations

import json

from flask import Blueprint, Response, jsonify, request, stream_with_context

from auth_utils import DEV_BYPASS_AUTH, current_user, normalize_username
from nova_context import (
    add_message,
    ensure_session,
    generate_reply,
    get_owned_session_or_404,
)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _username() -> str:
    if DEV_BYPASS_AUTH:
        return "dev"
    return normalize_username(str(current_user().get("username", "") or ""))


@chat_bp.get("/<session_id>")
def get_chat(session_id: str):
    session_obj, error = get_owned_session_or_404(session_id, _username(), jsonify)
    if error:
        return error
    return jsonify({"ok": True, "session": session_obj})


@chat_bp.post("/stream")
def chat_stream():
    data = request.get_json(silent=True) or {}
    content = str(data.get("content", "") or "").strip()
    incoming_session_id = str(data.get("session_id", "") or "").strip() or None
    username = _username()

    if not content:
        return jsonify({"ok": False, "error": "content is required"}), 400

    session_id = ensure_session(incoming_session_id, username)
    add_message(session_id, "user", content)

    def event_stream():
        try:
            yield 'event: start\ndata: {"ok":true}\n\n'
            reply_text, web_results, web_provider = generate_reply(username, content, session_id)
            add_message(
                session_id,
                "assistant",
                reply_text,
                web_results=web_results,
                web_provider=web_provider,
            )
            payload = {
                "ok": True,
                "session_id": session_id,
                "content": reply_text,
                "web_results": web_results,
                "web_provider": web_provider,
            }
            yield f"event: done\ndata: {json.dumps(payload)}\n\n"
        except Exception as exc:
            err = {"ok": False, "error": str(exc), "session_id": session_id}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )