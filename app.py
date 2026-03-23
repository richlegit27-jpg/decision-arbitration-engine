from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
import re
import time
import uuid

from threading import Lock
from typing import Any, Dict, List, Optional

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
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
USAGE_FILE = DATA_DIR / "nova_usage.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
APP_HOST = (os.getenv("APP_HOST") or "127.0.0.1").strip()
APP_PORT = int((os.getenv("APP_PORT") or "5001").strip())


def env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


APP_DEBUG = env_flag("APP_DEBUG", default=False)
MAX_UPLOAD_MB = int((os.getenv("MAX_UPLOAD_MB") or "25").strip())

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
io_lock = Lock()

LAST_ROUTER_META: Dict[str, Any] = {
    "mode": "general",
    "intent": "idle",
    "reason": "No user message yet.",
    "memory_hits": 0,
    "memory_used": [],
    "route_time_ms": 0,
    "timestamp": int(time.time() * 1000),
    "source": "startup",
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "model": OPENAI_MODEL,
}


def now_ts() -> float:
    return time.time()


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def read_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def ensure_sessions_shape(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict) and "sessions" in data and isinstance(data["sessions"], list):
        return data

    if isinstance(data, list):
        return {"sessions": data}

    return {"sessions": []}


def load_sessions() -> Dict[str, Any]:
    with io_lock:
        return ensure_sessions_shape(read_json_file(SESSIONS_FILE, {"sessions": []}))


def save_sessions(data: Dict[str, Any]) -> None:
    with io_lock:
        write_json_file(SESSIONS_FILE, ensure_sessions_shape(data))


def load_memory() -> List[Dict[str, Any]]:
    with io_lock:
        data = read_json_file(MEMORY_FILE, [])
        return data if isinstance(data, list) else []


def save_memory(items: List[Dict[str, Any]]) -> None:
    with io_lock:
        write_json_file(MEMORY_FILE, items)


def load_usage() -> Dict[str, Any]:
    with io_lock:
        data = read_json_file(USAGE_FILE, {})
        return data if isinstance(data, dict) else {}


def save_usage(data: Dict[str, Any]) -> None:
    with io_lock:
        write_json_file(USAGE_FILE, data)


