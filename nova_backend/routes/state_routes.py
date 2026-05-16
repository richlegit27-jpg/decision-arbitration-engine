from __future__ import annotations

from flask import Blueprint, jsonify

state_bp = Blueprint("state_bp", __name__)


def register_state_routes(app, session_store, artifact_store, memory_store):
    @state_bp.route("/api/state", methods=["GET"])
    def api_state():
        sessions_data = session_store.load()
        artifacts = artifact_store.load()
        memory = memory_store.load()

        return jsonify({
            "ok": True,
            "session": sessions_data,
            "artifacts": artifacts,
            "memory": memory,
        })

    app.register_blueprint(state_bp)