from __future__ import annotations

from pathlib import Path
import json
import os
import re
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    stream_with_context,
    url_for,
)
from openai import OpenAI


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

APP_PASSWORD = (os.getenv("NOVA_APP_PASSWORD") or "").strip()
FLASK_SECRET_KEY = (os.getenv("FLASK_SECRET_KEY") or "nova-local-dev-secret").strip()

MAX_MEMORY_USED = 6
MAX_SESSION_PREVIEW = 60
MAX_MODEL_MESSAGES = 20
MAX_UPLOAD_FILES = 10

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)
app.secret_key = FLASK_SECRET_KEY

data_lock = Lock()

client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


def now_ts() -> int:
    return int(time.time())


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def slugify_title(value: str) -> str:
    text = safe_text(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:80] if text else "New Chat"


def ensure_file(path: Path, fallback: Any) -> None:
    if not path.exists():
        path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")


def load_json(path: Path, fallback: Any) -> Any:
    ensure_file(path, fallback)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sse_event(event_name: str, data: Dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def require_login() -> bool:
    if not APP_PASSWORD:
        return True
    return bool(session.get("nova_logged_in"))


def memory_file_default() -> Dict[str, Any]:
    return {"memory": []}


def sessions_file_default() -> Dict[str, Any]:
    return {
        "current_session_id": None,
        "sessions": []
    }


def usage_file_default() -> Dict[str, Any]:
    return {
        "total_requests": 0,
        "total_sessions": 0,
        "last_request_at": None,
    }


def read_sessions_store() -> Dict[str, Any]:
    return load_json(SESSIONS_FILE, sessions_file_default())


def write_sessions_store(store: Dict[str, Any]) -> None:
    save_json(SESSIONS_FILE, store)


def read_memory_store() -> Dict[str, Any]:
    return load_json(MEMORY_FILE, memory_file_default())


def write_memory_store(store: Dict[str, Any]) -> None:
    save_json(MEMORY_FILE, store)


def read_usage_store() -> Dict[str, Any]:
    return load_json(USAGE_FILE, usage_file_default())


def write_usage_store(store: Dict[str, Any]) -> None:
    save_json(USAGE_FILE, store)


def bump_usage() -> None:
    with data_lock:
        usage = read_usage_store()
        usage["total_requests"] = int(usage.get("total_requests") or 0) + 1
        usage["last_request_at"] = now_ts()
        write_usage_store(usage)


def list_sessions() -> List[Dict[str, Any]]:
    store = read_sessions_store()
    sessions = store.get("sessions") or []
    sessions.sort(key=lambda x: int(x.get("updated_at") or 0), reverse=True)
    return sessions


def get_current_session_id() -> Optional[str]:
    store = read_sessions_store()
    return store.get("current_session_id")


def set_current_session_id(session_id: Optional[str]) -> None:
    with data_lock:
        store = read_sessions_store()
        store["current_session_id"] = session_id
        write_sessions_store(store)


def make_session_title_from_message(content: str) -> str:
    text = safe_text(content)
    if not text:
        return "New Chat"
    title = re.sub(r"\s+", " ", text).strip()
    return title[:48]


def build_session_summary(session_obj: Dict[str, Any]) -> Dict[str, Any]:
    messages = session_obj.get("messages") or []
    return {
        "id": session_obj.get("id"),
        "title": session_obj.get("title") or "New Chat",
        "message_count": len(messages),
        "created_at": session_obj.get("created_at"),
        "updated_at": session_obj.get("updated_at"),
    }


def create_session(title: str = "New Chat") -> Dict[str, Any]:
    ts = now_ts()
    session_obj = {
        "id": str(uuid.uuid4()),
        "title": slugify_title(title),
        "messages": [],
        "created_at": ts,
        "updated_at": ts,
    }

    with data_lock:
        store = read_sessions_store()
        sessions = store.get("sessions") or []
        sessions.insert(0, session_obj)
        store["sessions"] = sessions
        store["current_session_id"] = session_obj["id"]
        write_sessions_store(store)

        usage = read_usage_store()
        usage["total_sessions"] = int(usage.get("total_sessions") or 0) + 1
        write_usage_store(usage)

    return session_obj


def find_session(session_id: str) -> Optional[Dict[str, Any]]:
    store = read_sessions_store()
    for item in store.get("sessions") or []:
        if item.get("id") == session_id:
            return item
    return None


def update_session(session_id: str, updater) -> Optional[Dict[str, Any]]:
    with data_lock:
        store = read_sessions_store()
        sessions = store.get("sessions") or []
        found = None

        for index, item in enumerate(sessions):
            if item.get("id") == session_id:
                found = dict(item)
                updater(found)
                found["updated_at"] = now_ts()
                sessions[index] = found
                break

        if found is None:
            return None

        sessions.sort(key=lambda x: int(x.get("updated_at") or 0), reverse=True)
        store["sessions"] = sessions
        if not store.get("current_session_id"):
            store["current_session_id"] = session_id
        write_sessions_store(store)
        return found


def add_message_to_session(session_id: str, role: str, content: str, router: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    def _updater(session_obj: Dict[str, Any]) -> None:
        session_obj.setdefault("messages", []).append({
            "id": str(uuid.uuid4()),
            "role": safe_text(role or "assistant"),
            "content": str(content or ""),
            "timestamp": now_ts(),
            "router": router or None,
        })

        if len(session_obj["messages"]) == 1 and safe_text(content):
            session_obj["title"] = make_session_title_from_message(content)

    return update_session(session_id, _updater)


def get_memory_items() -> List[Dict[str, Any]]:
    store = read_memory_store()
    items = store.get("memory") or []
    items.sort(key=lambda x: int(x.get("updated_at") or x.get("created_at") or 0), reverse=True)
    return items


def add_memory_item(kind: str, value: str) -> Dict[str, Any]:
    ts = now_ts()
    item = {
        "id": str(uuid.uuid4()),
        "kind": safe_text(kind or "memory") or "memory",
        "value": safe_text(value),
        "created_at": ts,
        "updated_at": ts,
    }

    with data_lock:
        store = read_memory_store()
        items = store.get("memory") or []

        dedupe_key = item["value"].strip().lower()
        existing_index = None
        for idx, existing in enumerate(items):
            if safe_text(existing.get("value")).strip().lower() == dedupe_key:
                existing_index = idx
                break

        if existing_index is not None:
            items[existing_index]["kind"] = item["kind"]
            items[existing_index]["value"] = item["value"]
            items[existing_index]["updated_at"] = ts
            item = items[existing_index]
        else:
            items.insert(0, item)

        store["memory"] = items
        write_memory_store(store)

    return item


def delete_memory_item(memory_id: str) -> bool:
    with data_lock:
        store = read_memory_store()
        items = store.get("memory") or []
        before = len(items)
        items = [x for x in items if x.get("id") != memory_id]
        store["memory"] = items
        write_memory_store(store)
        return len(items) != before


def guess_route(content: str, memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = safe_text(content).lower()

    mode = "general"
    intent = "chat"
    reason = "default"

    coding_words = [
        "code", "bug", "fix", "javascript", "python", "flask", "html",
        "css", "json", "api", "smff", "full file", "app.py", ".js", ".css", ".html"
    ]
    planning_words = ["plan", "roadmap", "steps", "checklist", "strategy", "next"]
    writing_words = ["write", "rewrite", "email", "story", "book", "blog", "caption"]
    analysis_words = ["analyze", "why", "debug", "issue", "problem", "compare", "review"]

    if any(word in text for word in coding_words):
        mode = "coding"
        intent = "build"
        reason = "matched coding keywords"
    elif any(word in text for word in planning_words):
        mode = "planning"
        intent = "organize"
        reason = "matched planning keywords"
    elif any(word in text for word in writing_words):
        mode = "writing"
        intent = "compose"
        reason = "matched writing keywords"
    elif any(word in text for word in analysis_words):
        mode = "analysis"
        intent = "analyze"
        reason = "matched analysis keywords"

    memory_hits: List[str] = []
    lowered = text

    for item in memory_items:
        val = safe_text(item.get("value"))
        if not val:
            continue

        words = [w for w in re.split(r"[\s,.;:!?()\[\]{}]+", val.lower()) if len(w) >= 4]
        if not words:
            continue

        overlap = sum(1 for w in set(words[:8]) if w in lowered)
        if overlap > 0:
            memory_hits.append(val)

        if len(memory_hits) >= MAX_MEMORY_USED:
            break

    return {
        "mode": mode,
        "intent": intent,
        "reason": reason,
        "memory_hits": len(memory_hits),
        "memory_preview": memory_hits[:MAX_MEMORY_USED],
        "timestamp": now_ts(),
    }


def build_messages_for_model(
    session_messages: List[Dict[str, Any]],
    user_content: str,
    uploaded_files: List[Dict[str, Any]],
    router: Dict[str, Any],
) -> List[Dict[str, str]]:
    system_parts: List[str] = [
        "You are Nova, a direct, fast, highly useful AI assistant.",
        "Be concise, solution-first, and practical.",
        "When the user asks for code, prefer full-file style.",
        f"Current route mode: {router.get('mode', 'general')}.",
        f"Current route intent: {router.get('intent', 'chat')}.",
    ]

    memory_preview = router.get("memory_preview") or []
    if memory_preview:
        system_parts.append("Relevant memory:\n- " + "\n- ".join(memory_preview))

    if uploaded_files:
        file_lines = []
        for file_info in uploaded_files[:MAX_UPLOAD_FILES]:
            name = safe_text(file_info.get("name"))
            path = safe_text(file_info.get("path"))
            snippet = safe_text(file_info.get("text_snippet"))
            file_lines.append(f"File: {name}\nPath: {path}\nSnippet:\n{snippet[:4000]}")
        system_parts.append("Uploaded file context:\n\n" + "\n\n".join(file_lines))

    trimmed_history = session_messages[-MAX_MODEL_MESSAGES:]
    messages: List[Dict[str, str]] = [{"role": "system", "content": "\n\n".join(system_parts)}]

    for msg in trimmed_history:
        role = safe_text(msg.get("role")).lower()
        if role not in {"user", "assistant", "system"}:
            continue
        content = str(msg.get("content") or "")
        if content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_content})
    return messages


def fallback_response(user_content: str, router: Dict[str, Any]) -> str:
    mode = router.get("mode") or "general"
    if mode == "coding":
        return (
            "Nova backend is running, but no OpenAI API key is configured.\n\n"
            "Set OPENAI_API_KEY in your environment to enable model responses.\n\n"
            "Your routing, session storage, memory, uploads, and streaming are still working."
        )
    return (
        "Nova backend is running, but no OpenAI API key is configured. "
        "Set OPENAI_API_KEY to enable model responses."
    )


def stream_model_text(messages: List[Dict[str, str]]) -> Tuple[str, List[str]]:
    if client is None:
        text = fallback_response(messages[-1]["content"], {"mode": "general"})
        return text, [text]

    collected_chunks: List[str] = []
    full_text_parts: List[str] = []

    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.4,
        stream=True,
    )

    for chunk in stream:
        try:
            delta = chunk.choices[0].delta
            piece = getattr(delta, "content", None)
        except Exception:
            piece = None

        if not piece:
            continue

        full_text_parts.append(piece)
        collected_chunks.append(piece)

    return "".join(full_text_parts), collected_chunks


