"""
NOVA UPGRADE MISSION BRIDGE V1

Converts approved upgrade decisions into
planner-compatible mission proposals.

Does not execute missions.
"""


from datetime import datetime, timezone


class NovaUpgradeMissionBridge:


    def __init__(self):

        self.version = (
            "NOVA_UPGRADE_MISSION_BRIDGE_V1_20260710"
        )


    def create_mission_proposal(
        self,
        decision
    ):

        if not decision:

            return self._empty()


        if decision.get(
            "decision"
        ) != "consider_upgrade":

            return self._empty()


        return {

            "engine":
                self.version,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "mission_type":
                "self_improvement",

            "goal":
                (
                    "Improve "
                    +
                    decision.get(
                        "recommended_upgrade",
                        "system quality"
                    )
                ),

            "target_system":
                decision.get(
                    "target_system",
                    "unknown"
                ),

            "priority":
                decision.get(
                    "priority",
                    "low"
                ),

            "requires_approval":
                True,

            "source":
                "nova_self_improvement_loop",
        }



    def _empty(self):

        return {

            "mission_type":
                "none",

            "requires_approval":
                True,
        }



upgrade_mission_bridge = (
    NovaUpgradeMissionBridge()
)


def create_upgrade_mission_proposal(
    decision
):

    return (
        upgrade_mission_bridge
        .create_mission_proposal(
            decision
        )
    )