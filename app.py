from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
)
from openai import OpenAI
from werkzeug.security import check_password_hash, generate_password_hash

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = DATA_DIR / "memory.json"
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

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

# =========================================================
# UTILS
# =========================================================

USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clean_text(value: Any) -> str:
    return str(value or "").strip()


# =========================================================
# USERS / AUTH
# =========================================================

def load_users() -> dict[str, dict[str, Any]]:
    raw = read_json_file(USERS_FILE, {})
    if isinstance(raw, dict):
        return raw
    return {}


USERS: dict[str, dict[str, Any]] = load_users()


def save_users() -> None:
    write_json_file(USERS_FILE, USERS)


def normalize_username(value: str) -> str:
    return clean_text(value).lower()


def validate_username(username: str) -> str | None:
    if not USERNAME_RE.fullmatch(username):
        return "Username must be 3 to 32 chars using lowercase letters, numbers, underscore, or dash."
    return None


def validate_password(password: str) -> str | None:
    if len(password or "") < 8:
        return "Password must be at least 8 characters."
    return None


def create_user(username: str, password: str) -> tuple[bool, str]:
    username = normalize_username(username)
    err = validate_username(username)
    if err:
        return False, err

    err = validate_password(password)
    if err:
        return False, err

    with STATE_LOCK:
        if username in USERS:
            return False, "Username already exists."

        USERS[username] = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "created_at": now_iso(),
        }
        save_users()

    return True, "Account created."


def authenticate_user(username: str, password: str) -> tuple[bool, str]:
    username = normalize_username(username)
    user = USERS.get(username)

    if not user:
        return False, "Invalid username or password."

    try:
        ok = check_password_hash(str(user.get("password_hash", "")), password or "")
    except Exception:
        ok = False

    if not ok:
        return False, "Invalid username or password."

    return True, username


def current_user() -> str | None:
    value = session.get("username")
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return None


def is_logged_in() -> bool:
    user = current_user()
    return bool(user and user in USERS)


def login_user(username: str) -> None:
    session["username"] = normalize_username(username)
    session["logged_in"] = True


def logout_user() -> None:
    session.clear()


def require_page_auth():
    if not is_logged_in():
        return redirect("/login")
    return None


@app.before_request
def protect_routes():
    public_paths = {
        "/login",
        "/logout",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/health",
    }

    path = request.path or "/"

    if path.startswith("/static/"):
        return None

    if path in public_paths:
        return None

    if path == "/" or path == "/mobile":
        if not is_logged_in():
            return redirect("/login")
        return None

    if path.startswith("/api/"):
        if not is_logged_in():
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return None

    return None


# =========================================================
# MEMORY
# =========================================================

def load_memory() -> list[dict[str, Any]]:
    raw = read_json_file(MEMORY_FILE, [])
    if isinstance(raw, list):
        return raw
    return []


MEMORY_ITEMS: list[dict[str, Any]] = load_memory()


def save_memory() -> None:
    write_json_file(MEMORY_FILE, MEMORY_ITEMS)


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
# SESSIONS
# =========================================================

def load_sessions() -> dict[str, dict[str, Any]]:
    raw = read_json_file(SESSIONS_FILE, {})
    if isinstance(raw, dict):
        return raw
    return {}


SESSIONS: dict[str, dict[str, Any]] = load_sessions()


def save_sessions() -> None:
    write_json_file(SESSIONS_FILE, SESSIONS)


# =========================================================
# HELPERS
# =========================================================

def ensure_session(session_id: str | None, username: str) -> str:
    sid = clean_text(session_id) or str(uuid.uuid4())
    username = normalize_username(username)

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
            }
            save_sessions()
        else:
            owner = normalize_username(str(SESSIONS[sid].get("user", "")))
            if owner != username:
                raise PermissionError("Session does not belong to current user.")

    return sid


def get_user_sessions(username: str) -> list[dict[str, Any]]:
    username = normalize_username(username)
    with STATE_LOCK:
        items = [s for s in SESSIONS.values() if normalize_username(str(s.get("user", ""))) == username]
    items.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
    return items


def get_owned_session_or_404(session_id: str, username: str) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    with STATE_LOCK:
        session_obj = SESSIONS.get(session_id)

    if not session_obj:
        return None, (jsonify({"ok": False, "error": "Session not found"}), 404)

    owner = normalize_username(str(session_obj.get("user", "")))
    if owner != normalize_username(username):
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


