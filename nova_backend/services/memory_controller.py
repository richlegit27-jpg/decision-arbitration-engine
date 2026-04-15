from __future__ import annotations

from typing import Any, Dict, List

from nova_backend.services.memory_weighting_service import MemoryWeightingService


class MemoryController:
    def __init__(self, memory_service):
        self.memory = memory_service
        self.weighting = MemoryWeightingService()

    def should_override_identity(self, user_text: str) -> bool:
        t = str(user_text or "").strip().lower()
        return any(
            x in t
            for x in [
                "what is my name",
                "whats my name",
                "who am i",
                "do you know my name",
            ]
        )

    def rank(self, user_text: str, memory_items: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        return self.weighting.rank(user_text=user_text, memory_items=memory_items, limit=limit)

    def apply(self, user_text: str, memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        ranked = self.rank(user_text=user_text, memory_items=memory_items, limit=5)
        identity = self.weighting.best_identity_name(ranked)

        if self.should_override_identity(user_text) and identity:
            return {
                "override": True,
                "text": f"Your name is {identity}.",
                "ranked_memory": ranked,
            }

        return {
            "override": False,
            "ranked_memory": ranked,
        }