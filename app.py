from pathlib import Path
import json
import os
import time
import uuid
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)


def now_ts() -> int:
    return int(time.time())


def safe_read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_session(name: str = "New Chat") -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    return {
        "id": session_id,
        "name": name,
        "created_at": now_ts(),
        "updated_at": now_ts(),
        "messages": [],
    }


def load_sessions() -> Dict[str, Any]:
    data = safe_read_json(SESSIONS_FILE, None)
    if not isinstance(data, dict):
        starter = default_session()
        data = {
            "active_session_id": starter["id"],
            "sessions": [starter],
        }
        save_sessions(data)
        return data

    sessions = data.get("sessions", [])
    if not isinstance(sessions, list) or not sessions:
        starter = default_session()
        data = {
            "active_session_id": starter["id"],
            "sessions": [starter],
        }
        save_sessions(data)
        return data

    if not data.get("active_session_id"):
        data["active_session_id"] = sessions[0]["id"]

    return data


def save_sessions(data: Dict[str, Any]) -> None:
    safe_write_json(SESSIONS_FILE, data)


def sort_sessions(data: Dict[str, Any]) -> None:
    data["sessions"] = sorted(
        data["sessions"],
        key=lambda s: s.get("updated_at", 0),
        reverse=True,
    )


def find_session(data: Dict[str, Any], session_id: str) -> Dict[str, Any] | None:
    for session in data["sessions"]:
        if session["id"] == session_id:
            return session
    return None


def title_from_messages(messages: List[Dict[str, Any]]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = (msg.get("content") or "").strip()
            if text:
                return text[:40]
    return "New Chat"


def normalize_state(data: Dict[str, Any]) -> Dict[str, Any]:
    sort_sessions(data)
    active_id = data.get("active_session_id")
    active_session = find_session(data, active_id)

    if active_session is None and data["sessions"]:
        active_session = data["sessions"][0]
        data["active_session_id"] = active_session["id"]

    return {
        "active_session_id": data["active_session_id"],
        "sessions": [
            {
                "id": s["id"],
                "name": s.get("name", "New Chat"),
                "created_at": s.get("created_at", 0),
                "updated_at": s.get("updated_at", 0),
                "message_count": len(s.get("messages", [])),
                "preview": next(
                    (
                        (m.get("content") or "").strip()[:60]
                        for m in s.get("messages", [])
                        if (m.get("content") or "").strip()
                    ),
                    "",
                ),
            }
            for s in data["sessions"]
        ],
        "active_messages": active_session.get("messages", []) if active_session else [],
    }


def chat_reply(user_text: str, session_messages: List[Dict[str, Any]]) -> str:
    if not client:
        return f"Nova reply: {user_text}"

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Nova, a clean, direct, helpful assistant. "
                    "Keep replies practical and concise."
                ),
            }
        ]

        for msg in session_messages[-12:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in {"user", "assistant", "system"} and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_text})

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content or "No response."
    except Exception as exc:
        return f"Nova error: {exc}"


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    data = load_sessions()
    save_sessions(data)
    return jsonify(normalize_state(data))


@app.route("/api/chat/<session_id>", methods=["GET"])
def api_get_chat(session_id: str):
    data = load_sessions()
    session = find_session(data, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    data["active_session_id"] = session_id
    save_sessions(data)

    return jsonify(
        {
            "session_id": session["id"],
            "name": session.get("name", "New Chat"),
            "messages": session.get("messages", []),
        }
    )


@app.route("/api/session/new", methods=["POST"])
def api_new_session():
    data = load_sessions()
    session = default_session()
    data["sessions"].insert(0, session)
    data["active_session_id"] = session["id"]
    save_sessions(data)
    return jsonify(
        {
            "ok": True,
            "session_id": session["id"],
            "state": normalize_state(data),
        }
    )


@app.route("/api/session/rename", methods=["POST"])
def api_rename_session():
    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or "").strip()
    new_name = (payload.get("name") or "").strip()

    if not session_id or not new_name:
        return jsonify({"error": "session_id and name are required"}), 400

    data = load_sessions()
    session = find_session(data, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    session["name"] = new_name[:80]
    session["updated_at"] = now_ts()
    save_sessions(data)
    return jsonify({"ok": True, "state": normalize_state(data)})


@app.route("/api/session/delete", methods=["POST"])
def api_delete_session():
    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    data = load_sessions()
    original_count = len(data["sessions"])
    data["sessions"] = [s for s in data["sessions"] if s["id"] != session_id]

    if len(data["sessions"]) == original_count:
        return jsonify({"error": "Session not found"}), 404

    if not data["sessions"]:
        starter = default_session()
        data["sessions"] = [starter]
        data["active_session_id"] = starter["id"]
    elif data.get("active_session_id") == session_id:
        data["active_session_id"] = data["sessions"][0]["id"]

    save_sessions(data)
    return jsonify({"ok": True, "state": normalize_state(data)})


@app.route("/api/session/clear", methods=["POST"])
def api_clear_session():
    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    data = load_sessions()
    session = find_session(data, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    session["messages"] = []
    session["updated_at"] = now_ts()
    save_sessions(data)
    return jsonify({"ok": True, "state": normalize_state(data)})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or "").strip()
    user_text = (payload.get("content") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not user_text:
        return jsonify({"error": "content is required"}), 400

    data = load_sessions()
    session = find_session(data, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_text,
        "timestamp": now_ts(),
    }
    session["messages"].append(user_msg)
    session["updated_at"] = now_ts()

    if session.get("name", "New Chat") == "New Chat":
        session["name"] = title_from_messages(session["messages"])

    reply = chat_reply(user_text, session["messages"])
    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": reply,
        "timestamp": now_ts(),
    }
    session["messages"].append(assistant_msg)
    session["updated_at"] = now_ts()

    data["active_session_id"] = session_id
    save_sessions(data)

    return jsonify(
        {
            "ok": True,
            "reply": reply,
            "messages": session["messages"],
            "state": normalize_state(data),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)