from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class MemoryPromotionService:
    """
    Promotes strong repeated memories into more durable memory forms.

    Goals:
    - detect repeated user instructions/preferences
    - promote recurring project context into stronger project memory
    - avoid promoting junk or weak ephemeral notes
    - add promotion metadata for later inspection/debugging
    """

    PROMOTABLE_SOURCE_KINDS = {
        "memory",
        "note",
        "recent",
        "session",
        "context",
        "project",
        "style",
        "preference",
        "instruction",
        "goal",
        "checkpoint",
    }

    PROMOTION_TARGETS = {
        "style": "style",
        "preference": "preference",
        "instruction": "instruction",
        "project": "project",
        "goal": "goal",
        "checkpoint": "checkpoint",
    }

    DURABLE_KINDS = {"style", "preference", "instruction", "project", "goal", "checkpoint"}

    def promote(
        self,
        items: List[Dict[str, Any]] | None,
    ) -> Dict[str, Any]:
        items = items or []

        prepared = [self._prepare_item(item) for item in items if self._prepare_item(item)]
        if not prepared:
            return {
                "items": items or [],
                "promoted": [],
                "before_count": len(items or []),
                "after_count": len(items or []),
            }

        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        passthrough: List[Dict[str, Any]] = []

        for item in prepared:
            text = str(item.get("normalized_text") or "")
            if not text:
                passthrough.append(item)
                continue

            grouped[text].append(item)

        promoted: List[Dict[str, Any]] = []
        final_items: List[Dict[str, Any]] = []

        for normalized_text, group in grouped.items():
            if len(group) == 1:
                final_items.append(self._strip_helper_fields(group[0]))
                continue

            winner = self._pick_best(group)
            promotion = self._build_promotion(winner, group)

            if promotion:
                final_items.append(self._strip_helper_fields(promotion))
                promoted.append({
                    "id": promotion.get("id"),
                    "text": promotion.get("text"),
                    "kind": promotion.get("kind"),
                    "promotion_count": promotion.get("promotion_count", 0),
                    "promoted_from": promotion.get("promoted_from", []),
                })
            else:
                final_items.append(self._strip_helper_fields(winner))

        # preserve anything that was not grouped meaningfully
        final_items.extend(self._strip_helper_fields(item) for item in passthrough)

        # dedupe by id after merge
        deduped: List[Dict[str, Any]] = []
        seen_ids = set()

        for item in final_items:
            item_id = str(item.get("id") or "").strip()
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            deduped.append(item)

        deduped.sort(
            key=lambda entry: (
                self._kind_priority(str(entry.get("kind") or "")),
                int(entry.get("promotion_count", 0)),
                str(entry.get("updated_at") or entry.get("created_at") or ""),
                len(str(entry.get("text") or "")),
            ),
            reverse=True,
        )

        return {
            "items": deduped,
            "promoted": promoted,
            "before_count": len(items or []),
            "after_count": len(deduped),
        }

    def _prepare_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        text = self._extract_text(item)
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return None

        prepared = dict(item)
        prepared["text"] = text
        prepared["normalized_text"] = normalized_text
        prepared["kind"] = str(item.get("kind") or "memory").strip().lower()
        return prepared

    def _build_promotion(
        self,
        winner: Dict[str, Any],
        group: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self._is_promotable_group(group):
            return None

        promoted = dict(winner)

        current_kind = str(winner.get("kind") or "memory").lower()
        target_kind = self._promoted_kind(winner, group, fallback=current_kind)

        promoted["kind"] = target_kind
        promoted["promotion_count"] = len(group)
        promoted["promoted_from"] = [str(item.get("id") or "") for item in group if item.get("id")]
        promoted["promotion_sources"] = sorted(
            list({str(item.get("source") or "") for item in group if str(item.get("source") or "").strip()})
        )

        reasons = list(promoted.get("promotion_reasons") or [])
        reasons.append(f"repeated {len(group)} times")
        reasons.append(f"promoted to {target_kind}")
        promoted["promotion_reasons"] = reasons

        promoted["updated_at"] = self._latest_timestamp(group) or promoted.get("updated_at") or promoted.get("created_at")
        promoted["preview"] = str(promoted.get("text") or "")[:140]

        return promoted

    def _is_promotable_group(self, group: List[Dict[str, Any]]) -> bool:
        if len(group) < 2:
            return False

        texts = [str(item.get("normalized_text") or "") for item in group]
        if not all(texts):
            return False

        winner = self._pick_best(group)
        kind = str(winner.get("kind") or "memory").lower()
        text = str(winner.get("normalized_text") or "")

        if kind not in self.PROMOTABLE_SOURCE_KINDS:
            return False

        if len(text) < 16:
            return False

        if self._looks_ephemeral(text):
            return False

        if self._looks_question(text):
            return False

        return True

    def _promoted_kind(
        self,
        winner: Dict[str, Any],
        group: List[Dict[str, Any]],
        fallback: str = "memory",
    ) -> str:
        text = str(winner.get("normalized_text") or "")
        winner_kind = str(winner.get("kind") or fallback).lower()

        if winner_kind in self.DURABLE_KINDS:
            return winner_kind

        if self._looks_like_instruction(text):
            return "instruction"

        if self._looks_like_preference(text):
            return "preference"

        if self._looks_like_style(text):
            return "style"

        if self._looks_like_project(text):
            return "project"

        if self._looks_like_goal(text):
            return "goal"

        return winner_kind if winner_kind in self.PROMOTION_TARGETS else fallback

    def _pick_best(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        ranked = sorted(
            group,
            key=lambda entry: (
                self._kind_priority(str(entry.get("kind") or "")),
                self._quality_score(entry),
                str(entry.get("updated_at") or entry.get("created_at") or ""),
                len(str(entry.get("text") or "")),
            ),
            reverse=True,
        )
        return dict(ranked[0])

    def _quality_score(self, item: Dict[str, Any]) -> float:
        text = str(item.get("normalized_text") or "")
        kind = str(item.get("kind") or "memory").lower()
        score = 0.0

        score += min(len(text) / 40.0, 4.0)

        if kind in {"instruction", "preference", "style"}:
            score += 3.0
        elif kind in {"project", "goal", "checkpoint"}:
            score += 2.5
        else:
            score += 1.0

        if self._looks_like_instruction(text):
            score += 2.0
        if self._looks_like_preference(text):
            score += 1.5
        if self._looks_like_style(text):
            score += 1.25
        if self._looks_like_project(text):
            score += 1.25
        if self._looks_like_goal(text):
            score += 1.0

        return score

    def _latest_timestamp(self, group: List[Dict[str, Any]]) -> str:
        timestamps = [
            str(item.get("updated_at") or item.get("created_at") or "").strip()
            for item in group
            if str(item.get("updated_at") or item.get("created_at") or "").strip()
        ]
        return max(timestamps) if timestamps else ""

    def _extract_text(self, item: Dict[str, Any]) -> str:
        return str(
            item.get("text")
            or item.get("content")
            or item.get("value")
            or item.get("body")
            or ""
        ).strip()

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip().lower()
        return " ".join(text.split())

    def _looks_ephemeral(self, text: str) -> bool:
        markers = (
            "how are you",
            "good morning",
            "good night",
            "see you",
            "talk later",
            "what's up",
            "whats up",
            "test",
            "testing",
        )
        return any(marker in text for marker in markers)

    def _looks_question(self, text: str) -> bool:
        return text.endswith("?")

    def _looks_like_instruction(self, text: str) -> bool:
        markers = (
            "always ",
            "never ",
            "do not ",
            "don't ",
            "dont ",
            "from now on",
            "going forward",
            "make sure",
            "remember to",
        )
        return any(marker in text for marker in markers)

    def _looks_like_preference(self, text: str) -> bool:
        markers = (
            "i prefer",
            "prefer ",
            "i want",
            "keep ",
            "use ",
            "full file",
            "full files",
            "solution-first",
            "concise",
            "direct",
        )
        return any(marker in text for marker in markers)

    def _looks_like_style(self, text: str) -> bool:
        markers = (
            "smff",
            "full file",
            "full files",
            "powershell me always",
            "concise",
            "direct",
            "no fluff",
            "solution-first",
        )
        return any(marker in text for marker in markers)

    def _looks_like_project(self, text: str) -> bool:
        markers = (
            "working on",
            "project",
            "build",
            "building",
            "nova",
            "backend",
            "frontend",
            "checkpoint",
            "app.py",
        )
        return any(marker in text for marker in markers)

    def _looks_like_goal(self, text: str) -> bool:
        markers = (
            "goal",
            "plan to",
            "want to build",
            "trying to",
            "finish",
            "launch",
        )
        return any(marker in text for marker in markers)

    def _kind_priority(self, kind: str) -> int:
        kind = str(kind or "").lower()
        if kind == "instruction":
            return 6
        if kind in {"preference", "style"}:
            return 5
        if kind in {"project", "goal", "checkpoint"}:
            return 4
        if kind == "memory":
            return 2
        return 1

    def _strip_helper_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(item)
        clean.pop("normalized_text", None)
        return clean