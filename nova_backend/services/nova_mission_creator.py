"""
NOVA MISSION CREATOR V1

Safe bridge between Nova self-improvement
recommendations and the existing planner.

No execution.
No autonomous changes.
Creates missions only.
"""


from datetime import datetime, timezone


class NovaMissionCreator:


    def __init__(self):

        self.version = (
            "NOVA_MISSION_CREATOR_V1_20260710"
        )


    def create_mission_payload(
        self,
        planner_request
    ):

        if not planner_request:

            return self._empty()


        if planner_request.get(
            "planner_action"
        ) != "create_mission":

            return self._empty()


        return {

            "created_by":
                "nova_self_improvement",

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "goal":
                planner_request.get(
                    "goal",
                    ""
                ),

            "priority":
                planner_request.get(
                    "priority",
                    "low"
                ),

            "target_system":
                planner_request.get(
                    "target_system",
                    ""
                ),

            "requires_approval":
                True,
        }



    def _empty(self):

        return {

            "created_by":
                "none",

            "requires_approval":
                True,
        }



nova_mission_creator = NovaMissionCreator()


def create_mission_payload(
    planner_request
):

    return (
        nova_mission_creator
        .create_mission_payload(
            planner_request
        )
    )