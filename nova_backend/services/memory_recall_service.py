import re


class MemoryRecallService:

    IDENTITY_QUESTION_PATTERNS = [
        re.compile(
            r"\bwhat(?:'s| is)\s+my\s+name\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdo\s+you\s+know\s+my\s+name\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bwho\s+am\s+i\b",
            re.IGNORECASE,
        ),
    ]

    NAME_VALUE_PATTERNS = [
        re.compile(
            r"^\s*user\s+name\s+is\s+(.+?)\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*name\s*:\s*(.+?)\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*my\s+name\s+is\s+(.+?)\s*$",
            re.IGNORECASE,
        ),
    ]


    def __init__(self, memory_service):
        self.memory_service = memory_service


    def clean_fact_value(self, value):
        raw = str(value or "").strip()

        if not raw:
            return ""

        raw = re.sub(
            r"\s+",
            " ",
            raw,
        )

        return raw[:1].upper() + raw[1:]


    def clean_memory_value(self, value):
        value = str(value or "").strip()

        return re.sub(
            r"\s+",
            " ",
            value,
        )


    def normalize_name(self, value):
        value = self.clean_memory_value(value)

        value = re.sub(
            r"[^\w\s'\-]",
            "",
            value,
        ).strip()

        if not value:
            return ""

        return value[:1].upper() + value[1:]

    def extract_memory_fact(
        self,
        user_text,
    ):
        text = str(user_text or "").strip()

        if not text:
            return None

        patterns = [
            (
                re.compile(
                    r"\bmy name is\s+([A-Za-z][A-Za-z0-9_\-']{0,40})\b",
                    re.IGNORECASE,
                ),
                "profile",
                ["identity", "name"],
                5.0,
                lambda m: (
                    f"User name is "
                    f"{self.clean_fact_value(m.group(1))}"
                ),
            ),
            (
                re.compile(
                    r"\bi am\s+([A-Za-z][A-Za-z0-9_\-']{0,40})\b",
                    re.IGNORECASE,
                ),
                "profile",
                ["identity"],
                3.5,
                lambda m: (
                    f"User says they are "
                    f"{self.clean_fact_value(m.group(1))}"
                ),
            ),
            (
                re.compile(
                    r"\bi prefer\s+(.+)$",
                    re.IGNORECASE,
                ),
                "preference",
                ["preference"],
                2.5,
                lambda m: (
                    f"User preference: "
                    f"{m.group(1).strip()}"
                ),
            ),
            (
                re.compile(
                    r"\bremember that\s+(.+)$",
                    re.IGNORECASE,
                ),
                "note",
                ["memory"],
                2.0,
                lambda m: m.group(1).strip(),
            ),
        ]

        for pattern, kind, tags, weight, builder in patterns:
            match = pattern.search(text)

            if not match:
                continue

            fact_text = str(
                builder(match) or ""
            ).strip()

            if not fact_text:
                continue

            return {
                "text": fact_text,
                "kind": kind,
                "tags": tags,
                "weight": float(weight),
            }

        return None


    def memory_exists_for_session(
        self,
        session_id,
        fact_text,
    ):
        target_session = str(
            session_id or ""
        ).strip()

        target_text = str(
            fact_text or ""
        ).strip().lower()

        if not target_text:
            return False

        try:
            for item in self.memory_service.all():

                item_text = str(
                    item.get("text") or ""
                ).strip().lower()

                item_session = str(
                    item.get("session_id") or ""
                ).strip()

                if (
                    item_text == target_text
                    and item_session == target_session
                ):
                    return True

        except Exception:
            return False

        return False

    def extract_name_from_memory_text(
        self,
        text,
    ):
        raw = self.clean_memory_value(
            text
        )

        if not raw:
            return ""

        for pattern in self.NAME_VALUE_PATTERNS:
            match = pattern.search(raw)

            if match:
                return self.normalize_name(
                    match.group(1)
                )

        return ""


    def is_name_memory_item(
        self,
        item,
    ):
        if not isinstance(item, dict):
            return False

        return bool(
            self.extract_name_from_memory_text(
                item.get("text", "")
            )
        )


    def get_memory_items(self):
        try:
            items = self.memory_service.all()

            if isinstance(items, list):
                return items

        except Exception:
            pass

        return []

    def score_name_memory(
        self,
        item,
        session_id,
    ):
        if not isinstance(item, dict):
            return -9999.0

        score = 0.0

        item_text = str(
            item.get("text") or ""
        ).strip()

        item_session = str(
            item.get("session_id") or ""
        ).strip()

        item_kind = str(
            item.get("kind") or ""
        ).strip().lower()

        item_source = str(
            item.get("source") or ""
        ).strip().lower()

        item_updated = str(
            item.get("updated_at")
            or item.get("created_at")
            or ""
        )

        if not self.extract_name_from_memory_text(
            item_text
        ):
            return -9999.0

        if item_session and item_session == str(session_id or "").strip():
            score += 100.0
        elif not item_session:
            score += 15.0

        if item_kind == "profile":
            score += 20.0

        if item_source in {
            "router_auto",
            "assistant",
            "manual",
            "user",
        }:
            score += 5.0

        lowered = item_text.lower()

        if lowered.startswith("user name is"):
            score += 15.0
        elif lowered.startswith("name:"):
            score += 10.0
        elif lowered.startswith("my name is"):
            score += 5.0

        if item_updated:
            score += 1.0

        return score


    def find_best_name_memory(
        self,
        session_id,
    ):
        items = self.get_memory_items()

        candidates = []

        for item in items:
            score = self.score_name_memory(
                item,
                session_id,
            )

            if score <= -9999.0:
                continue

            candidates.append(
                {
                    "item": item,
                    "score": score,
                    "updated_at": str(
                        item.get("updated_at")
                        or item.get("created_at")
                        or ""
                    ),
                    "name": self.extract_name_from_memory_text(
                        item.get("text", "")
                    ),
                }
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda x: (
                x["score"],
                x["updated_at"],
            ),
            reverse=True,
        )

        return candidates[0]

    def cleanup_competing_name_memories(
        self,
        session_id,
        winning_text,
    ):
        target_session = str(
            session_id or ""
        ).strip()

        winning_text = str(
            winning_text or ""
        ).strip().lower()

        if not winning_text:
            return

        for item in self.get_memory_items():

            if not isinstance(item, dict):
                continue

            item_id = str(
                item.get("id") or ""
            ).strip()

            item_session = str(
                item.get("session_id") or ""
            ).strip()

            item_text = str(
                item.get("text") or ""
            ).strip().lower()

            if not item_id:
                continue

            if item_session != target_session:
                continue

            if not self.is_name_memory_item(item):
                continue

            if item_text == winning_text:
                continue

            for method_name in (
                "delete_memory",
                "delete",
                "remove",
            ):
                method = getattr(
                    self.memory_service,
                    method_name,
                    None,
                )

                if callable(method):
                    try:
                        method(item_id)
                    except Exception:
                        pass

                    break