def normalize_router_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    meta = meta or {}

    memory_used_raw = meta.get("memory_used", [])
    if isinstance(memory_used_raw, list):
        memory_count_from_used = len(memory_used_raw)
    elif memory_used_raw:
        memory_count_from_used = 1
    else:
        memory_count_from_used = 0

    memory_hits = meta.get("memory_hits", 0) or 0
    memory_count = int(memory_hits or memory_count_from_used)

    return {
        "mode": meta.get("mode", "general"),
        "intent": meta.get("intent", meta.get("mode", "general")),
        "confidence": meta.get("confidence"),
        "reason": meta.get("reason", ""),
        "memory_used": bool(memory_count),
        "memory_count": memory_count,
        "memory_items": meta.get("memory_used", []) if isinstance(meta.get("memory_used", []), list) else [],
        "route_time_ms": meta.get("route_time_ms", 0),
        "model": meta.get("model", OPENAI_MODEL),
        "provider": meta.get("provider", "openai"),
        "source": meta.get("source", "server"),
        "timestamp": meta.get("timestamp", now_ms()),
        "updated_at": meta.get("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    }


def set_last_router_meta(router_meta: Optional[Dict[str, Any]] = None, source: str = "server") -> Dict[str, Any]:
    global LAST_ROUTER_META

    meta = normalize_router_meta(dict(router_meta or {}))
    meta["source"] = str(meta.get("source") or source).strip()
    meta["updated_at"] = str(meta.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).strip()
    meta["model"] = str(meta.get("model") or OPENAI_MODEL).strip()

    LAST_ROUTER_META = meta
    return LAST_ROUTER_META


def make_session(title: str = "New Chat") -> Dict[str, Any]:
    ts = now_ts()
    initial_router_meta = normalize_router_meta(
        {
            "mode": "general",
            "intent": "idle",
            "reason": "No user message yet.",
            "memory_hits": 0,
            "memory_used": [],
            "route_time_ms": 0,
            "timestamp": now_ms(),
            "source": "session_create",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": OPENAI_MODEL,
        }
    )

    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": ts,
        "updated_at": ts,
        "pinned": False,
        "messages": [],
        "router_meta": initial_router_meta,
    }


def get_or_create_default_session() -> Dict[str, Any]:
    payload = load_sessions()
    sessions = payload["sessions"]

    if not sessions:
        session = make_session("New Chat")
        sessions.append(session)
        save_sessions(payload)
        set_last_router_meta(session.get("router_meta", {}), source="default_session_create")
        return session

    sessions.sort(key=lambda s: (not bool(s.get("pinned")), -(s.get("updated_at") or 0)))
    set_last_router_meta(sessions[0].get("router_meta", {}), source="default_session_pick")
    return sessions[0]


def find_session(session_id: str) -> Optional[Dict[str, Any]]:
    payload = load_sessions()
    for session in payload["sessions"]:
        if session.get("id") == session_id:
            return session
    return None


def save_session(updated_session: Dict[str, Any]) -> None:
    payload = load_sessions()
    found = False
    for i, session in enumerate(payload["sessions"]):
        if session.get("id") == updated_session.get("id"):
            payload["sessions"][i] = updated_session
            found = True
            break

    if not found:
        payload["sessions"].append(updated_session)

    save_sessions(payload)


def summarize_text(text: str, max_len: int = 80) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return "New Chat"
    return text[:max_len].strip()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def route_message(user_text: str, memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    started = now_ms()
    text = normalize_text(user_text)
    lowered = text.lower()

    mode = "general"
    intent = "conversation"
    reason = "Defaulted to general conversation."
    memory_used: List[str] = []

    coding_terms = [
        "code", "bug", "fix", "app.py", "javascript", "python", "flask",
        "html", "css", "smff", "file", "router", "panel", "backend",
        "frontend", "script", "function", "json", "api",
    ]
    planning_terms = [
        "plan", "roadmap", "next", "steps", "phase", "version", "launch", "strategy",
    ]
    writing_terms = [
        "write", "rewrite", "email", "book", "blog", "post", "caption", "story",
    ]
    analysis_terms = [
        "analyze", "compare", "why", "reason", "breakdown", "audit", "review",
    ]

    if any(term in lowered for term in coding_terms):
        mode = "coding"
        intent = "build_or_fix_code"
        reason = "Detected coding and app-building language in the request."
    elif any(term in lowered for term in planning_terms):
        mode = "planning"
        intent = "project_planning"
        reason = "Detected planning / roadmap language."
    elif any(term in lowered for term in writing_terms):
        mode = "writing"
        intent = "draft_or_rewrite"
        reason = "Detected writing-oriented language."
    elif any(term in lowered for term in analysis_terms):
        mode = "analysis"
        intent = "inspect_or_explain"
        reason = "Detected analysis / explanation language."

    significant_words = {
        word
        for word in re.findall(r"[a-zA-Z0-9_\-]{3,}", lowered)
        if word not in {"the", "and", "for", "with", "that", "this", "you", "your", "are", "was"}
    }

    for item in memory_items:
        kind = str(item.get("kind", "")).strip()
        value = normalize_text(str(item.get("value", "")))
        blob = f"{kind} {value}".lower()
        if not value:
            continue

        matched = any(word in blob for word in significant_words)
        if matched:
            memory_used.append(value)

    memory_used = memory_used[:6]

    return {
        "mode": mode,
        "intent": intent,
        "reason": reason,
        "memory_hits": len(memory_used),
        "memory_used": memory_used,
        "route_time_ms": max(1, now_ms() - started),
        "timestamp": now_ms(),
        "source": "route_message",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": OPENAI_MODEL,
    }


def build_system_prompt(router_meta: Dict[str, Any], memory_items: List[Dict[str, Any]]) -> str:
    memory_lines = []
    for item in memory_items[:12]:
        kind = item.get("kind", "memory")
        value = item.get("value", "")
        if value:
            memory_lines.append(f"- {kind}: {value}")

    memory_block = "\n".join(memory_lines) if memory_lines else "- none"

    return f"""
You are Nova, a direct, helpful AI assistant.

Current route:
- mode: {router_meta.get("mode", "general")}
- intent: {router_meta.get("intent", "conversation")}
- reason: {router_meta.get("reason", "")}

Relevant memory:
{memory_block}

Behavior:
- be direct
- be practical
- prefer solution-first responses
- when user asks for SMFF, provide a full file
- keep coding answers concrete
""".strip()


def chat_with_model(messages: List[Dict[str, str]], router_meta: Dict[str, Any], memory_items: List[Dict[str, Any]]) -> str:
    if not client:
        return (
            "[Nova offline fallback]\n\n"
            f"Mode: {router_meta.get('mode')}\n"
            f"Intent: {router_meta.get('intent')}\n"
            "No OPENAI_API_KEY found, so this is a local fallback response."
        )

    system_prompt = build_system_prompt(router_meta, memory_items)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            *messages,
        ],
    )
    return (response.choices[0].message.content or "").strip()


