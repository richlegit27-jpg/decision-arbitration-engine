"""
NOVA BEHAVIOR MEMORY STORE

Persistent storage layer for behavior history.

Keeps Nova's behavior improvement signals
between restarts.
"""

import json
from pathlib import Path
from datetime import datetime, timezone


DEFAULT_PATH = Path(
    "data/nova_behavior_memory.json"
)


class NovaBehaviorMemoryStore:


    def __init__(
        self,
        path=None
    ):

        self.path = Path(
            path or DEFAULT_PATH
        )

        self.path.parent.mkdir(
            exist_ok=True
        )


    def load(self):

        if not self.path.exists():

            return {
                "events": []
            }


        try:

            with open(
                self.path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)


            if "events" not in data:

                data["events"] = []


            return data


        except Exception:

            return {
                "events": []
            }



    def save(
        self,
        data
    ):

        with open(
            self.path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )


        return data



    def add_event(
        self,
        behavior_event
    ):

        data = self.load()

        event = dict(
            behavior_event
        )


        event.setdefault(
            "timestamp",
            datetime.now(
                timezone.utc
            ).isoformat()
        )


        data["events"].append(
            event
        )


        self.save(data)

        return event


    def get_events(self):

        return self.load().get(
            "events",
            []
        )


    def get_relevant_patterns(
        self,
        limit=5
    ):
        """
        Return useful behavior patterns.

        High severity events are prioritized.
        """

        events = self.get_events()

        severity_rank = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        ranked = sorted(
            events,
            key=lambda event: severity_rank.get(
                event.get("severity", "low"),
                0,
            ),
            reverse=True,
        )

        return ranked[:limit]


    def count_problem(
        self,
        problem
    ):

        events = self.get_events()

        return sum(
            1
            for event in events
            if event.get(
                "behavior_problem"
            ) == problem
        )



behavior_memory_store = (
    NovaBehaviorMemoryStore()
)