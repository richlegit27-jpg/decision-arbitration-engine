from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def ensure_parent_dir(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target.parent


def safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def read_text_file(path: str | Path, encoding: str = "utf-8") -> str:
    target = Path(path)
    if not target.exists():
        return ""
    return target.read_text(encoding=encoding)


def write_text_file(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    target = Path(path)
    ensure_parent_dir(target)
    target.write_text(content, encoding=encoding)
    return target


def read_json_file(path: str | Path, default: Any = None) -> Any:
    target = Path(path)

    if not target.exists():
        if default is not None:
            return default
        return {}

    try:
        raw = target.read_text(encoding="utf-8").strip()
        if not raw:
            if default is not None:
                return default
            return {}
        return json.loads(raw)
    except Exception:
        if default is not None:
            return default
        return {}


def write_json_file(path: str | Path, data: Any, indent: int = 2) -> Path:
    target = Path(path)
    ensure_parent_dir(target)
    target.write_text(
        json.dumps(data, indent=indent, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def atomic_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    target = Path(path)
    ensure_parent_dir(target)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=str(target.parent),
        newline="",
    ) as temp_file:
        temp_file.write(content)
        temp_name = temp_file.name

    os.replace(temp_name, target)
    return target


def atomic_write_json(path: str | Path, data: Any, indent: int = 2) -> Path:
    payload = json.dumps(data, indent=indent, ensure_ascii=False)
    return atomic_write_text(path, payload, encoding="utf-8")