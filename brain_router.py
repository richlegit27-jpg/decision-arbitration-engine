from __future__ import annotations

from pathlib import Path
import json
import os
import time
import uuid
from typing import Any, Dict, List

from flask import Flask, Response, jsonify, render_template, request
from openai import OpenAI

from brain_router import build_messages_for_openai

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
USAGE_FILE = DATA_DIR / "nova_usage.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)


def now_ts() -> int:
    return int(time.time())


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_session_store() -> Dict[str, Any]:
    data = read_json(SESSIONS_FILE, {"sessions": [], "active_session_id": None})
    if not isinstance(data, dict):
        data = {"sessions": [], "active_session_id": None}
    data.setdefault("sessions", [])
    data.setdefault("active_session_id", None)
    return data


def ensure_memory_store() -> Dict[str, Any]:
    data = read_json(MEMORY_FILE, {"items": []})
    if not isinstance(data, dict):
        data = {"items": []}
    data.setdefault("items", [])
    return data


def ensure_usage_store() -> Dict[str, Any]:
    data = read_json(USAGE_FILE, {"events": []})
    if not isinstance(data, dict):
        data = {"events": []}
    data.setdefault("events", [])
    return data


def log_usage(event_type: str, payload: Dict[str, Any]) -> None:
    data = ensure_usage_store()
    data["events"].insert(0, {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "payload": payload,
        "timestamp": now_ts(),
    })
    data["events"] = data["events"][:500]
    write_json(USAGE_FILE, data)


def find_session(data: Dict[str, Any], session_id: str) -> Dict[str, Any] | None:
    for session in data.get("sessions", []):
        if session.get("session_id") == session_id:
            return session
    return None


def create_session(title: str = "New Chat") -> Dict[str, Any]:
    data = ensure_session_store()
    session = {
        "session_id": str(uuid.uuid4()),
        "title": title,
        "messages": [],
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }
    data["sessions"].insert(0, session)
    data["active_session_id"] = session["session_id"]
    write_json(SESSIONS_FILE, data)
    return session


def maybe_update_session_title(session: Dict[str, Any], user_text: str) -> None:
    current = str(session.get("title") or "").strip()
    if current and current != "New Chat":
        return

    clean = " ".join(str(user_text or "").strip().split())
    if not clean:
        return

    title = clean[:48].strip()
    if len(clean) > 48:
        title = title.rstrip(" .,:;!-") + "..."
    session["title"] = title or "New Chat"


def build_fallback_reply(user_text: str, mode: str) -> str:
    text = str(user_text or "").strip()

    if mode == "coding":
        return (
            "Nova brain router is active, but the OpenAI key is missing.\n\n"
            "Backend is routing this as a coding request.\n"
            "Next move: add OPENAI_API_KEY to your environment and restart the app."
        )

    if mode == "planning":
        return (
            "Nova brain router is active, but the OpenAI key is missing.\n\n"
            "Backend is routing this as a planning request.\n"
            "Next move: add OPENAI_API_KEY to your environment and restart the app."
        )

    if text:
        return (
            "Nova brain router is active, but the OpenAI key is missing.\n\n"
            f"I received: {text[:180]}"
        )

    return "Nova brain router is active, but the OpenAI key is missing."


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/mobile")
def mobile():
    return render_template("mobile.html")


@app.get("/blog")
def blog():
    return render_template("blog.html")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/state")
def api_state():
    data = ensure_session_store()
    sessions = data.get("sessions", [])

    shaped = []
    for session in sessions:
        messages = session.get("messages", [])
        shaped.append({
            "session_id": session.get("session_id"),
            "title": session.get("title", "New Chat"),
            "message_count": len(messages),
            "updated_at": session.get("updated_at", now_ts()),
        })

    shaped.sort(key=lambda x: x.get("updated_at", 0), reverse=True)

    return jsonify({
        "sessions": shaped,
        "active_session_id": data.get("active_session_id"),
    })


@app.post("/api/session/new")
def api_new_session():
    session = create_session()
    return jsonify({"session_id": session["session_id"]})


