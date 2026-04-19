from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from nova_backend.utils.file_utils import load_json_file, save_json_file
from nova_backend.utils.time_utils import iso_now


class MemoryService:
    def __init__(self, memory_file: str):
        self.memory_file = Path(memory_file)
        self._ensure_store()

    def _ensure_store(self) -> None:
        if not self.memory_file.exists():
            save_json_file(self.memory_file, {"memory": []})

    def _read_store(self) -> Dict[str, Any]:
        data = load_json_file(self.memory_file, {"memory": []})
        if not isinstance(data, dict):
            return {"memory": []}

        memory = data.get("memory")
        if not isinstance(memory, list):
            data["memory"] = []

        return data

    def _write_store(self, data: Dict[str, Any]) -> None:
        save_json_file(self.memory_file, data)

    def all(self) -> List[Dict[str, Any]]:
        items = self._read_store().get("memory", [])
        if not isinstance(items, list):
            return []
        items = [dict(x or {}) for x in items]
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return items

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        target = str(memory_id or "").strip()
        if not target:
            return None

        for item in self.all():
            if str(item.get("id") or "").strip() == target:
                return item
        return None

    def add_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read_store()
        memory = data.get("memory", [])

        item = dict(item or {})
        now = iso_now()

        if not item.get("id"):
            import uuid
            item["id"] = f"memory_{uuid.uuid4().hex}"

        item["updated_at"] = now
        if not item.get("created_at"):
            item["created_at"] = now

        memory.append(item)

        # 🔥 STORAGE CONTROL
        MAX_MEMORY_ITEMS = 100
        memory = memory[-MAX_MEMORY_ITEMS:]

        data["memory"] = memory
        self._write_store(data)

        return item

    def save_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read_store()
        memory = data.get("memory", [])

        item = dict(item or {})
        now = iso_now()

        if not item.get("id"):
            import uuid
            item["id"] = f"memory_{uuid.uuid4().hex}"

        item["updated_at"] = now
        if not item.get("created_at"):
            item["created_at"] = now

        replaced = False
        for i, existing in enumerate(memory):
            if str(existing.get("id") or "") == str(item["id"]):
                memory[i] = item
                replaced = True
                break

        if not replaced:
            memory.append(item)

        # 🔥 STORAGE CONTROL
        MAX_MEMORY_ITEMS = 100
        memory = memory[-MAX_MEMORY_ITEMS:]

        data["memory"] = memory
        self._write_store(data)

        return item

    def delete_memory(self, memory_id: str) -> bool:
        target = str(memory_id or "").strip()
        if not target:
            return False

        data = self._read_store()
        memory = data.get("memory", [])
        kept = [
            item for item in memory
            if str((item or {}).get("id") or "").strip() != target
        ]

        if len(kept) == len(memory):
            return False

        data["memory"] = kept
        self._write_store(data)
        return True

    def clear(self) -> None:
        self._write_store({"memory": []})