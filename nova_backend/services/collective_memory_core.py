from datetime import datetime


class CollectiveMemoryCore:

    def __init__(self):

        self.memory = {
            "missions": [],
            "reflections": [],
            "repairs": [],
            "emergent_patterns": [],
            "strategy_mutations": [],
            "architectural_events": [],
            "identity_events": [],
            "environment_snapshots": [],
            "knowledge_events": [],
        }

    def remember(
        self,
        category="",
        event=None,
    ):

        if (
            category
            not in self.memory
        ):

            self.memory[
                category
            ] = []

        payload = {
            "timestamp": (
                datetime.utcnow()
                .isoformat()
            ),
            "event": event,
        }

        self.memory[
            category
        ].append(payload)

    def recall(
        self,
        category="",
    ):

        return (
            self.memory.get(
                category,
                [],
            )
        )

    def summarize(self):

        return {
            key: len(value)
            for key, value
            in self.memory.items()
        }

    def recent(
        self,
        category="",
        limit=5,
    ):

        items = (
            self.memory.get(
                category,
                [],
            )
        )

        return items[-limit:]