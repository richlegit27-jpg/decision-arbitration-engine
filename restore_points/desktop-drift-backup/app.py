from __future__ import annotations

from pathlib import Path
import copy
import json
import os
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
USAGE_FILE = DATA_DIR / "nova_usage.json"

DATA_LOCK = Lock()

DEFAULT_MODEL = "gpt-4.1-mini"


def utc_ts() -> int:
    return int(time.time())


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_store() -> Dict[str, Any]:
    default_store = {
        "active_session_id": None,
        "current_model": DEFAULT_MODEL,
        "route_meta": {
            "route": "general",
            "reason": "default route",
            "memory_scope": "general",
            "model": DEFAULT_MODEL,
        },
        "sessions": [],
    }

    store = read_json(SESSIONS_FILE, default_store)

    if not isinstance(store, dict):
        store = copy.deepcopy(default_store)

    store.setdefault("active_session_id", None)
    store.setdefault("current_model", DEFAULT_MODEL)
    store.setdefault("route_meta", {})
    store.setdefault("sessions", [])

    if not isinstance(store["sessions"], list):
        store["sessions"] = []

    normalized_sessions: List[Dict[str, Any]] = []
    for raw in store["sessions"]:
        if not isinstance(raw, dict):
            continue

        session_id = str(raw.get("id") or raw.get("session_id") or uuid.uuid4().hex)
        created_at = int(raw.get("created_at") or utc_ts())
        updated_at = int(raw.get("updated_at") or created_at)

        normalized_messages: List[Dict[str, Any]] = []
        for msg in raw.get("messages", []):
            if not isinstance(msg, dict):
                continue
            normalized_messages.append(
                {
                    "id": str(msg.get("id") or uuid.uuid4().hex),
                    "role": str(msg.get("role") or "assistant"),
                    "content": str(msg.get("content") or ""),
                    "created_at": int(msg.get("created_at") or updated_at),
                }
            )

        normalized_sessions.append(
            {
                "id": session_id,
                "title": str(raw.get("title") or "Untitled Chat"),
                "pinned": bool(raw.get("pinned", False)),
                "created_at": created_at,
                "updated_at": updated_at,
                "messages": normalized_messages,
                "route_meta": {
                    "route": str(raw.get("route_meta", {}).get("route") or store["route_meta"].get("route") or "general"),
                    "reason": str(raw.get("route_meta", {}).get("reason") or store["route_meta"].get("reason") or "default route"),
                    "memory_scope": str(
                        raw.get("route_meta", {}).get("memory_scope")
                        or store["route_meta"].get("memory_scope")
                        or "general"
                    ),
                    "model": str(raw.get("route_meta", {}).get("model") or store["current_model"] or DEFAULT_MODEL),
                },
            }
        )

    store["sessions"] = normalized_sessions

    if not store["active_session_id"] and store["sessions"]:
        store["active_session_id"] = store["sessions"][0]["id"]

    active_id = store["active_session_id"]
    if active_id and not any(s["id"] == active_id for s in store["sessions"]):
        store["active_session_id"] = store["sessions"][0]["id"] if store["sessions"] else None

    if not MEMORY_FILE.exists():
        write_json(MEMORY_FILE, [])

    if not USAGE_FILE.exists():
        write_json(USAGE_FILE, {"started_at": utc_ts(), "message_count": 0})

    write_json(SESSIONS_FILE, store)
    return store


def read_store() -> Dict[str, Any]:
    with DATA_LOCK:
        return ensure_store()


def save_store(store: Dict[str, Any]) -> None:
    with DATA_LOCK:
        write_json(SESSIONS_FILE, store)


