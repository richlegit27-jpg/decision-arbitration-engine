from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import uuid

app = Flask(__name__, static_folder="static", template_folder="templates")

# Use a fixed session ID for simplicity
SESSION_ID = str(uuid.uuid4())
sessions = [{"id": SESSION_ID, "name": "Default", "messages": [], "lastActive": datetime.now().timestamp()}]

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    content = data.get("content", "").strip()
    session_id = data.get("session_id") or SESSION_ID

    # Always return this single session
    session = sessions[0]

    user_msg = {"role": "user", "content": content}
    assistant_msg = {"role": "assistant", "content": f"Echo: {content}"}

    session["messages"].append(user_msg)
    session["messages"].append(assistant_msg)
    session["lastActive"] = datetime.now().timestamp()

    # Always return both messages
    return jsonify([user_msg, assistant_msg])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8743, debug=True)