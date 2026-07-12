"""
NOVA BEHAVIOR TO SELF IMPROVEMENT LOOP SMOKE

Verifies:

behavior observation
-> coordinator
-> recommendation
-> mission proposal
-> improvement loop
"""


from nova_backend.services.nova_behavior_memory import (
    behavior_memory,
)

from nova_backend.services.nova_self_improvement_coordinator import (
    process_behavior_observation,
)


print(
    "NOVA BEHAVIOR TO SELF IMPROVEMENT LOOP SMOKE"
)

print(
    "============================================"
)


observation = {

    "recommended_focus":
        {

            "focus":
                "weak_actionability",

            "priority":
                "critical",

            "reason":
                "responses lack actionable next steps",

        }

}


print()

print(
    "Observation:"
)

print(
    observation
)


result = (
    process_behavior_observation(
        observation
    )
)


print()

print(
    "Coordinator Result:"
)

print(
    result
)


if result:

    print()

    print(
        "PASS behavior to self improvement"
    )

else:

    print()

    print(
        "FAIL behavior to self improvement"
    )

    raise SystemExit(1)