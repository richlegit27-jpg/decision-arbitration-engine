from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

USERS_FILE = DATA_DIR / "nova_users.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"
SESSIONS_FILE = DATA_DIR / "nova_sessions.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    _ensure_data_dir()

    if not path.exists():
        return default

    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_users() -> dict[str, dict[str, Any]]:
    data = _read_json(USERS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_users(users: dict[str, dict[str, Any]]) -> None:
    _write_json(USERS_FILE, users)


def load_memory() -> list[dict[str, Any]]:
    data = _read_json(MEMORY_FILE, [])
    return data if isinstance(data, list) else []


def save_memory(items: list[dict[str, Any]]) -> None:
    _write_json(MEMORY_FILE, items)


def load_sessions() -> dict[str, dict[str, Any]]:
    data = _read_json(SESSIONS_FILE, {})
    if isinstance(data, dict):
        return data

    if isinstance(data, list):
        fixed: dict[str, dict[str, Any]] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id", "") or "").strip()
            if sid:
                fixed[sid] = item
        return fixed

    return {}


def save_sessions(sessions: dict[str, dict[str, Any]]) -> None:
    _write_json(SESSIONS_FILE, sessions)