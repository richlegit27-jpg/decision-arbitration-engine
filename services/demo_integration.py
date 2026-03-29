# =========================================================
# Nova Ultimate 2026 Phase 6
# Demo Integration: Connect frontend to pre-populated backend
# =========================================================

from flask import Flask, jsonify
from demo_backend import get_memory, get_artifacts, get_messages, get_sessions

app = Flask(__name__)

@app.route("/api/memory", methods=["GET"])
def api_memory():
    return jsonify({"ok": True, "memory": get_memory()})

@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    return jsonify({"ok": True, "artifacts": get_artifacts()})

@app.route("/api/chat/<session_id>", methods=["GET"])
def api_chat(session_id):
    sessions = get_sessions()
    for sess in sessions:
        if sess["id"] == session_id:
            return jsonify({"ok": True, "session": sess})
    return jsonify({"ok": False, "error": "Session not found"}), 404

@app.route("/api/sessions", methods=["GET"])
def api_sessions():
    return jsonify({"ok": True, "sessions": get_sessions()})

if __name__ == "__main__":
    app.run(port=8743, debug=True)