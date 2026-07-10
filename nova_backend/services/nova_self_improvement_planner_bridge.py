"""
NOVA SELF IMPROVEMENT PLANNER BRIDGE V1

Connects Nova generated improvement missions
to the existing PlannerService.

No execution.
No bypassing planner guards.
"""


from datetime import datetime, timezone

from nova_backend.services.planner_service import (
    planner_service
)


class NovaSelfImprovementPlannerBridge:


    def __init__(self):

        self.version = (
            "NOVA_SELF_IMPROVEMENT_PLANNER_BRIDGE_V1_20260710"
        )


    def submit_improvement_mission(
        self,
        mission_payload
    ):

        if not mission_payload:

            return {
                "status": "empty"
            }


        if not mission_payload.get(
            "requires_approval"
        ):

            return {
                "status": "blocked",
                "reason": "approval required"
            }


        goal = mission_payload.get(
            "goal",
            ""
        )


        if not goal:

            return {
                "status": "blocked",
                "reason": "missing goal"
            }


        mission = (
            planner_service.create_mission(
                goal
            )
        )


        return {

            "bridge":
                self.version,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "status":
                "created",

            "mission":
                mission,
        }



self_improvement_planner_bridge = (
    NovaSelfImprovementPlannerBridge()
)


def submit_improvement_mission(
    mission_payload
):

    return (
        self_improvement_planner_bridge
        .submit_improvement_mission(
            mission_payload
        )
    )