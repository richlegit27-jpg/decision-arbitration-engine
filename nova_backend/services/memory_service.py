from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from nova_backend.utils.file_utils import load_json_file, save_json_file
from nova_backend.utils.time_utils import iso_now
from nova_backend.services.auth_context import get_current_user_id


# NOVA_BAD_MEMORY_SAVE_GUARD_SAFE_20260610
_BAD_MEMORY_SAVE_MARKERS_20260610 = (
    "Project-aware context for Nova:",
    "Recent session context:",
    "Relevant persistent memory:",
    "Attachment received:",
    "Key points:",
    "[CURRENT UPLOADED",
    "python app.py Project-aware context",
)

def _nova_should_reject_memory_item_20260610(item):
    if not isinstance(item, dict):
        return False

    value = str(
        item.get("text")
        or item.get("content")
        or item.get("value")
        or item.get("memory")
        or ""
    ).strip()

    kind = str(
        item.get("type")
        or item.get("category")
        or item.get("kind")
        or ""
    ).lower()

    if not value:
        return True

    if any(marker in value for marker in _BAD_MEMORY_SAVE_MARKERS_20260610):
        return True

    if kind == "user_fact" and len(value) > 500:
        return True

    lowered = value.lower()
    question_starters = (
        "what is ",
        "what's ",
        "whats ",
        "who is ",
        "where is ",
        "when is ",
        "why is ",
        "how is ",
        "how do ",
        "do i ",
        "did i ",
        "can you ",
        "tell me ",
    )

    if lowered.endswith("?") or lowered.startswith(question_starters):
        return True
    transcript_markers = lowered.count("- [user]") + lowered.count("- [assistant]") + lowered.count("[note]")
    if transcript_markers >= 2:
        return True

    return False

