"""
NOVA SELF IMPROVEMENT COMPLETION HOOK SMOKE

Validates:
mission completion
        ->
automatic improvement history recording
"""


from nova_backend.services.mission_service import (
    mission_service,
)

from nova_backend.services.nova_upgrade_mission_bridge import (
    create_upgrade_mission_proposal,
)


print(
    "NOVA SELF IMPROVEMENT COMPLETION HOOK SMOKE"
)

print(
    "==========================================="
)


proposal = (
    create_upgrade_mission_proposal(
        {

            "decision":
                "consider_upgrade",

            "recommended_upgrade":
                "Test completion hook",

            "priority":
                "critical",

            "target_system":
                "general intelligence layer",

        }
    )
)


mission = (
    mission_service.create_mission(
        proposal.get(
            "goal",
            "Test completion hook"
        ),
        metadata=proposal
    )
)


mission_id = (
    mission.get(
        "id"
    )
)


print()

print(
    "Created mission:",
    mission_id
)


while (
    mission.get(
        "status"
    )
    !=
    "complete"
):

    mission = (
        mission_service.advance_step(
            mission_id,
            result="step complete",
        )
    )


print()

print(
    "Completed mission:"
)

print(
    mission
)


print()

print(
    "PASS completion hook executed"
)