def read_memory_items() -> List[Dict[str, Any]]:
    with DATA_LOCK:
        items = read_json(MEMORY_FILE, [])
        if not isinstance(items, list):
            items = []

        normalized: List[Dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            normalized.append(
                {
                    "id": str(raw.get("id") or uuid.uuid4().hex),
                    "kind": str(raw.get("kind") or "memory"),
                    "value": str(raw.get("value") or ""),
                    "created_at": int(raw.get("created_at") or utc_ts()),
                }
            )

        write_json(MEMORY_FILE, normalized)
        return normalized


def save_memory_items(items: List[Dict[str, Any]]) -> None:
    with DATA_LOCK:
        write_json(MEMORY_FILE, items)


def bump_usage() -> None:
    with DATA_LOCK:
        usage = read_json(USAGE_FILE, {"started_at": utc_ts(), "message_count": 0})
        if not isinstance(usage, dict):
            usage = {"started_at": utc_ts(), "message_count": 0}
        usage["message_count"] = int(usage.get("message_count") or 0) + 1
        usage["last_message_at"] = utc_ts()
        write_json(USAGE_FILE, usage)


def summarize_title(message: str) -> str:
    text = " ".join(str(message or "").strip().split())
    if not text:
        return "Untitled Chat"
    if len(text) <= 48:
        return text
    return text[:45].rstrip() + "..."


def make_route_meta(message: str, model: Optional[str]) -> Dict[str, str]:
    text = str(message or "").lower()

    route = "general"
    reason = "default route"
    memory_scope = "general"

    coding_terms = [
        "code",
        "python",
        "javascript",
        "js",
        "css",
        "html",
        "flask",
        "bug",
        "error",
        "traceback",
        "fix",
        "smff",
        "app.py",
    ]
    planning_terms = ["plan", "roadmap", "next step", "phase", "milestone", "strategy"]
    writing_terms = ["write", "draft", "email", "book", "rewrite", "story"]
    analysis_terms = ["analyze", "why", "compare", "breakdown", "diagnose", "root cause"]

    if any(term in text for term in coding_terms):
        route = "coding"
        reason = "matched code/debug keywords"
        memory_scope = "project"
    elif any(term in text for term in planning_terms):
        route = "planning"
        reason = "matched planning keywords"
        memory_scope = "project"
    elif any(term in text for term in writing_terms):
        route = "writing"
        reason = "matched writing keywords"
        memory_scope = "writing"
    elif any(term in text for term in analysis_terms):
        route = "analysis"
        reason = "matched analysis keywords"
        memory_scope = "project"

    return {
        "route": route,
        "reason": reason,
        "memory_scope": memory_scope,
        "model": model or DEFAULT_MODEL,
    }


def find_session(store: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    for session in store.get("sessions", []):
        if session.get("id") == session_id:
            return session
    return None


def create_session_record(title: str = "New Chat") -> Dict[str, Any]:
    now = utc_ts()
    return {
        "id": uuid.uuid4().hex,
        "title": title,
        "pinned": False,
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "route_meta": {
            "route": "general",
            "reason": "new chat created",
            "memory_scope": "general",
            "model": DEFAULT_MODEL,
        },
    }


def local_reply(message: str, route_meta: Dict[str, str]) -> str:
    clean = str(message or "").strip()
    route = route_meta.get("route", "general")

    if not clean:
        return "I didn’t receive a message."

    if route == "coding":
        return (
            "Desktop sync restore is active.\n\n"
            f"You said: {clean}\n\n"
            "The backend and frontend contract is now wired locally. "
            "If something is still broken, the next move is to target the exact failing file and endpoint."
        )

    if route == "planning":
        return (
            "Plan locked.\n\n"
            f"Focus item: {clean}\n\n"
            "Next move should be one concrete pass at a time so you can verify what changed."
        )

    if route == "writing":
        return (
            "Writing mode detected.\n\n"
            f"Topic: {clean}\n\n"
            "Give me the exact draft target and I’ll structure it directly."
        )

    if route == "analysis":
        return (
            "Analysis mode detected.\n\n"
            f"Subject: {clean}\n\n"
            "The visible shell suggests the UI is alive; remaining failures usually come from state shape mismatches or dead event bindings."
        )

    return (
        "Nova local reply online.\n\n"
        f"You said: {clean}\n\n"
        "The desktop restore is running on the synced local backend now."
    )


app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)


@app.after_request
def add_no_cache_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/mobile")
def mobile() -> str:
    mobile_path = TEMPLATES_DIR / "mobile.html"
    if mobile_path.exists():
        return render_template("mobile.html")
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


@app.route("/api/state", methods=["GET"])
def api_state():
    store = read_store()

    sessions = [
        {
            "id": session["id"],
            "title": session["title"],
            "pinned": session["pinned"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
        }
        for session in sorted(
            store["sessions"],
            key=lambda s: (not bool(s.get("pinned")), -int(s.get("updated_at") or 0)),
        )
    ]

    return jsonify(
        {
            "sessions": sessions,
            "active_session_id": store.get("active_session_id"),
            "current_model": store.get("current_model", DEFAULT_MODEL),
            "route_meta": store.get("route_meta", {}),
        }
    )


@app.route("/api/chat/<session_id>", methods=["GET"])
def api_chat_session(session_id: str):
    store = read_store()
    session = find_session(store, session_id)

    if not session:
        return jsonify({"messages": [], "route_meta": store.get("route_meta", {})}), 200

    return jsonify(
        {
            "session_id": session["id"],
            "messages": session.get("messages", []),
            "route_meta": session.get("route_meta", store.get("route_meta", {})),
        }
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    store = read_store()

    session_id = str(payload.get("session_id") or store.get("active_session_id") or "")
    message = str(payload.get("message") or "").strip()
    model = str(payload.get("model") or store.get("current_model") or DEFAULT_MODEL)

    if not message:
        return jsonify({"error": "Message is required."}), 400

    session = find_session(store, session_id)
    if not session:
        session = create_session_record()
        store["sessions"].insert(0, session)
        store["active_session_id"] = session["id"]
        session_id = session["id"]

    now = utc_ts()
    route_meta = make_route_meta(message, model)

    user_message = {
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": message,
        "created_at": now,
    }
    assistant_text = local_reply(message, route_meta)
    assistant_message = {
        "id": uuid.uuid4().hex,
        "role": "assistant",
        "content": assistant_text,
        "created_at": now,
    }

    session["messages"].append(user_message)
    session["messages"].append(assistant_message)

    if session["title"] in ("New Chat", "Untitled Chat") and message:
        session["title"] = summarize_title(message)

    session["updated_at"] = now
    session["route_meta"] = route_meta

    store["active_session_id"] = session["id"]
    store["current_model"] = model
    store["route_meta"] = route_meta
    save_store(store)
    bump_usage()

    return jsonify(
        {
            "session_id": session["id"],
            "answer": assistant_text,
            "content": assistant_text,
            "message": assistant_text,
            "route_meta": route_meta,
        }
    )


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    payload = request.get_json(silent=True) or {}
    store = read_store()

    session_id = str(payload.get("session_id") or store.get("active_session_id") or "")
    message = str(payload.get("message") or "").strip()
    model = str(payload.get("model") or store.get("current_model") or DEFAULT_MODEL)

    if not message:
        return jsonify({"error": "Message is required."}), 400

    session = find_session(store, session_id)
    if not session:
        session = create_session_record()
        store["sessions"].insert(0, session)
        store["active_session_id"] = session["id"]
        session_id = session["id"]

    now = utc_ts()
    route_meta = make_route_meta(message, model)

    user_message = {
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": message,
        "created_at": now,
    }
    assistant_text = local_reply(message, route_meta)
    assistant_message = {
        "id": uuid.uuid4().hex,
        "role": "assistant",
        "content": assistant_text,
        "created_at": now,
    }

    session["messages"].append(user_message)
    session["messages"].append(assistant_message)

    if session["title"] in ("New Chat", "Untitled Chat") and message:
        session["title"] = summarize_title(message)

    session["updated_at"] = now
    session["route_meta"] = route_meta

    store["active_session_id"] = session["id"]
    store["current_model"] = model
    store["route_meta"] = route_meta
    save_store(store)
    bump_usage()

    response_payload = {
        "session_id": session["id"],
        "answer": assistant_text,
        "content": assistant_text,
        "message": assistant_text,
        "route_meta": route_meta,
    }

    return Response(
        json.dumps(response_payload, ensure_ascii=False),
        mimetype="application/json",
    )


@app.route("/api/session/new", methods=["POST"])
def api_session_new():
    store = read_store()
    session = create_session_record(title="New Chat")
    store["sessions"].insert(0, session)
    store["active_session_id"] = session["id"]
    store["route_meta"] = session["route_meta"]
    save_store(store)

    return jsonify(
        {
            "ok": True,
            "session_id": session["id"],
            "session": {
                "id": session["id"],
                "title": session["title"],
                "pinned": session["pinned"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
            },
        }
    )


@app.route("/api/session/rename", methods=["POST"])
def api_session_rename():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()
    title = str(payload.get("title") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    if not title:
        return jsonify({"error": "title is required."}), 400

    store = read_store()
    session = find_session(store, session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    session["title"] = title
    session["updated_at"] = utc_ts()
    save_store(store)

    return jsonify({"ok": True, "session_id": session_id, "title": title})


@app.route("/api/session/duplicate", methods=["POST"])
def api_session_duplicate():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    store = read_store()
    session = find_session(store, session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    now = utc_ts()
    clone = {
        "id": uuid.uuid4().hex,
        "title": f'{session.get("title", "Untitled Chat")} (copy)',
        "pinned": False,
        "created_at": now,
        "updated_at": now,
        "messages": copy.deepcopy(session.get("messages", [])),
        "route_meta": copy.deepcopy(session.get("route_meta", store.get("route_meta", {}))),
    }

    store["sessions"].insert(0, clone)
    store["active_session_id"] = clone["id"]
    store["route_meta"] = clone["route_meta"]
    save_store(store)

    return jsonify(
        {
            "ok": True,
            "session_id": clone["id"],
            "session": {
                "id": clone["id"],
                "title": clone["title"],
                "pinned": clone["pinned"],
                "created_at": clone["created_at"],
                "updated_at": clone["updated_at"],
            },
        }
    )


@app.route("/api/session/delete", methods=["POST"])
def api_session_delete():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    store = read_store()
    before = len(store["sessions"])
    store["sessions"] = [s for s in store["sessions"] if s.get("id") != session_id]

    if len(store["sessions"]) == before:
        return jsonify({"error": "Session not found."}), 404

    if store.get("active_session_id") == session_id:
        store["active_session_id"] = store["sessions"][0]["id"] if store["sessions"] else None

    if store["sessions"]:
        active = find_session(store, store["active_session_id"])
        store["route_meta"] = active.get("route_meta", store.get("route_meta", {})) if active else store.get("route_meta", {})
    else:
        store["route_meta"] = {
            "route": "general",
            "reason": "default route",
            "memory_scope": "general",
            "model": store.get("current_model", DEFAULT_MODEL),
        }

    save_store(store)
    return jsonify({"ok": True, "active_session_id": store.get("active_session_id")})


@app.route("/api/session/pin", methods=["POST"])
def api_session_pin():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    store = read_store()
    session = find_session(store, session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    session["pinned"] = not bool(session.get("pinned"))
    session["updated_at"] = utc_ts()
    save_store(store)

    return jsonify({"ok": True, "session_id": session_id, "pinned": session["pinned"]})


@app.route("/api/memory", methods=["GET", "POST", "DELETE"])
def api_memory():
    if request.method == "GET":
        items = read_memory_items()
        items = sorted(items, key=lambda x: -int(x.get("created_at") or 0))
        return jsonify({"memory": items})

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        kind = str(payload.get("kind") or "memory").strip() or "memory"
        value = str(payload.get("value") or "").strip()

        if not value:
            return jsonify({"error": "value is required."}), 400

        items = read_memory_items()
        item = {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "value": value,
            "created_at": utc_ts(),
        }
        items.insert(0, item)
        save_memory_items(items)
        return jsonify({"ok": True, "item": item})

    payload = request.get_json(silent=True) or {}
    memory_id = str(payload.get("id") or "").strip()

    if not memory_id:
        return jsonify({"error": "id is required."}), 400

    items = read_memory_items()
    new_items = [item for item in items if item.get("id") != memory_id]

    if len(new_items) == len(items):
        return jsonify({"error": "Memory item not found."}), 404

    save_memory_items(new_items)
    return jsonify({"ok": True})


@app.route("/static/<path:filename>")
def serve_static(filename: str):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    ensure_store()
    host = os.environ.get("NOVA_HOST", "0.0.0.0")
    port = int(os.environ.get("NOVA_PORT", "5001"))
    debug = os.environ.get("NOVA_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)