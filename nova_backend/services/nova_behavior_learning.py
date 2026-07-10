"""
Nova Behavior Learning Engine v1

Purpose:
Analyze stored behavior observations and produce
ranked improvement opportunities.

This layer is intentionally advisory.
It does not modify runtime behavior automatically.
Project Brain decides what actions happen next.
"""

from collections import defaultdict
from datetime import datetime, timezone


class NovaBehaviorLearning:

    def __init__(self):
        self.version = "NOVA_BEHAVIOR_LEARNING_V1_20260710"

    def analyze_behavior_history(self, observations):
        """
        Analyze behavior observation history.

        Expected observation shape:

        {
            "signals": {
                "quality": "weak",
                "category": "continuity"
            },
            "timestamp": ...
        }
        """

        if not observations:
            return self._empty_report()

        categories = defaultdict(
            lambda: {
                "count": 0,
                "issues": []
            }
        )

        for observation in observations:

            signals = observation.get("signals", {})

            category = (
                signals.get("category")
                or "general_response_quality"
            )

            categories[category]["count"] += 1

            issue = (
                signals.get("issue")
                or signals.get("quality")
                or "observed behavior"
            )

            categories[category]["issues"].append(issue)

        ranked = []

        for category, data in categories.items():

            ranked.append(
                {
                    "category": category,
                    "frequency": data["count"],
                    "priority": self._priority(
                        data["count"]
                    ),
                    "evidence": data["issues"][:5],
                }
            )

        ranked.sort(
            key=lambda x: x["frequency"],
            reverse=True
        )

        return {
            "engine": self.version,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "observations_analyzed": len(
                observations
            ),

            "improvement_opportunities": ranked
        }


    def _priority(self, frequency):

        if frequency >= 10:
            return "high"

        if frequency >= 5:
            return "medium"

        return "low"


    def _empty_report(self):

        return {
            "engine": self.version,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "observations_analyzed": 0,
            "improvement_opportunities": []
        }


behavior_learning = NovaBehaviorLearning()


def analyze_behavior_history(observations):
    return behavior_learning.analyze_behavior_history(
        observations
    )