def json_request(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# =========================================================
# WEB SEARCH
# =========================================================

def is_web() -> bool:
    return bool(TAVILY_API_KEY)


def tavily(query: str) -> list[dict[str, Any]]:
    if not TAVILY_API_KEY:
        return []

    try:
        res = json_request(
            "https://api.tavily.com/search",
            payload={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 5,
            },
        )
        return list(res.get("results", []) or [])
    except Exception as exc:
        print("TAVILY ERROR:", exc)
        return []


def wants_web_search(user_text: str) -> bool:
    text = clean_text(user_text).lower()
    if not text:
        return False

    # hard block: coding/debug/local project asks should not hit web
    block_terms = {
        "smff",
        "app.py",
        "traceback",
        "stack trace",
        "error:",
        "fix this",
        "bug",
        "debug",
        "refactor",
        "function",
        "class",
        "javascript",
        "python",
        "flask",
        "html",
        "css",
        "sql",
        "powershell",
        "terminal",
        "render",
        "ngrok",
        "api route",
        "endpoint",
        "frontend",
        "backend",
        "nova",
    }
    if any(term in text for term in block_terms):
        return False

    # direct freshness / current-events intent
    strong_fetch_terms = {
        "latest",
        "today",
        "right now",
        "current",
        "currently",
        "recent",
        "recently",
        "news",
        "headline",
        "headlines",
        "update",
        "updates",
        "breaking",
        "live",
        "score",
        "scores",
        "record",
        "standings",
        "schedule",
        "injury",
        "price",
        "stock",
        "stocks",
        "weather",
        "forecast",
        "election",
        "poll",
        "ceo",
        "president",
        "launch",
        "release date",
        "partnership",
        "lawsuit",
        "deal",
    }
    if any(term in text for term in strong_fetch_terms):
        return True

    # proper nouns / entities that often benefit from current web info
    entity_terms = {
        "openai",
        "chatgpt",
        "microsoft",
        "google",
        "anthropic",
        "tesla",
        "nasa",
        "artemis",
        "spacex",
        "canucks",
        "nhl",
        "nba",
        "nfl",
        "mlb",
        "bitcoin",
        "ethereum",
        "vancouver",
        "canada election",
        "u.s. agencies",
    }
    if any(term in text for term in entity_terms):
        if any(word in text for word in ["latest", "current", "news", "today", "right now", "update", "updates", "record", "score", "standings"]):
            return True

    # question patterns that imply fresh facts
    freshness_patterns = [
        r"\bwhat('?s| is) happening\b",
        r"\bwhat('?s| is) new\b",
        r"\bwhat('?s| is) the latest\b",
        r"\bhow is\b.*\bdoing\b",
        r"\bwho is\b.*\bnow\b",
        r"\bwhen is\b.*\blaunch\b",
        r"\bwhen does\b.*\bstart\b",
        r"\bwhat('?s| is) the .*record\b",
        r"\bwhat('?s| is) the .*price\b",
    ]
    if any(re.search(pattern, text) for pattern in freshness_patterns):
        return True

    return False


def search_web_for_query(user_text: str) -> tuple[list[dict[str, Any]], str]:
    if not is_web():
        return [], ""

    queries: list[str] = []
    base = clean_text(user_text)
    lowered = base.lower()

    queries.append(base)

    if not any(token in lowered for token in ["latest", "today", "current", "right now", "recent", "news", "update"]):
        queries.append(f"{base} latest")

    results: list[dict[str, Any]] = []
    provider = ""

    for query in queries[:2]:
        try:
            items = tavily(query)
        except Exception:
            items = []
        if items:
            results.extend(items)
            provider = "tavily"

    seen: set[str] = set()
    final_results: list[dict[str, Any]] = []

    for item in results:
        if not isinstance(item, dict):
            continue

        url = clean_text(item.get("url"))
        title = clean_text(item.get("title"))
        snippet = clean_text(
            item.get("snippet")
            or item.get("content")
            or item.get("body")
            or item.get("text")
            or item.get("description")
        )

        dedupe_key = (url or title or snippet).strip().lower()
        if not dedupe_key or dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        final_results.append(
            {
                "title": title or (url or "Untitled source"),
                "url": url,
                "snippet": snippet[:500],
            }
        )

    return final_results[:5], provider


# =========================================================
# MODEL
# =========================================================

def call_model(text: str, context: str = "") -> str:
    if not OPENAI_CLIENT:
        return "Missing OpenAI key."

    final_input = f"{context}\n\n{text}" if context else text

    response = OPENAI_CLIENT.responses.create(
        model=DEFAULT_MODEL,
        input=final_input,
    )

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    return "No response"


def improve_answer(user_text: str, answer: str, context: str = "") -> str:
    prompt = f"""
Improve this answer.

User:
{user_text}

Answer:
{answer}

Make it:
- clearer
- more accurate
- more helpful
- tighter

Return only the improved answer.
""".strip()

    try:
        improved = call_model(prompt, context)
        return improved if improved else answer
    except Exception:
        return answer


def score_answer(user_text: str, answer: str) -> float:
    prompt = f"""
Score this answer from 1 to 10.

User:
{user_text}

Answer:
{answer}

Return only a number.
""".strip()

    try:
        raw = call_model(prompt)
        return float(raw.strip())
    except Exception:
        return 5.0


def autonomous_loop_refine(user_text: str, base_answer: str, context: str = "") -> str:
    best = base_answer

    for _ in range(2):
        improved = improve_answer(user_text, best, context)
        old_score = score_answer(user_text, best)
        new_score = score_answer(user_text, improved)
        if new_score > old_score:
            best = improved

    return best


# =========================================================
# INTELLIGENCE
# =========================================================

def generate_reply(username: str, user_text: str, session_id: str) -> tuple[str, list[dict[str, Any]], str]:
    final_results: list[dict[str, Any]] = []
    provider = ""

    if wants_web_search(user_text):
        final_results, provider = search_web_for_query(user_text)

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
# BACKGROUND AGENT
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
# ROUTES
# =========================================================

@app.route("/", endpoint="home_desktop")
def home_desktop():
    auth = require_page_auth()
    if auth:
        return auth
    return render_template("index.html")


@app.route("/mobile", endpoint="mobile_page")
def mobile_page():
    auth = require_page_auth()
    if auth:
        return auth
    return render_template("mobile.html")


@app.route("/login", methods=["GET"])
def login_page():
    if is_logged_in():
        return redirect("/")
    return render_template("login.html", active_tab="login")


@app.route("/logout", methods=["GET"])
def logout_page():
    logout_user()
    return redirect("/login")


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    data = request.get_json(silent=True) or {}
    username = normalize_username(str(data.get("username") or ""))
    password = str(data.get("password") or "")

    ok, message = create_user(username, password)
    if not ok:
        return jsonify({"ok": False, "error": message}), 400

    login_user(username)
    return jsonify({"ok": True, "username": username, "redirect": "/"})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json(silent=True) or {}
    username = normalize_username(str(data.get("username") or ""))
    password = str(data.get("password") or "")

    ok, result = authenticate_user(username, password)
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
            "authenticated": is_logged_in(),
            "username": user,
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
            "authenticated": is_logged_in(),
            "username": current_user(),
        }
    )


