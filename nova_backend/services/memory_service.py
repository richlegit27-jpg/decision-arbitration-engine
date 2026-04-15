from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nova_backend.services.memory_hygiene_service import MemoryHygieneService
from nova_backend.services.memory_cleanup_service import MemoryCleanupService
from nova_backend.services.memory_promotion_service import MemoryPromotionService
from nova_backend.utils.safe_file_store import atomic_write_json


PREFERENCE_PATTERNS = [
    r"\bi prefer\b",
    r"\bfrom now on\b",
    r"\balways\b",
    r"\bnever\b",
    r"\bkeep\b",
    r"\buse\b",
]

PROJECT_PATTERNS = [
    r"\bi am working on\b",
    r"\bmy project is\b",
    r"\bthe project is\b",
    r"\bcurrent project\b",
    r"\bnova\b",
]

IDENTITY_PATTERNS = [
    r"\bmy name is\b",
]

MEMORY_TRIGGER_PATTERNS = [
    r"\bremember that\b",
    r"\bnote that\b",
    r"\bfrom now on\b",
    r"\bi prefer\b",
    r"\bmy name is\b",
    r"\bi am working on\b",
    r"\bmy project is\b",
    r"\bthe project is\b",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _safe_text(value).lower()


class MemoryService:
    def __init__(self, memory_file: str | Path):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.memory_file.exists():
            self._write([])

        self.hygiene = MemoryHygieneService()
        self.cleanup_service = MemoryCleanupService()
        self.promotion_service = MemoryPromotionService()

    # -----------------------
    # STORAGE
    # -----------------------

    def _read(self) -> List[dict]:
        try:
            if not self.memory_file.exists():
                return []

            raw = self.memory_file.read_text(encoding="utf-8").strip()
            if not raw:
                return []

            data = json.loads(raw)

            if isinstance(data, dict):
                data = data.get("memory", [])

            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write(self, items: List[dict]) -> None:
        atomic_write_json(self.memory_file, items)

    def _write_all(self, items: List[dict]) -> None:
        self._write(items)

    def list_all(self) -> List[dict]:
        return self._read()

    def all(self) -> List[dict]:
        items = self._read()
        normalized = [self._normalize_item(item) for item in items]
        normalized.sort(key=lambda x: _safe_text(x.get("updated_at")), reverse=True)
        return normalized

    def build_list_payload(self) -> List[dict]:
        return self.all()

    def get(self, memory_id: str) -> Optional[dict]:
        memory_id = _safe_text(memory_id)
        if not memory_id:
            return None

        for item in self._read():
            if _safe_text(item.get("id")) == memory_id:
                return self._normalize_item(item)
        return None

    # -----------------------
    # ADD / DELETE
    # -----------------------

    def add(
        self,
        text: str,
        kind: str = "note",
        source: str = "assistant",
        session_id: str | None = None,
        weight: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> Optional[dict]:
        candidate = self.hygiene.prepare_candidate(
            text=text,
            session_id=session_id or "",
            source=source,
            kind=kind,
            existing_items=self.list_all(),
        )

        if not candidate:
            return None

        items = self._read()
        now = _utc_now()

        item = {
            "id": f"memory_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "text": candidate["text"],
            "kind": candidate["kind"],
            "source": candidate["source"],
            "session_id": candidate["session_id"],
            "weight": float(weight or 1.0),
            "tags": list(tags or []),
            "preview": candidate.get("preview", ""),
            "quality_score": candidate.get("quality_score", 0.0),
            "normalized_text": candidate.get("normalized_text", ""),
            "created_at": now,
            "updated_at": now,
        }

        items.append(item)
        self._write(items)
        return self._normalize_item(item)

    def add_memory(
        self,
        text: str,
        kind: str = "note",
        source: str = "assistant",
        session_id: str | None = None,
        weight: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> Optional[dict]:
        return self.add(
            text=text,
            kind=kind,
            source=source,
            session_id=session_id,
            weight=weight,
            tags=tags,
        )

    def delete(self, memory_id: str) -> bool:
        memory_id = _safe_text(memory_id)
        if not memory_id:
            return False

        items = self._read()
        kept = [item for item in items if _safe_text(item.get("id")) != memory_id]

        if len(kept) == len(items):
            return False

        self._write(kept)
        return True

    def delete_memory(self, memory_id: str) -> bool:
        return self.delete(memory_id)

    # -----------------------
    # CLEANUP + PROMOTION
    # -----------------------

    def cleanup_memories(self) -> dict:
        items = self.list_all()
        result = self.cleanup_service.cleanup(items)
        self._write_all(result["items"])
        return result

    def promote_memories(self) -> dict:
        items = self.list_all()
        result = self.promotion_service.promote(items)
        self._write_all(result["items"])
        return result

    def cleanup_and_promote_memories(self) -> dict:
        cleanup_result = self.cleanup_memories()
        promotion_result = self.promote_memories()

        return {
            "ok": True,
            "cleanup": cleanup_result,
            "promotion": promotion_result,
        }

    # -----------------------
    # NORMALIZATION
    # -----------------------

    def _normalize_item(self, item: dict) -> dict:
        text = _safe_text(item.get("text"))
        kind = _safe_text(item.get("kind")) or "note"
        source = _safe_text(item.get("source")) or "assistant"
        session_id = _safe_text(item.get("session_id"))
        weight = float(item.get("weight", 1.0) or 1.0)
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []

        preview = _safe_text(item.get("preview")) or text[:160].strip()
        if len(text) > 160 and not _safe_text(item.get("preview")):
            preview += "..."

        return {
            "id": _safe_text(item.get("id")),
            "text": text,
            "kind": kind,
            "source": source,
            "session_id": session_id,
            "weight": weight,
            "tags": tags,
            "created_at": _safe_text(item.get("created_at")),
            "updated_at": _safe_text(item.get("updated_at")),
            "preview": preview,
            "quality_score": float(item.get("quality_score", 0.0) or 0.0),
        }

    # -----------------------
    # EXTRACTION
    # -----------------------

    def classify_memory_kind(self, text: str) -> str:
        lowered = _lower(text)

        if any(re.search(pattern, lowered) for pattern in PREFERENCE_PATTERNS):
            return "preference"

        if any(re.search(pattern, lowered) for pattern in PROJECT_PATTERNS):
            return "project"

        if any(re.search(pattern, lowered) for pattern in IDENTITY_PATTERNS):
            return "identity"

        return "note"

    def initial_weight_for_kind(self, kind: str) -> float:
        mapping = {
            "preference": 3.0,
            "project": 2.5,
            "identity": 2.0,
            "note": 1.0,
        }
        return float(mapping.get(kind, 1.0))

    def _extract_tags(self, text: str) -> List[str]:
        lowered = _lower(text)
        tags: List[str] = []

        if "nova" in lowered:
            tags.append("nova")
        if "coding" in lowered or "code" in lowered or "python" in lowered or "flask" in lowered:
            tags.append("coding")
        if "writing" in lowered or "draft" in lowered:
            tags.append("writing")
        if "plan" in lowered or "roadmap" in lowered or "next steps" in lowered:
            tags.append("planning")
        if "web" in lowered or "url" in lowered or "site" in lowered:
            tags.append("web")
        if "image" in lowered:
            tags.append("image")

        return sorted(set(tags))

    def maybe_extract_from_text(
        self,
        text: str,
        session_id: str | None = None,
        source: str = "user",
    ) -> Optional[dict]:
        cleaned = _safe_text(text)
        lowered = _lower(cleaned)

        if not cleaned:
            return None

        triggered = any(
            re.search(pattern, lowered)
            for pattern in MEMORY_TRIGGER_PATTERNS
        )
        if not triggered:
            return None

        kind = self.classify_memory_kind(cleaned)
        weight = self.initial_weight_for_kind(kind)
        tags = self._extract_tags(cleaned)

        existing = self.find_similar(cleaned, kind=kind, session_id=session_id)
        if existing:
            bumped = self.bump_weight(existing["id"], amount=0.25)
            return bumped or self.get(existing["id"])

        return self.add(
            text=cleaned,
            kind=kind,
            source=source,
            session_id=session_id,
            weight=weight,
            tags=tags,
        )

    def find_similar(
        self,
        text: str,
        kind: str | None = None,
        session_id: str | None = None,
    ) -> Optional[dict]:
        target = _lower(text)
        if not target:
            return None

        for item in self.all():
            same_kind = not kind or _safe_text(item.get("kind")) == _safe_text(kind)
            same_session = not session_id or _safe_text(item.get("session_id")) == _safe_text(session_id)
            current = _lower(item.get("text"))
            if same_kind and same_session and current == target:
                return item

        return None

    def bump_weight(self, memory_id: str, amount: float = 0.25) -> Optional[dict]:
        items = self._read()
        changed: Optional[dict] = None

        for item in items:
            if _safe_text(item.get("id")) == _safe_text(memory_id):
                item["weight"] = float(item.get("weight", 1.0) or 1.0) + float(amount)
                item["updated_at"] = _utc_now()
                changed = item
                break

        if changed:
            self._write(items)
            return self._normalize_item(changed)

        return None

    # -----------------------
    # SCORING / RECALL
    # -----------------------

    def _term_hits(self, query: str, text: str) -> int:
        q = [part for part in re.split(r"[^a-zA-Z0-9_]+", _lower(query)) if part]
        t = _lower(text)
        if not q or not t:
            return 0
        return sum(1 for token in set(q) if token in t)

    def _recency_bonus(self, iso_ts: str) -> float:
        raw = _safe_text(iso_ts)
        if not raw:
            return 0.0

        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            age_seconds = max((datetime.now(timezone.utc) - dt).total_seconds(), 0)
            age_days = age_seconds / 86400.0
        except Exception:
            return 0.0

        if age_days <= 1:
            return 1.5
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.5
        return 0.0

    def _kind_bonus(self, kind: str, mode: str) -> float:
        kind = _safe_text(kind)
        mode = _safe_text(mode)

        if kind == "preference":
            return 2.5

        if kind == "project":
            if mode in {"coding", "planning", "analysis", "chat"}:
                return 2.0
            return 1.0

        if kind == "identity":
            return 0.75

        return 0.0

    def _tag_bonus(self, tags: List[str], mode: str) -> float:
        tags = [str(tag).strip().lower() for tag in (tags or [])]
        mode = _safe_text(mode)

        if mode in tags:
            return 1.5

        if mode == "coding" and any(tag in tags for tag in ["nova", "coding"]):
            return 1.5

        if mode == "planning" and any(tag in tags for tag in ["planning", "nova"]):
            return 1.25

        if mode == "web" and "web" in tags:
            return 1.25

        if mode == "image" and "image" in tags:
            return 1.25

        return 0.0

    def score_memory_item(
        self,
        item: dict,
        query: str,
        mode: str,
        session_id: str | None = None,
    ) -> dict:
        base_weight = float(item.get("weight", 1.0) or 1.0)
        text_hits = self._term_hits(query, item.get("text"))
        recency = self._recency_bonus(item.get("updated_at"))
        kind_bonus = self._kind_bonus(item.get("kind"), mode)
        tag_bonus = self._tag_bonus(item.get("tags") or [], mode)

        same_session_bonus = 0.0
        if session_id and _safe_text(item.get("session_id")) == _safe_text(session_id):
            same_session_bonus = 1.5

        total = base_weight + text_hits + recency + kind_bonus + tag_bonus + same_session_bonus

        reasons: List[str] = []
        if base_weight:
            reasons.append(f"base_weight={base_weight:.2f}")
        if text_hits:
            reasons.append(f"term_hits={text_hits}")
        if recency:
            reasons.append(f"recency_bonus={recency:.2f}")
        if kind_bonus:
            reasons.append(f"kind_bonus={kind_bonus:.2f}")
        if tag_bonus:
            reasons.append(f"tag_bonus={tag_bonus:.2f}")
        if same_session_bonus:
            reasons.append(f"same_session_bonus={same_session_bonus:.2f}")

        return {
            "item": self._normalize_item(item),
            "score": round(total, 3),
            "reasons": reasons,
        }

    def recall(
        self,
        query: str,
        mode: str = "chat",
        session_id: str | None = None,
        limit: int = 8,
    ) -> List[dict]:
        scored: List[dict] = []

        for item in self.all():
            scored.append(
                self.score_memory_item(
                    item=item,
                    query=query,
                    mode=mode,
                    session_id=session_id,
                )
            )

        scored.sort(key=lambda entry: entry["score"], reverse=True)
        return scored[: max(int(limit), 1)]

    # -----------------------
    # SANITIZATION / INJECTION
    # -----------------------

    def _clip_for_injection(self, text: str, limit: int = 220) -> str:
        cleaned = re.sub(r"\s+", " ", _safe_text(text)).strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rstrip() + "..."

    def _fingerprint(self, text: str) -> str:
        lowered = _lower(text)
        tokens = re.findall(r"[a-z0-9_]+", lowered)
        if not tokens:
            return ""
        return " ".join(tokens[:18])

    def _kind_priority(self, kind: str) -> int:
        mapping = {
            "preference": 4,
            "project": 3,
            "identity": 2,
            "note": 1,
        }
        return int(mapping.get(_safe_text(kind), 0))

    def sanitize_for_injection(
        self,
        ranked: List[dict],
        *,
        max_items: int = 5,
        min_score: float = 2.5,
        max_chars_total: int = 1000,
        per_item_char_limit: int = 220,
    ) -> dict:
        selected: List[dict] = []
        reasoning: List[dict] = []
        seen_fp = set()
        total_chars = 0
        dropped: List[dict] = []

        ordered = sorted(
            ranked or [],
            key=lambda entry: (
                float(entry.get("score", 0.0)),
                self._kind_priority((entry.get("item") or {}).get("kind")),
                float((entry.get("item") or {}).get("weight", 1.0) or 1.0),
            ),
            reverse=True,
        )

        for entry in ordered:
            item = dict(entry.get("item") or {})
            score = float(entry.get("score", 0.0))
            reasons = list(entry.get("reasons") or [])

            if score < float(min_score):
                dropped.append({
                    "id": _safe_text(item.get("id")),
                    "reason": "below_min_score",
                    "score": round(score, 3),
                })
                continue

            text = self._clip_for_injection(item.get("text"), limit=per_item_char_limit)
            if not text:
                dropped.append({
                    "id": _safe_text(item.get("id")),
                    "reason": "empty_after_clip",
                    "score": round(score, 3),
                })
                continue

            fp = self._fingerprint(text)
            if fp and fp in seen_fp:
                dropped.append({
                    "id": _safe_text(item.get("id")),
                    "reason": "duplicate_memory",
                    "score": round(score, 3),
                })
                continue

            projected_total = total_chars + len(text)
            if projected_total > int(max_chars_total):
                dropped.append({
                    "id": _safe_text(item.get("id")),
                    "reason": "prompt_char_cap",
                    "score": round(score, 3),
                })
                continue

            sanitized_item = {
                **item,
                "text": text,
            }

            selected.append(sanitized_item)
            reasoning.append({
                "id": _safe_text(item.get("id")),
                "kind": _safe_text(item.get("kind")),
                "score": round(score, 3),
                "reasons": reasons,
            })

            total_chars = projected_total
            if fp:
                seen_fp.add(fp)

            if len(selected) >= int(max_items):
                break

        preference_lock = any(_safe_text(item.get("kind")) == "preference" for item in selected)

        return {
            "items": selected,
            "reasoning": reasoning,
            "preference_lock": preference_lock,
            "stats": {
                "ranked_count": len(ranked or []),
                "selected_count": len(selected),
                "dropped_count": len(dropped),
                "max_items": int(max_items),
                "min_score": float(min_score),
                "max_chars_total": int(max_chars_total),
                "total_chars_used": int(total_chars),
            },
            "dropped": dropped[:25],
        }

    def memory_context(
        self,
        query: str,
        mode: str = "chat",
        session_id: str | None = None,
        limit: int = 8,
        inject_limit: int = 5,
        min_injection_score: float = 2.5,
        max_chars_total: int = 1000,
        per_item_char_limit: int = 220,
    ) -> dict:
        ranked = self.recall(
            query=query,
            mode=mode,
            session_id=session_id,
            limit=max(int(limit), int(inject_limit), 1),
        )

        sanitized = self.sanitize_for_injection(
            ranked,
            max_items=inject_limit,
            min_score=min_injection_score,
            max_chars_total=max_chars_total,
            per_item_char_limit=per_item_char_limit,
        )

        return {
            "items": sanitized.get("items", []),
            "reasoning": sanitized.get("reasoning", []),
            "preference_lock": bool(sanitized.get("preference_lock")),
            "stats": sanitized.get("stats", {}),
            "dropped": sanitized.get("dropped", []),
            "ranked": ranked,
        }