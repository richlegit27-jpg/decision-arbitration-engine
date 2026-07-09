from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class MemoryHygieneService:
    """
    Filters and normalizes candidate memories before they are written.

    Goals:
    - reject junk / tiny / conversational filler
    - normalize repeated wording
    - detect likely preference / project / instruction memories
    - suppress near-duplicates
    """

    REJECT_EXACT = {
        "",
        "ok",
        "okay",
        "k",
        "kk",
        "yes",
        "no",
        "yep",
        "nope",
        "cool",
        "nice",
        "thanks",
        "thank you",
        "sounds good",
        "got it",
        "hello",
        "hi",
        "hey",
    }

    PREFERENCE_MARKERS = (
        "i prefer",
        "prefer ",
        "always ",
        "never ",
        "from now on",
        "going forward",
        "do not ",
        "don't ",
        "dont ",
        "use ",
        "keep ",
    )

    PROJECT_MARKERS = (
        "i am working on",
        "i'm working on",
        "working on",
        "project",
        "building",
        "build",
        "checkpoint",
        "next move",
        "current state",
        "nova",
        "backend",
        "frontend",
    )

    STYLE_MARKERS = (
        "full file",
        "full files",
        "smff",
        "powerShell me always".lower(),
        "concise",
        "direct",
        "no fluff",
        "solution-first",
    )

    def prepare_candidate(
        self,
        *,
        text: str,
        session_id: str = "",
        source: str = "user",
        kind: str = "",
        existing_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        existing_items = existing_items or []

        cleaned = self._normalize_text(text)
        if not cleaned:
            return None

        if self._should_reject(cleaned):
            return None

        inferred_kind = self._infer_kind(cleaned, fallback=kind)
        preview = cleaned[:140]

        duplicate_of = self._find_duplicate(
            candidate_text=cleaned,
            existing_items=existing_items,
        )
        if duplicate_of:
            return None

        return {
            "text": cleaned,
            "kind": inferred_kind,
            "source": source or "user",
            "session_id": session_id or "",
            "preview": preview,
            "quality_score": self._quality_score(cleaned, inferred_kind),
            "normalized_text": cleaned,
        }

    def prepare_many(
        self,
        *,
        texts: List[str],
        session_id: str = "",
        source: str = "user",
        kind: str = "",
        existing_items: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        existing_items = existing_items or []
        accepted: List[Dict[str, Any]] = []

        for raw in texts:
            candidate = self.prepare_candidate(
                text=raw,
                session_id=session_id,
                source=source,
                kind=kind,
                existing_items=existing_items + accepted,
            )
            if candidate:
                accepted.append(candidate)

        accepted.sort(
            key=lambda item: (
                float(item.get("quality_score", 0.0)),
                len(str(item.get("text") or "")),
            ),
            reverse=True,
        )
        return accepted

    def _should_reject(self, text: str) -> bool:
        lowered = text.lower().strip()

        if lowered in self.REJECT_EXACT:
            return True

        if len(lowered) < 12:
            return True

        if lowered.count(" ") == 0 and len(lowered) < 18:
            return True

        if self._looks_like_pure_greeting(lowered):
            return True

        if self._looks_like_question(lowered):
            return True

        if self._looks_like_ephemeral_chat(lowered):
            return True

        return False

    def _infer_kind(self, text: str, fallback: str = "") -> str:
        lowered = text.lower()

        if any(marker in lowered for marker in self.PREFERENCE_MARKERS):
            return "preference"

        if any(marker in lowered for marker in self.STYLE_MARKERS):
            return "style"

        if any(marker in lowered for marker in self.PROJECT_MARKERS):
            return "project"

        fallback = str(fallback or "").strip().lower()
        return fallback or "memory"

    def _quality_score(self, text: str, kind: str) -> float:
        score = 0.0
        lowered = text.lower()

        if len(lowered) >= 20:
            score += 1.0
        if len(lowered) >= 40:
            score += 1.0
        if len(lowered) >= 80:
            score += 0.5

        if kind in {"preference", "style"}:
            score += 2.5
        elif kind == "project":
            score += 2.0
        else:
            score += 0.5

        if any(marker in lowered for marker in self.PREFERENCE_MARKERS):
            score += 1.5

        if any(marker in lowered for marker in self.STYLE_MARKERS):
            score += 1.5

        if any(marker in lowered for marker in self.PROJECT_MARKERS):
            score += 1.25

        if self._looks_like_question(lowered):
            score -= 1.0

        if self._looks_like_ephemeral_chat(lowered):
            score -= 2.0

        return round(max(score, 0.0), 4)

    def _find_duplicate(
        self,
        *,
        candidate_text: str,
        existing_items: List[Dict[str, Any]],
    ) -> str:
        candidate_tokens = set(self._tokenize(candidate_text))
        if not candidate_tokens:
            return ""

        for item in existing_items:
            existing_text = self._normalize_text(
                item.get("text")
                or item.get("content")
                or item.get("value")
                or item.get("body")
                or ""
            )
            if not existing_text:
                continue

            if existing_text == candidate_text:
                return str(item.get("id") or "exact")

            existing_tokens = set(self._tokenize(existing_text))
            if not existing_tokens:
                continue

            overlap = candidate_tokens.intersection(existing_tokens)
            ratio = len(overlap) / max(min(len(candidate_tokens), len(existing_tokens)), 1)

            if ratio >= 0.85:
                return str(item.get("id") or "near_duplicate")

        return ""

    def _looks_like_pure_greeting(self, text: str) -> bool:
        return text in {"hi", "hello", "hey", "yo", "sup", "what's up", "whats up"}

    def _looks_like_question(self, text: str) -> bool:
        return text.endswith("?")

    def _looks_like_ephemeral_chat(self, text: str) -> bool:
        ephemeral_markers = (
            "see you",
            "talk later",
            "good night",
            "good morning",
            "what's up",
            "whats up",
            "how are you",
            "test",
            "testing",
        )
        return any(marker in text for marker in ephemeral_markers)

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\s+", " ", text).strip()

        text = re.sub(r"^[\-\*\â€¢\s]+", "", text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)

        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9_]+", text.lower())

