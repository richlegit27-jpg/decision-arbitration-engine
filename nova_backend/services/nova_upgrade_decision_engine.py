"""
NOVA UPGRADE DECISION ENGINE V1

Turns self-improvement recommendations
into Project Brain upgrade decisions.

Advisory layer only.
Execution remains controlled by planner.
"""


from datetime import datetime, timezone


class NovaUpgradeDecisionEngine:


    def __init__(self):

        self.version = (
            "NOVA_UPGRADE_DECISION_ENGINE_V1_20260710"
        )


    def create_decision(
        self,
        recommendation
    ):

        if not recommendation:

            return self._empty()


        priority = recommendation.get(
            "priority",
            "low"
        )


        confidence = recommendation.get(
            "confidence",
            "low"
        )


        return {

            "engine":
                self.version,

            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "decision":
                "consider_upgrade",

            "problem":
                recommendation.get(
                    "problem",
                    "unknown"
                ),

            "target_system":
                recommendation.get(
                    "target_system",
                    "unknown"
                ),

            "recommended_upgrade":
                recommendation.get(
                    "recommended_upgrade",
                    ""
                ),

            "priority":
                priority,

            "confidence":
                confidence,

            "risk":
                self._calculate_risk(
                    priority,
                    confidence
                ),

            "requires_review":
                True,
        }



    def _calculate_risk(
        self,
        priority,
        confidence
    ):

        if (
            priority == "critical"
            and confidence == "high"
        ):
            return "medium"


        if priority in (
            "high",
            "critical"
        ):
            return "medium-high"


        return "low"



    def _empty(self):

        return {

            "decision":
                "collect_more_data",

            "requires_review":
                True,

            "risk":
                "low",
        }



upgrade_decision_engine = (
    NovaUpgradeDecisionEngine()
)


def create_upgrade_decision(
    recommendation
):

    return (
        upgrade_decision_engine.create_decision(
            recommendation
        )
    )