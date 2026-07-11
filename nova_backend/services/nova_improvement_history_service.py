"""
NOVA IMPROVEMENT HISTORY SERVICE V1

Tracks self improvement attempts.

Persistent storage backed.

Advisory only.
Does not execute upgrades.
"""


from datetime import datetime, timezone


from nova_backend.services.nova_improvement_history_store import (
    NovaImprovementHistoryStore,
)



class NovaImprovementHistoryService:


    def __init__(self):

        self.store = (
            NovaImprovementHistoryStore()
        )

    def record(
        self,
        improvement
    ):

        entry = {

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "problem":
                improvement.get(
                    "problem",
                    ""
                ),

            "upgrade":
                improvement.get(
                    "recommended_upgrade",
                    improvement.get(
                        "upgrade",
                        ""
                    )
                ),

            "priority":
                improvement.get(
                    "priority",
                    "low"
                ),

        }

        optional_fields = [

            "mission_id",

            "outcome",

            "status",

            "engine",

            "recorded_at",

            "judgment",

            "confidence",

        ]


        for field in optional_fields:

            if field in improvement:

                entry[field] = (
                    improvement.get(
                        field
                    )
                )


        self.store.add(
            entry
        )


        return entry

    def find_previous(
        self,
        problem
    ):

        matches = []


        for item in self.store.get_all():

            if item.get(
                "problem"
            ) == problem:

                matches.append(
                    item
                )


        return matches


improvement_history = (
    NovaImprovementHistoryService()
)