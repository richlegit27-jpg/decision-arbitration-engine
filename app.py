from pathlib import Path
import json
import os
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_FILE = TEMPLATES_DIR / "index.html"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
APP_HOST = (os.getenv("APP_HOST") or "127.0.0.1").strip()
APP_PORT = int((os.getenv("APP_PORT") or "8000").strip())

FILE_LOCK = Lock()

client = OpenAI(api_key=OPENAI_API_KEY) if (OpenAI and OPENAI_API_KEY) else None

MAX_CONTEXT_MESSAGES = 24
SYSTEM_PROMPT = (
    "You are Nova, an elite AI assistant. "
    "Be clear, direct, intelligent, and efficient. "
    "Give strong structured answers without fluff. "
    "Do not invent facts. If you are unsure, say so plainly. "
    "Keep answers practical and grounded in the user's request."
)


class SessionNewRequest(BaseModel):
    pass


class SessionDeleteRequest(BaseModel):
    session_id: str


class SessionRenameRequest(BaseModel):
    session_id: str
    title: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    content: str
    model: Optional[str] = None


def now_ts() -> int:
    return int(time.time())


def new_id() -> str:
    return str(uuid.uuid4())


def default_store() -> Dict[str, Any]:
    return {"sessions": {}}


def read_store() -> Dict[str, Any]:
    with FILE_LOCK:
        if not SESSIONS_FILE.exists():
            data = default_store()
            SESSIONS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data

        try:
            raw = SESSIONS_FILE.read_text(encoding="utf-8").strip()
            if not raw:
                return default_store()

            data = json.loads(raw)
            if not isinstance(data, dict):
                return default_store()

            data.setdefault("sessions", {})
            if not isinstance(data["sessions"], dict):
                data["sessions"] = {}

            return data
        except Exception:
            return default_store()


def write_store(data: Dict[str, Any]) -> None:
    with FILE_LOCK:
        SESSIONS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def normalize_session(session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
    messages = session.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    created_at = int(session.get("created_at") or now_ts())
    updated_at = int(session.get("updated_at") or created_at)
    title = str(session.get("title") or "New Chat").strip() or "New Chat"
    last_model = str(session.get("last_model") or "").strip()

    return {
        "session_id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "last_model": last_model,
        "messages": messages,
        "message_count": len(messages),
    }


def summarize_session(session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_session(session_id, session)
    return {
        "session_id": normalized["session_id"],
        "title": normalized["title"],
        "created_at": normalized["created_at"],
        "updated_at": normalized["updated_at"],
        "last_model": normalized["last_model"],
        "message_count": normalized["message_count"],
    }


def list_sessions() -> List[Dict[str, Any]]:
    store = read_store()
    items = [
        summarize_session(session_id, session)
        for session_id, session in store.get("sessions", {}).items()
    ]
    items.sort(key=lambda item: item.get("updated_at", 0), reverse=True)
    return items


def get_session_or_404(session_id: str) -> Dict[str, Any]:
    store = read_store()
    session = store.get("sessions", {}).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return normalize_session(session_id, session)


def save_session(session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
    store = read_store()
    store["sessions"][session_id] = session
    write_store(store)
    return normalize_session(session_id, session)


def create_session(title: str = "New Chat") -> Dict[str, Any]:
    session_id = new_id()
    ts = now_ts()
    session = {
        "title": title,
        "created_at": ts,
        "updated_at": ts,
        "last_model": "",
        "messages": [],
    }
    return save_session(session_id, session)


def delete_session(session_id: str) -> None:
    store = read_store()
    if session_id not in store.get("sessions", {}):
        raise HTTPException(status_code=404, detail="Session not found")
    del store["sessions"][session_id]
    write_store(store)


def rename_session(session_id: str, title: str) -> Dict[str, Any]:
    clean_title = str(title or "").strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    store = read_store()
    session = store.get("sessions", {}).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["title"] = clean_title
    session["updated_at"] = now_ts()
    store["sessions"][session_id] = session
    write_store(store)
    return normalize_session(session_id, session)


def build_title_from_text(text: str) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return "New Chat"
    return clean[:48].rstrip(" .,!?:;-") or "New Chat"


def append_message(
    session_id: str,
    role: str,
    content: str,
    model: str = ""
) -> Dict[str, Any]:
    store = read_store()
    session = store.get("sessions", {}).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    ts = now_ts()
    message = {
        "id": new_id(),
        "role": role,
        "content": str(content or ""),
        "timestamp": ts,
        "model": str(model or "").strip(),
    }
    messages.append(message)

    if len(messages) == 1 and role == "user":
        session["title"] = build_title_from_text(content)

    session["messages"] = messages
    session["updated_at"] = ts
    if model:
        session["last_model"] = model

    store["sessions"][session_id] = session
    write_store(store)
    return message


def get_model_list() -> List[str]:
    models = [
        OPENAI_MODEL,
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o-mini",
    ]
    seen = set()
    cleaned: List[str] = []

    for model in models:
        value = str(model or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)

    return cleaned


def build_openai_messages(session_messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    usable_messages: List[Dict[str, str]] = []

    for item in session_messages[-MAX_CONTEXT_MESSAGES:]:
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()

        if role not in {"user", "assistant", "system"}:
            continue
        if not content:
            continue

        usable_messages.append({
            "role": role,
            "content": content,
        })

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        *usable_messages,
    ]


def extract_completion_text(response: Any) -> str:
    try:
        text = response.choices[0].message.content
        if isinstance(text, str):
            text = text.strip()
            if text:
                return text
    except Exception:
        pass

    return "No response returned."


def request_completion(messages: List[Dict[str, str]], model: str, stream: bool = False):
    if client is None:
        raise RuntimeError("Nova is running, but OPENAI_API_KEY is not set.")

    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        stream=stream,
    )


def get_completion_text(messages: List[Dict[str, str]], model: str) -> str:
    if client is None:
        return "Nova is running, but OPENAI_API_KEY is not set."

    preferred_model = str(model or OPENAI_MODEL).strip() or OPENAI_MODEL
    fallback_model = OPENAI_MODEL

    try:
        response = request_completion(messages, preferred_model, stream=False)
        return extract_completion_text(response)
    except Exception as first_error:
        if preferred_model != fallback_model:
            try:
                response = request_completion(messages, fallback_model, stream=False)
                return extract_completion_text(response)
            except Exception as second_error:
                return f"Error: {second_error}"
        return f"Error: {first_error}"


def stream_completion_chunks(messages: List[Dict[str, str]], model: str):
    if client is None:
        fallback = "Nova is running, but OPENAI_API_KEY is not set."
        for i in range(0, len(fallback), 24):
            yield fallback[i:i + 24]
        return

    preferred_model = str(model or OPENAI_MODEL).strip() or OPENAI_MODEL
    fallback_model = OPENAI_MODEL

    def stream_from(selected_model: str):
        stream = request_completion(messages, selected_model, stream=True)
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = ""
            if delta:
                yield delta

    emitted = False

    try:
        for piece in stream_from(preferred_model):
            emitted = True
            yield piece
        if emitted:
            return
    except Exception:
        pass

    if preferred_model != fallback_model:
        try:
            for piece in stream_from(fallback_model):
                emitted = True
                yield piece
            if emitted:
                return
        except Exception:
            pass

    fallback_text = get_completion_text(messages, fallback_model)
    for i in range(0, len(fallback_text), 24):
        yield fallback_text[i:i + 24]


def sse_event(event_name: str, payload: Dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


app = FastAPI(title="Nova")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    if not INDEX_FILE.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"Missing index file: {INDEX_FILE}"}
        )
    return FileResponse(INDEX_FILE)


@app.get("/api/models")
def api_models():
    return {
        "default": OPENAI_MODEL,
        "models": get_model_list(),
    }


@app.get("/api/state")
def api_state():
    return {"sessions": list_sessions()}


@app.get("/api/chat/{session_id}")
def api_chat(session_id: str):
    return get_session_or_404(session_id)


@app.post("/api/session/new")
def api_session_new(_: SessionNewRequest):
    session = create_session()
    return {
        "session_id": session["session_id"],
        "title": session["title"],
        "message_count": session["message_count"],
        "last_model": session["last_model"],
    }


@app.post("/api/session/delete")
def api_session_delete(payload: SessionDeleteRequest):
    delete_session(payload.session_id)
    return {"ok": True}


@app.post("/api/session/rename")
def api_session_rename(payload: SessionRenameRequest):
    session = rename_session(payload.session_id, payload.title)
    return {
        "ok": True,
        "session_id": session["session_id"],
        "title": session["title"],
    }


@app.post("/api/chat")
def api_chat_post(payload: ChatRequest):
    content = str(payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    model = str(payload.model or OPENAI_MODEL).strip() or OPENAI_MODEL

    session_id = str(payload.session_id or "").strip()
    if not session_id:
        session = create_session()
        session_id = session["session_id"]

    _ = get_session_or_404(session_id)

    append_message(session_id, "user", content, model)
    session_after_user = get_session_or_404(session_id)

    reply = get_completion_text(
        build_openai_messages(session_after_user["messages"]),
        model,
    )

    assistant_message = append_message(session_id, "assistant", reply, model)
    final_session = get_session_or_404(session_id)

    return {
        "session_id": session_id,
        "title": final_session["title"],
        "message_count": final_session["message_count"],
        "last_model": final_session["last_model"],
        "message": assistant_message,
        "messages": final_session["messages"],
    }


@app.post("/api/chat/stream")
def api_chat_stream(payload: ChatRequest):
    content = str(payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    model = str(payload.model or OPENAI_MODEL).strip() or OPENAI_MODEL

    session_id = str(payload.session_id or "").strip()
    if not session_id:
        session = create_session()
        session_id = session["session_id"]

    _ = get_session_or_404(session_id)
    user_message = append_message(session_id, "user", content, model)
    session_after_user = get_session_or_404(session_id)

    def event_stream():
        full_text = ""

        try:
            yield sse_event(
                "start",
                {
                    "session_id": session_id,
                    "title": session_after_user["title"],
                    "model_used": model,
                },
            )

            openai_messages = build_openai_messages(session_after_user["messages"])

            for chunk in stream_completion_chunks(openai_messages, model):
                full_text += chunk
                yield sse_event(
                    "delta",
                    {
                        "text": chunk,
                        "model_used": model,
                    },
                )

            assistant_text = full_text.strip() or "No response returned."
            assistant_message = append_message(session_id, "assistant", assistant_text, model)
            final_session = get_session_or_404(session_id)

            yield sse_event(
                "done",
                {
                    "session_id": session_id,
                    "title": final_session["title"],
                    "model_used": model,
                    "message": assistant_message,
                    "user_message": user_message,
                },
            )

        except Exception as error:
            yield sse_event(
                "error",
                {
                    "message": str(error),
                    "model_used": model,
                },
            )

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
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)