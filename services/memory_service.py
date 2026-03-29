from __future__ import annotations
import uuid

class MemoryService:
    def __init__(self):
        self.memory = []

    def get_memory(self):
        return {"ok": True, "memory": self.memory}

    def add_memory(self, item):
        mem_item = {"id": str(uuid.uuid4()), **item}
        self.memory.append(mem_item)
        return {"ok": True, "item": mem_item}

    def delete_memory(self, mem_id):
        self.memory = [m for m in self.memory if m["id"] != mem_id]
        return {"ok": True}