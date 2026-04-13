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


def safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def read_json_file(path: str | Path, default: Any):
    file_path = Path(path)

    if not file_path.exists():
        return default

    try:
        raw = file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def write_json_atomic(path: str | Path, data: Any) -> None:
    file_path = Path(path)
    ensure_dir(file_path.parent)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(file_path.parent),
        delete=False,
        suffix=".tmp",
    ) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)

    os.replace(tmp_path, file_path)


def atomic_write_json(path: str | Path, data: Any) -> None:
    write_json_atomic(path, data)