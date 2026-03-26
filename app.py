from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
    stream_with_context,
)
from openai import OpenAI

from app_attachment_mount import register_attachment_compat


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"


# =========================================================
# CONFIG
# =========================================================

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-5.4").strip()
APP_TITLE = "Nova"

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)

app.config["UPLOAD_DIR"] = str(UPLOAD_DIR)
register_attachment_compat(app)


# =========================================================
# LOCKS
# =========================================================

sessions_lock = Lock()
memory_lock = Lock()


# =========================================================
# HELPERS
# =========================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json_load(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def safe_json_save(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_sessions_store() -> Dict[str, Any]:
    data = safe_json_load(SESSIONS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    if "sessions" not in data or not isinstance(data["sessions"], list):
        data["sessions"] = []
    return data


def ensure_memory_store() -> Dict[str, Any]:
    data = safe_json_load(MEMORY_FILE, {})
    if not isinstance(data, dict):
        data = {}
    if "items" not in data or not isinstance(data["items"], list):
        data["items"] = []
    return data


def make_session(title: str = "New Chat") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "messages": [],
    }


def get_all_sessions() -> List[Dict[str, Any]]:
    with sessions_lock:
        store = ensure_sessions_store()
        return store["sessions"]


def save_all_sessions(sessions: List[Dict[str, Any]]) -> None:
    with sessions_lock:
        safe_json_save(SESSIONS_FILE, {"sessions": sessions})


def get_session_by_id(session_id: str) -> Dict[str, Any] | None:
    sessions = get_all_sessions()
    for session in sessions:
      if session.get("id") == session_id:
        return session
    return None


def upsert_session(updated_session: Dict[str, Any]) -> None:
    sessions = get_all_sessions()
    replaced = False

    for index, session in enumerate(sessions):
        if session.get("id") == updated_session.get("id"):
            sessions[index] = updated_session
            replaced = True
            break

    if not replaced:
        sessions.insert(0, updated_session)

    save_all_sessions(sessions)


def summarize_session(session: Dict[str, Any]) -> Dict[str, Any]:
    messages = session.get("messages") or []
    last_message = messages[-1] if messages else {}
    preview = ""

    content = last_message.get("content")
    if isinstance(content, str):
        preview = content[:140]
    elif isinstance(content, list):
        preview = " ".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
        )[:140]

    return {
        "id": session.get("id"),
        "title": session.get("title") or "Untitled",
        "updated_at": session.get("updated_at"),
        "created_at": session.get("created_at"),
        "message_count": len(messages),
        "preview": preview,
    }


def list_memory_items() -> List[Dict[str, Any]]:
    with memory_lock:
        store = ensure_memory_store()
        return store["items"]


def save_memory_items(items: List[Dict[str, Any]]) -> None:
    with memory_lock:
        safe_json_save(MEMORY_FILE, {"items": items})


def extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(parts).strip()
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if isinstance(content.get("content"), str):
            return content["content"]
    return ""


