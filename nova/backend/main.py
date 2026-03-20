from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "backend" / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
STATE_FILE = DATA_DIR / "nova_state.json"
USERS_FILE = DATA_DIR / "users.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nova", version="6.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_SECRET = os.getenv("NOVA_SESSION_SECRET", "").strip() or "nova-dev-session-secret-change-me"
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="nova_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 30,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
ALLOWED_MODELS = [
    item.strip()
    for item in os.getenv("OPENAI_ALLOWED_MODELS", "gpt-4.1-mini,gpt-4.1").split(",")
    if item.strip()
]
if DEFAULT_MODEL not in ALLOWED_MODELS:
    ALLOWED_MODELS.insert(0, DEFAULT_MODEL)

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

APP_STATE: Dict[str, Any] = {}
STOP_FLAGS: Dict[str, bool] = {}
ACTIVE_MODEL = DEFAULT_MODEL

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".json",
    ".csv",
    ".log",
    ".yaml",
    ".yml",
    ".xml",
    ".ini",
    ".env",
    ".sql",
    ".ps1",
    ".sh",
    ".bat",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".go",
    ".rs",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

MAX_TEXT_FILE_BYTES = 200_000
MAX_FILE_BYTES = 8_000_000
MAX_CONTEXT_CHARS_PER_FILE = 12_000
MAX_TOTAL_FILE_CONTEXT_CHARS = 30_000
MAX_TOTAL_MEMORY_CONTEXT_CHARS = 10_000
MAX_MEMORY_TEXT_LENGTH = 1_000
PASSWORD_ITERATIONS = 200_000
MAX_AUTO_MEMORY_ITEMS_PER_MESSAGE = 3


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def slugify_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return cleaned[:120] or f"file_{uuid4().hex}"


def sse_event(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def build_chat_summary(chat: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": chat["id"],
        "title": chat["title"],
        "created_at": chat["created_at"],
        "updated_at": chat["updated_at"],
        "message_count": len(chat["messages"]),
        "file_count": len(chat.get("files", [])),
    }


def normalize_memory_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(item.get("id") or uuid4().hex),
        "text": str(item.get("text") or "").strip(),
        "kind": str(item.get("kind") or "general").strip() or "general",
        "pinned": bool(item.get("pinned", False)),
        "created_at": str(item.get("created_at") or now_iso()),
        "updated_at": str(item.get("updated_at") or item.get("created_at") or now_iso()),
    }


def default_state() -> Dict[str, Any]:
    return {
        "active_model": DEFAULT_MODEL,
        "users": {},
    }


def default_users() -> Dict[str, Any]:
    return {
        "users": {}
    }


