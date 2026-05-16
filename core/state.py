from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from core.config import CHATS_DIR, DATA_DIR, FILES_DIR, MEMORY_DIR

APP_STATE_FILE = DATA_DIR / "app_state.json"
CHATS_FILE = CHATS_DIR / "chats.json"
MESSAGES_FILE = CHATS_DIR / "messages.json"
MEMORY_FILE = MEMORY_DIR / "memory.json"
UPLOAD_INDEX_FILE = FILES_DIR / "uploads.json"
USERS_FILE = DATA_DIR / "users.json"

STATE_LOCK = Lock()

APP_STATE: dict[str, Any] = {
    "active_chat_id": None,
    "selected_model": None,
    "user": None,
    "theme": "dark",
}

STOP_FLAGS: dict[str, bool] = {}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_app_state() -> dict[str, Any]:
    global APP_STATE

    data = _read_json(APP_STATE_FILE, APP_STATE.copy())
    if not isinstance(data, dict):
        data = APP_STATE.copy()

    APP_STATE.update(data)
    return APP_STATE


def save_app_state() -> dict[str, Any]:
    with STATE_LOCK:
        _write_json(APP_STATE_FILE, APP_STATE)
    return APP_STATE


def update_app_state(**kwargs: Any) -> dict[str, Any]:
    with STATE_LOCK:
        APP_STATE.update(kwargs)
        _write_json(APP_STATE_FILE, APP_STATE)
    return APP_STATE


def get_app_state() -> dict[str, Any]:
    return APP_STATE


def load_users() -> list[dict[str, Any]]:
    data = _read_json(USERS_FILE, [])
    return data if isinstance(data, list) else []


def save_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with STATE_LOCK:
        _write_json(USERS_FILE, users)
    return users


def find_user(username: str) -> dict[str, Any] | None:
    target = str(username or "").strip().lower()

    for user in load_users():
        if str(user.get("username", "")).strip().lower() == target:
            return user

    return None


def create_user(username: str, password_hash: str) -> dict[str, Any]:
    users = load_users()

    if find_user(username):
        raise ValueError("User already exists.")

    user = {
        "id": max((int(item.get("id", 0)) for item in users), default=0) + 1,
        "username": str(username).strip(),
        "password_hash": str(password_hash),
    }

    users.append(user)
    save_users(users)
    return user


def update_user_password(username: str, password_hash: str) -> dict[str, Any]:
    users = load_users()
    updated: dict[str, Any] | None = None
    target = str(username or "").strip().lower()

    for user in users:
        if str(user.get("username", "")).strip().lower() == target:
            user["password_hash"] = str(password_hash)
            updated = user
            break

    if updated is None:
        raise ValueError("User not found.")

    save_users(users)
    return updated


def load_chats() -> list[dict[str, Any]]:
    data = _read_json(CHATS_FILE, [])
    return data if isinstance(data, list) else []


def save_chats(chats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with STATE_LOCK:
        _write_json(CHATS_FILE, chats)
    return chats


def create_chat(title: str | None = None) -> dict[str, Any]:
    chats = load_chats()
    next_id = len(chats) + 1

    chat = {
        "id": next_id,
        "title": title or f"Chat {next_id}",
    }

    chats.append(chat)
    save_chats(chats)
    return chat


def delete_chat(chat_id: int) -> dict[str, Any]:
    chats = load_chats()
    filtered = [chat for chat in chats if int(chat.get("id", 0)) != chat_id]
    save_chats(filtered)

    messages = load_messages()
    filtered_messages = [
        msg for msg in messages
        if int(msg.get("chat_id", 0)) != chat_id
    ]
    save_messages(filtered_messages)

    if APP_STATE.get("active_chat_id") == chat_id:
        update_app_state(active_chat_id=None)

    return {
        "ok": True,
        "deleted_chat_id": chat_id,
    }


def load_messages() -> list[dict[str, Any]]:
    data = _read_json(MESSAGES_FILE, [])
    return data if isinstance(data, list) else []


def save_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with STATE_LOCK:
        _write_json(MESSAGES_FILE, messages)
    return messages


def get_messages_for_chat(chat_id: int) -> list[dict[str, Any]]:
    messages = load_messages()
    return [
        msg for msg in messages
        if int(msg.get("chat_id", 0)) == chat_id
    ]


def add_message(
    *,
    chat_id: int,
    role: str,
    content: str,
) -> dict[str, Any]:
    messages = load_messages()

    message = {
        "id": len(messages) + 1,
        "chat_id": chat_id,
        "role": role,
        "content": content,
    }

    messages.append(message)
    save_messages(messages)
    return message


def clear_messages(chat_id: int | None = None) -> dict[str, Any]:
    if chat_id is None:
        save_messages([])
        return {"ok": True, "cleared": "all"}

    messages = load_messages()
    filtered = [
        msg for msg in messages
        if int(msg.get("chat_id", 0)) != chat_id
    ]
    save_messages(filtered)

    return {
        "ok": True,
        "cleared_chat_id": chat_id,
    }


def load_memory() -> list[dict[str, Any]]:
    data = _read_json(MEMORY_FILE, [])
    return data if isinstance(data, list) else []


def save_memory(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with STATE_LOCK:
        _write_json(MEMORY_FILE, items)
    return items


def load_upload_index() -> list[dict[str, Any]]:
    data = _read_json(UPLOAD_INDEX_FILE, [])
    return data if isinstance(data, list) else []


def save_upload_index(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with STATE_LOCK:
        _write_json(UPLOAD_INDEX_FILE, items)
    return items


def set_stop_flag(key: str, value: bool) -> None:
    STOP_FLAGS[key] = value


def get_stop_flag(key: str) -> bool:
    return STOP_FLAGS.get(key, False)


def clear_stop_flag(key: str) -> None:
    STOP_FLAGS.pop(key, None)


def initialize_runtime_state() -> None:
    load_app_state()

    if not CHATS_FILE.exists():
        save_chats([])

    if not MESSAGES_FILE.exists():
        save_messages([])

    if not MEMORY_FILE.exists():
        save_memory([])

    if not UPLOAD_INDEX_FILE.exists():
        save_upload_index([])

    if not USERS_FILE.exists():
        save_users([])