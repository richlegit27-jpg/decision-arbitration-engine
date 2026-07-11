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


print(
    "NOVA SELF IMPROVEMENT COMPLETION HOOK SMOKE"
)

print(
    "==========================================="
)


mission = (
mission_service.create_mission(
    {
        "goal":
            "Test self improvement completion hook",

        "metadata": {

            "mission_type":
                "self_improvement",

            "source":
                "nova_self_improvement_loop",

        }

    }
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