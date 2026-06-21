from __future__ import annotations

import json
import os
import random
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


_FILE_LOCKS: dict[str, threading.RLock] = {}
_FILE_LOCKS_GUARD = threading.RLock()


def _normalize_lock_key(path: str | Path) -> str:
    try:
        return str(Path(path).resolve()).lower()
    except Exception:
        return str(Path(path)).lower()


def _get_file_lock(path: str | Path) -> threading.RLock:
    key = _normalize_lock_key(path)
    with _FILE_LOCKS_GUARD:
        lock = _FILE_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _FILE_LOCKS[key] = lock
        return lock


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


def _fsync_parent_dir(path: Path) -> None:
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except Exception:
        return

    try:
        try:
            os.fsync(dir_fd)
        except Exception:
            pass
    finally:
        try:
            os.close(dir_fd)
        except Exception:
            pass

def atomic_write_json(path, data, raise_on_fail=True):
    import json
    import os
    import tempfile
    import time

    p = os.path.abspath(path)
    d = os.path.dirname(p)

    last_error = None
    temp_path = None

    for attempt in range(10):
        try:
            # write to temp file
            fd, temp_path = tempfile.mkstemp(dir=d, prefix="nova_sessions_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # try atomic replace
            os.replace(temp_path, p)
            return True

        except Exception as e:
            last_error = e

            # cleanup temp file if exists
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

            # small delay before retry
            time.sleep(0.05)

    # ðŸ”¥ FALLBACK: direct overwrite (non-atomic but safe enough)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("[atomic_write_json] fallback write used")
        return True

    except Exception as e:
        print("[atomic_write_json] fallback failed:", e)

        if raise_on_fail:
            raise e

    return False

def save_json_file(path: str | Path, data: Any, raise_on_fail: bool = True) -> bool:
    return atomic_write_json(path, data, raise_on_fail=raise_on_fail)


def write_json_file(path: str | Path, data: Any, raise_on_fail: bool = True) -> bool:
    return atomic_write_json(path, data, raise_on_fail=raise_on_fail)


def append_json_list(path: str | Path, item: Any, raise_on_fail: bool = True) -> bool:
    file_lock = _get_file_lock(path)
    with file_lock:
        data = load_json_file(path, default=[])

        if not isinstance(data, list):
            data = []

        data.append(item)
        return atomic_write_json(path, data, raise_on_fail=raise_on_fail)


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

