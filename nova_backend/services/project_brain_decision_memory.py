"""
NOVA PROJECT BRAIN DECISION MEMORY

Stores outcomes from Project Brain decisions.

Separate from conversation behavior memory:
- behavior memory = answer quality
- decision memory = judgment quality
"""

import json
from pathlib import Path
from datetime import datetime, timezone


DEFAULT_PATH = Path(
    "data/nova_project_brain_decision_memory.json"
)


class ProjectBrainDecisionMemory:

    def __init__(self, path=None):
        self.path = Path(path or DEFAULT_PATH)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def load(self):
        if not self.path.exists():
            return {"events": []}

        try:
            with open(
                self.path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if "events" not in data:
                data["events"] = []

            return data

        except Exception:
            return {"events": []}

    def save(self, data):
        with open(
            self.path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

        return data

    def add_outcome(self, outcome):
        data = self.load()

        event = dict(outcome)

        event.setdefault(
            "timestamp",
            datetime.now(timezone.utc).isoformat(),
        )

        event.setdefault(
            "event_type",
            "decision_outcome",
        )

        data["events"].append(event)

        self.save(data)

        return event

    def get_events(self):
        return self.load().get(
            "events",
            [],
        )


project_brain_decision_memory = ProjectBrainDecisionMemory()