def normalize_uploaded_files(raw_files: Any) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for item in raw_files or []:
        if not isinstance(item, dict):
            continue

        path_value = safe_text(item.get("path"))
        file_path = Path(path_value) if path_value else None

        snippet = ""
        if file_path and file_path.exists() and file_path.is_file():
            try:
                snippet = file_path.read_text(encoding="utf-8", errors="ignore")[:12000]
            except Exception:
                snippet = ""

        output.append({
            "name": safe_text(item.get("name")),
            "size": item.get("size") or 0,
            "path": path_value,
            "text_snippet": snippet,
        })

    return output


def public_session_payload(session_obj: Dict[str, Any]) -> Dict[str, Any]:
    messages = session_obj.get("messages") or []
    return {
        "session": build_session_summary(session_obj),
        "session_id": session_obj.get("id"),
        "messages": messages,
    }


@app.before_request
def auth_gate():
    allowed = {
        "login",
        "logout",
        "static",
    }

    if request.endpoint in allowed:
        return None

    if request.path.startswith("/static/"):
        return None

    if require_login():
        return None

    if request.path.startswith("/api/"):
        return jsonify({"error": "Unauthorized"}), 401

    return redirect(url_for("login", next=request.path))


@app.get("/login")
def login():
    if require_login():
        return redirect(url_for("home"))
    return render_template("login.html", next=request.args.get("next", "/"))