@app.route("/api/state")
def state_route():
    username = current_user() or ""
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
        }
    )


@app.route("/api/chat/<session_id>", methods=["GET"])
def get_session(session_id: str):
    username = current_user() or ""
    session_obj, error = get_owned_session_or_404(session_id, username)
    if error:
        return error

    return jsonify(
        {
            "ok": True,
            "session": session_obj,
            "messages": session_obj["messages"],
            "router": session_obj.get("router_meta", LAST_ROUTER_META),
            "router_meta": session_obj.get("router_meta", LAST_ROUTER_META),
            "last_router_meta": session_obj.get("router_meta", LAST_ROUTER_META),
        }
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    username = current_user() or ""

    msg = data.get("message") or data.get("content") or ""
    session_id = ensure_session(data.get("session_id"), username)

    add_message(session_id, "user", msg)

    mem = extract_memory(msg)
    if mem:
        mem["user"] = username
        MEMORY_ITEMS.insert(0, mem)
        save_memory()

    reply, results, provider = generate_reply(username, msg, session_id)
    add_message(session_id, "assistant", reply, web_results=results, web_provider=provider)

    return jsonify(
        {
            "ok": True,
            "reply": reply,
            "web_results": results,
            "web_provider": provider,
            "session_id": session_id,
            "messages": SESSIONS[session_id]["messages"],
            "session": SESSIONS[session_id],
        }
    )


@app.route("/api/chat/stream", methods=["POST"])
def stream():
    data = request.get_json(silent=True) or {}
    username = current_user() or ""

    msg = data.get("message") or data.get("content") or ""
    session_id = ensure_session(data.get("session_id"), username)

    add_message(session_id, "user", msg)

    mem = extract_memory(msg)
    if mem:
        mem["user"] = username
        MEMORY_ITEMS.insert(0, mem)
        save_memory()

    def gen():
        try:
            yield f"event: start\ndata: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"

            reply, results, provider = generate_reply(username, msg, session_id)

            add_message(
                session_id,
                "assistant",
                reply,
                web_results=results,
                web_provider=provider,
            )

            for i in range(0, len(reply), 3):
                chunk = reply[i:i + 3]
                yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'delta': chunk, 'session_id': session_id})}\n\n"
                time.sleep(0.01)

            yield f"event: done\ndata: {json.dumps({'type': 'done', 'content': reply, 'response': reply, 'session_id': session_id, 'web_results': results or [], 'web_provider': provider or ''})}\n\n"

        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(exc), 'session_id': session_id})}\n\n"
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'content': '', 'response': '', 'session_id': session_id, 'web_results': [], 'web_provider': ''})}\n\n"

    return Response(
        stream_with_context(gen()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/memory", methods=["GET"])
def memory():
    username = current_user() or ""
    return jsonify({"ok": True, "memory": get_user_memory_items(username)})


@app.route("/api/memory", methods=["POST"])
def memory_add():
    data = request.get_json(silent=True) or {}
    username = current_user() or ""
    value = str(data.get("value") or "").strip()
    kind = str(data.get("kind") or "memory").strip()

    if not value:
        return jsonify({"ok": False, "error": "Missing memory value"}), 400

    item = {
        "id": str(uuid.uuid4()),
        "user": username,
        "kind": kind or "memory",
        "value": value[:300],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    with STATE_LOCK:
        MEMORY_ITEMS.insert(0, item)
        save_memory()

    return jsonify({"ok": True, "item": item, "memory": get_user_memory_items(username)})


@app.route("/api/memory/delete", methods=["POST"])
def memory_delete():
    data = request.get_json(silent=True) or {}
    username = current_user() or ""
    memory_id = str(data.get("id") or "").strip()

    if not memory_id:
        return jsonify({"ok": False, "error": "Missing memory id"}), 400

    with STATE_LOCK:
        before = len(MEMORY_ITEMS)
        MEMORY_ITEMS[:] = [
            item
            for item in MEMORY_ITEMS
            if not (
                str(item.get("id", "")).strip() == memory_id
                and normalize_username(str(item.get("user", ""))) == normalize_username(username)
            )
        ]
        changed = len(MEMORY_ITEMS) != before
        if changed:
            save_memory()

    return jsonify({"ok": True, "deleted": changed})


@app.route("/api/session/new", methods=["POST"])
def new_session():
    username = current_user() or ""
    sid = str(uuid.uuid4())
    ensure_session(sid, username)
    return jsonify({"ok": True, "session_id": sid, "session": SESSIONS[sid]})


@app.route("/api/agent/status", methods=["GET"])
def agent_status():
    return jsonify({"ok": True, "agent": AGENT_STATE})


@app.route("/api/agent/start", methods=["POST"])
def agent_start():
    ensure_agent_thread()

    data = request.get_json(silent=True) or {}
    interval = int(data.get("interval_seconds") or AGENT_STATE.get("interval_seconds") or 20)
    AGENT_STATE["interval_seconds"] = max(3, interval)
    AGENT_STATE["enabled"] = True
    AGENT_STATE["last_error"] = ""

    return jsonify({"ok": True, "agent": AGENT_STATE})


@app.route("/api/agent/stop", methods=["POST"])
def agent_stop():
    AGENT_STATE["enabled"] = False
    return jsonify({"ok": True, "agent": AGENT_STATE})


@app.route("/api/agent/session/config", methods=["POST"])
def agent_session_config():
    data = request.get_json(silent=True) or {}
    username = current_user() or ""
    session_id = ensure_session(data.get("session_id"), username)
    enabled = bool(data.get("enabled", True))
    goal = str(data.get("goal") or "").strip()

    with STATE_LOCK:
        SESSIONS[session_id]["agent_enabled"] = enabled
        SESSIONS[session_id]["agent_goal"] = goal
        SESSIONS[session_id]["agent_status"] = "idle"
        SESSIONS[session_id]["updated_at"] = now_iso()
        save_sessions()

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "session": SESSIONS[session_id],
        }
    )


@app.route("/api/agent/session/run_once", methods=["POST"])
def agent_run_once():
    data = request.get_json(silent=True) or {}
    username = current_user() or ""
    session_id = ensure_session(data.get("session_id"), username)
    output = run_agent_step_for_session(session_id)

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "output": output,
            "session": SESSIONS[session_id],
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
    app.run(host="0.0.0.0", port=5001, debug=True)