from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.parent


def path_exists(path: str | Path) -> bool:
    return Path(path).exists()


def file_exists(path: str | Path) -> bool:
    return Path(path).exists()


def load_json_file(path: str | Path, default: Any = None) -> Any:
    p = Path(path)

    if not p.exists():
        return default

    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_json_file(path: str | Path, default: Any = None) -> Any:
    return load_json_file(path, default)


def atomic_write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    ensure_parent_dir(p)

    fd, temp_path = tempfile.mkstemp(
        prefix=f"{p.stem}_",
        suffix=p.suffix or ".json",
        dir=str(p.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, p)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise


def save_json_file(path: str | Path, data: Any) -> None:
    atomic_write_json(path, data)


def write_json_file(path: str | Path, data: Any) -> None:
    atomic_write_json(path, data)


def append_json_list(path: str | Path, item: Any) -> None:
    data = load_json_file(path, default=[])

    if not isinstance(data, list):
        data = []

    data.append(item)
    atomic_write_json(path, data)


def read_text_file(path: str | Path, default: str = "") -> str:
    p = Path(path)

    if not p.exists():
        return default

    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return default


def write_text_file(path: str | Path, content: str) -> None:
    p = Path(path)
    ensure_parent_dir(p)
    p.write_text(str(content or ""), encoding="utf-8")


def safe_read_text(path: str | Path) -> str:
    return read_text_file(path, default="")


def safe_write_text(path: str | Path, content: str) -> None:
    write_text_file(path, content)

def delete_file(path: str | Path) -> bool:
    p = Path(path)
    try:
        if p.exists():
            p.unlink()
            return True
    except Exception:
        return False
    return False


def remove_file(path: str | Path) -> bool:
    return delete_file(path)


def safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)