@app.post("/login")
def login_post():
    if not APP_PASSWORD:
        return redirect(url_for("home"))

    password = safe_text(request.form.get("password"))
    next_url = safe_text(request.form.get("next")) or "/"

    if password == APP_PASSWORD:
        session["nova_logged_in"] = True
        return redirect(next_url)

    return render_template("login.html", error="Wrong password", next=next_url), 401


@app.get("/logout")
def logout():
    session.pop("nova_logged_in", None)
    return redirect(url_for("login"))


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    sessions = [build_session_summary(s) for s in list_sessions()]
    current_session_id = get_current_session_id()

    if not current_session_id and sessions:
        current_session_id = sessions[0]["id"]
        set_current_session_id(current_session_id)

    return jsonify({
        "sessions": sessions,
        "current_session_id": current_session_id,
        "model": OPENAI_MODEL,
    })


@app.post("/api/session/new")
def api_new_session():
    session_obj = create_session("New Chat")
    return jsonify({
        "session": build_session_summary(session_obj),
        "session_id": session_obj["id"],
    })


@app.get("/api/chat/<session_id>")
def api_get_chat(session_id: str):
    session_obj = find_session(session_id)
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404

    set_current_session_id(session_id)
    return jsonify(public_session_payload(session_obj))


@app.post("/api/session/delete")
def api_delete_session():
    payload = request.get_json(silent=True) or {}
    session_id = safe_text(payload.get("session_id") or payload.get("id"))
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    with data_lock:
        store = read_sessions_store()
        sessions = store.get("sessions") or []
        before = len(sessions)
        sessions = [s for s in sessions if s.get("id") != session_id]
        if len(sessions) == before:
            return jsonify({"error": "Session not found"}), 404

        store["sessions"] = sessions
        current_id = store.get("current_session_id")
        if current_id == session_id:
            store["current_session_id"] = sessions[0]["id"] if sessions else None
        write_sessions_store(store)

    return jsonify({
        "ok": True,
        "current_session_id": get_current_session_id(),
    })


