"""
NOVA MISSION COMPLETION OUTCOME HOOK SMOKE

Verifies:
mission completion
-> outcome recorder
-> improvement history
"""


from nova_backend.services.mission_service import (
    mission_service,
)

from nova_backend.services.nova_improvement_history_service import (
    improvement_history,
)


print(
    "NOVA MISSION COMPLETION OUTCOME HOOK SMOKE"
)

print(
    "========================================="
)


mission = (
    mission_service.create_mission(
        "Improve test completion hook",

        [
            "test"
        ],

        {
            "mission_type":
                "self_improvement",

            "problem":
                "test_completion_hook",
        }
    )
)


mission_id = (
    mission.get(
        "id"
    )
)


result = (
    mission_service.advance_step(
        mission_id,
        {
            "status":
                "passed"
        }
    )
)


print()

print(
    "Mission Result:"
)

print(
    result
)


history = (
    improvement_history.find_previous(
        "test_completion_hook"
    )
)


if history:

    print()

    print(
        "PASS mission completion outcome hook"
    )

else:

    print()

    print(
        "FAIL mission completion outcome hook"
    )

    raise SystemExit(1)