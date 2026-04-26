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

    # =========================
    # DECAY SYSTEM
    # =========================
    def _apply_memory_decay(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if item.get("pinned"):
            item["weight"] = 10.0
            return item

        weight = float(item.get("weight") or 1.0)
        updated_at = str(item.get("updated_at") or item.get("created_at") or "")

        if not updated_at:
            item["weight"] = max(1.0, weight)
            return item

        try:
            from datetime import datetime, timezone

            raw = updated_at.replace("Z", "+00:00")
            updated = datetime.fromisoformat(raw)

            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            age_days = max(0, (now - updated).days)

            decay_steps = age_days // 30
            decayed = weight - (decay_steps * 0.35)

            item["weight"] = max(1.0, round(decayed, 2))
        except Exception:
            item["weight"] = max(1.0, weight)

        return item

    def all(self) -> List[Dict[str, Any]]:
        items = self._read_store().get("memory", [])
        if not isinstance(items, list):
            return []

        items = [self._apply_memory_decay(dict(x or {})) for x in items]

        items.sort(
            key=lambda x: (
                float(x.get("weight") or 1.0),
                x.get("updated_at", "")
            ),
            reverse=True
        )

        return items

    def build_list_payload(self) -> List[Dict[str, Any]]:
        return self.all()

    def build_view_payload(self, memory_id: str) -> Optional[Dict[str, Any]]:
        return self.get(memory_id)

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

        new_text = str(item.get("text") or "").strip().lower()
        new_kind = str(item.get("kind") or "note").strip().lower()

        # ===== BASE WEIGHT =====
        if item.get("pinned"):
            item["weight"] = 10.0
        elif new_kind in ("project", "goal"):
            item["weight"] = 6.0
        elif new_kind in ("profile", "preference"):
            item["weight"] = 5.0
        elif new_kind in ("fact",):
            item["weight"] = 3.0
        else:
            item["weight"] = float(item.get("weight") or 1.0)

        # ===== DEDUP + REINFORCEMENT =====
        for i, existing in enumerate(memory):
            existing_text = str((existing or {}).get("text") or "").strip().lower()
            existing_kind = str((existing or {}).get("kind") or "note").strip().lower()

            if existing_text == new_text and existing_kind == new_kind:
                existing = dict(existing or {})

                count = int(existing.get("count") or 1) + 1
                existing_weight = float(existing.get("weight") or item["weight"])

                existing.update(item)
                existing["count"] = count
                existing["updated_at"] = now

                # 🔥 reinforcement
                existing["weight"] = min(10.0, existing_weight + 1.25)

                if count >= 3:
                    existing["pinned"] = True
                    existing["weight"] = 10.0

                memory[i] = existing
                data["memory"] = memory
                self._write_store(data)
                return existing

        # ===== NEW ITEM =====
        if not item.get("id"):
            import uuid
            item["id"] = f"memory_{uuid.uuid4().hex}"

        item["kind"] = new_kind
        item["updated_at"] = now

        if not item.get("created_at"):
            item["created_at"] = now

        memory.append(item)

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

        MAX_MEMORY_ITEMS = 100
        memory = memory[-MAX_MEMORY_ITEMS:]

        data["memory"] = memory
        self._write_store(data)

        return item

    def pin_memory(self, memory_id: str, pinned: bool = True) -> dict | None:
        target = str(memory_id or "").strip()
        if not target:
            return None

        data = self._read_store()
        memory = data.get("memory", [])

        for i, item in enumerate(memory):
            item = dict(item or {})
            if str(item.get("id") or "").strip() == target:
                item["pinned"] = bool(pinned)
                item["weight"] = 10.0 if pinned else max(1.0, float(item.get("weight") or 1.0))
                item["updated_at"] = iso_now()

                memory[i] = item
                data["memory"] = memory
                self._write_store(data)
                return item

        return None

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