def persist_state() -> None:
    state = {
        "active_model": ACTIVE_MODEL,
        "users": APP_STATE.get("users", {}),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_state() -> None:
    global ACTIVE_MODEL, APP_STATE

    if not STATE_FILE.exists():
        ACTIVE_MODEL = DEFAULT_MODEL
        APP_STATE = default_state()
        persist_state()
        return

    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        raw = default_state()

    ACTIVE_MODEL = str(raw.get("active_model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if ACTIVE_MODEL not in ALLOWED_MODELS:
        ACTIVE_MODEL = DEFAULT_MODEL

    raw_users = raw.get("users")
    if not isinstance(raw_users, dict):
        raw_users = {}

    normalized_users: Dict[str, Any] = {}
    for username, user_state in raw_users.items():
        if not isinstance(user_state, dict):
            continue

        raw_chats = user_state.get("chats") or {}
        if not isinstance(raw_chats, dict):
            raw_chats = {}

        normalized_chats: Dict[str, Dict[str, Any]] = {}
        for chat_id, chat in raw_chats.items():
            if not isinstance(chat, dict):
                continue

            normalized_chats[chat_id] = {
                "id": str(chat.get("id") or chat_id),
                "title": str(chat.get("title") or "New Chat"),
                "created_at": str(chat.get("created_at") or now_iso()),
                "updated_at": str(chat.get("updated_at") or now_iso()),
                "messages": list(chat.get("messages") or []),
                "files": list(chat.get("files") or []),
            }

        raw_memory_items = user_state.get("memory_items") or []
        if not isinstance(raw_memory_items, list):
            raw_memory_items = []

        normalized_memory_items: List[Dict[str, Any]] = []
        for item in raw_memory_items:
            if not isinstance(item, dict):
                continue
            normalized_item = normalize_memory_item(item)
            if normalized_item["text"]:
                normalized_memory_items.append(normalized_item)

        normalized_users[str(username)] = {
            "chats": normalized_chats,
            "memory_items": normalized_memory_items,
        }

    APP_STATE = {
        "users": normalized_users,
    }
    persist_state()


def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        users = default_users()
        USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
        return users

    try:
        raw = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        raw = default_users()

    users = raw.get("users")
    if not isinstance(users, dict):
        users = {}

    normalized: Dict[str, Any] = {}
    for username, info in users.items():
        if not isinstance(info, dict):
            continue

        normalized[str(username)] = {
            "username": str(info.get("username") or username),
            "password_hash": str(info.get("password_hash") or ""),
            "salt": str(info.get("salt") or ""),
            "created_at": str(info.get("created_at") or now_iso()),
        }

    result = {"users": normalized}
    USERS_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def persist_users(users_data: Dict[str, Any]) -> None:
    USERS_FILE.write_text(json.dumps(users_data, indent=2), encoding="utf-8")


USER_STORE = load_users()


def get_user_record(username: str) -> Dict[str, Any] | None:
    return USER_STORE.get("users", {}).get(username)


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return digest.hex()


def create_password_hash(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return salt, hash_password(password, salt)


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


def validate_username(username: str) -> str | None:
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 32:
        return "Username must be 32 characters or less."
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
        return "Username can only contain letters, numbers, underscore, dot, and dash."
    return None


def validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 200:
        return "Password is too long."
    return None


def ensure_user_space(username: str) -> None:
    users = APP_STATE.setdefault("users", {})
    if username not in users or not isinstance(users.get(username), dict):
        users[username] = {"chats": {}, "memory_items": []}
    else:
        if "chats" not in users[username] or not isinstance(users[username].get("chats"), dict):
            users[username]["chats"] = {}
        if "memory_items" not in users[username] or not isinstance(users[username].get("memory_items"), list):
            users[username]["memory_items"] = []
    persist_state()


def get_request_user(request: Request) -> str | None:
    username = request.session.get("username")
    if not username:
        return None

    if not get_user_record(str(username)):
        request.session.clear()
        return None

    ensure_user_space(str(username))
    return str(username)


def require_user_json(request: Request) -> str | None:
    return get_request_user(request)


def require_user_or_redirect(request: Request) -> str | None:
    return get_request_user(request)


def get_user_chat_store(username: str) -> Dict[str, Dict[str, Any]]:
    ensure_user_space(username)
    users = APP_STATE.setdefault("users", {})
    user_state = users.setdefault(username, {"chats": {}, "memory_items": []})
    chats = user_state.setdefault("chats", {})
    if not isinstance(chats, dict):
        user_state["chats"] = {}
        chats = user_state["chats"]
    return chats


def get_user_memory_store(username: str) -> List[Dict[str, Any]]:
    ensure_user_space(username)
    users = APP_STATE.setdefault("users", {})
    user_state = users.setdefault(username, {"chats": {}, "memory_items": []})
    memory_items = user_state.setdefault("memory_items", [])
    if not isinstance(memory_items, list):
        user_state["memory_items"] = []
        memory_items = user_state["memory_items"]
    return memory_items


def parse_iso_for_sort(value: Any) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        return datetime.min
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


def sort_memory_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            0 if bool(item.get("pinned")) else 1,
            -parse_iso_for_sort(item.get("updated_at") or item.get("created_at")).timestamp(),
            -parse_iso_for_sort(item.get("created_at")).timestamp(),
        ),
    )


def canonical_memory_text(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def memory_exists(username: str, text: str) -> bool:
    canonical_target = canonical_memory_text(text)
    if not canonical_target:
        return True

    for item in get_user_memory_store(username):
        if canonical_memory_text(str(item.get("text") or "")) == canonical_target:
            return True
    return False


def save_memory_item(username: str, text: str, kind: str = "general", pinned: bool = False) -> Dict[str, Any] | None:
    clean_text = str(text or "").strip()
    clean_kind = str(kind or "general").strip() or "general"

    if not clean_text:
        return None

    if len(clean_text) > MAX_MEMORY_TEXT_LENGTH:
        clean_text = clean_text[:MAX_MEMORY_TEXT_LENGTH].strip()

    if memory_exists(username, clean_text):
        return None

    item = normalize_memory_item(
        {
            "id": uuid4().hex,
            "text": clean_text,
            "kind": clean_kind,
            "pinned": bool(pinned),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )
    get_user_memory_store(username).append(item)
    persist_state()
    return item


def describe_learned_memory(item: Dict[str, Any]) -> str:
    prefix = "📌" if bool(item.get("pinned")) else "🧠"
    kind = str(item.get("kind") or "general").strip() or "general"
    text = str(item.get("text") or "").strip()
    return f"{prefix} Learned {kind}: {text}"


def extract_auto_memories(user_message: str) -> List[Dict[str, Any]]:
    text = " ".join(str(user_message or "").strip().split())
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    lowered = text.lower()

    strong_patterns = [
        r"\bi always want (.+)",
        r"\balways answer with (.+)",
        r"\bi prefer (.+)",
        r"\bfrom now on (.+)",
        r"\balways use (.+)",
        r"\bnever use (.+)",
        r"\bi want you to always (.+)",
        r"\bi do not want (.+)",
        r"\bdon't ask me to (.+)",
        r"\bpower[s]?hell me always\b",
        r"\bsmff\b",
    ]

    medium_patterns = [
        r"\bmy project is called (.+)",
        r"\bthe project name is (.+)",
        r"\bremember that (.+)",
        r"\bi am using (.+)",
        r"\buse this path (.+)",
        r"\bmy preferred file path format is (.+)",
    ]

    for pattern in strong_patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue

        if pattern.endswith(r"\bpower[s]?hell me always\b"):
            results.append(
                {
                    "text": "User prefers PowerShell commands.",
                    "kind": "preference",
                    "pinned": True,
                }
            )
            continue

        if pattern.endswith(r"\bsmff\b"):
            results.append(
                {
                    "text": "User prefers full files, not snippets.",
                    "kind": "workflow",
                    "pinned": True,
                }
            )
            continue

        captured = match.group(1).strip(" .,:;!-")
        if captured:
            normalized = captured[0].upper() + captured[1:] if len(captured) > 1 else captured.upper()
            results.append(
                {
                    "text": f"User preference: {normalized}.",
                    "kind": "preference",
                    "pinned": True,
                }
            )

    for pattern in medium_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        captured = match.group(1).strip(" .,:;!-")
        if not captured:
            continue

        if pattern in {r"\bmy project is called (.+)", r"\bthe project name is (.+)"}:
            results.append(
                {
                    "text": f"Project name: {captured}.",
                    "kind": "project",
                    "pinned": True,
                }
            )
        elif pattern == r"\bremember that (.+)":
            results.append(
                {
                    "text": captured[0].upper() + captured[1:] if len(captured) > 1 else captured.upper(),
                    "kind": "general",
                    "pinned": False,
                }
            )
        elif pattern == r"\bi am using (.+)":
            results.append(
                {
                    "text": f"User is using {captured}.",
                    "kind": "environment",
                    "pinned": False,
                }
            )
        elif pattern in {r"\buse this path (.+)", r"\bmy preferred file path format is (.+)"}:
            results.append(
                {
                    "text": f"Preferred file path format: {captured}.",
                    "kind": "workflow",
                    "pinned": True,
                }
            )

    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in results:
        key = canonical_memory_text(item["text"])
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped[:MAX_AUTO_MEMORY_ITEMS_PER_MESSAGE]


def auto_learn_from_message(username: str, user_message: str) -> List[Dict[str, Any]]:
    created: List[Dict[str, Any]] = []

    for candidate in extract_auto_memories(user_message):
        saved = save_memory_item(
            username=username,
            text=str(candidate.get("text") or ""),
            kind=str(candidate.get("kind") or "general"),
            pinned=bool(candidate.get("pinned")),
        )
        if saved:
            created.append(saved)

    return created


def create_chat_record(username: str, title: str | None = None) -> Dict[str, Any]:
    chat_id = uuid4().hex
    created_at = now_iso()
    safe_title = (title or "").strip() or "New Chat"

    chat = {
        "id": chat_id,
        "title": safe_title,
        "created_at": created_at,
        "updated_at": created_at,
        "messages": [],
        "files": [],
    }
    get_user_chat_store(username)[chat_id] = chat
    persist_state()
    return chat


def get_or_create_chat(username: str, chat_id: str | None) -> Dict[str, Any]:
    chat_store = get_user_chat_store(username)
    if chat_id and chat_id in chat_store:
        return chat_store[chat_id]
    return create_chat_record(username)


def maybe_update_chat_title(chat: Dict[str, Any], user_message: str) -> None:
    if chat["title"] != "New Chat":
        return

    cleaned = " ".join(user_message.strip().split())
    if not cleaned:
        return

    title = cleaned[:40].strip()
    if len(cleaned) > 40:
        title += "..."
    chat["title"] = title


def chat_upload_dir(username: str, chat_id: str) -> Path:
    path = UPLOADS_DIR / username / chat_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_text_extension(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def is_image_extension(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def read_text_file_for_context(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""

    if path.stat().st_size > MAX_TEXT_FILE_BYTES:
        return f"[Skipped file content because file is too large for inline context: {path.name}]"

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return f"[Could not decode text content for file: {path.name}]"

    if len(text) > MAX_CONTEXT_CHARS_PER_FILE:
        text = text[:MAX_CONTEXT_CHARS_PER_FILE] + "\n...[truncated]"
    return text


def build_memory_context(username: str) -> str:
    items = sort_memory_items(get_user_memory_store(username))
    if not items:
        return ""

    pinned_lines: List[str] = []
    recent_lines: List[str] = []
    total_chars = 0

    for item in items:
        text = str(item.get("text") or "").strip()
        if not text:
            continue

        kind = str(item.get("kind") or "general").strip() or "general"
        label = f"[PINNED:{kind}]" if bool(item.get("pinned")) else f"[MEMORY:{kind}]"
        line = f"{label} {text}"

        if total_chars + len(line) + 1 > MAX_TOTAL_MEMORY_CONTEXT_CHARS:
            break

        if bool(item.get("pinned")):
            pinned_lines.append(line)
        else:
            recent_lines.append(line)

        total_chars += len(line) + 1

    sections: List[str] = []

    if pinned_lines:
        sections.append("Pinned user preferences and durable instructions:\n" + "\n".join(pinned_lines))

    if recent_lines:
        sections.append("Other saved memory:\n" + "\n".join(recent_lines))

    if not sections:
        return ""

    return "\n\n".join(sections)


def build_file_context(chat: Dict[str, Any]) -> str:
    files = chat.get("files") or []
    if not files:
        return ""

    parts: List[str] = []
    total_chars = 0

    for file_meta in files:
        stored_path = Path(str(file_meta.get("stored_path") or ""))
        if not stored_path.exists():
            continue

        original_name = str(file_meta.get("original_name") or stored_path.name)
        file_kind = str(file_meta.get("kind") or "file")

        if file_kind == "image":
            parts.append(
                f"Image attached: {original_name} "
                f"(image is available in workspace but not yet passed as vision input in this version)."
            )
            continue

        if file_kind != "text":
            parts.append(f"File attached: {original_name}")
            continue

        content = read_text_file_for_context(stored_path)
        if not content:
            continue

        chunk = f"Attached file: {original_name}\n```text\n{content}\n```"
        if total_chars + len(chunk) > MAX_TOTAL_FILE_CONTEXT_CHARS:
            break

        parts.append(chunk)
        total_chars += len(chunk)

    return "\n\n".join(parts).strip()


def build_openai_input(username: str, chat: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    memory_context = build_memory_context(username)
    if memory_context:
        items.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Persistent memory for this user. "
                            "Treat pinned memory as stronger than normal memory. "
                            "Use saved memory when relevant, especially for user preferences, workflow habits, and durable instructions. "
                            "Do not mention the memory block unless useful.\n\n"
                            f"{memory_context}"
                        ),
                    }
                ],
            }
        )

    file_context = build_file_context(chat)
    if file_context:
        items.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Workspace file context for this chat. "
                            "Use it when relevant, but do not pretend to have read files that are not shown below.\n\n"
                            f"{file_context}"
                        ),
                    }
                ],
            }
        )

    for message in chat.get("messages", []):
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()

        if not content:
            continue

        if role == "user":
            items.append(
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}],
                }
            )
        elif role == "assistant":
            items.append(
                {
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": content}],
                }
            )

    return items


