from __future__ import annotations

from nova_backend.tools.base import NovaTool


class MemoryDeleteTool(NovaTool):

    name = "memory_delete"

    description = (
        "Deletes a specific stored user memory using its memory identifier."
    )

    category = "memory"

    capabilities = [
        "memory deletion",
        "memory management",
        "stored data removal",
    ]

    risk_level = "medium"

    requires_confirmation = True

    def run(
        self,
        memory_id="",
        **kwargs,
    ):
        from pathlib import Path

        from nova_backend.services.memory_service import (
            MemoryService,
        )

        service = MemoryService(
            memory_file=str(
                Path("runtime")
                / "user_memory.json"
            )
        )

        return {
            "ok": service.delete_memory(
                memory_id
            ),
            "memory_id": memory_id,
        }
