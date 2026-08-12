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

        memories = store.get(
            "memory",
            [],
        )

        query = str(
            kwargs.get("query")
            or kwargs.get("text")
            or ""
        ).lower()

        def score(memory):
            value = str(
                memory.get("text")
                or memory.get("content")
                or ""
            ).lower()

            points = 0

            # pinned memories first
            if memory.get("pinned"):
                points += 100

            # importance weight
            points += float(
                memory.get("weight")
                or 0
            ) * 10

            # keyword relevance
            if query:
                words = query.split()

                for word in words:
                    if word in value:
                        points += 5

            # newer memories slightly preferred
            if memory.get("updated_at"):
                points += 1

            return points

        ranked = sorted(
            memories,
            key=score,
            reverse=True,
        )

        return ranked[:20]