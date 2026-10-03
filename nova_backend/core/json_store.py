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
        # utf-8-sig accepts ordinary UTF-8 and strips a BOM when older
        # Windows tools have written one. Invalid JSON still fails closed.
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        # Keep the original bytes available for recovery. Mutations must fail
        # until the existing store is repaired explicitly.
        raise ValueError(f"Unable to read JSON store: {path}") from exc