def _nova_memory_semantic_key_20260618(text: str) -> str:
    import re

    value = str(text or "").strip().lower()

    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    replacements = {
        "my favourite color is": "favorite color",
        "my favorite color is": "favorite color",
        "favourite color is": "favorite color",
        "favorite color is": "favorite color",
        "fav color is": "favorite color",
        "fav color": "favorite color",
        "i like": "likes",
        "i prefer": "prefers",
        "richard likes": "likes",
        "rich likes": "likes",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    words = [
        word for word in value.split()
        if word not in {"my", "the", "a", "an", "is", "are", "to", "that"}
    ]

    return " ".join(words)

class MemoryService:

    def _current_owner_id(self) -> str:
        return get_current_user_id()

    def _same_memory_owner(self, item: Dict[str, Any]) -> bool:
        owner_id = self._current_owner_id()

        if not owner_id:
            return False

        item_owner = str(
            (item or {}).get("owner_id") or ""
        ).strip()

        return item_owner == owner_id

    def __init__(self, memory_file: str):
        self.memory_file = Path(memory_file)
        self._ensure_store()

    def _ensure_store(self) -> None:
        if not self.memory_file.exists():
            save_json_file(self.memory_file, {"memory": []})

    def _read_store(self) -> Dict[str, Any]:
        data = load_json_file(self.memory_file, {"memory": []})
        if not isinstance(data, dict):
            return {"memory": []}

        if not isinstance(data.get("memory"), list):
            data["memory"] = []

        return data

    def _write_store(self, data: Dict[str, Any]) -> None:
        save_json_file(self.memory_file, data)

    def _base_weight_for_kind(self, kind: str, pinned: bool = False) -> float:
        if pinned:
            return 10.0

        k = str(kind or "note").strip().lower()

        if k in ("project", "goal"):
            return 6.0
        if k in ("profile", "preference"):
            return 5.0
        if k == "fact":
            return 3.0

        return 1.0

    def _apply_memory_decay(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(item or {})

        if item.get("pinned"):
            item["weight"] = 10.0
            return item

        weight = float(item.get("weight") or self._base_weight_for_kind(item.get("kind")))
        updated_at = str(item.get("updated_at") or item.get("created_at") or "")

        if not updated_at:
            item["weight"] = max(1.0, weight)
            return item

        try:
            from datetime import datetime, UTC, timezone

            raw = updated_at.replace("Z", "+00:00")
            updated = datetime.fromisoformat(raw)

            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)

            age_days = max(0, (datetime.now(timezone.utc) - updated).days)
            decay_steps = age_days // 30
            decayed = weight - (decay_steps * 0.35)

            item["weight"] = max(1.0, round(decayed, 2))
        except Exception:
            item["weight"] = max(1.0, weight)

        return item

    def all(self) -> List[Dict[str, Any]]:
        items = self._read_store().get("memory", [])

        owner_id = self._current_owner_id()

        if not owner_id:
            return []

        items = [
            item
            for item in items
            if item.get("owner_id") == owner_id
        ]

        if not isinstance(items, list):
            return []

        items = [self._apply_memory_decay(dict(x or {})) for x in items]

        items.sort(
            key=lambda x: (
                float(x.get("weight") or 1.0),
                str(x.get("updated_at") or ""),
            ),
            reverse=True,
        )

        return items

    def build_list_payload(self) -> List[Dict[str, Any]]:
        return self.all()

    def build_view_payload(self, memory_id: str) -> Optional[Dict[str, Any]]:
        return self.get(memory_id)

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        target = str(memory_id or "").strip()
        if not target:
            return None

        for item in self.all():
            if str(item.get("id") or "").strip() == target:
                return item

        return None

    def summarize_memory_list(self, memory: list) -> list:
        if len(memory) <= 80:
            return memory

        strong = [
            m for m in memory
            if float(m.get("weight", 1.0)) >= 3.0 or bool(m.get("pinned"))
        ]

        weak = [
            m for m in memory
            if float(m.get("weight", 1.0)) < 3.0 and not bool(m.get("pinned"))
        ]

        summary_texts = []
        for m in weak[-20:]:
            text = str(m.get("text") or "").strip()
            if text:
                summary_texts.append(text)

        if summary_texts:
            import uuid
            summary = {
                "id": f"memory_summary_{uuid.uuid4().hex}",
                "text": "Memory summary: " + "; ".join(summary_texts[:10]),
                "kind": "summary",
                "source": "memory-summary",
                "weight": 2.0,
                "count": 1,
                "pinned": False,
                "created_at": iso_now(),
                "updated_at": iso_now(),
            }
            strong.append(summary)

        return strong[-100:]

    def add_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # NOVA_BAD_MEMORY_SAVE_GUARD_SAFE_20260610_ENTRY
        if _nova_should_reject_memory_item_20260610(item):
            return item

        data = self._read_store()
        memory = data.get("memory", [])

        item = dict(item or {})
        now = iso_now()

        new_text = str(item.get("text") or "").strip()
        new_text_key = new_text.lower()
        new_kind = str(item.get("kind") or "note").strip().lower()
        pinned = bool(item.get("pinned"))

        # ðŸ”¥ CONFLICT RESOLUTION (newer overrides older)
        conflict_groups = [
            ("short answers", "long answers"),
            ("concise", "detailed"),
            ("formal", "casual"),
        ]

        for a, b in conflict_groups:
            if a in new_text_key or b in new_text_key:
                for i, existing in enumerate(memory):
                    existing = dict(existing or {})
                    existing_text = str(existing.get("text") or "").lower()

                    if (a in existing_text or b in existing_text) and existing_text != new_text_key:
                        existing["weight"] = 0.5
                        existing["pinned"] = False
                        existing["updated_at"] = now
                        memory[i] = existing

        item["text"] = new_text
        item["kind"] = new_kind
        item["weight"] = float(item.get("weight") or self._base_weight_for_kind(new_kind, pinned=pinned))

        preference_keys = (
            "favorite color",
            "favourite color",
            "favorite drink",
            "favourite drink",
            "favorite snack",
            "favourite snack",
            "favorite food",
            "favourite food",
            "favorite movie",
            "favourite movie",
            "favorite show",
            "favourite show",
            "favorite song",
            "favourite song",
            "favorite game",
            "favourite game",
            "communication style",
            "name is",
            "prefers to be called",
        )

        # ðŸ”¥ KEYED PREFERENCE REPLACEMENT
        for key in preference_keys:
            if key in new_text_key:
                for i, existing in enumerate(memory):
                    existing = dict(existing or {})
                    existing_text = str(existing.get("text") or "").strip().lower()
                    existing_kind = str(existing.get("kind") or "note").strip().lower()

                    if (
                        self._same_memory_owner(existing)
                        and key in existing_text
                        and existing_kind == new_kind
                    ):
                        existing.update(item)
                        existing["updated_at"] = now
                        existing["created_at"] = existing.get("created_at") or now

                        memory[i] = existing
                        data["memory"] = memory
                        self._write_store(data)
                        return existing

        # DUPLICATE REINFORCEMENT
        for i, existing in enumerate(memory):
            existing = dict(existing or {})
            existing_text = str(existing.get("text") or "").strip().lower()
            existing_kind = str(existing.get("kind") or "note").strip().lower()

            if (
                self._same_memory_owner(existing)
                and existing_text == new_text_key
                and existing_kind == new_kind
            ):
                count = int(existing.get("count") or 1) + 1
                existing_weight = float(existing.get("weight") or item.get("weight") or 1.0)

                existing.update(item)
                existing["count"] = count
                existing["updated_at"] = now
                existing["created_at"] = existing.get("created_at") or now

                # ðŸ”¥ DECAY BEFORE BOOST
                try:
                    from datetime import datetime, UTC
                    created_at = existing.get("created_at")
                    if created_at:
                        created_ts = datetime.fromisoformat(created_at.replace("Z", ""))
                        age_days = (datetime.now(UTC) - created_ts).days

                        if age_days > 7:
                            existing_weight *= 0.85
                        if age_days > 30:
                            existing_weight *= 0.65
                except Exception:
                    pass

                # ðŸ”¥ IMPORTANCE BOOST
                boost = 1.25
                if existing.get("pinned"):
                    boost = 0.5
                if "from now on" in existing_text or "always" in existing_text:
                    boost = 2.0

                existing["weight"] = min(10.0, existing_weight + boost)

                if count >= 3:
                    existing["pinned"] = True
                    existing["weight"] = 10.0

                memory[i] = existing
                data["memory"] = memory
                self._write_store(data)
                return existing

        # 🔥 NEW MEMORY
        if not item.get("id"):
            item["id"] = f"memory_{uuid.uuid4().hex}"

        owner_id = self._current_owner_id()
        if owner_id:
            item["owner_id"] = owner_id

        item["updated_at"] = now
        item["created_at"] = item.get("created_at") or now
        item["count"] = int(item.get("count") or 1)

        # NOVA_MEMORY_DEDUPE_LOCK_20260618
        normalized_text = str(item.get("text") or "").strip().lower()
        semantic_text = _nova_memory_semantic_key_20260618(normalized_text)

        for i, existing in enumerate(memory):
            existing = dict(existing or {})
            existing_text = str(existing.get("text") or "").strip().lower()
            existing_semantic_text = _nova_memory_semantic_key_20260618(existing_text)

            if (
                self._same_memory_owner(existing)
                and (
                    existing_text == normalized_text
                    or existing_semantic_text == semantic_text
                )
            ):

                existing["updated_at"] = now
                existing["last_seen_at"] = now
                existing["count"] = int(existing.get("count") or 1) + 1

                if item.get("weight"):
                    existing["weight"] = max(
                        float(existing.get("weight") or 1.0),
                        float(item.get("weight") or 1.0),
                    )

                memory[i] = existing
                data["memory"] = memory
                self._write_store(data)
                return existing

        memory.append(item)

        # ðŸ”¥ CLEANUP WEAK MEMORY
        memory = [
            m for m in memory
            if float(m.get("weight", 1.0)) > 0.5
        ]

        MAX_MEMORY_ITEMS = 300
        memory = self.summarize_memory_list(memory)

        memory.sort(
            key=lambda m: (
                bool(m.get("pinned")),
                float(m.get("weight") or 1.0),
                int(m.get("count") or 1),
                str(m.get("updated_at") or ""),
            ),
            reverse=True,
        )

        memory = memory[:MAX_MEMORY_ITEMS]

        data["memory"] = memory
        self._write_store(data)

        return item

    def save_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read_store()
        memory = data.get("memory", [])

        item = dict(item or {})
        now = iso_now()

        if not item.get("id"):
            import uuid
            item["id"] = f"memory_{uuid.uuid4().hex}"

        owner_id = self._current_owner_id()
        if owner_id:
            item["owner_id"] = owner_id

        kind = str(item.get("kind") or "note").strip().lower()
        item["kind"] = kind
        item["updated_at"] = now
        item["created_at"] = item.get("created_at") or now

        if item.get("pinned"):
            item["weight"] = 10.0
        elif not item.get("weight"):
            item["weight"] = self._base_weight_for_kind(kind)

        replaced = False
        for i, existing in enumerate(memory):
            if str((existing or {}).get("id") or "") == str(item["id"]):
                memory[i] = item
                replaced = True
                break

        if not replaced:
            memory.append(item)

        MAX_MEMORY_ITEMS = 300

        memory.sort(
            key=lambda m: (
                bool(m.get("pinned")),
                float(m.get("weight") or 1.0),
                int(m.get("count") or 1),
                str(m.get("updated_at") or ""),
            ),
            reverse=True,
        )

        memory = memory[:MAX_MEMORY_ITEMS]

        data["memory"] = memory
        self._write_store(data)

        return item

    def pin_memory(self, memory_id: str, pinned: bool = True) -> dict | None:
        target = str(memory_id or "").strip()
        if not target:
            return None

        data = self._read_store()
        memory = data.get("memory", [])

        owner_id = self._current_owner_id()

        data = self._read_store()
        memory = data.get("memory", [])

        owner_id = self._current_owner_id()

        for i, item in enumerate(memory):
            item = dict(item or {})

            if owner_id:
                if item.get("owner_id") and item.get("owner_id") != owner_id:
                    continue

            if str(item.get("id") or "").strip() == target:
                item["pinned"] = bool(pinned)
                item["weight"] = 10.0 if pinned else self._base_weight_for_kind(item.get("kind"))
                item["updated_at"] = iso_now()

                memory[i] = item
                data["memory"] = memory
                self._write_store(data)
                return item

        return None

    def delete_memory(self, memory_id: str) -> bool:
        target = str(memory_id or "").strip()
        if not target:
            return False

        data = self._read_store()
        memory = data.get("memory", [])

        owner_id = self._current_owner_id()

        if not owner_id:
            return False

        kept = [
            item for item in memory
            if not (
                str(item.get("id") or "").strip() == target
                and item.get("owner_id") == owner_id
            )
        ]

        if len(kept) == len(memory):
            return False

        data["memory"] = kept
        self._write_store(data)
        return True

    def clear(self) -> None:
        self._write_store({"memory": []})

    def cleanup_memories(self) -> Dict[str, Any]:
        junk_patterns = (
            "traceback",
            "attributeerror",
            "nameerror",
            "unboundlocalerror",
            "taberror",
            "syntaxerror",
            "indentationerror",
            "internal error",
            "chat_service.py",
            "nova_backend",
            "copy regenerate",
        )

        preference_keys = (
            "favorite color",
            "favourite color",
            "favorite drink",
            "favourite drink",
            "favorite snack",
            "favourite snack",
            "favorite food",
            "favourite food",
            "favorite movie",
            "favourite movie",
            "favorite show",
            "favourite show",
            "favorite song",
            "favourite song",
            "favorite game",
            "favourite game",
        )

        items = self.all()
        cleaned = []
        removed = []
        seen_keys = set()
        latest_preference_by_key = {}

        for item in items:
            text = str(item.get("text") or "").lower()

            question_starters = (
                "what is ",
                "what's ",
                "whats ",
                "who is ",
                "where is ",
                "when is ",
                "why is ",
                "how is ",
                "how do ",
                "do i ",
                "did i ",
                "can you ",
                "tell me ",
            )

            if text.endswith("?") or text.startswith(question_starters):
                removed.append(item)
                continue

            if any(pattern in text for pattern in junk_patterns):
                removed.append(item)
                continue

            semantic_key = _nova_memory_semantic_key_20260618(text)

            if semantic_key in seen_keys:
                removed.append(item)
                continue

            seen_keys.add(semantic_key)

            matched_preference_key = None
            for key in preference_keys:
                if key in text:
                    matched_preference_key = key.replace("favourite", "favorite")
                    break

            if matched_preference_key:
                existing = latest_preference_by_key.get(matched_preference_key)

                if existing:
                    existing_time = str(existing.get("updated_at") or existing.get("created_at") or "")
                    item_time = str(item.get("updated_at") or item.get("created_at") or "")

                    if item_time > existing_time:
                        removed.append(existing)
                        latest_preference_by_key[matched_preference_key] = item
                    else:
                        removed.append(item)

                    continue

                latest_preference_by_key[matched_preference_key] = item
                continue

            cleaned.append(item)

        cleaned.extend(latest_preference_by_key.values())

        self._write_store({"memory": cleaned})

        return {
            "removed": len(removed),
            "kept": len(cleaned),
            "memory": cleaned,
        }

    def promote_memories(self) -> Dict[str, Any]:
        data = self._read_store()
        memory = data.get("memory", [])

        promoted = 0
        updated_items = []

        for item in memory:
            item = dict(item or {})
            kind = str(item.get("kind") or "note").strip().lower()
            count = int(item.get("count") or 1)
            text = str(item.get("text") or "").strip()

            if not text:
                updated_items.append(item)
                continue

            base_weight = self._base_weight_for_kind(kind, pinned=bool(item.get("pinned")))
            current_weight = float(item.get("weight") or base_weight)

            if item.get("pinned"):
                item["weight"] = 10.0
            elif count >= 3:
                item["pinned"] = True
                item["weight"] = 10.0
                promoted += 1
            else:
                item["weight"] = max(current_weight, base_weight)

            updated_items.append(item)

        self._write_store({"memory": updated_items})

        return {
            "promoted": promoted,
            "kept": len(updated_items),
            "memory": self.all(),
        }

    def cleanup_and_promote_memories(self) -> Dict[str, Any]:
        cleanup_result = self.cleanup_memories()
        promote_result = self.promote_memories()

        return {
            "removed": cleanup_result.get("removed", 0),
            "promoted": promote_result.get("promoted", 0),
            "kept": promote_result.get("kept", 0),
            "memory": self.all(),
        }


