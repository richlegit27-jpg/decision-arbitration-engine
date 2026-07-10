"""
NOVA BEHAVIOR MEMORY

Stores repeated conversation behavior signals
and converts them into improvement priorities.
"""

from collections import defaultdict
from datetime import datetime, timezone


class NovaBehaviorMemory:

    def __init__(self):
        self.events = []


    def record_behavior(self, behavior_upgrade):
        """
        Store a behavior upgrade event.

        Accepts:
        - dict
        - object with as_dict()
        """

        if hasattr(behavior_upgrade, "as_dict"):
            data = behavior_upgrade.as_dict()
        else:
            data = dict(behavior_upgrade or {})


        event = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "behavior_problem": data.get(
                "behavior_problem",
                "unknown"
            ),

            "severity": data.get(
                "severity",
                "unknown"
            ),

            "upgrade": data.get(
                "upgrade",
                ""
            ),

            "action": data.get(
                "action",
                ""
            ),

            "reason": data.get(
                "reason",
                ""
            ),
        }


        self.events.append(event)

        return event



    def get_behavior_counts(self):

        counts = defaultdict(int)

        for event in self.events:
            counts[
                event["behavior_problem"]
            ] += 1

        return dict(counts)



    def rank_behavior_problems(self):

        counts = self.get_behavior_counts()

        ranked = sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True
        )


        results = []

        for problem, count in ranked:

            if count >= 5:
                priority = "critical"

            elif count >= 3:
                priority = "high"

            elif count >= 2:
                priority = "medium"

            else:
                priority = "low"


            results.append(
                {
                    "problem": problem,
                    "occurrences": count,
                    "priority": priority,
                }
            )


        return results



    def create_improvement_priority(self):

        ranked = self.rank_behavior_problems()


        if not ranked:
            return {
                "focus": "collect_behavior_data",
                "priority": "low",
                "reason": "No behavior history exists yet."
            }


        top = ranked[0]


        return {
            "focus": top["problem"],
            "priority": top["priority"],
            "reason": (
                f"{top['problem']} detected "
                f"{top['occurrences']} times."
            ),
        }



    def export_report(self):

        return {
            "total_events": len(self.events),
            "behavior_counts": self.get_behavior_counts(),
            "ranked_problems": self.rank_behavior_problems(),
            "recommended_focus": (
                self.create_improvement_priority()
            ),
        }



behavior_memory = NovaBehaviorMemory()