from __future__ import annotations

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

        service = MemoryService()

        return service.add_memory(
            content=content,
        )