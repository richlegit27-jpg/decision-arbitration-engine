"""
NOVA PLANNER INTEGRATION V1

Converts self-improvement mission proposals
into planner-compatible mission requests.

Adapter only.
Planner remains source of execution truth.
"""


from datetime import datetime, timezone


class NovaPlannerIntegration:


    def __init__(self):

        self.version = (
            "NOVA_PLANNER_INTEGRATION_V1_20260710"
        )


    def build_planner_request(
        self,
        mission_proposal
    ):

        if not mission_proposal:

            return self._empty()


        if mission_proposal.get(
            "mission_type"
        ) != "self_improvement":

            return self._empty()


        return {

            "source":
                "nova_self_improvement",

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "goal":
                mission_proposal.get(
                    "goal",
                    ""
                ),

            "target_system":
                mission_proposal.get(
                    "target_system",
                    ""
                ),

            "priority":
                mission_proposal.get(
                    "priority",
                    "low"
                ),

            "requires_approval":
                True,

            "planner_action":
                "create_mission",
        }



    def _empty(self):

        return {

            "planner_action":
                "none",

            "requires_approval":
                True,
        }



nova_planner_integration = (
    NovaPlannerIntegration()
)


def build_planner_request(
    mission_proposal
):

    return (
        nova_planner_integration
        .build_planner_request(
            mission_proposal
        )
    )