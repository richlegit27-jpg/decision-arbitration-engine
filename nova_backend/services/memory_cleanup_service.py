from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class MemoryCleanupService:
    """
    Cleans existing memory items.

    Goals:
    - remove junk memories already saved
    - merge near-duplicate memories
    - prefer stronger / richer / more recent versions
    - keep durable preferences and project memories
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
        "hi",
        "hello",
        "hey",
        "test",
        "testing",
    }

    DURABLE_KINDS = {"preference", "instruction", "style", "project", "goal", "checkpoint"}

    def cleanup(self, items: List[Dict[str, Any]] | None) -> Dict[str, Any]:
        items = items or []

        kept: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        merged: List[Dict[str, Any]] = []

        normalized_map: Dict[str, Dict[str, Any]] = {}
        similarity_groups: List[List[Dict[str, Any]]] = []

        # first pass: remove obvious junk and exact normalized duplicates
        for item in items:
            prepared = self._prepare_item(item)
            text = prepared["normalized_text"]

            if self._should_remove(prepared):
                removed.append({
                    "id": item.get("id"),
                    "reason": "junk_or_low_value",
                    "text": prepared["text"],
                })
                continue

            if text in normalized_map:
                winner, loser = self._pick_winner(normalized_map[text], prepared)
                normalized_map[text] = winner
                removed.append({
                    "id": loser.get("id"),
                    "reason": "exact_duplicate",
                    "text": loser.get("text"),
                    "kept_id": winner.get("id"),
                })
                continue

            normalized_map[text] = prepared

        exact_deduped = list(normalized_map.values())

        # second pass: near-duplicate grouping
        for item in exact_deduped:
            placed = False

            for group in similarity_groups:
                if self._is_near_duplicate(item, group[0]):
                    group.append(item)
                    placed = True
                    break

            if not placed:
                similarity_groups.append([item])

        for group in similarity_groups:
            if len(group) == 1:
                kept.append(self._strip_helper_fields(group[0]))
                continue

            winner = group[0]
            for challenger in group[1:]:
                winner, loser = self._pick_winner(winner, challenger)
                if loser is not challenger:
                    loser = challenger

                removed.append({
                    "id": loser.get("id"),
                    "reason": "near_duplicate",
                    "text": loser.get("text"),
                    "kept_id": winner.get("id"),
                })

            merged_item = self._merge_group(winner, group)
            kept.append(self._strip_helper_fields(merged_item))

            merged.append({
                "kept_id": merged_item.get("id"),
                "merged_count": len(group),
                "text": merged_item.get("text"),
            })

        kept.sort(
            key=lambda entry: (
                self._kind_priority(str(entry.get("kind") or "")),
                len(str(entry.get("text") or "")),
                str(entry.get("updated_at") or entry.get("created_at") or ""),
            ),
            reverse=True,
        )

        return {
            "items": kept,
            "removed": removed,
            "merged": merged,
            "before_count": len(items),
            "after_count": len(kept),
        }

    def _prepare_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(item)
        text = self._extract_text(item)
        prepared["text"] = text
        prepared["normalized_text"] = self._normalize_text(text)
        prepared["kind"] = str(item.get("kind") or "memory").strip().lower()
        return prepared

    def _extract_text(self, item: Dict[str, Any]) -> str:
        return str(
            item.get("text")
            or item.get("content")
            or item.get("value")
            or item.get("body")
            or ""
        ).strip()

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\s+", " ", text).strip().lower()
        text = re.sub(r"^[\-\*\â€¢\s]+", "", text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9_]+", text.lower())

    def _should_remove(self, item: Dict[str, Any]) -> bool:
        text = str(item.get("normalized_text") or "")
        kind = str(item.get("kind") or "memory").lower()

        if not text:
            return True

        if text in self.REJECT_EXACT:
            return True

        if len(text) < 12:
            return True

        if text.endswith("?"):
            return True

        if self._looks_ephemeral(text) and kind not in self.DURABLE_KINDS:
            return True

        return False

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

    def _is_near_duplicate(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        a_text = str(a.get("normalized_text") or "")
        b_text = str(b.get("normalized_text") or "")

        if not a_text or not b_text:
            return False

        if a_text == b_text:
            return True

        a_tokens = set(self._tokenize(a_text))
        b_tokens = set(self._tokenize(b_text))

        if not a_tokens or not b_tokens:
            return False

        overlap = a_tokens.intersection(b_tokens)
        ratio = len(overlap) / max(min(len(a_tokens), len(b_tokens)), 1)

        return ratio >= 0.85

    def _pick_winner(
        self,
        a: Dict[str, Any],
        b: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        a_kind = str(a.get("kind") or "")
        b_kind = str(b.get("kind") or "")

        a_score = 0.0
        b_score = 0.0

        a_score += self._kind_priority(a_kind)
        b_score += self._kind_priority(b_kind)

        a_score += min(len(str(a.get("text") or "")) / 40.0, 3.0)
        b_score += min(len(str(b.get("text") or "")) / 40.0, 3.0)

        if str(a.get("updated_at") or a.get("created_at") or "") > str(
            b.get("updated_at") or b.get("created_at") or ""
        ):
            a_score += 0.5
        else:
            b_score += 0.5

        if a_score >= b_score:
            return a, b
        return b, a

    def _merge_group(self, winner: Dict[str, Any], group: List[Dict[str, Any]]) -> Dict[str, Any]:
        merged = dict(winner)

        # preserve best preview/normalized fields
        merged["preview"] = str(merged.get("text") or "")[:140]
        merged["normalized_text"] = str(merged.get("normalized_text") or "")

        # enrich with aliases if there were small wording variants
        variants = []
        winner_text = str(winner.get("normalized_text") or "")
        for item in group:
            text = str(item.get("normalized_text") or "")
            if text and text != winner_text:
                variants.append(text)

        if variants:
            merged["merge_variants"] = variants[:10]

        return merged

    def _kind_priority(self, kind: str) -> int:
        kind = str(kind or "").lower()
        if kind in {"instruction", "preference", "style"}:
            return 5
        if kind in {"project", "goal", "checkpoint"}:
            return 4
        if kind in {"memory"}:
            return 2
        return 1

    def _strip_helper_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(item)
        clean.pop("normalized_text", None)
        return clean

