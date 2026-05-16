from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    target = ensure_parent_dir(path)

    fd, tmp_path = tempfile.mkstemp(
        prefix=f"{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise


def atomic_write_json(path: str | Path, payload: Any, encoding: str = "utf-8") -> None:
    atomic_write_text(
        path=path,
        text=json.dumps(payload, indent=2, ensure_ascii=False),
        encoding=encoding,
    )