def get_active_model() -> str:
    return ACTIVE_MODEL


load_state()


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    username = get_request_user(request)
    if username:
        return RedirectResponse(url="/app", status_code=303)

    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
        },
    )


@app.get("/app", response_class=HTMLResponse)
async def app_page(request: Request):
    username = require_user_or_redirect(request)
    if not username:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "username": username,
        },
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    username = get_request_user(request)
    if username:
        return RedirectResponse(url="/app", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_api(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        data = {}

    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")

    if not username or not password:
        return JSONResponse({"error": "Username and password are required."}, status_code=400)

    user = get_user_record(username)
    if not user:
        return JSONResponse({"error": "Invalid username or password."}, status_code=401)

    salt = str(user.get("salt") or "")
    password_hash = str(user.get("password_hash") or "")
    if not salt or not password_hash or not verify_password(password, salt, password_hash):
        return JSONResponse({"error": "Invalid username or password."}, status_code=401)

    request.session["username"] = username
    ensure_user_space(username)

    return JSONResponse(
        {
            "ok": True,
            "username": username,
            "redirect_to": "/app",
        }
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    username = get_request_user(request)
    if username:
        return RedirectResponse(url="/app", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    username = require_user_or_redirect(request)
    if not username:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "account.html",
        {
            "request": request,
            "username": username,
        },
    )


@app.post("/register")
async def register_api(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        data = {}

    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")

    username_error = validate_username(username)
    if username_error:
        return JSONResponse({"error": username_error}, status_code=400)

    password_error = validate_password(password)
    if password_error:
        return JSONResponse({"error": password_error}, status_code=400)

    if get_user_record(username):
        return JSONResponse({"error": "Username already exists."}, status_code=409)

    salt, password_hash = create_password_hash(password)

    USER_STORE.setdefault("users", {})[username] = {
        "username": username,
        "password_hash": password_hash,
        "salt": salt,
        "created_at": now_iso(),
    }
    persist_users(USER_STORE)

    ensure_user_space(username)
    request.session["username"] = username

    return JSONResponse(
        {
            "ok": True,
            "username": username,
            "redirect_to": "/app",
        }
    )


@app.post("/account/password")
async def change_account_password(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    current_password = str(data.get("current_password") or "")
    new_password = str(data.get("new_password") or "")

    if not current_password or not new_password:
        return JSONResponse({"error": "Current password and new password are required."}, status_code=400)

    user = get_user_record(username)
    if not user:
        request.session.clear()
        return JSONResponse({"error": "User not found."}, status_code=404)

    salt = str(user.get("salt") or "")
    password_hash = str(user.get("password_hash") or "")

    if not salt or not password_hash or not verify_password(current_password, salt, password_hash):
        return JSONResponse({"error": "Current password is incorrect."}, status_code=401)

    password_error = validate_password(new_password)
    if password_error:
        return JSONResponse({"error": password_error}, status_code=400)

    if verify_password(new_password, salt, password_hash):
        return JSONResponse({"error": "New password must be different from the current password."}, status_code=400)

    new_salt, new_hash = create_password_hash(new_password)

    USER_STORE.setdefault("users", {})[username] = {
        **user,
        "username": username,
        "salt": new_salt,
        "password_hash": new_hash,
    }
    persist_users(USER_STORE)

    return JSONResponse(
        {
            "ok": True,
            "message": "Password updated successfully.",
        }
    )


@app.post("/logout")
async def logout_api(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"ok": True, "redirect_to": "/login"})


@app.get("/logout")
async def logout_get(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/api/health")
async def health(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat_store = get_user_chat_store(username)
    memory_store = get_user_memory_store(username)
    return JSONResponse(
        {
            "ok": True,
            "app": "Nova",
            "openai_configured": bool(client),
            "model": get_active_model(),
            "allowed_models": ALLOWED_MODELS,
            "chat_count": len(chat_store),
            "memory_count": len(memory_store),
            "username": username,
        }
    )


@app.get("/api/models")
async def get_models(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    return JSONResponse(
        {
            "active_model": get_active_model(),
            "allowed_models": ALLOWED_MODELS,
            "username": username,
        }
    )


@app.post("/api/models")
async def set_model(request: Request) -> JSONResponse:
    global ACTIVE_MODEL

    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    model = str(data.get("model") or "").strip()
    if not model:
        return JSONResponse({"error": "Model is required."}, status_code=400)

    if model not in ALLOWED_MODELS:
        return JSONResponse(
            {
                "error": "Model is not allowed.",
                "allowed_models": ALLOWED_MODELS,
            },
            status_code=400,
        )

    ACTIVE_MODEL = model
    persist_state()
    return JSONResponse({"ok": True, "active_model": ACTIVE_MODEL})


@app.get("/api/memory")
async def get_memory(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    items = sort_memory_items(get_user_memory_store(username))
    return JSONResponse({"items": items})


@app.post("/api/memory")
async def create_memory(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    text = str(data.get("text") or "").strip()
    kind = str(data.get("kind") or "general").strip() or "general"
    pinned = bool(data.get("pinned", False))

    if not text:
        return JSONResponse({"error": "Memory text is required."}, status_code=400)

    if len(text) > MAX_MEMORY_TEXT_LENGTH:
        return JSONResponse({"error": f"Memory text must be {MAX_MEMORY_TEXT_LENGTH} characters or less."}, status_code=400)

    item = normalize_memory_item(
        {
            "id": uuid4().hex,
            "text": text,
            "kind": kind,
            "pinned": pinned,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )

    items = get_user_memory_store(username)
    items.append(item)
    persist_state()

    return JSONResponse({"ok": True, "item": item, "items": sort_memory_items(items)})


@app.put("/api/memory/{memory_id}")
async def update_memory(memory_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    items = get_user_memory_store(username)
    target = None
    for item in items:
        if str(item.get("id")) == memory_id:
            target = item
            break

    if not target:
        return JSONResponse({"error": "Memory not found."}, status_code=404)

    if "text" in data:
        text = str(data.get("text") or "").strip()
        if not text:
            return JSONResponse({"error": "Memory text cannot be empty."}, status_code=400)
        if len(text) > MAX_MEMORY_TEXT_LENGTH:
            return JSONResponse({"error": f"Memory text must be {MAX_MEMORY_TEXT_LENGTH} characters or less."}, status_code=400)
        target["text"] = text

    if "kind" in data:
        target["kind"] = str(data.get("kind") or "general").strip() or "general"

    if "pinned" in data:
        target["pinned"] = bool(data.get("pinned"))

    target["updated_at"] = now_iso()
    persist_state()

    return JSONResponse({"ok": True, "item": target, "items": sort_memory_items(items)})


@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    items = get_user_memory_store(username)
    remaining = [item for item in items if str(item.get("id")) != memory_id]

    if len(remaining) == len(items):
        return JSONResponse({"error": "Memory not found."}, status_code=404)

    APP_STATE["users"][username]["memory_items"] = remaining
    persist_state()

    return JSONResponse({"ok": True, "items": sort_memory_items(remaining)})


@app.delete("/api/memory")
async def delete_all_memory(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    APP_STATE["users"][username]["memory_items"] = []
    persist_state()
    return JSONResponse({"ok": True, "items": []})


@app.get("/api/chats")
async def get_chats(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat_store = get_user_chat_store(username)
    chats: List[Dict[str, Any]] = sorted(
        (build_chat_summary(chat) for chat in chat_store.values()),
        key=lambda item: item["updated_at"],
        reverse=True,
    )
    return JSONResponse({"chats": chats})


@app.post("/api/chats")
async def create_chat(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    title = str(data.get("title") or "").strip() or "New Chat"
    chat = create_chat_record(username=username, title=title)
    return JSONResponse({"chat": build_chat_summary(chat)})


@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    return JSONResponse(
        {
            "chat": build_chat_summary(chat),
            "messages": chat["messages"],
            "files": chat.get("files", []),
        }
    )


@app.get("/api/chats/{chat_id}/export")
async def export_chat(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    return JSONResponse(
        {
            "chat": {
                "id": chat["id"],
                "title": chat["title"],
                "created_at": chat["created_at"],
                "updated_at": chat["updated_at"],
                "messages": chat["messages"],
                "files": [
                    {
                        "id": item.get("id"),
                        "original_name": item.get("original_name"),
                        "kind": item.get("kind"),
                        "size": item.get("size"),
                        "created_at": item.get("created_at"),
                    }
                    for item in chat.get("files", [])
                ],
            }
        }
    )


@app.post("/api/chats/{chat_id}/rename")
async def rename_chat(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        data = {}

    title = str(data.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "Title is required."}, status_code=400)

    chat["title"] = title[:120]
    chat["updated_at"] = now_iso()
    persist_state()
    return JSONResponse({"ok": True, "chat": build_chat_summary(chat)})


@app.post("/api/chats/{chat_id}/upload")
async def upload_files(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    form = await request.form()
    upload_items = form.getlist("files")

    if not upload_items:
        return JSONResponse({"error": "No files received."}, status_code=400)

    saved: List[Dict[str, Any]] = []
    target_dir = chat_upload_dir(username, chat_id)

    for item in upload_items:
        if not isinstance(item, UploadFile):
            continue

        original_name = item.filename or f"upload_{uuid4().hex}"
        safe_name = f"{uuid4().hex}_{slugify_filename(original_name)}"
        target_path = target_dir / safe_name

        contents = await item.read()
        size = len(contents)

        if size > MAX_FILE_BYTES:
            continue

        target_path.write_bytes(contents)

        suffix = target_path.suffix.lower()
        kind = "binary"
        if suffix in TEXT_EXTENSIONS:
            kind = "text"
        elif suffix in IMAGE_EXTENSIONS:
            kind = "image"

        meta = {
            "id": uuid4().hex,
            "original_name": original_name,
            "stored_name": safe_name,
            "stored_path": str(target_path),
            "kind": kind,
            "size": size,
            "created_at": now_iso(),
        }
        chat.setdefault("files", []).append(meta)
        saved.append(meta)

    chat["updated_at"] = now_iso()
    persist_state()

    return JSONResponse(
        {
            "ok": True,
            "files": saved,
            "chat": build_chat_summary(chat),
        }
    )


@app.delete("/api/chats/{chat_id}/files/{file_id}")
async def delete_file(chat_id: str, file_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    files = chat.get("files", [])
    target = None
    remaining = []

    for item in files:
        if str(item.get("id")) == file_id:
            target = item
        else:
            remaining.append(item)

    if not target:
        return JSONResponse({"error": "File not found."}, status_code=404)

    stored_path = Path(str(target.get("stored_path") or ""))
    if stored_path.exists():
        try:
            stored_path.unlink()
        except Exception:
            pass

    chat["files"] = remaining
    chat["updated_at"] = now_iso()
    persist_state()

    return JSONResponse(
        {
            "ok": True,
            "chat": build_chat_summary(chat),
            "files": remaining,
        }
    )


@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    return JSONResponse({"messages": chat["messages"]})


@app.post("/api/chats/{chat_id}/clear")
async def clear_chat(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat = get_user_chat_store(username).get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    chat["messages"] = []
    chat["updated_at"] = now_iso()
    persist_state()

    return JSONResponse(
        {
            "chat": build_chat_summary(chat),
            "messages": [],
        }
    )


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    chat_store = get_user_chat_store(username)
    chat = chat_store.get(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found."}, status_code=404)

    del chat_store[chat_id]
    STOP_FLAGS.pop(f"{username}:{chat_id}", None)

    upload_dir = UPLOADS_DIR / username / chat_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)

    persist_state()
    return JSONResponse({"ok": True, "deleted_chat_id": chat_id})


@app.post("/api/chat/stop")
async def stop_chat_stream(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    chat_id = str(data.get("chat_id") or "").strip()
    if not chat_id:
        return JSONResponse({"error": "chat_id is required."}, status_code=400)

    STOP_FLAGS[f"{username}:{chat_id}"] = True
    return JSONResponse({"ok": True, "chat_id": chat_id})


@app.post("/api/chat")
async def chat_api(request: Request) -> JSONResponse:
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    user_message = str(data.get("message") or "").strip()
    incoming_chat_id = str(data.get("chat_id") or "").strip() or None

    if not user_message:
        return JSONResponse({"reply": "No message received."})

    learned_memories = auto_learn_from_message(username, user_message)

    chat = get_or_create_chat(username, incoming_chat_id)

    user_entry = {
        "id": uuid4().hex,
        "role": "user",
        "content": user_message,
        "created_at": now_iso(),
    }
    chat["messages"].append(user_entry)

    maybe_update_chat_title(chat, user_message)
    chat["updated_at"] = now_iso()
    persist_state()

    if not client:
        reply_text = "OpenAI API key is missing on the backend."
    else:
        try:
            response = client.responses.create(
                model=get_active_model(),
                instructions=(
                    "You are Nova, a sharp, direct AI assistant inside a custom app. "
                    "Use attached text files when relevant. "
                    "Use saved user memory when relevant. "
                    "Treat pinned memory as higher priority than normal memory. "
                    "Honor durable user preferences and workflow instructions when they fit the request. "
                    "Do not claim to inspect image contents unless explicitly given image vision input. "
                    "Be concise, clear, and strong with software help."
                ),
                input=build_openai_input(username, chat),
            )
            reply_text = getattr(response, "output_text", "") or "No reply returned."
        except Exception as exc:
            reply_text = f"OpenAI request failed: {exc}"

    assistant_entry = {
        "id": uuid4().hex,
        "role": "assistant",
        "content": reply_text,
        "created_at": now_iso(),
    }
    chat["messages"].append(assistant_entry)
    chat["updated_at"] = now_iso()
    persist_state()

    return JSONResponse(
        {
            "chat": build_chat_summary(chat),
            "reply": reply_text,
            "messages": chat["messages"],
            "files": chat.get("files", []),
            "memory_items": sort_memory_items(get_user_memory_store(username)),
            "learned_memories": learned_memories,
            "learned_memory_messages": [describe_learned_memory(item) for item in learned_memories],
        }
    )


@app.post("/api/chat/stream", response_model=None)
async def chat_stream(request: Request):
    username = require_user_json(request)
    if not username:
        return JSONResponse({"error": "Unauthorized."}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    user_message = str(data.get("message") or "").strip()
    incoming_chat_id = str(data.get("chat_id") or "").strip() or None

    def event_generator():
        if not user_message:
            yield sse_event("error", {"message": "No message received."})
            return

        learned_memories = auto_learn_from_message(username, user_message)

        chat = get_or_create_chat(username, incoming_chat_id)
        stop_key = f"{username}:{chat['id']}"
        STOP_FLAGS[stop_key] = False

        user_entry = {
            "id": uuid4().hex,
            "role": "user",
            "content": user_message,
            "created_at": now_iso(),
        }
        chat["messages"].append(user_entry)

        maybe_update_chat_title(chat, user_message)
        chat["updated_at"] = now_iso()
        persist_state()

        yield sse_event(
            "start",
            {
                "chat": build_chat_summary(chat),
                "files": chat.get("files", []),
                "learned_memories": learned_memories,
                "learned_memory_messages": [describe_learned_memory(item) for item in learned_memories],
            },
        )

        if not client:
            error_text = "OpenAI API key is missing on the backend."

            assistant_entry = {
                "id": uuid4().hex,
                "role": "assistant",
                "content": error_text,
                "created_at": now_iso(),
            }
            chat["messages"].append(assistant_entry)
            chat["updated_at"] = now_iso()
            persist_state()

            yield sse_event("chunk", {"text": error_text})
            yield sse_event(
                "done",
                {
                    "chat": build_chat_summary(chat),
                    "reply": error_text,
                    "messages": chat["messages"],
                    "files": chat.get("files", []),
                    "stopped": False,
                    "memory_items": sort_memory_items(get_user_memory_store(username)),
                    "learned_memories": learned_memories,
                    "learned_memory_messages": [describe_learned_memory(item) for item in learned_memories],
                },
            )
            STOP_FLAGS.pop(stop_key, None)
            return

        full_reply = ""
        stopped = False

        try:
            with client.responses.stream(
                model=get_active_model(),
                instructions=(
                    "You are Nova, a sharp, direct AI assistant inside a custom app. "
                    "Use attached text files when relevant. "
                    "Use saved user memory when relevant. "
                    "Treat pinned memory as higher priority than normal memory. "
                    "Honor durable user preferences and workflow instructions when they fit the request. "
                    "Do not claim to inspect image contents unless explicitly given image vision input. "
                    "Format code cleanly using fenced code blocks when useful."
                ),
                input=build_openai_input(username, chat),
            ) as stream:
                for event in stream:
                    if STOP_FLAGS.get(stop_key):
                        stopped = True
                        break

                    event_type = getattr(event, "type", "")
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, "delta", "") or ""
                        if delta:
                            full_reply += delta
                            yield sse_event("chunk", {"text": delta})

                if not stopped:
                    final_response = stream.get_final_response()
                    final_text = getattr(final_response, "output_text", "") or full_reply

                    if final_text and final_text != full_reply and final_text.startswith(full_reply):
                        remainder = final_text[len(full_reply):]
                        if remainder:
                            full_reply = final_text
                            yield sse_event("chunk", {"text": remainder})
                    elif final_text and not full_reply:
                        full_reply = final_text
                        yield sse_event("chunk", {"text": final_text})

        except Exception as exc:
            error_text = f"OpenAI stream failed: {exc}"
            full_reply = error_text
            yield sse_event("chunk", {"text": error_text})

        if not full_reply and stopped:
            full_reply = "[stopped]"

        assistant_entry = {
            "id": uuid4().hex,
            "role": "assistant",
            "content": full_reply,
            "created_at": now_iso(),
        }
        chat["messages"].append(assistant_entry)
        chat["updated_at"] = now_iso()
        persist_state()

        yield sse_event(
            "done",
            {
                "chat": build_chat_summary(chat),
                "reply": full_reply,
                "messages": chat["messages"],
                "files": chat.get("files", []),
                "stopped": stopped,
                "memory_items": sort_memory_items(get_user_memory_store(username)),
                "learned_memories": learned_memories,
                "learned_memory_messages": [describe_learned_memory(item) for item in learned_memories],
            },
        )

        STOP_FLAGS.pop(stop_key, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )