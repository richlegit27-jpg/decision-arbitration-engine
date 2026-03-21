from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.routers.chat_stream import router as chat_stream_router
from backend.routers.files import router as files_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "backend" / "data"
STATE_FILE = DATA_DIR / "nova_state.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nova", version="6.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

AVAILABLE_MODELS: List[Dict[str, str]] = [
    {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"},
    {"id": "gpt-4.1", "name": "GPT-4.1"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
    {"id": "gpt-4o", "name": "GPT-4o"},
]

ALLOWED_MODEL_IDS = {item["id"] for item in AVAILABLE_MODELS}
DEFAULT_MODEL = "gpt-4.1-mini"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_default_models() -> List[Dict[str, str]]:
    return [dict(item) for item in AVAILABLE_MODELS]


def default_state() -> Dict[str, Any]:
    return {
        "selectedModel": DEFAULT_MODEL,
        "activeChatId": None,
        "chats": [],
        "messagesByChatId": {},
        "models": get_default_models(),
        "memory": [],
        "conversationSummaries": {},
    }


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return default_state()

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default_state()

        base = default_state()
        base.update(data)

        selected_model = str(base.get("selectedModel", DEFAULT_MODEL)).strip()
        if selected_model not in ALLOWED_MODEL_IDS:
            base["selectedModel"] = DEFAULT_MODEL

        base["models"] = get_default_models()

        if not isinstance(base.get("chats"), list):
            base["chats"] = []

        if not isinstance(base.get("messagesByChatId"), dict):
            base["messagesByChatId"] = {}

        if not isinstance(base.get("memory"), list):
            base["memory"] = []

        if not isinstance(base.get("conversationSummaries"), dict):
            base["conversationSummaries"] = {}

        return base
    except Exception:
        return default_state()


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize_model(model: str) -> str:
    requested = str(model or "").strip()
    return requested if requested in ALLOWED_MODEL_IDS else DEFAULT_MODEL


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/state")
async def get_state() -> JSONResponse:
    state = load_state()
    state["models"] = get_default_models()
    state["selectedModel"] = normalize_model(str(state.get("selectedModel", DEFAULT_MODEL)))
    return JSONResponse(state)


@app.post("/api/state")
async def post_state(request: Request) -> JSONResponse:
    data = await request.json()
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "error": "Invalid state payload."}, status_code=400)

    current = default_state()
    current.update(data)
    current["selectedModel"] = normalize_model(str(current.get("selectedModel", DEFAULT_MODEL)))
    current["models"] = get_default_models()

    if not isinstance(current.get("chats"), list):
        current["chats"] = []

    if not isinstance(current.get("messagesByChatId"), dict):
        current["messagesByChatId"] = {}

    if not isinstance(current.get("memory"), list):
        current["memory"] = []

    if not isinstance(current.get("conversationSummaries"), dict):
        current["conversationSummaries"] = {}

    save_state(current)
    return JSONResponse({"ok": True})


@app.get("/api/models")
async def get_models() -> JSONResponse:
    return JSONResponse({"models": get_default_models()})


@app.get("/api/chat/models")
async def get_chat_models() -> JSONResponse:
    return JSONResponse({"models": get_default_models()})


@app.get("/api/auth/status")
async def auth_status() -> JSONResponse:
    has_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return JSONResponse(
        {
            "authenticated": has_key,
            "has_openai_key": has_key,
            "openai_sdk_available": True,
        }
    )


app.include_router(chat_stream_router)
app.include_router(files_router)