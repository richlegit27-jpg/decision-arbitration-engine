from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RankedMemory:
    id: str
    text: str
    kind: str
    source: str
    session_id: str
    created_at: str
    updated_at: str
    score: float
    reasons: List[str]
    item: Dict[str, Any]


class MemoryDominanceService:
    """
    Scores memory items for prompt injection so Nova uses the most useful
    memories instead of dumping raw memory into every request.

    What it does:
    - preference/user-profile memories get a strong base score
    - exact keyword overlap with the current user request gets boosted
    - very recent memories get a recency boost
    - same-session memories get a session boost
    - conflicting short memories are suppressed by normalized text key
    - final result is capped and returned with debug reasons
    """

    KIND_BASE_SCORES = {
        "preference": 8.0,
        "profile": 7.5,
        "identity": 7.0,
        "project": 6.5,
        "goal": 6.0,
        "constraint": 6.0,
        "workflow": 5.5,
        "summary": 5.0,
        "note": 4.0,
        "memory": 4.0,
    }

    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
        "has", "have", "i", "i'm", "if", "in", "into", "is", "it", "its", "me",
        "my", "of", "on", "or", "our", "so", "that", "the", "their", "them",
        "there", "these", "they", "this", "to", "up", "us", "was", "we", "were",
        "what", "when", "where", "which", "who", "why", "will", "with", "you",
        "your"
    }

    PREFERENCE_PHRASES = (
        "prefer",
        "always",
        "never",
        "from now on",
        "going forward",
        "powerShell me always",
        "smff",
        "full file",
        "full files",
        "solution-first",
        "direct",
        "no wasted time",
    )

    def rank_memories(
        self,
        *,
        user_text: str,
        memory_items: List[Dict[str, Any]] | None,
        session_id: str = "",
        max_items: int = 6,
    ) -> Dict[str, Any]:
        memory_items = memory_items or []
        cleaned_user_text = self._safe_text(user_text)
        user_terms = self._extract_terms(cleaned_user_text)

        ranked: List[RankedMemory] = []

        for item in memory_items:
            ranked_item = self._score_item(
                item=item,
                user_text=cleaned_user_text,
                user_terms=user_terms,
                session_id=session_id,
            )
            if ranked_item is not None:
                ranked.append(ranked_item)

        ranked.sort(
            key=lambda entry: (
                -entry.score,
                self._timestamp_sort_key(entry.updated_at),
                self._timestamp_sort_key(entry.created_at),
            )
        )

        deduped = self._dedupe_and_suppress_conflicts(ranked)
        selected = deduped[: max(0, int(max_items))]

        return {
            "selected": [self._serialize_ranked_memory(entry) for entry in selected],
            "debug": {
                "memory_count_in": len(memory_items),
                "memory_count_ranked": len(ranked),
                "memory_count_selected": len(selected),
                "selected_ids": [entry.id for entry in selected],
            },
        }

    def _score_item(
        self,
        *,
        item: Dict[str, Any],
        user_text: str,
        user_terms: set[str],
        session_id: str,
    ) -> Optional[RankedMemory]:
        text = self._safe_text(
            item.get("text")
            or item.get("content")
            or item.get("value")
            or item.get("body")
            or ""
        )
        if not text:
            return None

        item_id = self._safe_text(item.get("id"))
        kind = self._safe_text(item.get("kind") or "memory").lower()
        source = self._safe_text(item.get("source"))
        item_session_id = self._safe_text(item.get("session_id"))
        created_at = self._safe_text(item.get("created_at"))
        updated_at = self._safe_text(item.get("updated_at") or created_at)

        score = 0.0
        reasons: List[str] = []

        base = self.KIND_BASE_SCORES.get(kind, 4.0)
        score += base
        reasons.append(f"kind:{kind}+{base:.1f}")

        overlap_score, overlap_terms = self._keyword_overlap_score(user_terms, text)
        if overlap_score > 0:
            score += overlap_score
            reasons.append(
                f"overlap:{','.join(overlap_terms[:6])}+{overlap_score:.1f}"
            )

        if self._looks_like_preference(text):
            score += 2.0
            reasons.append("preference_phrase+2.0")

        recency_bonus = self._recency_bonus(updated_at or created_at)
        if recency_bonus > 0:
            score += recency_bonus
            reasons.append(f"recency+{recency_bonus:.1f}")

        if session_id and item_session_id and session_id == item_session_id:
            score += 1.5
            reasons.append("same_session+1.5")

        if source == "manual":
            score += 0.5
            reasons.append("manual+0.5")

        text_len = len(text)
        if 20 <= text_len <= 240:
            score += 0.75
            reasons.append("good_length+0.8")
        elif text_len > 450:
            score -= 1.0
            reasons.append("too_long-1.0")

        return RankedMemory(
            id=item_id,
            text=text,
            kind=kind,
            source=source,
            session_id=item_session_id,
            created_at=created_at,
            updated_at=updated_at,
            score=round(score, 3),
            reasons=reasons,
            item=item,
        )

    def _dedupe_and_suppress_conflicts(
        self,
        ranked: List[RankedMemory],
    ) -> List[RankedMemory]:
        result: List[RankedMemory] = []
        seen_norm_keys: set[str] = set()
        seen_preference_heads: dict[str, float] = {}

        for entry in ranked:
            norm_key = self._normalize_for_dedupe(entry.text)
            if norm_key in seen_norm_keys:
                continue

            head_key = self._preference_head_key(entry.text)
            if head_key:
                existing_score = seen_preference_heads.get(head_key)
                if existing_score is not None and existing_score >= entry.score:
                    continue
                seen_preference_heads[head_key] = entry.score

            seen_norm_keys.add(norm_key)
            result.append(entry)

        return result

    def _keyword_overlap_score(
        self,
        user_terms: set[str],
        memory_text: str,
    ) -> Tuple[float, List[str]]:
        if not user_terms:
            return 0.0, []

        memory_terms = self._extract_terms(memory_text)
        overlap = sorted(user_terms.intersection(memory_terms))
        if not overlap:
            return 0.0, []

        score = min(4.0, len(overlap) * 1.2)
        return score, overlap

    def _extract_terms(self, text: str) -> set[str]:
        lowered = self._safe_text(text).lower()
        chars = []
        for ch in lowered:
            if ch.isalnum() or ch in {"_", "-", " "}:
                chars.append(ch)
            else:
                chars.append(" ")
        tokens = [part.strip("-_ ") for part in "".join(chars).split()]
        return {
            token
            for token in tokens
            if token and len(token) >= 3 and token not in self.STOP_WORDS
        }

    def _looks_like_preference(self, text: str) -> bool:
        lowered = self._safe_text(text).lower()
        return any(phrase.lower() in lowered for phrase in self.PREFERENCE_PHRASES)

    def _recency_bonus(self, iso_value: str) -> float:
        dt = self._parse_iso(iso_value)
        if dt is None:
            return 0.0

        now = datetime.now(timezone.utc)
        delta_seconds = max(0.0, (now - dt).total_seconds())
        days = delta_seconds / 86400.0

        if days <= 1:
            return 2.0
        if days <= 3:
            return 1.5
        if days <= 7:
            return 1.0
        if days <= 30:
            return 0.5
        return 0.0

    def _timestamp_sort_key(self, iso_value: str) -> float:
        dt = self._parse_iso(iso_value)
        if dt is None:
            return 0.0
        return dt.timestamp()

    def _parse_iso(self, value: str) -> Optional[datetime]:
        text = self._safe_text(value)
        if not text:
            return None

        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    def _normalize_for_dedupe(self, text: str) -> str:
        lowered = self._safe_text(text).lower()
        chars = []
        for ch in lowered:
            chars.append(ch if ch.isalnum() or ch == " " else " ")
        normalized = " ".join("".join(chars).split())
        return normalized[:240]

    def _preference_head_key(self, text: str) -> str:
        lowered = self._safe_text(text).lower()
        for marker in ("prefer", "always", "never", "from now on", "going forward"):
            if marker in lowered:
                idx = lowered.find(marker)
                head = lowered[idx: idx + 80]
                chars = []
                for ch in head:
                    chars.append(ch if ch.isalnum() or ch == " " else " ")
                return " ".join("".join(chars).split())
        return ""

    def _serialize_ranked_memory(self, entry: RankedMemory) -> Dict[str, Any]:
        data = dict(entry.item)
        data["text"] = entry.text
        data["kind"] = entry.kind
        data["source"] = entry.source
        data["session_id"] = entry.session_id
        data["created_at"] = entry.created_at
        data["updated_at"] = entry.updated_at
        data["score"] = entry.score
        data["reasons"] = list(entry.reasons)
        return data

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()