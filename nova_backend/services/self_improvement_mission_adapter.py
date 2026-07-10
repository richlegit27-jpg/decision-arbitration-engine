"""
NOVA SELF IMPROVEMENT MISSION ADAPTER V1

Converts approved improvement proposals
into planner missions.

Does not execute missions.
"""

from datetime import datetime, timezone


class SelfImprovementMissionAdapter:

    def __init__(self):

        self.version = (
            "NOVA_SELF_IMPROVEMENT_MISSION_ADAPTER_V1_20260710"
        )


    def build_mission_request(
        self,
        mission_proposal,
    ):

        if not mission_proposal:

            return self._empty()


        return {

            "goal":
                mission_proposal.get(
                    "goal",
                    "",
                ),

            "metadata":
                {
                    "source":
                        "self_improvement_pipeline",

                    "proposal_type":
                        mission_proposal.get(
                            "type",
                            "",
                        ),

                    "approval_required":
                        mission_proposal.get(
                            "approval_required",
                            True,
                        ),

                    "risk":
                        mission_proposal.get(
                            "risk",
                            "unknown",
                        ),

                    "created_by":
                        self.version,

                    "created_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                },

        }


    def _empty(self):

        return {

            "goal":
                "",

            "metadata":
                {
                    "source":
                        "self_improvement_pipeline",
                },

        }


adapter = SelfImprovementMissionAdapter()


def build_self_improvement_mission_request(
    mission_proposal,
):

    return adapter.build_mission_request(
        mission_proposal
    )