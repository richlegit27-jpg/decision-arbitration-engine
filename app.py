# C:\Users\Owner\nova\app.py

from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
)

from openai import OpenAI

from auth_utils import (
    DEV_BYPASS_AUTH,
    authenticate_user,
    create_user,
    current_user,
    login_user,
    logout_user,
    normalize_username,
    protect_routes as auth_protect_routes,
    require_page_auth,
)
from routes_agent import agent_bp
from routes_chat import chat_bp
from routes_memory import memory_bp
from routes_sessions import sessions_bp
from services_ai import (
    autonomous_loop_refine as ai_autonomous_loop_refine,
    call_model as ai_call_model,
)
from services_web import (
    is_web as web_is_web,
    search_web_for_query,
    wants_web_search,
)
from storage import (
    load_memory,
    load_sessions,
    load_users,
    save_memory as storage_save_memory,
    save_sessions as storage_save_sessions,
    save_users as storage_save_users,
)

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.register_blueprint(sessions_bp)
app.register_blueprint(memory_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(agent_bp)

# =========================================================
# CONFIG
# =========================================================

DEFAULT_MODEL = (os.getenv("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY", "") or "").strip()
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# =========================================================
# STATE
# =========================================================

LAST_ROUTER_META: dict[str, Any] = {
    "mode": "general",
    "intent": "default",
    "confidence": 1.0,
}

STATE_LOCK = threading.RLock()

AGENT_STATE: dict[str, Any] = {
    "enabled": False,
    "interval_seconds": 20,
    "last_tick_at": None,
    "last_error": "",
    "last_summary": "",
    "thread_started": False,
}

USERS: dict[str, dict[str, Any]] = load_users()
MEMORY_ITEMS: list[dict[str, Any]] = load_memory()
SESSIONS: dict[str, dict[str, Any]] = load_sessions()

# =========================================================
# UTILS
# =========================================================

def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def save_users() -> None:
    storage_save_users(USERS)


def save_memory() -> None:
    storage_save_memory(MEMORY_ITEMS)


def save_sessions() -> None:
    storage_save_sessions(SESSIONS)


# =========================================================
# AUTH WRAPPER
# =========================================================

@app.before_request
def protect_routes():
    return auth_protect_routes(USERS)


# =========================================================
# MEMORY HELPERS
# =========================================================

def get_user_memory_items(username: str) -> list[dict[str, Any]]:
    username = normalize_username(username)
    return [item for item in MEMORY_ITEMS if normalize_username(str(item.get("user", ""))) == username]


def extract_memory(text: str) -> dict[str, Any] | None:
    raw = clean_text(text)
    lowered = raw.lower()

    triggers = [
        "my name is",
        "i am",
        "i like",
        "i want",
        "my goal is",
        "i prefer",
    ]

    if any(t in lowered for t in triggers):
        return {
            "id": str(uuid.uuid4()),
            "value": raw[:200],
            "kind": "memory",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    return None


def get_relevant_memory(username: str, user_text: str) -> list[dict[str, Any]]:
    text = clean_text(user_text).lower()
    user_items = get_user_memory_items(username)

    scored: list[tuple[int, dict[str, Any]]] = []

    for item in user_items:
        value = str(item.get("value", "")).lower()
        score = sum(1 for word in text.split() if word and word in value)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:3]]


# =========================================================
# HELPERS
# =========================================================

def ensure_session(session_id: str | None, username: str) -> str:
    sid = clean_text(session_id) or str(uuid.uuid4())
    username = normalize_username(username or "dev")

    with STATE_LOCK:
        if sid not in SESSIONS:
            SESSIONS[sid] = {
                "id": sid,
                "user": username,
                "title": "New Chat",
                "messages": [],
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "router_meta": dict(LAST_ROUTER_META),
                "last_web_results": [],
                "agent_enabled": False,
                "agent_goal": "",
                "agent_status": "idle",
                "agent_last_run_at": None,
                "agent_last_output": "",
                "pinned": False,
            }
            save_sessions()
        else:
            owner = normalize_username(str(SESSIONS[sid].get("user", "")))
            if owner != username and not DEV_BYPASS_AUTH:
                raise PermissionError("Session does not belong to current user.")

    return sid


