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
        from app import memory_service

        target = str(memory_id or "").strip()

        if not target:
            return {
                "ok": False,
                "memory_id": "",
                "error": "Missing memory ID.",
            }

        deleted = memory_service.delete_memory(target)

        return {
            "ok": bool(deleted),
            "memory_id": target,
        }