"""
NOVA SELF IMPROVEMENT CRITICAL RUNTIME SMOKE

Validates that a critical behavior signal
creates an improvement mission.

Advisory only.
"""

from nova_backend.services.nova_self_improvement_coordinator import (
    process_behavior_observation,
)


print(
    "NOVA SELF IMPROVEMENT CRITICAL RUNTIME SMOKE"
)

print(
    "============================================"
)


behavior_report = {

    "recommended_focus": {

"focus":
    "weak_memory_recall",

        "priority":
            "critical",

        "reason":
            "Critical runtime test signal.",

    }

}


result = (
    process_behavior_observation(
        behavior_report
    )
)


print()

print(
    "Result:"
)

print(
    result
)

if result.get(
    "improved"
):

    print()

    print(
        "PASS critical signal created improvement mission"
    )

elif result.get(
    "reason"
) == "improvement_already_attempted":

    print()

    print(
        "PASS duplicate improvement correctly blocked"
    )

else:

    print()

    print(
        "FAIL unexpected improvement result:",
        result
    )