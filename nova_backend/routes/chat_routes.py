from __future__ import annotations

from flask import Blueprint, request, jsonify

chat_bp = Blueprint("chat_bp", __name__)


def register_chat_routes(app, agent_service):
    @chat_bp.route("/api/chat", methods=["POST"])
    def api_chat():
        data = request.get_json(silent=True) or {}
        user_text = str(data.get("user_text") or "")
        attachments = data.get("attachments") or []

        result = agent_service.run(user_text, attachments)

        return jsonify(result)

    app.register_blueprint(chat_bp)