@app.post("/api/session/rename")
def api_rename_session():
    payload = request.get_json(silent=True) or {}
    session_id = safe_text(payload.get("session_id") or payload.get("id"))
    title = slugify_title(payload.get("title"))

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    updated = update_session(session_id, lambda s: s.update({"title": title or "New Chat"}))
    if not updated:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "ok": True,
        "session": build_session_summary(updated),
    })


@app.post("/api/session/duplicate")
def api_duplicate_session():
    payload = request.get_json(silent=True) or {}
    session_id = safe_text(payload.get("session_id") or payload.get("id"))
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    original = find_session(session_id)
    if not original:
        return jsonify({"error": "Session not found"}), 404

    ts = now_ts()
    duplicated = {
        "id": str(uuid.uuid4()),
        "title": f"{safe_text(original.get('title') or 'New Chat')} Copy",
        "messages": list(original.get("messages") or []),
        "created_at": ts,
        "updated_at": ts,
    }

    with data_lock:
        store = read_sessions_store()
        sessions = store.get("sessions") or []
        sessions.insert(0, duplicated)
        store["sessions"] = sessions
        store["current_session_id"] = duplicated["id"]
        write_sessions_store(store)

    return jsonify({
        "ok": True,
        "session": build_session_summary(duplicated),
        "session_id": duplicated["id"],
    })


@app.get("/api/memory")
def api_get_memory():
    return jsonify({"memory": get_memory_items()})


