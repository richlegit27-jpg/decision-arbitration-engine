from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class WeightedMemory:
    item: Dict[str, Any]
    score: float


class MemoryWeightingService:
    def __init__(self) -> None:
        pass

    def _clean_text(self, value: Any) -> str:
        return str(value or "").strip()

    def _score_base(self, item: Dict[str, Any]) -> float:
        score = 0.0

        kind = self._clean_text(item.get("kind")).lower()
        source = self._clean_text(item.get("source")).lower()
        text = self._clean_text(item.get("text"))
        weight = item.get("weight")
        quality_score = item.get("quality_score")

        if kind == "profile":
            score += 4.0
        elif kind == "preference":
            score += 3.0
        elif kind == "identity":
            score += 4.5
        else:
            score += 1.0

        if source in {"router_auto", "user", "manual"}:
            score += 1.5
        elif source == "assistant":
            score += 0.5

        if isinstance(weight, (int, float)):
            score += float(weight)

        if isinstance(quality_score, (int, float)):
            score += float(quality_score)

        text_lower = text.lower()
        if text_lower.startswith("name:"):
            score += 6.0

        if "my name is" in text_lower:
            score += 2.0

        return score

    def _score_query_match(self, user_text: str, item: Dict[str, Any]) -> float:
        user_lower = self._clean_text(user_text).lower()
        text_lower = self._clean_text(item.get("text")).lower()
        kind = self._clean_text(item.get("kind")).lower()

        score = 0.0

        if "what is my name" in user_lower or "whats my name" in user_lower:
            if text_lower.startswith("name:"):
                score += 10.0
            if kind in {"profile", "identity"}:
                score += 2.0

        if "who am i" in user_lower:
            if kind in {"profile", "identity"}:
                score += 5.0

        if "remember" in user_lower:
            if "name:" in text_lower:
                score += 3.0

        query_words = {w for w in user_lower.split() if len(w) >= 3}
        text_words = set(text_lower.split())
        overlap = len(query_words.intersection(text_words))
        score += float(overlap) * 0.5

        return score

    def rank(self, user_text: str, memory_items: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        weighted: List[WeightedMemory] = []

        for item in memory_items or []:
            if not isinstance(item, dict):
                continue
            total = self._score_base(item) + self._score_query_match(user_text, item)
            weighted.append(WeightedMemory(item=item, score=total))

        weighted.sort(
            key=lambda x: (
                x.score,
                self._clean_text(x.item.get("updated_at")),
                self._clean_text(x.item.get("created_at")),
            ),
            reverse=True,
        )

        ranked_items: List[Dict[str, Any]] = []
        for wm in weighted[: max(1, int(limit))]:
            enriched = dict(wm.item)
            enriched["memory_score"] = wm.score
            ranked_items.append(enriched)

        return ranked_items

    def best_identity_name(self, memory_items: List[Dict[str, Any]]) -> str:
        for item in memory_items or []:
            text = self._clean_text(item.get("text"))
            if text.lower().startswith("name:"):
                return text.split(":", 1)[1].strip()
        return ""

