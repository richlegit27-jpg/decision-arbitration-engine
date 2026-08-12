from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class MemoryReadTool(NovaTool):
    name = "memory_read"

    description = (
        "Reads stored user memories."
    )

    def run(
        self,
        **kwargs,
    ):
        from nova_backend.services.memory_service import (
            MemoryService,
        )

        memory_file = (
            Path("runtime")
            / "user_memory.json"
        )

        service = MemoryService(
            memory_file=str(memory_file)
        )

        store = service._read_store()

        return store.get(
            "memory",
            [],
        )