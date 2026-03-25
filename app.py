from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from openai import OpenAI

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))

# =========================================================
# CONFIG
# =========================================================

DEFAULT_MODEL = (os.getenv("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY", "") or "").strip()

# local dev fallback only
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# =========================================================
# STATE
# =========================================================

SESSIONS: dict[str, dict[str, Any]] = {}

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
# MEMORY
# =========================================================

MEMORY_FILE = DATA_DIR / "memory.json"
MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def load_memory() -> list[dict[str, Any]]:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


MEMORY_ITEMS: list[dict[str, Any]] = load_memory()


def save_memory() -> None:
    MEMORY_FILE.write_text(json.dumps(MEMORY_ITEMS, indent=2), encoding="utf-8")


def extract_memory(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
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
            "created_at": now_iso(),
        }
    return None


def get_relevant_memory(user_text: str) -> list[dict[str, Any]]:
    text = (user_text or "").lower()
    scored: list[tuple[int, dict[str, Any]]] = []

    for item in MEMORY_ITEMS:
        value = str(item.get("value", "")).lower()
        score = sum(1 for word in text.split() if word and word in value)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:3]]


# =========================================================
# HELPERS
# =========================================================

def ensure_session(session_id: str | None) -> str:
    sid = (session_id or "").strip() or str(uuid.uuid4())

    with STATE_LOCK:
        if sid not in SESSIONS:
            SESSIONS[sid] = {
                "id": sid,
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

    return sid


def add_message(session_id: str, role: str, content: str) -> dict[str, Any]:
    ensure_session(session_id)

    msg = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "created_at": now_iso(),
    }

    with STATE_LOCK:
        SESSIONS[session_id]["messages"].append(msg)
        SESSIONS[session_id]["updated_at"] = now_iso()

        if role == "user":
            cleaned = " ".join((content or "").strip().split())
            if cleaned and SESSIONS[session_id].get("title") == "New Chat":
                SESSIONS[session_id]["title"] = cleaned[:60]

    return msg


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

def generate_reply(user_text: str, session_id: str) -> tuple[str, list[dict[str, Any]], str]:
    text = (user_text or "").lower()

    coding_block = any(x in text for x in ["smff", "app.py", "python", "fix", "traceback"])
    allow_web = is_web() and not coding_block

    results: list[dict[str, Any]] = []
    provider = ""

    if allow_web:
        for query in [user_text, f"{user_text} latest"]:
            items = tavily(query)
            if items:
                results.extend(items)
                provider = "tavily"

    seen: set[str] = set()
    final_results: list[dict[str, Any]] = []
    for item in results:
        url = str(item.get("url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        final_results.append(item)

    final_results = final_results[:5]

    with STATE_LOCK:
        ensure_session(session_id)
        SESSIONS[session_id]["last_web_results"] = final_results

    memory_items = get_relevant_memory(user_text)
    memory_context = "\n".join(f"- {m.get('value', '')}" for m in memory_items if m.get("value"))

    web_context = ""
    if final_results:
        parts = []
        for idx, item in enumerate(final_results, start=1):
            parts.append(f"[{idx}] {item.get('title', '')}")
            parts.append(str(item.get("content", "") or ""))
            parts.append(str(item.get("url", "") or ""))
            parts.append("")
        web_context = "\n".join(parts)

    context_parts = []
    if memory_context:
        context_parts.append("User memory:\n" + memory_context)
    if web_context:
        context_parts.append("Web context:\n" + web_context)

    context = "\n\n".join(context_parts).strip()

    initial = call_model(user_text, context)
    final = autonomous_loop_refine(user_text, initial, context)

    return final, final_results, provider


# =========================================================
# BACKGROUND AGENT
# =========================================================

def agent_brain_prompt(session: dict[str, Any]) -> str:
    goal = str(session.get("agent_goal") or "").strip()
    if not goal:
        return ""

    messages = session.get("messages", [])[-8:]
    transcript_lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", "") or "")
        transcript_lines.append(f"{role.upper()}: {content}")

    transcript = "\n".join(transcript_lines).strip()
    memory_items = get_relevant_memory(goal)
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
        session = SESSIONS.get(session_id)
        if not session:
            return ""
        if not session.get("agent_enabled"):
            return ""
        goal = str(session.get("agent_goal") or "").strip()
        if not goal:
            session["agent_status"] = "idle"
            return ""

        session["agent_status"] = "running"

    prompt = agent_brain_prompt(session)
    if not prompt:
        with STATE_LOCK:
            if session_id in SESSIONS:
                SESSIONS[session_id]["agent_status"] = "idle"
        return ""

    try:
        draft = call_model(prompt)
        if not draft or draft.strip() == "NO_UPDATE":
            with STATE_LOCK:
                if session_id in SESSIONS:
                    SESSIONS[session_id]["agent_status"] = "idle"
                    SESSIONS[session_id]["agent_last_run_at"] = now_iso()
                    SESSIONS[session_id]["agent_last_output"] = ""
            return ""

        improved = autonomous_loop_refine(goal, draft, "")
        add_message(session_id, "assistant", improved)

        with STATE_LOCK:
            if session_id in SESSIONS:
                SESSIONS[session_id]["agent_status"] = "idle"
                SESSIONS[session_id]["agent_last_run_at"] = now_iso()
                SESSIONS[session_id]["agent_last_output"] = improved

        return improved
    except Exception as exc:
        with STATE_LOCK:
            AGENT_STATE["last_error"] = str(exc)
            AGENT_STATE["last_tick_at"] = now_iso()
            if session_id in SESSIONS:
                SESSIONS[session_id]["agent_status"] = "error"
                SESSIONS[session_id]["agent_last_run_at"] = now_iso()
                SESSIONS[session_id]["agent_last_output"] = f"Agent error: {exc}"
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

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "model": DEFAULT_MODEL,
            "tavily_configured": bool(TAVILY_API_KEY),
            "web_search_configured": is_web(),
            "agent": AGENT_STATE,
        }
    )


