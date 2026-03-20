from pathlib import Path
from contextlib import asynccontextmanager
import json
import os
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
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

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()

client = OpenAI(api_key=OPENAI_API_KEY)

def now():
    return int(time.time())

def load_sessions():
    if not SESSIONS_FILE.exists():
        return []
    return json.loads(SESSIONS_FILE.read_text())

def save_sessions(data):
    SESSIONS_FILE.write_text(json.dumps(data, indent=2))

def get_session(sessions, session_id):
    for s in sessions:
        if s["session_id"] == session_id:
            return s
    return None

def get_context(messages, limit=10):
    # 🔥 CORE UPGRADE — smarter memory window
    return messages[-limit:]

def generate_title(text):
    text = text.strip()
    if len(text) <= 40:
        return text
    return text[:40] + "..."

app = FastAPI()

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
        "models": ["gpt-4.1-mini", "gpt-4.1"],
        "default": OPENAI_MODEL
    }

@app.get("/api/state")
async def get_state():
    sessions = load_sessions()
    return {"sessions": sessions}

@app.get("/api/chat/{session_id}")
async def get_chat(session_id: str):
    sessions = load_sessions()
    s = get_session(sessions, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s

@app.post("/api/session/new")
async def new_session():
    sessions = load_sessions()

    session_id = str(uuid.uuid4())
    new = {
        "session_id": session_id,
        "title": "New Chat",
        "messages": [],
        "message_count": 0
    }

    sessions.insert(0, new)
    save_sessions(sessions)

    return {"session_id": session_id}

@app.post("/api/session/delete")
async def delete_session(data: dict):
    sessions = load_sessions()
    sessions = [s for s in sessions if s["session_id"] != data["session_id"]]
    save_sessions(sessions)
    return {"ok": True}

@app.post("/api/session/rename")
async def rename_session(data: dict):
    sessions = load_sessions()
    s = get_session(sessions, data["session_id"])
    if not s:
        raise HTTPException(404)

    s["title"] = data["title"]
    save_sessions(sessions)
    return {"ok": True}

@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    content = data.get("content")
    model = data.get("model") or OPENAI_MODEL

    if not OPENAI_API_KEY:
        raise HTTPException(500, "Missing API key")

    sessions = load_sessions()
    s = get_session(sessions, session_id)

    if not s:
        raise HTTPException(404)

    # add user message
    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": content,
        "timestamp": now()
    }
    s["messages"].append(user_msg)

    # 🔥 CONTEXT UPGRADE
    context_messages = get_context(s["messages"])

    def event_stream():
        assistant_text = ""

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=context_messages,
                stream=True
            )

            yield f"event: start\ndata: {json.dumps({'title': s['title']})}\n\n"

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    assistant_text += delta
                    yield f"event: delta\ndata: {json.dumps({'text': delta})}\n\n"

            # save assistant message
            assistant_msg = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_text,
                "timestamp": now()
            }
            s["messages"].append(assistant_msg)
            s["message_count"] = len(s["messages"])

            # auto title if first message
            if s["message_count"] == 2:
                s["title"] = generate_title(content)

            save_sessions(sessions)

            yield f"event: done\ndata: {json.dumps({'message': assistant_msg})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8743)