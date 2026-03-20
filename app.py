from pathlib import Path
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_FILE = TEMPLATES_DIR / "index.html"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
APP_HOST = (os.getenv("APP_HOST") or "127.0.0.1").strip()
APP_PORT = int((os.getenv("APP_PORT") or "8743").strip())

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are Nova, an elite AI assistant. "
    "Be clear, direct, intelligent, and efficient. "
    "Give strong structured answers without fluff. "
    "Do not invent facts. If you are unsure, say so plainly. "
    "Use saved memory only when it is relevant to the user's request."
)

MAX_CONTEXT_MESSAGES = 12
MAX_MEMORY_ITEMS = 50


def now() -> int:
    return int(time.time())


def load_json_file(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_sessions() -> List[Dict[str, Any]]:
    data = load_json_file(SESSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_sessions(data: List[Dict[str, Any]]) -> None:
    save_json_file(SESSIONS_FILE, data)


def load_memory() -> Dict[str, Any]:
    data = load_json_file(MEMORY_FILE, {"items": []})
    if not isinstance(data, dict):
        return {"items": []}
    items = data.get("items", [])
    if not isinstance(items, list):
        items = []
    return {"items": items}


def save_memory(data: Dict[str, Any]) -> None:
    save_json_file(MEMORY_FILE, data)


def get_session(sessions: List[Dict[str, Any]], session_id: str):
    for session in sessions:
        if session.get("session_id") == session_id:
            return session
    return None


def get_context(messages: List[Dict[str, Any]], limit: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
    usable: List[Dict[str, Any]] = []
    for msg in messages[-limit:]:
        role = str(msg.get("role") or "").strip().lower()
        content = str(msg.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            usable.append({"role": role, "content": content})
    return usable


def generate_title(text: str) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return "New Chat"
    if len(clean) <= 48:
        return clean
    return clean[:48].rstrip(" .,!?:;-") + "..."


def normalize_memory_text(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def upsert_memory_item(kind: str, value: str, source: str = "auto") -> None:
    clean_value = normalize_memory_text(value)
    if not clean_value:
        return

    data = load_memory()
    items = data.get("items", [])

    existing = None
    for item in items:
        if item.get("kind") == kind and str(item.get("value") or "").strip().lower() == clean_value.lower():
            existing = item
            break

    ts = now()

    if existing:
        existing["updated_at"] = ts
        existing["source"] = source
    else:
        items.insert(0, {
            "id": str(uuid.uuid4()),
            "kind": kind,
            "value": clean_value,
            "source": source,
            "created_at": ts,
            "updated_at": ts,
        })

    # dedupe exact duplicates and trim
    seen = set()
    deduped = []
    for item in items:
        key = (str(item.get("kind") or "").lower(), str(item.get("value") or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    data["items"] = deduped[:MAX_MEMORY_ITEMS]
    save_memory(data)


def extract_memory_from_message(text: str) -> None:
    content = normalize_memory_text(text)
    if not content:
        return

    patterns = [
        ("name", r"\bmy name is\s+([A-Za-z][A-Za-z0-9' -]{0,40})\b"),
        ("goal", r"\bi(?:'m| am)\s+learning\s+(.+)$"),
        ("goal", r"\bi want to learn\s+(.+)$"),
        ("goal", r"\bi want to build\s+(.+)$"),
        ("preference", r"\bi prefer\s+(.+)$"),
        ("project", r"\bi(?:'m| am)\s+working on\s+(.+)$"),
    ]

    for kind, pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .")
            if 2 <= len(value) <= 120:
                upsert_memory_item(kind, value, source="auto")


def build_memory_prompt() -> str:
    data = load_memory()
    items = data.get("items", [])
    if not items:
        return ""

    lines = []
    for item in items[:12]:
        kind = str(item.get("kind") or "memory").strip()
        value = str(item.get("value") or "").strip()
        if value:
            lines.append(f"- {kind}: {value}")

    if not lines:
        return ""

    return "Saved user memory:\n" + "\n".join(lines)


def build_openai_messages(session_messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    memory_prompt = build_memory_prompt()
    if memory_prompt:
        messages.append({"role": "system", "content": memory_prompt})

    messages.extend(get_context(session_messages))
    return messages


def summarize_sessions_for_state(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for session in sessions:
        messages = session.get("messages", [])
        items.append({
            "session_id": session.get("session_id"),
            "title": session.get("title") or "New Chat",
            "message_count": len(messages) if isinstance(messages, list) else int(session.get("message_count") or 0),
            "updated_at": int(session.get("updated_at") or session.get("created_at") or now()),
        })
    items.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return items


app = FastAPI(title="Nova")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(INDEX_FILE)


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            OPENAI_MODEL,
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-4o-mini",
        ],
        "default": OPENAI_MODEL,
    }


@app.get("/api/state")
async def get_state():
    sessions = load_sessions()
    return {"sessions": summarize_sessions_for_state(sessions)}


@app.get("/api/chat/{session_id}")
async def get_chat(session_id: str):
    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["message_count"] = len(session.get("messages", []))
    return session


@app.get("/api/memory")
async def get_memory():
    return load_memory()


@app.post("/api/memory/add")
async def add_memory(request: Request):
    data = await request.json()
    kind = normalize_memory_text(data.get("kind"))
    value = normalize_memory_text(data.get("value"))
    if not kind or not value:
        raise HTTPException(status_code=400, detail="kind and value are required")
    upsert_memory_item(kind[:40], value[:120], source="manual")
    return {"ok": True, "memory": load_memory()}


@app.post("/api/memory/delete")
async def delete_memory(request: Request):
    data = await request.json()
    memory_id = str(data.get("id") or "").strip()
    if not memory_id:
        raise HTTPException(status_code=400, detail="id is required")

    memory = load_memory()
    before = len(memory["items"])
    memory["items"] = [item for item in memory["items"] if str(item.get("id")) != memory_id]
    if len(memory["items"]) == before:
        raise HTTPException(status_code=404, detail="Memory item not found")

    save_memory(memory)
    return {"ok": True, "memory": memory}


@app.post("/api/session/new")
async def new_session():
    sessions = load_sessions()

    session_id = str(uuid.uuid4())
    ts = now()
    new = {
        "session_id": session_id,
        "title": "New Chat",
        "messages": [],
        "message_count": 0,
        "created_at": ts,
        "updated_at": ts,
    }

    sessions.insert(0, new)
    save_sessions(sessions)

    return {"session_id": session_id}


@app.post("/api/session/delete")
async def delete_session(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()

    sessions = load_sessions()
    new_sessions = [s for s in sessions if s.get("session_id") != session_id]
    if len(new_sessions) == len(sessions):
        raise HTTPException(status_code=404, detail="Session not found")

    save_sessions(new_sessions)
    return {"ok": True}


@app.post("/api/session/rename")
async def rename_session(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()
    title = normalize_memory_text(data.get("title"))

    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["title"] = title[:80]
    session["updated_at"] = now()
    save_sessions(sessions)
    return {"ok": True}


@app.post("/api/chat")
async def chat_once(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()
    content = normalize_memory_text(data.get("content"))
    model = str(data.get("model") or OPENAI_MODEL).strip() or OPENAI_MODEL

    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API key")

    sessions = load_sessions()
    session = get_session(sessions, session_id)

    if not session:
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "title": "New Chat",
            "messages": [],
            "message_count": 0,
            "created_at": now(),
            "updated_at": now(),
        }
        sessions.insert(0, session)

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": content,
        "timestamp": now(),
        "model": model,
    }
    session["messages"].append(user_msg)
    session["updated_at"] = now()
    extract_memory_from_message(content)

    response = client.chat.completions.create(
        model=model,
        messages=build_openai_messages(session["messages"]),
        temperature=0.7,
    )

    assistant_text = str(response.choices[0].message.content or "").strip() or "No response returned."

    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": assistant_text,
        "timestamp": now(),
        "model": model,
    }
    session["messages"].append(assistant_msg)
    session["message_count"] = len(session["messages"])
    session["updated_at"] = now()

    if session["message_count"] == 2:
        session["title"] = generate_title(content)

    save_sessions(sessions)

    return {
        "session_id": session_id,
        "title": session["title"],
        "message_count": session["message_count"],
        "message": assistant_msg,
        "messages": session["messages"],
    }


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()
    content = normalize_memory_text(data.get("content"))
    model = str(data.get("model") or OPENAI_MODEL).strip() or OPENAI_MODEL

    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API key")

    sessions = load_sessions()
    session = get_session(sessions, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": content,
        "timestamp": now(),
        "model": model,
    }
    session["messages"].append(user_msg)
    session["updated_at"] = now()
    extract_memory_from_message(content)

    openai_messages = build_openai_messages(session["messages"])

    def event_stream():
        assistant_text = ""

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=openai_messages,
                stream=True,
                temperature=0.7,
            )

            yield f"event: start\ndata: {json.dumps({'title': session['title'], 'model_used': model}, ensure_ascii=False)}\n\n"

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    assistant_text += delta
                    yield f"event: delta\ndata: {json.dumps({'text': delta, 'model_used': model}, ensure_ascii=False)}\n\n"

            assistant_msg = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_text.strip() or "No response returned.",
                "timestamp": now(),
                "model": model,
            }
            session["messages"].append(assistant_msg)
            session["message_count"] = len(session["messages"])
            session["updated_at"] = now()

            if session["message_count"] == 2:
                session["title"] = generate_title(content)

            save_sessions(sessions)

            yield f"event: done\ndata: {json.dumps({'message': assistant_msg, 'session_id': session_id, 'title': session['title']}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)