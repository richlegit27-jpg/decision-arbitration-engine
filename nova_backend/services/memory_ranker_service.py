from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class MemoryRankerService:
    """
    Memory dominance v2

    Goals:
    - rank memories against the current request
    - prefer durable instructions and preferences when relevant
    - resolve conflicts between competing memories
    - distinguish short-term vs long-term memory value
    - decay stale weak memories
    - prioritize active working-state context
    """

    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
        "has", "have", "how", "i", "if", "in", "into", "is", "it", "its", "me",
        "my", "of", "on", "or", "our", "so", "that", "the", "their", "them",
        "they", "this", "to", "was", "we", "were", "what", "with", "you", "your"
    }

    PREFERENCE_KINDS = {"preference", "instruction", "style"}

    PROJECT_KINDS = {
        "project",
        "work",
        "goal",
        "checkpoint",
    }

    SHORT_TERM_KINDS = {
        "recent",
        "temp",
        "session",
        "context",
    }

    LONG_TERM_KINDS = {
        "preference",
        "instruction",
        "style",
        "project",
        "goal",
    }

    WORKING_STATE_KINDS = {
        "active_task",
        "current_file",
        "current_bug",
        "next_move",
        "checkpoint",
        "execution",
    }

    WEAK_MEMORY_TEXTS = {
        "ok", "okay", "thanks", "thank you", "cool", "nice", "yes", "no",
        "sounds good", "got it"
    }

    NEGATION_MARKERS = {
        "do not", "don't", "dont", "never", "avoid", "no ", "not "
    }

    POSITIVE_PREFERENCE_MARKERS = {
        "prefer", "always", "use", "keep", "want", "likes", "love"
    }

    ACTIVE_NOVA_MARKERS = {
        "nova",
        "execution",
        "memory",
        "stream",
        "frontend",
        "backend",
        "image",
        "artifact",
        "session",
        "checkpoint",
        "autofix",
        "auto-fix",
        "web fetch",
        "composer",
        "rail",
        "chat_service",
    }

    CONTINUITY_REQUEST_MARKERS = {
        "continue",
        "next",
        "fix",
        "resume",
        "run",
        "where are we",
        "what now",
        "keep going",
        "go",
        "endgame",
        "smff",
    }

    def rank_memories(
        self,
        *,
        user_text: str,
        memory_items: List[Dict[str, Any]] | None = None,
        max_items: int = 6,
    ) -> List[Dict[str, Any]]:
        memory_items = memory_items or []

        user_text_clean = self._clean_text(user_text)
        user_tokens = self._tokenize(user_text_clean)
        user_phrases = self._extract_phrases(user_text_clean)

        scored: List[Dict[str, Any]] = []

        for item in memory_items:
            scored_item = self._score_memory_item(
                item=item,
                user_text=user_text_clean,
                user_tokens=user_tokens,
                user_phrases=user_phrases,
            )
            scored.append(scored_item)

        resolved = self._resolve_conflicts(scored, user_text_clean)

        resolved.sort(
            key=lambda entry: (
                float(entry.get("score", 0.0)),
                int(bool(entry.get("instruction_lock"))),
                int(bool(entry.get("working_state"))),
                int(bool(entry.get("long_term"))),
                self._safe_text(entry.get("updated_at") or entry.get("created_at")),
                self._safe_text(entry.get("text") or entry.get("content") or ""),
            ),
            reverse=True,
        )

        return resolved[:max_items] if max_items > 0 else resolved

    def _score_memory_item(
        self,
        *,
        item: Dict[str, Any],
        user_text: str,
        user_tokens: List[str],
        user_phrases: List[str],
    ) -> Dict[str, Any]:
        text = self._memory_text(item)
        text_clean = self._clean_text(text)
        text_tokens = self._tokenize(text_clean)

        kind = self._safe_text(item.get("kind") or "memory").lower()
        score = 0.0
        reasons: List[str] = []
        matched_terms: List[str] = []

        overlap_terms = sorted(set(user_tokens).intersection(text_tokens))
        if overlap_terms:
            overlap_score = min(len(overlap_terms) * 1.35, 7.0)
            score += overlap_score
            matched_terms.extend(overlap_terms)
            reasons.append(f"keyword overlap x{len(overlap_terms)}")

        phrase_hits = [phrase for phrase in user_phrases if phrase and phrase in text_clean]
        if phrase_hits:
            phrase_score = min(len(phrase_hits) * 2.4, 7.2)
            score += phrase_score
            reasons.append(f"phrase overlap x{len(phrase_hits)}")

        if user_text and text_clean:
            if user_text in text_clean:
                score += 2.0
                reasons.append("user message contained in memory")
            elif text_clean in user_text and len(text_clean) >= 12:
                score += 1.5
                reasons.append("memory contained in user message")

        if kind in self.PREFERENCE_KINDS:
            score += 1.8
            reasons.append("preference boost")

        if kind in self.PROJECT_KINDS:
            score += 1.5
            reasons.append("project boost")

        if kind in self.LONG_TERM_KINDS:
            score += 0.75
            reasons.append("long-term memory boost")

        if kind in self.SHORT_TERM_KINDS:
            score += 0.35
            reasons.append("short-term memory boost")

        if kind in self.WORKING_STATE_KINDS:
            score += 4.5
            reasons.append("working-state dominance")

            if any(marker in text_clean for marker in self.ACTIVE_NOVA_MARKERS):
                score += 2.5
                reasons.append("active nova system focus")

            if any(marker in user_text for marker in self.CONTINUITY_REQUEST_MARKERS):
                score += 2.0
                reasons.append("execution continuity request")

        if self._looks_like_preference(text_clean):
            score += 1.5
            reasons.append("durable instruction pattern")

        if self._looks_like_project_memory(text_clean):
            score += 1.0
            reasons.append("active work pattern")

        if self._looks_like_instruction_lock(text_clean, user_text):
            score += 3.0
            reasons.append("instruction lock")

        recency_bonus = self._recency_bonus(item, kind=kind)
        if recency_bonus > 0:
            score += recency_bonus
            reasons.append(f"recency +{recency_bonus:.2f}")

        decay_penalty = self._decay_penalty(item, kind=kind, text_clean=text_clean)
        if decay_penalty > 0:
            score -= decay_penalty
            reasons.append(f"stale decay -{decay_penalty:.2f}")

        length = len(text_clean)
        if length >= 24:
            score += 0.6
            reasons.append("substantive memory")
        elif 0 < length < 8:
            score -= 1.25
            reasons.append("very short memory penalty")

        if text_clean in self.WEAK_MEMORY_TEXTS:
            score -= 2.0
            reasons.append("generic memory penalty")

        if not overlap_terms and not phrase_hits:
            score -= 0.5
            reasons.append("no direct lexical match")

        instruction_lock = self._looks_like_instruction_lock(text_clean, user_text)
        long_term = kind in self.LONG_TERM_KINDS or self._looks_like_preference(text_clean)
        short_term = kind in self.SHORT_TERM_KINDS
        working_state = kind in self.WORKING_STATE_KINDS

        score = round(max(score, 0.0), 4)

        enriched = dict(item)
        enriched["score"] = score
        enriched["reasons"] = reasons
        enriched["matched_terms"] = matched_terms
        enriched["instruction_lock"] = instruction_lock
        enriched["long_term"] = long_term
        enriched["short_term"] = short_term
        enriched["working_state"] = working_state
        enriched["memory_text"] = text
        return enriched

    def _resolve_conflicts(
        self,
        items: List[Dict[str, Any]],
        user_text: str,
    ) -> List[Dict[str, Any]]:
        if not items:
            return items

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        passthrough: List[Dict[str, Any]] = []

        for item in items:
            text = self._clean_text(item.get("memory_text") or self._memory_text(item))
            topic = self._infer_topic(text, user_text)

            if not topic:
                passthrough.append(item)
                continue

            grouped.setdefault(topic, []).append(item)

        resolved: List[Dict[str, Any]] = list(passthrough)

        for topic, group in grouped.items():
            if len(group) == 1:
                resolved.extend(group)
                continue

            group.sort(
                key=lambda entry: (
                    int(bool(entry.get("instruction_lock"))),
                    int(bool(entry.get("working_state"))),
                    int(bool(entry.get("long_term"))),
                    float(entry.get("score", 0.0)),
                    self._safe_text(entry.get("updated_at") or entry.get("created_at")),
                ),
                reverse=True,
            )

            winner = dict(group[0])
            winner_reasons = list(winner.get("reasons") or [])
            winner_reasons.append(f"won conflict on topic '{topic}'")
            winner["reasons"] = winner_reasons
            resolved.append(winner)

            winner_polarity = self._polarity(self._clean_text(winner.get("memory_text") or ""))

            for loser in group[1:]:
                loser_text = self._clean_text(loser.get("memory_text") or "")
                loser_polarity = self._polarity(loser_text)

                if winner_polarity != 0 and loser_polarity != 0 and winner_polarity != loser_polarity:
                    loser = dict(loser)
                    loser["score"] = round(max(float(loser.get("score", 0.0)) - 3.0, 0.0), 4)
                    loser_reasons = list(loser.get("reasons") or [])
                    loser_reasons.append(f"lost contradiction on topic '{topic}'")
                    loser["reasons"] = loser_reasons

                elif self._near_duplicate(
                    winner_text=self._clean_text(winner.get("memory_text") or ""),
                    loser_text=loser_text,
                ):
                    loser = dict(loser)
                    loser["score"] = round(max(float(loser.get("score", 0.0)) - 1.5, 0.0), 4)
                    loser_reasons = list(loser.get("reasons") or [])
                    loser_reasons.append(f"duplicate under topic '{topic}'")
                    loser["reasons"] = loser_reasons

                resolved.append(loser)

        return resolved

    def _infer_topic(self, text: str, user_text: str) -> str:
        if not text:
            return ""

        tokens = [t for t in self._tokenize(text) if t not in self.STOP_WORDS]
        if not tokens:
            return ""

        user_tokens = set(self._tokenize(user_text))
        overlapping = [token for token in tokens if token in user_tokens]

        if overlapping:
            return " ".join(overlapping[:2]).strip()

        for marker in (
            "prefer",
            "always",
            "never",
            "nova",
            "project",
            "style",
            "backend",
            "frontend",
            "memory",
            "execution",
            "checkpoint",
            "session",
        ):
            if marker in tokens:
                return marker

        return tokens[0]

    def _polarity(self, text: str) -> int:
        if not text:
            return 0

        negative = any(marker in text for marker in self.NEGATION_MARKERS)
        positive = any(marker in text for marker in self.POSITIVE_PREFERENCE_MARKERS)

        if negative and not positive:
            return -1
        if positive and not negative:
            return 1
        return 0

    def _near_duplicate(self, winner_text: str, loser_text: str) -> bool:
        if not winner_text or not loser_text:
            return False

        if winner_text == loser_text:
            return True

        winner_tokens = set(self._tokenize(winner_text))
        loser_tokens = set(self._tokenize(loser_text))
        if not winner_tokens or not loser_tokens:
            return False

        overlap = winner_tokens.intersection(loser_tokens)
        ratio = len(overlap) / max(min(len(winner_tokens), len(loser_tokens)), 1)
        return ratio >= 0.8

    def _looks_like_preference(self, text: str) -> bool:
        markers = (
            "prefer ",
            "i prefer",
            "always ",
            "from now on",
            "going forward",
            "do not ",
            "don't ",
            "dont ",
            "never ",
            "keep ",
            "use ",
        )
        return any(marker in text for marker in markers)

    def _looks_like_project_memory(self, text: str) -> bool:
        markers = (
            "working on",
            "project",
            "build",
            "building",
            "nova",
            "checkpoint",
            "next move",
            "current state",
            "backend",
            "frontend",
            "execution",
            "memory",
            "session",
            "artifact",
            "web fetch",
            "image generation",
        )
        return any(marker in text for marker in markers)

    def _looks_like_instruction_lock(self, text: str, user_text: str) -> bool:
        if not text:
            return False

        if any(
            marker in text
            for marker in (
                "always",
                "never",
                "do not",
                "don't",
                "dont",
                "from now on",
                "going forward",
            )
        ):
            return True

        request_markers = (
            "how",
            "what",
            "continue",
            "fix",
            "update",
            "change",
            "edit",
            "build",
            "wire",
            "next",
            "smff",
            "endgame",
        )
        return any(marker in user_text for marker in request_markers) and self._looks_like_preference(text)

    def _recency_bonus(self, item: Dict[str, Any], *, kind: str) -> float:
        dt = self._parse_dt(item.get("updated_at") or item.get("created_at"))
        if dt is None:
            return 0.0

        now = datetime.now(timezone.utc)
        age_days = max((now - dt).total_seconds() / 86400.0, 0.0)

        if kind in self.WORKING_STATE_KINDS:
            if age_days <= 1:
                return 2.0
            if age_days <= 7:
                return 1.35
            if age_days <= 30:
                return 0.85
            if age_days <= 90:
                return 0.35
            return 0.0

        if kind in self.LONG_TERM_KINDS:
            if age_days <= 7:
                return 0.9
            if age_days <= 30:
                return 0.55
            if age_days <= 180:
                return 0.2
            return 0.0

        if age_days <= 1:
            return 1.25
        if age_days <= 7:
            return 0.9
        if age_days <= 30:
            return 0.5
        if age_days <= 90:
            return 0.2
        return 0.0

    def _decay_penalty(self, item: Dict[str, Any], *, kind: str, text_clean: str) -> float:
        if kind in self.LONG_TERM_KINDS or kind in self.WORKING_STATE_KINDS:
            return 0.0

        dt = self._parse_dt(item.get("updated_at") or item.get("created_at"))
        if dt is None:
            return 0.0

        now = datetime.now(timezone.utc)
        age_days = max((now - dt).total_seconds() / 86400.0, 0.0)

        if len(text_clean) >= 40:
            return 0.0

        if age_days > 90:
            return 1.5
        if age_days > 30:
            return 0.9
        if age_days > 7:
            return 0.35
        return 0.0

    def _memory_text(self, item: Dict[str, Any]) -> str:
        return self._safe_text(
            item.get("text")
            or item.get("content")
            or item.get("value")
            or item.get("body")
            or ""
        )

    def _clean_text(self, value: Any) -> str:
        text = self._safe_text(value).lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[a-z0-9_]+", text.lower())
        return [
            token
            for token in tokens
            if len(token) >= 3 and token not in self.STOP_WORDS
        ]

    def _extract_phrases(self, text: str) -> List[str]:
        tokens = self._tokenize(text)
        phrases: List[str] = []

        for size in (2, 3):
            for i in range(len(tokens) - size + 1):
                phrase = " ".join(tokens[i:i + size]).strip()
                if phrase:
                    phrases.append(phrase)

        deduped: List[str] = []
        seen = set()

        for phrase in phrases:
            if phrase not in seen:
                seen.add(phrase)
                deduped.append(phrase)

        return deduped

    def _parse_dt(self, value: Any) -> Optional[datetime]:
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

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""

        return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()

