from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


class MemoryService:
    def __init__(self, memory_file: str | Path):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        data = read_json_file(self.memory_file, [])
        return data if isinstance(data, list) else []

    def _save(self, items: list[dict[str, Any]]) -> None:
        write_json_file(self.memory_file, items)

    def get_memory_items(self) -> list[dict[str, Any]]:
        items = self._load()
        return sorted(
            items,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )

    def add_memory_item(self, content: str, pinned: bool = False) -> dict[str, Any]:
        items = self._load()

        item = {
            "id": str(uuid.uuid4()),
            "content": str(content).strip(),
            "created_at": utc_now(),
            "pinned": bool(pinned),
        }

        items.insert(0, item)
        self._save(items)
        return item

    def delete_memory_item(self, memory_id: str) -> bool:
        items = self._load()
        new_items = [i for i in items if i.get("id") != memory_id]

        changed = len(new_items) != len(items)
        if changed:
            self._save(new_items)

        return changed

    def clear_memory(self) -> dict[str, Any]:
        self._save([])
        return {"cleared": True}