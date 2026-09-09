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

# NOVA_WEAK_MEMORY_MARKERS_SAFE_20260822
_NOVA_WEAK_MEMORY_MARKERS_20260822 = (
    "temporary",
    " temp",
    "test",
    " trace",
    "debug",
    "debugging",
    "experiment",
    "testing",
    "sample",
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

    lowered = value.lower()

    junk_memory = (
        "hi",
        "hello",
        "hey",
        "yo",
        "ok",
        "okay",
        "thanks",
        "thank you",
        "thx",
        "test",
    )

    if lowered in junk_memory:
        return True

    if any(marker in value for marker in _BAD_MEMORY_SAVE_MARKERS_20260610):
        return True

    if any(
        marker in value.lower()
        for marker in _NOVA_WEAK_MEMORY_MARKERS_20260822
    ):
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

        "remember that my name is": "name is",
        "my name is": "name is",
        "my name": "name is",

        "nova uses powershell commands": "always use powershell commands",
        "i always want powershell commands": "always use powershell commands",
        "always want powershell commands": "always use powershell commands",
        "use powershell commands": "always use powershell commands",

        "remember that nova uses port 5001 for development": "nova uses port 5001",
        "nova uses port 5001 for development": "nova uses port 5001",
        "remember that nova uses port 5001": "nova uses port 5001",
        "nova uses port 5001": "nova uses port 5001",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    words = [
        word for word in value.split()
        if word not in {"my", "the", "a", "an", "is", "are", "to", "that"}
    ]

    return " ".join(words)

def _nova_memory_fact_key(text: str) -> str:
    value = str(text or "").lower().strip()

    if "nova" in value and "backend" in value and "port" in value:
        return "nova_backend_port"

    if "nova" in value and "ui" in value and "port" in value:
        return "nova_ui_port"

    if "ollama" in value and "port" in value:
        return "ollama_port"

    return ""

class MemoryService:

    def _nova_should_accept_memory_confidence(self, item):
        try:
            confidence = float(
                item.get("confidence", 0.5)
            )
        except Exception:
            confidence = 0.5

        return confidence >= 0.35

    def _current_owner_id(self) -> str:
        return get_current_user_id()

    def _same_memory_owner(self, item: Dict[str, Any]) -> bool:
        owner_id = str(self._current_owner_id() or "").strip()

        item_owner = str(
            (item or {}).get("owner_id") or ""
        ).strip()

        # No authenticated owner:
        # treat anonymous/manual memory as same owner
        if not owner_id and not item_owner:
            return True

        return item_owner == owner_id

    def __init__(self, memory_file: str):
        self.memory_file = Path(memory_file)
        self._ensure_store()

    def _ensure_store(self) -> None:
        if not self.memory_file.exists():
            save_json_file(self.memory_file, {"memory": []})

    def _read_store(self) -> Dict[str, Any]:
        data = load_json_file(
            self.memory_file,
            {"memory": []},
        )

        if not isinstance(data, dict):
            return {"memory": []}

        if not isinstance(data.get("memory"), list):
            data["memory"] = []

        memory = data["memory"]

        seen_fact_keys = {}

        cleaned_memory = []

        for item in memory:
            fact_key = item.get("fact_key")

            if fact_key:
                if fact_key in seen_fact_keys:
                    existing = seen_fact_keys[fact_key]

                    if (
                        int(item.get("count") or 1)
                        >
                        int(existing.get("count") or 1)
                    ):
                        seen_fact_keys[fact_key] = item

                    continue

                seen_fact_keys[fact_key] = item

            cleaned_memory.append(item)

        data["memory"] = (
            list(seen_fact_keys.values())
            + [
                item
                for item in cleaned_memory
                if not item.get("fact_key")
            ]
        )

        return data

    def _write_store(self, data: Dict[str, Any]) -> None:
        print(
            "DEBUG MEMORY WRITE PATH =",
            self.memory_file,
            flush=True,
        )

        try:
            print(
                "[MEMORY WRITE DATA LAST ITEM]",
                data.get("memory", [])[-1]
                if data.get("memory")
                else None,
                flush=True,
            )

            save_json_file(
                self.memory_file,
                data,
            )

            print(
                "[MEMORY WRITE COMPLETE]",
                self.memory_file,
                flush=True,
            )

            print(
                "[MEMORY WRITE VERIFY]",
                self.memory_file,
                self.memory_file.exists(),
                self.memory_file.stat().st_size
                if self.memory_file.exists()
                else 0,
                flush=True,
            )

        except Exception as exc:
            try:
                from nova_backend.services.error_reporting_service import (
                    ErrorReportingService,
                )

                ErrorReportingService().report(
                    exc,
                    service="memory_write_store",
                )

            except Exception:
                pass

            raise

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

        if not isinstance(items, list):
            return []

        owner_id = self._current_owner_id()

        if owner_id:
            items = [
                item
                for item in items
                if not item.get("owner_id")
                or item.get("owner_id") == owner_id
            ]

        items = [
            self._apply_memory_decay(dict(x or {}))
            for x in items
        ]

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

    def _nova_memory_confidence(self, item):
        try:
            value = float(
                item.get("confidence", 0.5)
            )
        except Exception:
            value = 0.5

        return max(
            0.0,
            min(value, 1.0)
        )

    def add_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        print(
            "[MEMORY ADD HIT]",
            {
                "text": item.get("text"),
                "kind": item.get("kind"),
                "confidence": item.get("confidence"),
                "source": item.get("source"),
            },
            flush=True,
        )

        if _nova_should_reject_memory_item_20260610(item):
            print(
                "[MEMORY REJECTED]",
                item,
                flush=True,
            )
            return item

        item["confidence"] = self._nova_memory_confidence(item)

        if not self._nova_should_accept_memory_confidence(item):
            return item

        data = self._read_store()
        memory = data.get("memory", [])

        item = dict(item or {})
        now = iso_now()

        item_text = str(
            item.get("text")
            or ""
        ).strip()

        item["text"] = item_text

        new_text_key = item_text.lower()

        new_kind = str(
            item.get("kind")
            or "note"
        ).strip().lower()

        item["kind"] = new_kind

        fact_key = _nova_memory_fact_key(
            item_text
        )

        if fact_key:
            item["fact_key"] = fact_key

        item["weight"] = float(
            item.get("weight")
            or self._base_weight_for_kind(
                new_kind,
                pinned=bool(item.get("pinned"))
            )
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
            "communication style",
            "prefers to be called",
            "always want",
            "always use",
            "prefer",
            "prefers",
        )

        for key in preference_keys:
            if key in new_text_key:

                for i, existing in enumerate(memory):
                    existing = dict(existing or {})

                    existing_text = str(
                        existing.get("text")
                        or ""
                    ).strip().lower()

                    existing_kind = str(
                        existing.get("kind")
                        or ""
                    ).strip().lower()

                    if (
                        key in existing_text
                        and existing_kind == new_kind
                    ):
                        existing.update(item)

                        existing["count"] = int(
                            existing.get("count")
                            or 1
                        ) + 1

                        existing["created_at"] = (
                            existing.get("created_at")
                            or now
                        )

                        existing["updated_at"] = now

                        memory[i] = existing

                        data["memory"] = memory

                        self._write_store(data)

                        return existing



        # DUPLICATE REINFORCEMENT
        for i, existing in enumerate(memory):
            existing = dict(existing or {})

            existing_fact_key = existing.get(
                "fact_key"
            )

            if not existing_fact_key:
                existing_fact_key = _nova_memory_fact_key(
                    existing.get("text")
                )

            existing_kind = str(
                existing.get("kind") or "note"
            ).strip().lower()

            if (
                self._same_memory_owner(existing)
                and existing_fact_key
                and existing_fact_key == fact_key
                and existing_kind == new_kind
            ):
                count = int(
                    existing.get("count")
                    or 1
                ) + 1

                existing_weight = float(
                    existing.get("weight")
                    or item.get("weight")
                    or 1.0
                )

                existing.update(item)

                existing["count"] = count
                existing["fact_key"] = fact_key
                existing["updated_at"] = now
                existing["created_at"] = (
                    existing.get("created_at")
                    or now
                )

                # DECAY BEFORE BOOST
                try:
                    from datetime import datetime, UTC

                    created_at = existing.get(
                        "created_at"
                    )

                    if created_at:
                        created_ts = datetime.fromisoformat(
                            created_at.replace("Z", "")
                        )

                        age_days = (
                            datetime.now(UTC)
                            - created_ts
                        ).days

                        if age_days > 7:
                            existing_weight *= 0.85

                        if age_days > 30:
                            existing_weight *= 0.65

                except Exception:
                    pass

                # IMPORTANCE BOOST
                boost = 1.25

                existing_text = str(
                    existing.get("text") or ""
                ).lower()

                if existing.get("pinned"):
                    boost = 0.5

                if (
                    "from now on" in existing_text
                    or "always" in existing_text
                ):
                    boost = 2.0

                existing["weight"] = min(
                    10.0,
                    existing_weight + boost
                )

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

        normalized_text = str(
            item.get("text") or ""
        ).strip().lower()

        semantic_text = _nova_memory_semantic_key_20260618(
            normalized_text
        )

        fact_key = _nova_memory_fact_key(
            normalized_text
        )

        if fact_key:
            item["fact_key"] = fact_key

        # FACT KEY REPLACEMENT
        if fact_key:
            for i, existing in enumerate(memory):
                existing = dict(existing or {})

                existing_fact_key = existing.get(
                    "fact_key"
                )

                if not existing_fact_key:
                    existing_fact_key = _nova_memory_fact_key(
                        existing.get("text")
                    )

                    if existing_fact_key:
                        existing["fact_key"] = existing_fact_key

                if (
                    self._same_memory_owner(existing)
                    and existing_fact_key == fact_key
                ):

                    item["created_at"] = (
                        existing.get("created_at")
                        or now
                    )

                    item["count"] = int(
                        existing.get("count")
                        or 1
                    ) + 1

                    item["fact_key"] = fact_key

                    item["updated_at"] = now

                    if existing.get("pinned"):
                        item["pinned"] = True

                    if existing.get("weight"):
                        item["weight"] = max(
                            float(existing.get("weight") or 1.0),
                            float(item.get("weight") or 1.0),
                        )

                    memory[i] = item

                    data["memory"] = memory

                    self._write_store(data)

                    return item

        # SEMANTIC DUPLICATE CHECK
        for i, existing in enumerate(memory):
            existing = dict(existing or {})

            existing_text = str(
                existing.get("text") or ""
            ).strip().lower()

            existing_semantic_text = (
                _nova_memory_semantic_key_20260618(
                    existing_text
                )
            )

            if (
                self._same_memory_owner(existing)
                and (
                    existing_text == normalized_text
                    or existing_semantic_text == semantic_text
                )
            ):

                existing["updated_at"] = now
                existing["last_seen_at"] = now
                existing["count"] = int(
                    existing.get("count")
                    or 1
                ) + 1

                if item.get("weight"):
                    existing["weight"] = max(
                        float(existing.get("weight") or 1.0),
                        float(item.get("weight") or 1.0),
                    )

                memory[i] = existing

                data["memory"] = memory

                self._write_store(data)

                return existing


        print(
            "[FINAL MEMORY BEFORE APPEND]",
            item,
            flush=True,
        )

        memory.append(item)

        print(
            "[MEMORY APPENDED ITEM]",
            item,
            flush=True,
        )

        print(
            "[MEMORY COUNT AFTER APPEND]",
            len(memory),
            flush=True,
        )

        # 🔥 CLEANUP WEAK MEMORY
        memory = [
            m for m in memory
            if float(m.get("weight", 1.0)) > 0.5
        ]

        MAX_MEMORY_ITEMS = 300
        print(
            "[BEFORE SUMMARY CHECK]",
            [

                m.get("text")
                for m in memory
                if "full file" in str(m.get("text") or "").lower()
            ],
            flush=True,
        )

        memory = self.summarize_memory_list(memory)

        print(
            "[AFTER SUMMARY CHECK]",
            [
                m.get("text")
                for m in memory
                if "full file" in str(m.get("text") or "").lower()
            ],
            flush=True,
        )

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
        return self.add_memory(item)

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

        kept = []

        for item in memory:
            item_id = str(item.get("id") or "").strip()

            if item_id != target:
                kept.append(item)
                continue

            if owner_id:
                if item.get("owner_id") == owner_id:
                    continue
                kept.append(item)
                continue

            # local tool execution without auth context
            continue

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
            "communication style",
            "prefers to be called",
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

            transient_patterns = (
                "price right now",
                "current price",
                "stock price",
                "weather today",
                "latest news",
                "search for",
                "look up",
                "tell me the price",
                "what time is",
                "current time",
            )

            if any(pattern in text for pattern in transient_patterns):
                removed.append(item)
                continue

            protected_junk_patterns = (
                "price right now",
                "current price",
                "stock price",
                "weather today",
                "latest news",
                "search for",
                "look up",
            )

            if any(
                pattern in text
                for pattern in protected_junk_patterns
            ):
                removed.append(item)
                continue

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


