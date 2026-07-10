"""
NOVA IMPROVEMENT PROPOSAL CONTRACT V1

Converts intelligence recommendations into
standardized improvement proposals.

Advisory only.
Does not execute changes.
"""


from datetime import datetime, timezone


class NovaImprovementProposal:

    def __init__(self):

        self.version = (
            "NOVA_IMPROVEMENT_PROPOSAL_V1_20260710"
        )


    def create(self, recommendation):

        if not recommendation:

            return self._empty()


        return {

            "type":
                "improvement_proposal",

            "engine":
                self.version,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "problem":
                recommendation.get(
                    "problem",
                    "unknown",
                ),

            "evidence":
                recommendation.get(
                    "reason",
                    "",
                ),

            "recommended_upgrade":
                recommendation.get(
                    "recommended_upgrade",
                    "",
                ),

            "target_system":
                recommendation.get(
                    "target_system",
                    "",
                ),

            "confidence":
                recommendation.get(
                    "confidence",
                    0.0,
                ),

            "risk":
                "low",

        }


    def _empty(self):

        return {

            "type":
                "improvement_proposal",

            "engine":
                self.version,

            "problem":
                None,

            "evidence":
                "",

            "recommended_upgrade":
                "",

            "target_system":
                "",

            "confidence":
                0.0,

            "risk":
                "unknown",

        }


proposal_builder = NovaImprovementProposal()


def create_improvement_proposal(
    recommendation,
):

    return proposal_builder.create(
        recommendation
    )