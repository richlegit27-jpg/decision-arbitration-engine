import re

from datetime import datetime, timezone


class MemoryContextService:

    def __init__(
        self,
        data_dir,
        session_service,
    ):
        self.data_dir = data_dir
        self.session_service = session_service

    def read_json_file(self, path):
        try:
            if not path.exists():
                return None

            import json

            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            return None

    def compact_text(
        self,
        value,
        *,
        limit=500,
    ):
        text_value = (
            str(value or "")
            .replace("\r", "\n")
            .strip()
        )

        while "\n\n\n" in text_value:
            text_value = text_value.replace(
                "\n\n\n",
                "\n\n",
            )

        if len(text_value) > limit:
            return (
                text_value[:limit]
                .rstrip()
                + "..."
            )

        return text_value

    def memory_text(self, item):
        if isinstance(item, str):
            return item.strip()

        if not isinstance(item, dict):
            return ""

        for key in (
            "text",
            "content",
            "memory",
            "summary",
            "value",
            "note",
            "description",
        ):
            value = item.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def normalize_key(self, value):
        text_value = (
            str(value or "")
            .strip()
            .lower()
        )

        text_value = re.sub(
            r"\s+",
            " ",
            text_value,
        )

        return text_value[:500]

    def memory_text_tokens(self, value):
        text_value = str(value or "").lower()

        return {
            token.strip(".,!?;:()[]{}\"'")
            for token in text_value.split()
            if len(
                token.strip(".,!?;:()[]{}\"'")
            ) >= 3
        }

    def memory_is_relevant_enough(
        self,
        item: dict,
        score: float,
        user_text: str,
    ) -> bool:
        text = self.memory_text(item)

        if not text:
            return False

        query = str(user_text or "").lower()

        if any(
            x in query
            for x in [
                "remember",
                "memory",
                "about me",
                "my project",
            ]
        ):
            return True

        query_tokens = self.memory_text_tokens(user_text)
        memory_tokens = self.memory_text_tokens(text)

        overlap = query_tokens.intersection(
            memory_tokens
        )

        if score >= 1.5:
            return True

        if len(overlap) >= 1:
            return True

        kind = self.memory_kind(item).lower()

        if kind in {
            "project",
            "preference",
            "profile",
            "goal",
        }:
            return True

        return False

    def memory_kind_weight(self, kind: str) -> float:
        weights = {
            "profile": 5.0,
            "preference": 4.0,
            "user_fact": 4.0,
            "project_focus": 3.5,
            "note": 2.0,
            "memory": 1.0,
        }

        return weights.get(
            str(kind or "").strip().lower(),
            1.0,
        )


    def memory_time_bonus(self, item: dict) -> float:
        if not isinstance(item, dict):
            return 0.0

        timestamp = (
            item.get("created_at")
            or item.get("updated_at")
            or item.get("timestamp")
            or ""
        )

        if not timestamp:
            return 0.0

        try:
            parsed = datetime.fromisoformat(
                str(timestamp).replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            age_days = (
                datetime.now(timezone.utc)
                - parsed
            ).days

            if age_days <= 1:
                return 5.0

            if age_days <= 7:
                return 2.0

        except Exception:
            pass

        return 0.0


    def memory_session_bonus(
        self,
        item: dict,
        session_id: str = "",
    ) -> float:
        if not isinstance(item, dict):
            return 0.0

        item_session = str(
            item.get("session_id")
            or ""
        ).strip()

        if item_session and item_session == str(session_id or "").strip():
            return 5.0

        return 0.0


    def score_memory_item(
        self,
        item,
        query,
        session_id="",
    ):
        memory_text = self.memory_text(item)

        if not memory_text:
            return 0.0

        query_tokens = self.memory_text_tokens(query)
        memory_tokens = self.memory_text_tokens(memory_text)

        overlap = len(
            query_tokens.intersection(
                memory_tokens
            )
        )

        kind_score = self.memory_kind_weight(
            self.memory_kind(item)
        )

        return (
            overlap * 10
            + kind_score
            + self.memory_time_bonus(item)
            + self.memory_session_bonus(
                item,
                session_id=session_id,
            )
            - self.score_penalty(
                memory_text,
                self.memory_kind(item),
            )
        )

    def is_junk_memory(
        self,
        text_value,
        kind="",
    ):
        raw = str(text_value or "").strip()
        lowered = raw.lower()
        item_kind = str(kind or "").strip().lower()

        if not lowered:
            return True

        junk_markers = (
            "project-aware context for nova:",
            "relevant persistent memory:",
            "session attachment memory:",
        )

        if sum(
            lowered.count(marker)
            for marker in junk_markers
        ) >= 2:
            return True

        stale_project_markers = (
            "remote push is still finishing",
            "expanding project-aware memory",
            "project focus recall cleanup committed",
            "backend intelligence context testing",
        )

        if item_kind in {
            "note",
            "user_fact",
            "project_focus",
        }:
            if any(
                marker in lowered
                for marker in stale_project_markers
            ):
                return True

        if lowered.strip() in {
            "say pong only",
            "user preference/correction: say pong only",
        }:
            return True

        if lowered.count("say pong only") >= 2:
            return True

        if lowered.count("what is my current task") >= 2:
            return True

        return False

    def score_penalty(
        self,
        text_value,
        kind="",
    ):
        lowered = str(text_value or "").strip().lower()
        item_kind = str(kind or "").strip().lower()

        penalty = 0

        if item_kind in {
            "project_focus",
            "user_fact",
            "note",
        }:
            if (
                "current task is" in lowered
                or "blocker:" in lowered
            ):
                penalty += 200

        if "project-aware context for nova:" in lowered:
            penalty += 500

        if "say pong only" in lowered:
            penalty += 1000

        return penalty

    def memory_kind(self, item):
        if not isinstance(item, dict):
            return "memory"

        return (
            str(
                item.get("kind")
                or item.get("type")
                or item.get("category")
                or "memory"
            ).strip()
            or "memory"
        )

    def memory_priority(self, item):
        if not isinstance(item, dict):
            return 0

        value = item.get(
            "priority",
            0,
        )

        try:
            return int(value)

        except Exception:
            return 0

    def extract_memory_items(self, payload):
        if isinstance(payload, list):
            return payload

        if not isinstance(payload, dict):
            return []

        for key in (
            "items",
            "memories",
            "memory",
            "records",
            "data",
        ):
            value = payload.get(key)

            if isinstance(value, list):
                return value

        return []



    def message_text(self, message):
        if isinstance(message, str):
            return message.strip()

        if not isinstance(message, dict):
            return ""

        for key in (
            "text",
            "content",
            "message",
            "body",
        ):
            value = message.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def get_memory_context(
        self,
        user_text,
        *,
        limit=12,
        char_limit=3500,
    ):
        payload = self.read_json_file(
            self.data_dir / "nova_memory.json"
        )

        items = self.extract_memory_items(
            payload
        )

        if not items:
            return []

        query_words = {
            word.strip(
                ".,!?;:()[]{}\"'"
            ).lower()
            for word in str(
                user_text or ""
            ).split()
            if len(
                word.strip(
                    ".,!?;:()[]{}\"'"
                )
            ) >= 4
        }

        scored = []

        for item in items:
            text_value = self.memory_text(item)

            if not text_value:
                continue

            kind = self.memory_kind(item)

            if self.is_junk_memory(
                text_value,
                kind,
            ):
                continue

            score = self.score_memory_item(
                item,
                user_text
            )

            score -= self.score_penalty(
                text_value,
                kind,
            )

            scored.append(
                (
                    score,
                    self.memory_priority(item),
                    text_value,
                    kind,
                )
            )

        scored.sort(
            key=lambda row: (
                row[0],
                row[1],
            ),
            reverse=True,
        )

        lines = []
        seen = set()
        used = 0

        for (
            _score,
            _priority,
            text_value,
            kind,
        ) in scored:

            compact = self.compact_text(
                text_value,
                limit=450,
            )

            key = self.normalize_key(
                compact
            )

            if key in seen:
                continue

            seen.add(key)

            line = (
                f"- [{kind}] {compact}"
            )

            if used + len(line) > char_limit:
                break

            lines.append(line)
            used += len(line)

            if len(lines) >= limit:
                break

        return lines

    def get_recent_session_context(
        self,
        session_id,
        *,
        limit=12,
        char_limit=3500,
    ):
        target_session_id = str(
            session_id or ""
        ).strip()

        if not target_session_id:
            return []

        try:
            session = self.session_service.get_session(
                target_session_id
            )

        except Exception:
            session = None

        if not isinstance(session, dict):
            return []

        messages = session.get(
            "messages"
        ) or []

        if not isinstance(messages, list):
            return []

        lines = []
        used = 0

        for message in messages[-limit:]:
            if not isinstance(message, dict):
                continue

            role = str(
                message.get("role")
                or "message"
            ).strip()

            text_value = self.message_text(
                message
            )

            if not text_value:
                continue

            compact = self.compact_text(
                text_value,
                limit=350,
            )

            line = (
                f"- [{role}] {compact}"
            )

            if used + len(line) > char_limit:
                break

            lines.append(line)
            used += len(line)

        return lines

