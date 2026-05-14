class RuntimeCognitiveFirewall:
    """
    Filters memory before it enters operational/runtime cognition.

    Goal:
        Keep identity, mission, execution, and working-state memory.
        Suppress jokes, casual noise, contamination, and low-signal memory.
    """

    def __init__(self):
        self.identity_keywords = {
            "name",
            "identity",
            "profile",
            "user",
            "preference",
            "prefers",
            "likes",
        }

        self.mission_keywords = {
            "mission",
            "goal",
            "task",
            "project",
            "nova",
            "runtime",
            "execution",
            "working",
            "checkpoint",
            "next move",
            "bug",
            "file",
        }

        self.noise_keywords = {
            "big butts",
            "cannot lie",
            "joke",
            "funny",
            "meme",
            "lol",
            "lmao",
            "haha",
        }

    def _safe_str(self, value):
        if value is None:
            return ""

        try:
            return str(value).strip()
        except Exception:
            return ""

    def _memory_text(self, memory):
        if isinstance(memory, str):
            return memory

        if not isinstance(memory, dict):
            return ""

        parts = []

        for key in (
            "text",
            "content",
            "summary",
            "value",
            "memory",
            "category",
            "kind",
        ):
            value = memory.get(key)
            if value:
                parts.append(self._safe_str(value))

        return " ".join(parts).strip()

    def classify_memory(self, memory):
        text = self._memory_text(memory).lower()

        if not text:
            return "LOW_SIGNAL"

        if any(keyword in text for keyword in self.noise_keywords):
            return "NOISE"

        if any(keyword in text for keyword in self.mission_keywords):
            return "MISSION"

        if any(keyword in text for keyword in self.identity_keywords):
            return "IDENTITY"

        return "CASUAL"

    def score_memory(self, memory):
        category = self.classify_memory(memory)

        score = {
            "IDENTITY": 80,
            "MISSION": 100,
            "CASUAL": 20,
            "NOISE": -100,
            "LOW_SIGNAL": -50,
        }.get(category, 0)

        return {
            "category": category,
            "runtime_relevance": score,
            "contamination_score": 100 if category == "NOISE" else 0,
            "allow_runtime_injection": score > 0,
        }

    def filter_for_runtime(self, memories, user_text=""):
        if not isinstance(memories, list):
            return []

        user_text_lower = self._safe_str(user_text).lower()
        filtered = []

        explicit_noise_request = any(
            keyword in user_text_lower
            for keyword in self.noise_keywords
        )

        for memory in memories:
            score = self.score_memory(memory)
            category = score.get("category")

            if category == "NOISE" and not explicit_noise_request:
                continue

            if not score.get("allow_runtime_injection"):
                continue

            if isinstance(memory, dict):
                clean_memory = dict(memory)
                clean_memory["firewall"] = score
                filtered.append(clean_memory)
            else:
                filtered.append(
                    {
                        "text": self._safe_str(memory),
                        "firewall": score,
                    }
                )

        return filtered