def normalize_messages_for_model(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []

    for msg in messages:
        role = str(msg.get("role") or "user").lower().strip()
        if role not in {"system", "user", "assistant"}:
            role = "user"

        text = extract_text_from_content(msg.get("content") or msg.get("text") or "")
        if not text.strip():
            continue

        normalized.append({
            "role": role,
            "content": text,
        })

    return normalized


def attachment_context_block(attachments: List[Dict[str, Any]]) -> str:
    if not attachments:
        return ""

    lines = ["Attached files:"]
    for item in attachments:
        name = str(item.get("name") or item.get("filename") or "file").strip() or "file"
        size = int(item.get("size") or 0)
        mime_type = str(item.get("type") or item.get("mime_type") or "").strip()
        url = str(item.get("url") or item.get("file_url") or "").strip()

        meta = []
        if size:
            meta.append(f"size={size}")
        if mime_type:
            meta.append(f"type={mime_type}")
        if url:
            meta.append(f"url={url}")

        if meta:
            lines.append(f"- {name} ({', '.join(meta)})")
        else:
            lines.append(f"- {name}")

    return "\n".join(lines).strip()


def build_model_messages(session_messages: List[Dict[str, Any]], user_text: str, attachments: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    base_messages = normalize_messages_for_model(session_messages)

    system_prompt = (
        "You are Nova, a helpful AI assistant. "
        "Be direct, useful, and clear."
    )

    output: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    output.extend(base_messages)

    final_user_text = user_text.strip()
    attachment_block = attachment_context_block(attachments)

    if attachment_block:
        if final_user_text:
            final_user_text = f"{final_user_text}\n\n{attachment_block}"
        else:
            final_user_text = attachment_block

    output.append({
        "role": "user",
        "content": final_user_text or "Hello.",
    })

    return output


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def ensure_default_session() -> Dict[str, Any]:
    sessions = get_all_sessions()
    if sessions:
        return sessions[0]

    session = make_session()
    sessions.insert(0, session)
    save_all_sessions(sessions)
    return session


def create_assistant_reply(model_messages: List[Dict[str, str]]) -> str:
    if client is None:
        return "Nova backend is running, but OPENAI_API_KEY is missing."

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=model_messages,
            temperature=0.7,
        )
        return (
            response.choices[0].message.content
            if response and response.choices and response.choices[0].message
            else "No response received."
        ) or "No response received."
    except Exception as exc:
        return f"Model error: {exc}"


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    return jsonify({
        "ok": True,
        "app": APP_TITLE,
        "model": OPENAI_MODEL,
        "model_connected": bool(client),
        "sessions_count": len(get_all_sessions()),
    })


@app.get("/api/state")
def api_state():
    sessions = get_all_sessions()
    sessions_sorted = sorted(
        sessions,
        key=lambda s: s.get("updated_at") or "",
        reverse=True,
    )

    active = sessions_sorted[0]["id"] if sessions_sorted else None

    return jsonify({
        "ok": True,
        "app": APP_TITLE,
        "sessions": [summarize_session(s) for s in sessions_sorted],
        "active_session_id": active,
        "memory": list_memory_items(),
        "model": OPENAI_MODEL,
    })


@app.post("/api/session/new")
def api_session_new():
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title") or "New Chat").strip() or "New Chat"

    session = make_session(title=title)
    sessions = get_all_sessions()
    sessions.insert(0, session)
    save_all_sessions(sessions)

    return jsonify({
        "ok": True,
        "session_id": session["id"],
        "session": session,
    })


@app.post("/api/session/delete")
def api_session_delete():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    sessions = get_all_sessions()
    filtered = [s for s in sessions if s.get("id") != session_id]
    save_all_sessions(filtered)

    return jsonify({"ok": True})


@app.post("/api/session/rename")
def api_session_rename():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()
    title = str(payload.get("title") or "").strip()

    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400

    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400

    sessions = get_all_sessions()
    target = None

    for session in sessions:
        if session.get("id") == session_id:
            session["title"] = title
            session["updated_at"] = now_iso()
            target = session
            break

    if target is None:
        return jsonify({"ok": False, "error": "session not found"}), 404

    save_all_sessions(sessions)

    return jsonify({"ok": True, "session": target})


@app.get("/api/chat/<session_id>")
def api_chat_get(session_id: str):
    session_id = str(session_id or "").strip()
    session = get_session_by_id(session_id)

    if session is None:
        return jsonify({"ok": False, "error": "session not found"}), 404

    return jsonify({
        "ok": True,
        "session": session,
    })


@app.get("/api/memory")
def api_memory_list():
    return jsonify({
        "ok": True,
        "items": list_memory_items(),
    })


@app.post("/api/memory")
@app.post("/api/memory/add")
def api_memory_add():
    payload = request.get_json(silent=True) or {}
    value = str(payload.get("value") or "").strip()
    kind = str(payload.get("kind") or "note").strip() or "note"

    if not value:
        return jsonify({"ok": False, "error": "value is required"}), 400

    items = list_memory_items()
    item = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "value": value,
        "created_at": now_iso(),
    }
    items.insert(0, item)
    save_memory_items(items)

    return jsonify({"ok": True, "item": item, "items": items})


@app.post("/api/memory/delete")
def api_memory_delete():
    payload = request.get_json(silent=True) or {}
    item_id = str(payload.get("id") or payload.get("item_id") or "").strip()

    if not item_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    items = list_memory_items()
    filtered = [item for item in items if item.get("id") != item_id]
    save_memory_items(filtered)

    return jsonify({"ok": True, "items": filtered})


@app.post("/api/chat/stream")
def api_chat_stream():
    payload = request.get_json(silent=True) or {}

    session_id = str(payload.get("session_id") or "").strip()
    content = str(payload.get("content") or "").strip()
    attachments = app.extract_attachments_from_json(payload)

    if not session_id:
        session = ensure_default_session()
        session_id = session["id"]
    else:
        session = get_session_by_id(session_id)

    if session is None:
        return jsonify({"ok": False, "error": "session not found"}), 404

    if not content and not attachments:
        return jsonify({"ok": False, "error": "content is required"}), 400

    user_message: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": content,
        "created_at": now_iso(),
    }

    if attachments:
        user_message["attachments"] = attachments

    session_messages = session.get("messages") or []
    session_messages.append(user_message)
    session["messages"] = session_messages
    session["updated_at"] = now_iso()
    upsert_session(session)

    model_messages = build_model_messages(
        session_messages=session_messages[:-1],
        user_text=content,
        attachments=attachments,
    )

    def generate():
        yield sse("start", {"ok": True, "session_id": session_id})

        start_time = time.time()
        assistant_text = create_assistant_reply(model_messages)

        chunk_size = 120
        for i in range(0, len(assistant_text), chunk_size):
            delta = assistant_text[i:i + chunk_size]
            yield sse("delta", {"delta": delta})

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_text,
            "created_at": now_iso(),
        }

        latest = get_session_by_id(session_id)
        if latest is not None:
            latest_messages = latest.get("messages") or []
            latest_messages.append(assistant_message)
            latest["messages"] = latest_messages
            latest["updated_at"] = now_iso()
            upsert_session(latest)

        yield sse("done", {
            "ok": True,
            "session_id": session_id,
            "content": assistant_text,
            "message": assistant_message,
            "elapsed": round(time.time() - start_time, 3),
        })

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    ensure_default_session()
    app.run(host="0.0.0.0", port=5001, debug=True)