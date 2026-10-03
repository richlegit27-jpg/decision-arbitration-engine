from __future__ import annotations

from nova_backend.tools.base import NovaTool


class MemoryWriteTool(NovaTool):

    name = "memory_write"

    description = (
        "Stores a durable user memory that Nova can retrieve "
        "and use in future conversations."
    )

    category = "memory"

    capabilities = [
        "memory storage",
        "durable preference storage",
        "user fact storage",
        "conversation memory",
    ]

    risk_level = "medium"

    requires_confirmation = False

    def run(
        self,
        content="",
        **kwargs,
    ):
        from app import memory_service

        return memory_service.add_memory(
            {
                "content": content,
                "type": "user_fact",
            }
        )
