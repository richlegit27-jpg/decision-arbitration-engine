"""
NOVA MISSION PROPOSAL SERVICE V1

Converts improvement proposals into
mission proposals.

Advisory only.
Requires approval before execution.
"""


from datetime import datetime, timezone


class NovaMissionProposalService:

    def __init__(self):

        self.version = (
            "NOVA_MISSION_PROPOSAL_SERVICE_V1_20260710"
        )


    def create_proposal(
        self,
        improvement_proposal,
    ):

        if not improvement_proposal:

            return self._empty()


        return {

            "type":
                "mission_proposal",

            "engine":
                self.version,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "mission_type":
                "improvement",

            "goal":
                improvement_proposal.get(
                    "recommended_upgrade",
                    "",
                ),

            "target":
                improvement_proposal.get(
                    "target_system",
                    "",
                ),

            "source_problem":
                improvement_proposal.get(
                    "problem",
                    "",
                ),

            "confidence":
                improvement_proposal.get(
                    "confidence",
                    0.0,
                ),

            "risk":
                improvement_proposal.get(
                    "risk",
                    "unknown",
                ),

            "status":
                "proposal",

            "approval_required":
                True,

        }


    def _empty(self):

        return {

            "type":
                "mission_proposal",

            "engine":
                self.version,

            "mission_type":
                "improvement",

            "goal":
                "",

            "target":
                "",

            "status":
                "proposal",

            "approval_required":
                True,

        }


mission_proposal_service = (
    NovaMissionProposalService()
)


def create_mission_proposal(
    improvement_proposal,
):

    return (
        mission_proposal_service
        .create_proposal(
            improvement_proposal
        )
    )