@app.route("/api/state")
def state():
    with STATE_LOCK:
        sessions = list(SESSIONS.values())

    return jsonify(
        {
            "ok": True,
            "sessions": sessions,
            "router": LAST_ROUTER_META,
            "router_meta": LAST_ROUTER_META,
            "last_router_meta": LAST_ROUTER_META,
            "current_model": DEFAULT_MODEL,
            "agent": AGENT_STATE,
        }
    )


@app.route("/api/chat/<session_id>", methods=["GET"])
def get_session(session_id: str):
    with STATE_LOCK:
        session = SESSIONS.get(session_id)

    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404

    return jsonify(
        {
            "ok": True,
            "session": session,
            "messages": session["messages"],
            "router": session.get("router_meta", LAST_ROUTER_META),
            "router_meta": session.get("router_meta", LAST_ROUTER_META),
            "last_router_meta": session.get("router_meta", LAST_ROUTER_META),
        }
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}

    msg = data.get("message") or data.get("content") or ""
    session_id = ensure_session(data.get("session_id"))

    add_message(session_id, "user", msg)

    mem = extract_memory(msg)
    if mem:
        MEMORY_ITEMS.insert(0, mem)
        save_memory()

    reply, results, provider = generate_reply(msg, session_id)
    add_message(session_id, "assistant", reply)

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
    data = request.json or {}

    msg = data.get("message") or data.get("content") or ""
    session_id = ensure_session(data.get("session_id"))

    add_message(session_id, "user", msg)

    mem = extract_memory(msg)
    if mem:
        MEMORY_ITEMS.insert(0, mem)
        save_memory()

    def gen():
        try:
            yield "event: start\ndata: {}\n\n"

            reply, results, provider = generate_reply(msg, session_id)
            add_message(session_id, "assistant", reply)

            for i in range(0, len(reply), 3):
                chunk = reply[i : i + 3]
                yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'delta': chunk})}\n\n"
                time.sleep(0.01)

            yield f"event: done\ndata: {json.dumps({'type': 'done', 'content': reply, 'web_results': results, 'web_provider': provider})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            yield "event: done\ndata: {}\n\n"

    return Response(
        stream_with_context(gen()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/memory")
def memory():
    return jsonify({"ok": True, "memory": MEMORY_ITEMS})


@app.route("/api/session/new", methods=["POST"])
def new_session():
    sid = str(uuid.uuid4())
    ensure_session(sid)
    return jsonify({"ok": True, "session_id": sid, "session": SESSIONS[sid]})


@app.route("/api/agent/status", methods=["GET"])
def agent_status():
    return jsonify({"ok": True, "agent": AGENT_STATE})


@app.route("/api/agent/start", methods=["POST"])
def agent_start():
    ensure_agent_thread()

    data = request.json or {}
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
    data = request.json or {}
    session_id = ensure_session(data.get("session_id"))
    enabled = bool(data.get("enabled", True))
    goal = str(data.get("goal") or "").strip()

    with STATE_LOCK:
        SESSIONS[session_id]["agent_enabled"] = enabled
        SESSIONS[session_id]["agent_goal"] = goal
        SESSIONS[session_id]["agent_status"] = "idle"
        SESSIONS[session_id]["updated_at"] = now_iso()

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "session": SESSIONS[session_id],
        }
    )


@app.route("/api/agent/session/run_once", methods=["POST"])
def agent_run_once():
    data = request.json or {}
    session_id = ensure_session(data.get("session_id"))
    output = run_agent_step_for_session(session_id)

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "output": output,
            "session": SESSIONS[session_id],
        }
    )

@app.route("/")
def index():
    return render_template("mobile.html")

@app.route("/mobile")
def mobile():
    return render_template("mobile.html")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    ensure_agent_thread()
    print("=== NOVA AUTONOMOUS BACKGROUND AGENT ===")
    print("MODEL:", DEFAULT_MODEL)
    print("WEB:", is_web())
    app.run(host="0.0.0.0", port=5001, debug=True)