def get_user_sessions(username: str) -> list[dict[str, Any]]:
    username = normalize_username(username or "dev")
    with STATE_LOCK:
        if DEV_BYPASS_AUTH and username == "dev":
            items = list(SESSIONS.values())
        else:
            items = [s for s in SESSIONS.values() if normalize_username(str(s.get("user", ""))) == username]
    items.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
    return items


def get_owned_session_or_404(session_id: str, username: str) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    with STATE_LOCK:
        session_obj = SESSIONS.get(session_id)

    if not session_obj:
        return None, (jsonify({"ok": False, "error": "Session not found"}), 404)

    if DEV_BYPASS_AUTH:
        return session_obj, None

    owner = normalize_username(str(session_obj.get("user", "")))
    if owner != normalize_username(username or ""):
        return None, (jsonify({"ok": False, "error": "Forbidden"}), 403)

    return session_obj, None


def add_message(
    session_id: str,
    role: str,
    content: str,
    web_results: list[dict[str, Any]] | None = None,
    web_provider: str = "",
) -> dict[str, Any]:
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": int(time.time()),
        "web_results": web_results or [],
        "web_provider": web_provider or "",
    }

    with STATE_LOCK:
        session_obj = SESSIONS.get(session_id)
        if not session_obj:
            raise KeyError(f"Session not found: {session_id}")

        session_obj.setdefault("messages", []).append(message)
        session_obj["updated_at"] = now_iso()

        if session_obj.get("title") in ("", "New Chat") and role == "user" and content.strip():
            session_obj["title"] = content.strip()[:60]

        if web_results is not None:
            session_obj["last_web_results"] = web_results

        save_sessions()

    return message


# =========================================================
# WEB / MODEL WRAPPERS
# =========================================================

def is_web() -> bool:
    return web_is_web(TAVILY_API_KEY)


def call_model(text: str, context: str = "") -> str:
    return ai_call_model(
        text=text,
        context=context,
        openai_client=OPENAI_CLIENT,
        default_model=DEFAULT_MODEL,
    )


def autonomous_loop_refine(user_text: str, base_answer: str, context: str = "") -> str:
    return ai_autonomous_loop_refine(
        user_text=user_text,
        base_answer=base_answer,
        context=context,
        call_model_func=call_model,
    )


# =========================================================
# INTELLIGENCE
# =========================================================

def generate_reply(username: str, user_text: str, session_id: str) -> tuple[str, list[dict[str, Any]], str]:
    final_results: list[dict[str, Any]] = []
    provider = ""

    if wants_web_search(user_text):
        final_results, provider = search_web_for_query(user_text, TAVILY_API_KEY)

    with STATE_LOCK:
        if session_id in SESSIONS:
            SESSIONS[session_id]["last_web_results"] = final_results
            save_sessions()

    memory_items = get_relevant_memory(username, user_text)
    memory_context = "\n".join(
        f"- {m.get('value', '')}" for m in memory_items if m.get("value")
    ).strip()

    web_context = ""
    if final_results:
        parts: list[str] = []
        for idx, item in enumerate(final_results, start=1):
            title = clean_text(item.get("title"))
            url = clean_text(item.get("url"))
            snippet = clean_text(item.get("snippet"))

            parts.append(f"[{idx}] {title}")
            if url:
                parts.append(f"URL: {url}")
            if snippet:
                parts.append(f"Snippet: {snippet}")
            parts.append("")

        web_context = "\n".join(parts).strip()

    context_parts = [
        "You are Nova, a direct, no-BS AI assistant.",
        "You speak clearly, directly, and naturally.",
        "You do not write like a news article.",
        "You do not use citation numbering like [1] [2] in your final answer.",
        "When web results exist, use them to improve accuracy, but rewrite naturally.",
        "Keep answers tight, sharp, readable, and useful.",
    ]

    if memory_context:
        context_parts.append("Relevant user memory:\n" + memory_context)

    if web_context:
        context_parts.append(
            "Use these web results when relevant. Prefer them over guessing.\n\n" + web_context
        )

    context = "\n\n".join(context_parts).strip()

    try:
        reply_text = clean_text(call_model(user_text, context))
    except Exception as e:
        if final_results:
            bullets: list[str] = []
            for item in final_results:
                title = clean_text(item.get("title"))
                snippet = clean_text(item.get("snippet"))
                if title and snippet:
                    bullets.append(f"- {title}: {snippet}")
                elif title:
                    bullets.append(f"- {title}")

            reply_text = "Here are the strongest results I found:\n\n" + "\n".join(bullets[:5]).strip()
        else:
            reply_text = f"Error generating reply: {e}"

    if not reply_text:
        if final_results:
            bullets = []
            for item in final_results:
                title = clean_text(item.get("title"))
                snippet = clean_text(item.get("snippet"))
                if title and snippet:
                    bullets.append(f"- {title}: {snippet}")
                elif title:
                    bullets.append(f"- {title}")
            reply_text = "Here are the strongest results I found:\n\n" + "\n".join(bullets[:5]).strip()
        else:
            reply_text = "I couldn't generate a response."

    return reply_text, final_results, provider


