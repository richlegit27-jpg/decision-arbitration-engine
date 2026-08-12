from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class MemoryWriteTool(NovaTool):
    name = "memory_write"

    description = (
        "Stores a durable user memory."
    )

    def run(
        self,
        content="",
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

return service.add_memory(
    {
        "content": content,
        "type": "user_fact",
    }
)