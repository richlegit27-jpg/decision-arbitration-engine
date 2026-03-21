from pathlib import Path
import os
import time
import uuid
from shutil import copyfileobj

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
import uvicorn


# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_FILE = TEMPLATES_DIR / "index.html"
ATTACH_DIR = STATIC_DIR / "attachments"
ATTACH_DIR.mkdir(parents=True, exist_ok=True)


# --- Env ---
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "").strip()

print("RUNNING NOVA APP FROM:", __file__)
print("OPENAI MODEL:", OPENAI_MODEL if OPENAI_MODEL else "MISSING")
print("OPENAI KEY PREFIX:", OPENAI_API_KEY[:12] if OPENAI_API_KEY else "MISSING")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")

if not OPENAI_MODEL:
    raise RuntimeError("OPENAI_MODEL is missing")

client = OpenAI(api_key=OPENAI_API_KEY)


# --- FastAPI app ---
app = FastAPI(title="Nova")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Static mounts ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/attachments", StaticFiles(directory=ATTACH_DIR), name="attachments")


# --- In-memory stores ---
chat_sessions: dict[str, list[dict]] = {}
memory_state: list[dict] = []


def now_ts() -> int:
    return int(time.time())


def make_message(role: str, content: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": now_ts(),
    }


def get_session_id(payload: dict) -> str:
    raw = str(payload.get("session_id") or "default").strip()
    return raw or "default"


def get_session_messages(session_id: str) -> list[dict]:
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    return chat_sessions[session_id]


def build_model_input(messages: list[dict]) -> str:
    parts = [
        "You are Nova, a clean, direct AI assistant inside a local chat app.",
        "Be helpful, natural, and concise.",
        "Do not simply repeat the user's message."
    ]

    for msg in messages[-20:]:
        role = "Assistant" if msg["role"] == "assistant" else "User"
        parts.append(f"{role}: {msg['content']}")

    parts.append("Assistant:")
    return "\n".join(parts)


def generate_ai_reply(messages: list[dict]) -> str:
    prompt = build_model_input(messages)

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    text = (response.output_text or "").strip()
    if text:
        return text

    return "Model returned an empty response."


# --- Frontend ---
@app.get("/")
async def read_index():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(INDEX_FILE)


# --- Health ---
@app.get("/api/health")
async def health_check():
    return {
        "ok": True,
        "app": "Nova",
        "timestamp": now_ts(),
        "sessions": len(chat_sessions),
        "model_connected": True,
        "model": OPENAI_MODEL,
        "key_prefix": OPENAI_API_KEY[:12],
    }


# --- Chat endpoint ---
@app.post("/api/chat")
async def send_message(req: Request):
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    session_id = get_session_id(data)
    content = str(data.get("content") or "").strip()

    if not content:
        return JSONResponse(
            {
                "session_id": session_id,
                "reply": "",
                "error": "Empty message",
            },
            status_code=200,
        )

    messages = get_session_messages(session_id)

    user_msg = make_message("user", content)
    messages.append(user_msg)

    try:
        ai_text = generate_ai_reply(messages)
    except Exception as error:
        ai_text = f"Model request failed: {type(error).__name__}: {error}"

    ai_msg = make_message("assistant", ai_text)
    messages.append(ai_msg)

    return JSONResponse(
        {
            "session_id": session_id,
            "reply": ai_text,
            "message": ai_msg,
        },
        status_code=200,
    )


# --- Session state ---
@app.get("/api/state")
async def get_state():
    session_summaries = []

    for session_id, messages in chat_sessions.items():
        session_summaries.append({
            "session_id": session_id,
            "message_count": len(messages),
            "last_timestamp": messages[-1]["timestamp"] if messages else None,
        })

    session_summaries.sort(
        key=lambda item: item["last_timestamp"] or 0,
        reverse=True,
    )

    return {
        "sessions": session_summaries,
        "session_count": len(session_summaries),
        "timestamp": now_ts(),
    }


@app.get("/api/chat/{session_id}")
async def get_chat_session(session_id: str):
    messages = get_session_messages(session_id)
    return {
        "session_id": session_id,
        "messages": messages,
        "message_count": len(messages),
    }


# --- Memory endpoints ---
@app.post("/api/memory/add")
async def add_memory(req: Request):
    data = await req.json()
    text = str(data.get("text") or "").strip()

    item = {
        "id": str(uuid.uuid4()),
        "text": text,
        "embedding": [ord(c) for c in text][:50],
        "timestamp": now_ts(),
    }
    memory_state.append(item)

    return JSONResponse({"status": "ok", "item": item})


@app.post("/api/memory/search")
async def search_memory(req: Request):
    data = await req.json()
    query = str(data.get("query") or "")
    query_vec = [ord(c) for c in query][:50]

    scored = []
    for item in memory_state:
        score = sum(a * b for a, b in zip(query_vec, item["embedding"]))
        scored.append((score, item))

    scored.sort(reverse=True, key=lambda x: x[0])
    return JSONResponse([item for _, item in scored[:5]])


@app.post("/api/memory/suggest")
async def memory_suggest(req: Request):
    data = await req.json()
    query = str(data.get("query") or "")
    query_vec = [ord(c) for c in query][:50]

    scored = []
    for item in memory_state:
        score = sum(a * b for a, b in zip(query_vec, item["embedding"]))
        scored.append((score, item))

    scored.sort(reverse=True, key=lambda x: x[0])
    return JSONResponse([item for _, item in scored[:3]])


# --- File uploads ---
@app.post("/api/chat/upload")
async def upload_attachment(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    ext = Path(file.filename or "").suffix
    save_path = ATTACH_DIR / f"{file_id}{ext}"

    with save_path.open("wb") as out_file:
        copyfileobj(file.file, out_file)

    return JSONResponse({
        "status": "ok",
        "file_id": file_id,
        "filename": file.filename,
        "url": f"/attachments/{file_id}{ext}",
    })


# --- Run server ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8743, reload=False)