@app.get("/api/chat/<session_id>")
def api_get_chat(session_id: str):
    data = ensure_session_store()
    session = find_session(data, session_id)

    if not session:
        return jsonify({
            "session_id": session_id,
            "title": "New Chat",
            "messages": [],
        })

    return jsonify({
        "session_id": session_id,
        "title": session.get("title", "New Chat"),
        "messages": session.get("messages", []),
    })


@app.get("/api/memory")
def api_memory():
    data = ensure_memory_store()
    return jsonify({"items": data.get("items", [])})


@app.post("/api/memory/add")
def api_memory_add():
    payload = request.get_json(silent=True) or {}
    kind = str(payload.get("kind") or "memory").strip()
    value = str(payload.get("value") or "").strip()

    if not value:
        return jsonify({"ok": False, "message": "Value is required"}), 400

    data = ensure_memory_store()
    item = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "value": value,
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }
    data["items"].insert(0, item)
    write_json(MEMORY_FILE, data)

    return jsonify({"ok": True, "item": item})


@app.post("/api/upload")
def api_upload():
    files = request.files.getlist("files")
    uploaded: List[Dict[str, Any]] = []

    for file in files:
        filename = str(file.filename or "").strip()
        if not filename:
            continue

        ext = Path(filename).suffix
        safe_name = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOADS_DIR / safe_name
        file.save(save_path)

        uploaded.append({
            "name": filename,
            "filename": filename,
            "path": str(save_path),
            "size": save_path.stat().st_size if save_path.exists() else 0,
            "uploaded_at": now_ts(),
        })

    return jsonify({"files": uploaded})


@app.post("/api/chat/stream")
def api_chat_stream():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()
    user_text = str(payload.get("content") or "").strip()
    model = str(payload.get("model") or OPENAI_MODEL).strip() or OPENAI_MODEL
    uploaded_files = payload.get("uploaded_files") or []

    data = ensure_session_store()
    session = find_session(data, session_id)

    if not session:
        session = create_session()
        data = ensure_session_store()
        session = find_session(data, session["session_id"])

    if session is None:
        return jsonify({"ok": False, "message": "Session unavailable"}), 500

    user_message = {
        "role": "user",
        "content": user_text if user_text else f"[Uploaded {len(uploaded_files)} file(s)]",
        "timestamp": now_ts(),
    }
    session.setdefault("messages", []).append(user_message)
    maybe_update_session_title(session, user_text)
    session["updated_at"] = now_ts()
    data["active_session_id"] = session["session_id"]
    write_json(SESSIONS_FILE, data)

    memory_items = ensure_memory_store().get("items", [])
    messages_for_openai, decision = build_messages_for_openai(
        user_text=user_text,
        session_messages=session.get("messages", []),
        memory_items=memory_items,
        uploaded_files=uploaded_files,
        max_history=12,
    )

    if client is None:
        assistant_text = build_fallback_reply(user_text, decision.mode)
    else:
        try:
            response = client.responses.create(
                model=model,
                input=messages_for_openai,
                temperature=0.7,
            )
            assistant_text = getattr(response, "output_text", "") or "No response returned."
        except Exception as exc:
            assistant_text = f"Nova router error: {exc}"

    data = ensure_session_store()
    session = find_session(data, session["session_id"])
    if session is None:
        return jsonify({"ok": False, "message": "Session lost during response"}), 500

    assistant_message = {
        "role": "assistant",
        "content": assistant_text,
        "timestamp": now_ts(),
        "meta": {
            "route_mode": decision.mode,
            "route_confidence": decision.confidence,
            "route_notes": decision.notes,
        },
    }

    session.setdefault("messages", []).append(assistant_message)
    session["updated_at"] = now_ts()
    data["active_session_id"] = session["session_id"]
    write_json(SESSIONS_FILE, data)

    log_usage("chat_completion", {
        "session_id": session["session_id"],
        "mode": decision.mode,
        "confidence": decision.confidence,
        "model": model,
        "has_files": bool(uploaded_files),
        "prompt_length": len(user_text),
    })

    return Response(assistant_text, mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    host = (os.getenv("APP_HOST") or "127.0.0.1").strip()
    port = int((os.getenv("APP_PORT") or "5001").strip())
    debug = (os.getenv("APP_DEBUG") or "true").strip().lower() == "true"
    app.run(host=host, port=port, debug=debug)