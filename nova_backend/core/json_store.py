from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        write_json(path, default)
        return deepcopy(default)

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        write_json(path, default)
        return deepcopy(default)