@app.post("/api/memory")
def api_add_memory():
    payload = request.get_json(silent=True) or {}
    kind = safe_text(payload.get("kind") or "memory")
    value = safe_text(payload.get("value"))

    if not value:
        return jsonify({"error": "Missing memory value"}), 400

    item = add_memory_item(kind, value)
    return jsonify({"ok": True, "item": item, "memory": get_memory_items()})


@app.post("/api/memory/delete")
def api_delete_memory():
    payload = request.get_json(silent=True) or {}
    memory_id = safe_text(payload.get("id"))
    if not memory_id:
        return jsonify({"error": "Missing memory id"}), 400

    ok = delete_memory_item(memory_id)
    if not ok:
        return jsonify({"error": "Memory not found"}), 404

    return jsonify({"ok": True, "memory": get_memory_items()})


@app.post("/api/upload")
def api_upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"files": []})

    uploaded: List[Dict[str, Any]] = []

    for file_storage in files[:MAX_UPLOAD_FILES]:
        original_name = safe_text(file_storage.filename) or "upload.bin"
        ext = Path(original_name).suffix
        saved_name = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOAD_DIR / saved_name
        file_storage.save(save_path)

        uploaded.append({
            "name": original_name,
            "size": save_path.stat().st_size if save_path.exists() else 0,
            "path": str(save_path),
        })

    return jsonify({"files": uploaded})


@app.post("/api/chat/stream")
def api_chat_stream():
    payload = request.get_json(silent=True) or {}
    session_id = safe_text(payload.get("session_id"))
    content = str(payload.get("content") or "")
    model = safe_text(payload.get("model") or OPENAI_MODEL)
    uploaded_files = normalize_uploaded_files(payload.get("uploaded_files") or [])

    if not session_id:
        created = create_session("New Chat")
        session_id = created["id"]

    session_obj = find_session(session_id)
    if not session_obj:
        session_obj = create_session("New Chat")
        session_id = session_obj["id"]

    if not safe_text(content) and not uploaded_files:
        return jsonify({"error": "Missing content"}), 400

    set_current_session_id(session_id)
    bump_usage()

    memory_items = get_memory_items()
    router = guess_route(content, memory_items)

    def generate():
        user_label = content if safe_text(content) else f"[Uploaded {len(uploaded_files)} file(s)]"
        add_message_to_session(session_id, "user", user_label)

        yield sse_event("start", {
            "ok": True,
            "session_id": session_id,
            "router": router,
            "model": model,
        })

        try:
            fresh_session = find_session(session_id) or {}
            session_messages = list(fresh_session.get("messages") or [])

            model_messages = build_messages_for_model(
                session_messages=session_messages[:-1],
                user_content=content if safe_text(content) else user_label,
                uploaded_files=uploaded_files,
                router=router,
            )

            if client is None:
                final_text = fallback_response(content, router)
                yield sse_event("token", {"delta": final_text})
            else:
                stream = client.chat.completions.create(
                    model=model or OPENAI_MODEL,
                    messages=model_messages,
                    temperature=0.4,
                    stream=True,
                )

                final_parts: List[str] = []
                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta
                        piece = getattr(delta, "content", None)
                    except Exception:
                        piece = None

                    if not piece:
                        continue

                    final_parts.append(piece)
                    yield sse_event("token", {"delta": piece})

                final_text = "".join(final_parts).strip()

                if not final_text:
                    final_text = "I’m here."

            add_message_to_session(session_id, "assistant", final_text, router=router)

            yield sse_event("done", {
                "ok": True,
                "session_id": session_id,
                "router": router,
                "message": final_text,
            })

        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            add_message_to_session(
                session_id,
                "assistant",
                "Something went wrong while generating that response.",
                router={
                    "mode": "general",
                    "intent": "error",
                    "reason": error_text,
                    "memory_hits": 0,
                    "memory_preview": [],
                    "timestamp": now_ts(),
                },
            )
            yield sse_event("error", {
                "ok": False,
                "message": error_text,
            })

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    ensure_file(SESSIONS_FILE, sessions_file_default())
    ensure_file(MEMORY_FILE, memory_file_default())
    ensure_file(USAGE_FILE, usage_file_default())
    app.run(host=APP_HOST, port=APP_PORT, debug=True)