def session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": session.get("id"),
        "title": session.get("title", "New Chat"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned")),
        "message_count": len(session.get("messages", [])),
    }


def safe_json() -> Dict[str, Any]:
    try:
        return request.get_json(force=True, silent=True) or {}
    except Exception:
        return {}


@app.after_request
def apply_response_headers(response: Response) -> Response:
    path = request.path or ""

    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    if path in {"/", "/mobile"}:
        response.headers["Cache-Control"] = "no-store, max-age=0"

    return response


@app.get("/")
def index() -> Any:
    return render_template("index.html")


@app.get("/mobile")
def mobile() -> Any:
    return render_template("mobile.html")


@app.get("/health")
def health() -> Any:
    return jsonify({"ok": True, "time": iso_now()})


@app.get("/api/state")
def api_state() -> Any:
    payload = load_sessions()
    sessions = payload["sessions"]

    if not sessions:
        current = get_or_create_default_session()
        sessions = load_sessions()["sessions"]
    else:
        sessions.sort(key=lambda s: (not bool(s.get("pinned")), -(s.get("updated_at") or 0)))
        current = sessions[0]

    current_id = request.args.get("session_id") or current.get("id")
    current = find_session(current_id) or current

    memory_items = load_memory()
    current_router = normalize_router_meta(current.get("router_meta", {}) or LAST_ROUTER_META)
    set_last_router_meta(current_router, source="api_state")

    return jsonify(
        {
            "ok": True,
            "model": OPENAI_MODEL,
            "current_model": OPENAI_MODEL,
            "current_session_id": current.get("id"),
            "active_session_id": current.get("id"),
            "sessions": [session_summary(s) for s in sessions],
            "memory": memory_items,
            "router_meta": current_router,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.get("/api/chat/<session_id>")
def api_get_chat(session_id: str) -> Any:
    session = find_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    router_meta = normalize_router_meta(session.get("router_meta", {}) or LAST_ROUTER_META)
    set_last_router_meta(router_meta, source="api_get_chat")

    return jsonify(
        {
            "ok": True,
            "session": session_summary(session),
            "session_id": session.get("id"),
            "messages": session.get("messages", []),
            "router_meta": router_meta,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/chat")
def api_chat() -> Any:
    data = safe_json()

    session_id = str(data.get("session_id") or "").strip()
    user_message = normalize_text(str(data.get("message") or data.get("content") or ""))

    if not user_message:
        return jsonify({"ok": False, "error": "Message is required."}), 400

    session = find_session(session_id) if session_id else None
    if not session:
        session = make_session()

    memory_items = load_memory()
    raw_meta = route_message(user_message, memory_items)
    router_meta = normalize_router_meta(raw_meta)
    set_last_router_meta(router_meta, source="api_chat_route")

    user_entry = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_message,
        "created_at": now_ts(),
    }
    session.setdefault("messages", []).append(user_entry)

    model_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in session["messages"][-16:]
        if m.get("role") in {"user", "assistant"}
    ]

    try:
        assistant_text = chat_with_model(model_messages, router_meta, memory_items)
    except Exception as exc:
        assistant_text = f"Nova hit an error talking to the model: {exc}"

    assistant_entry = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": assistant_text,
        "created_at": now_ts(),
        "router_meta": router_meta,
    }
    session["messages"].append(assistant_entry)

    if session.get("title", "New Chat") == "New Chat":
        session["title"] = summarize_text(user_message)

    session["updated_at"] = now_ts()
    session["router_meta"] = router_meta

    save_session(session)
    set_last_router_meta(router_meta, source="api_chat_saved")

    usage = load_usage()
    usage["last_chat_at"] = now_ts()
    usage["last_mode"] = router_meta.get("mode")
    usage["last_intent"] = router_meta.get("intent")
    usage["chat_count"] = int(usage.get("chat_count", 0)) + 1
    save_usage(usage)

    return jsonify(
        {
            "ok": True,
            "session_id": session["id"],
            "active_session_id": session["id"],
            "message": assistant_entry,
            "router_meta": router_meta,
            "last_router_meta": LAST_ROUTER_META,
            "session": session_summary(session),
        }
    )


@app.route("/api/chat/stream", methods=["POST", "OPTIONS"])
def api_chat_stream():
    if request.method == "OPTIONS":
        return ("", 204)

    data = safe_json()

    session_id = str(data.get("session_id") or "").strip()
    user_message = normalize_text(str(data.get("message") or data.get("content") or ""))

    if not user_message:
        return jsonify({"ok": False, "error": "Message is required."}), 400

    session = find_session(session_id) if session_id else None
    if not session:
        session = make_session()

    memory_items = load_memory()
    raw_meta = route_message(user_message, memory_items)
    router_meta = normalize_router_meta(raw_meta)
    set_last_router_meta(router_meta, source="stream_route")

    user_entry = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_message,
        "created_at": now_ts(),
    }
    session.setdefault("messages", []).append(user_entry)

    model_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in session["messages"][-16:]
        if m.get("role") in {"user", "assistant"}
    ]

    def sse(payload: Dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        full_text = ""

        try:
            yield sse(
                {
                    "type": "meta",
                    "router_meta": router_meta,
                    "session_id": session["id"],
                }
            )

            if not client:
                fallback = (
                    "[Nova offline fallback]\n\n"
                    f"Mode: {router_meta.get('mode')}\n"
                    f"Intent: {router_meta.get('intent')}\n"
                    "No OPENAI_API_KEY found."
                )
                full_text = fallback

                yield sse(
                    {
                        "type": "delta",
                        "delta": fallback,
                        "session_id": session["id"],
                    }
                )
            else:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    temperature=0.3,
                    stream=True,
                    messages=[
                        {"role": "system", "content": build_system_prompt(router_meta, memory_items)},
                        *model_messages,
                    ],
                )

                for chunk in response:
                    try:
                        delta = chunk.choices[0].delta.content or ""
                    except Exception:
                        delta = ""

                    if not delta:
                        continue

                    full_text += delta

                    yield sse(
                        {
                            "type": "delta",
                            "delta": delta,
                            "session_id": session["id"],
                        }
                    )

            assistant_entry = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": full_text,
                "created_at": now_ts(),
                "router_meta": router_meta,
            }
            session["messages"].append(assistant_entry)

            if session.get("title", "New Chat") == "New Chat":
                session["title"] = summarize_text(user_message)

            session["updated_at"] = now_ts()
            session["router_meta"] = router_meta

            save_session(session)
            set_last_router_meta(router_meta, source="stream_saved")

            usage = load_usage()
            usage["last_chat_at"] = now_ts()
            usage["last_mode"] = router_meta.get("mode")
            usage["last_intent"] = router_meta.get("intent")
            usage["chat_count"] = int(usage.get("chat_count", 0)) + 1
            save_usage(usage)

            yield sse(
                {
                    "type": "done",
                    "response": full_text,
                    "router_meta": router_meta,
                    "session": session_summary(session),
                    "session_id": session["id"],
                }
            )
            yield "data: [DONE]\n\n"

        except Exception as exc:
            yield sse(
                {
                    "type": "error",
                    "error": str(exc),
                    "session_id": session["id"],
                }
            )
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/upload")
def api_upload() -> Any:
    incoming_files = request.files.getlist("files")
    if not incoming_files:
        single = request.files.get("file")
        if single:
            incoming_files = [single]

    if not incoming_files:
        return jsonify({"ok": False, "error": "No files uploaded."}), 400

    saved_files: List[Dict[str, Any]] = []

    for incoming in incoming_files:
        original_name = secure_filename(incoming.filename or "")
        if not original_name:
            continue

        file_id = str(uuid.uuid4())
        stored_name = f"{file_id}_{original_name}"
        target_path = UPLOAD_DIR / stored_name
        incoming.save(target_path)

        saved_files.append(
            {
                "id": file_id,
                "name": original_name,
                "stored_name": stored_name,
                "size": target_path.stat().st_size,
                "created_at": now_ts(),
            }
        )

    if not saved_files:
        return jsonify({"ok": False, "error": "No valid files uploaded."}), 400

    return jsonify(
        {
            "ok": True,
            "files": saved_files,
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/session/new")
def api_session_new() -> Any:
    data = safe_json()
    title = normalize_text(str(data.get("title") or "New Chat"))
    session = make_session(title=title)
    save_session(session)
    set_last_router_meta(session.get("router_meta", {}), source="api_session_new")
    return jsonify(
        {
            "ok": True,
            "session": session_summary(session),
            "session_id": session["id"],
            "active_session_id": session["id"],
            "router_meta": session["router_meta"],
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/session/delete")
def api_session_delete() -> Any:
    data = safe_json()
    session_id = str(data.get("session_id") or "").strip()

    payload = load_sessions()
    before = len(payload["sessions"])
    payload["sessions"] = [s for s in payload["sessions"] if s.get("id") != session_id]
    after = len(payload["sessions"])

    if before == after:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    if not payload["sessions"]:
        payload["sessions"].append(make_session())

    save_sessions(payload)
    remaining_router = payload["sessions"][0].get("router_meta", {}) if payload["sessions"] else LAST_ROUTER_META
    set_last_router_meta(remaining_router, source="api_session_delete")

    return jsonify(
        {
            "ok": True,
            "sessions": [session_summary(s) for s in payload["sessions"]],
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/session/rename")
def api_session_rename() -> Any:
    data = safe_json()
    session_id = str(data.get("session_id") or "").strip()
    title = normalize_text(str(data.get("title") or ""))

    if not title:
        return jsonify({"ok": False, "error": "Title is required."}), 400

    session = find_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    session["title"] = title
    session["updated_at"] = now_ts()
    save_session(session)

    router_meta = normalize_router_meta(session.get("router_meta", {}) or LAST_ROUTER_META)
    set_last_router_meta(router_meta, source="api_session_rename")

    return jsonify(
        {
            "ok": True,
            "session": session_summary(session),
            "router_meta": router_meta,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/session/duplicate")
def api_session_duplicate() -> Any:
    data = safe_json()
    session_id = str(data.get("session_id") or "").strip()

    session = find_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    clone = json.loads(json.dumps(session))
    clone["id"] = str(uuid.uuid4())
    clone["title"] = f"{session.get('title', 'Chat')} Copy"
    clone["created_at"] = now_ts()
    clone["updated_at"] = now_ts()

    for message in clone.get("messages", []):
        message["id"] = str(uuid.uuid4())

    clone["router_meta"] = normalize_router_meta(clone.get("router_meta", {}) or LAST_ROUTER_META)

    save_session(clone)
    router_meta = clone.get("router_meta", {}) or LAST_ROUTER_META
    set_last_router_meta(router_meta, source="api_session_duplicate")

    return jsonify(
        {
            "ok": True,
            "session": session_summary(clone),
            "router_meta": router_meta,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/session/pin")
def api_session_pin() -> Any:
    data = safe_json()
    session_id = str(data.get("session_id") or "").strip()
    pinned = bool(data.get("pinned", True))

    session = find_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    session["pinned"] = pinned
    session["updated_at"] = now_ts()
    save_session(session)

    router_meta = normalize_router_meta(session.get("router_meta", {}) or LAST_ROUTER_META)
    set_last_router_meta(router_meta, source="api_session_pin")

    return jsonify(
        {
            "ok": True,
            "session": session_summary(session),
            "router_meta": router_meta,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/session/export")
def api_session_export() -> Any:
    data = safe_json()
    session_id = str(data.get("session_id") or "").strip()

    session = find_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    router_meta = normalize_router_meta(session.get("router_meta", {}) or LAST_ROUTER_META)
    set_last_router_meta(router_meta, source="api_session_export")

    return jsonify(
        {
            "ok": True,
            "session": session,
            "router_meta": router_meta,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.get("/api/memory")
def api_memory_get() -> Any:
    return jsonify(
        {
            "ok": True,
            "memory": load_memory(),
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/memory")
def api_memory_add() -> Any:
    data = safe_json()
    kind = normalize_text(str(data.get("kind") or "memory")).lower()
    value = normalize_text(str(data.get("value") or ""))

    if not value:
        return jsonify({"ok": False, "error": "Memory value is required."}), 400

    items = load_memory()
    entry = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "value": value,
        "created_at": now_ts(),
    }
    items.insert(0, entry)
    save_memory(items)

    return jsonify(
        {
            "ok": True,
            "item": entry,
            "memory": items,
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.post("/api/memory/delete")
def api_memory_delete() -> Any:
    data = safe_json()
    memory_id = str(data.get("id") or "").strip()

    items = load_memory()
    before = len(items)
    items = [m for m in items if m.get("id") != memory_id]
    after = len(items)

    if before == after:
        return jsonify({"ok": False, "error": "Memory item not found."}), 404

    save_memory(items)
    return jsonify(
        {
            "ok": True,
            "memory": items,
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
        }
    )


@app.get("/favicon.ico")
def favicon() -> Any:
    return ("", 204)


@app.get("/static/<path:filename>")
def serve_static(filename: str) -> Any:
    return send_from_directory(STATIC_DIR, filename)

APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("PORT", "5001"))
APP_DEBUG = False

if __name__ == "__main__":
    print(f"Nova running on http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)