# =========================================================
# BACKGROUND AGENT HELPERS
# =========================================================

def agent_brain_prompt(session_obj: dict[str, Any], username: str) -> str:
    goal = str(session_obj.get("agent_goal") or "").strip()
    if not goal:
        return ""

    messages = session_obj.get("messages", [])[-8:]
    transcript_lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", "") or "")
        transcript_lines.append(f"{role.upper()}: {content}")

    transcript = "\n".join(transcript_lines).strip()
    memory_items = get_relevant_memory(username, goal)
    memory_context = "\n".join(f"- {m.get('value', '')}" for m in memory_items if m.get("value"))

    return f"""
You are Nova running in autonomous background agent mode for this one session.

Your job:
- Continue working on the user's goal without asking follow-up questions
- Make one useful incremental step only
- Be concise
- If there is nothing useful to add right now, return exactly: NO_UPDATE

Current goal:
{goal}

Relevant memory:
{memory_context}

Recent session context:
{transcript}
""".strip()


def run_agent_step_for_session(session_id: str) -> str:
    with STATE_LOCK:
        session_obj = SESSIONS.get(session_id)
        if not session_obj:
            return ""
        if not session_obj.get("agent_enabled"):
            return ""
        goal = str(session_obj.get("agent_goal") or "").strip()
        if not goal:
            session_obj["agent_status"] = "idle"
            save_sessions()
            return ""

        username = normalize_username(str(session_obj.get("user", "")))
        session_obj["agent_status"] = "running"
        save_sessions()

    prompt = agent_brain_prompt(session_obj, username)
    if not prompt:
        with STATE_LOCK:
            if session_id in SESSIONS:
                SESSIONS[session_id]["agent_status"] = "idle"
                save_sessions()
        return ""

    try:
        draft = call_model(prompt)
        if not draft or draft.strip() == "NO_UPDATE":
            with STATE_LOCK:
                if session_id in SESSIONS:
                    SESSIONS[session_id]["agent_status"] = "idle"
                    SESSIONS[session_id]["agent_last_run_at"] = now_iso()
                    SESSIONS[session_id]["agent_last_output"] = ""
                    save_sessions()
            return ""

        improved = autonomous_loop_refine(goal, draft, "")
        add_message(session_id, "assistant", improved)

        with STATE_LOCK:
            if session_id in SESSIONS:
                SESSIONS[session_id]["agent_status"] = "idle"
                SESSIONS[session_id]["agent_last_run_at"] = now_iso()
                SESSIONS[session_id]["agent_last_output"] = improved
                save_sessions()

        return improved

    except Exception as exc:
        with STATE_LOCK:
            AGENT_STATE["last_error"] = str(exc)
            AGENT_STATE["last_tick_at"] = now_iso()
            if session_id in SESSIONS:
                SESSIONS[session_id]["agent_status"] = "error"
                SESSIONS[session_id]["agent_last_run_at"] = now_iso()
                SESSIONS[session_id]["agent_last_output"] = f"Agent error: {exc}"
                save_sessions()
        return ""


def background_agent_worker() -> None:
    while True:
        try:
            if AGENT_STATE.get("enabled"):
                AGENT_STATE["last_tick_at"] = now_iso()

                with STATE_LOCK:
                    session_ids = [sid for sid, s in SESSIONS.items() if s.get("agent_enabled")]

                outputs = []
                for sid in session_ids:
                    out = run_agent_step_for_session(sid)
                    if out:
                        outputs.append(f"{sid}: updated")

                AGENT_STATE["last_summary"] = ", ".join(outputs) if outputs else "no updates"
        except Exception as exc:
            AGENT_STATE["last_error"] = str(exc)

        interval = int(AGENT_STATE.get("interval_seconds", 20) or 20)
        time.sleep(max(3, interval))


def ensure_agent_thread() -> None:
    if AGENT_STATE.get("thread_started"):
        return

    thread = threading.Thread(target=background_agent_worker, daemon=True, name="nova-background-agent")
    thread.start()
    AGENT_STATE["thread_started"] = True


# =========================================================
# CORE PAGE + AUTH ROUTES
# =========================================================

@app.route("/", endpoint="home_desktop")
def home_desktop():
    auth = require_page_auth(USERS)
    if auth:
        return auth
    return render_template("index.html")


@app.route("/mobile", endpoint="mobile_page")
def mobile_page():
    auth = require_page_auth(USERS)
    if auth:
        return auth
    return render_template("mobile.html")


@app.route("/login", methods=["GET"])
def login_page():
    if DEV_BYPASS_AUTH:
        return redirect("/")
    if current_user():
        return redirect("/")
    return render_template("login.html", active_tab="login")


@app.route("/logout", methods=["GET"])
def logout_page():
    logout_user()
    return redirect("/login")


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    if DEV_BYPASS_AUTH:
        username = normalize_username(str((request.get_json(silent=True) or {}).get("username") or "dev"))
        login_user(username or "dev")
        return jsonify({"ok": True, "username": current_user(), "redirect": "/"})

    data = request.get_json(silent=True) or {}
    username = normalize_username(str(data.get("username") or ""))
    password = str(data.get("password") or "")

    ok, message = create_user(USERS, username, password, now_iso)
    if not ok:
        return jsonify({"ok": False, "error": message}), 400

    save_users()
    login_user(username)
    return jsonify({"ok": True, "username": username, "redirect": "/"})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    if DEV_BYPASS_AUTH:
        username = normalize_username(str((request.get_json(silent=True) or {}).get("username") or "dev"))
        login_user(username or "dev")
        return jsonify({"ok": True, "username": current_user(), "redirect": "/"})

    data = request.get_json(silent=True) or {}
    username = normalize_username(str(data.get("username") or ""))
    password = str(data.get("password") or "")

    ok, result = authenticate_user(USERS, username, password)
    if not ok:
        return jsonify({"ok": False, "error": result}), 401

    login_user(result)
    return jsonify({"ok": True, "username": result, "redirect": "/"})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    logout_user()
    return jsonify({"ok": True, "redirect": "/login"})


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user = current_user()
    return jsonify(
        {
            "ok": True,
            "authenticated": True if DEV_BYPASS_AUTH else bool(user and user in USERS),
            "username": user,
            "dev_bypass_auth": DEV_BYPASS_AUTH,
        }
    )


@app.route("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "model": DEFAULT_MODEL,
            "tavily_configured": bool(TAVILY_API_KEY),
            "web_search_configured": is_web(),
            "agent": AGENT_STATE,
            "authenticated": True if DEV_BYPASS_AUTH else bool((current_user() or "") in USERS),
            "username": current_user(),
            "dev_bypass_auth": DEV_BYPASS_AUTH,
        }
    )


@app.route("/api/state")
def state_route():
    username = current_user() or "dev"
    sessions_for_user = get_user_sessions(username)

    return jsonify(
        {
            "ok": True,
            "sessions": sessions_for_user,
            "router": LAST_ROUTER_META,
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
            "current_model": DEFAULT_MODEL,
            "agent": AGENT_STATE,
            "username": username,
            "dev_bypass_auth": DEV_BYPASS_AUTH,
        }
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    ensure_agent_thread()
    print("=== NOVA AUTH + AGENT ===")
    print("MODEL:", DEFAULT_MODEL)
    print("WEB:", is_web())
    print("DEV_BYPASS_AUTH:", DEV_BYPASS_AUTH)
    app.run(host="0.0.0.0", port=5001, debug=True)