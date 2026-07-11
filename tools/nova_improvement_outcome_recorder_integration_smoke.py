"""
NOVA IMPROVEMENT OUTCOME RECORDER INTEGRATION SMOKE

Verifies:
mission -> outcome recorder -> judge -> history
"""


from nova_backend.services.nova_improvement_outcome_recorder import (
    improvement_outcome_recorder,
)

from nova_backend.services.nova_improvement_history_service import (
    improvement_history,
)


print(
    "NOVA IMPROVEMENT OUTCOME RECORDER INTEGRATION SMOKE"
)

print(
    "==============================================="
)


mission = {

    "id":
        "mission_outcome_test_001",

    "goal":
        "Improve weak_memory_recall",

    "metadata":
        {

            "problem":
                "weak_memory_recall",

        },

    "results":
        [

            {
                "step":
                    "test",

                "status":
                    "passed",

            }

        ]

}


result = (
    improvement_outcome_recorder.record_outcome(
        mission,
        "completed",
    )
)


print()

print(
    "Result:"
)

print(
    result
)


history = (
    improvement_history.find_previous(
        "weak_memory_recall"
    )
)


if (
    result.get(
        "recorded"
    )
    and history
):

    print()

    print(
        "PASS outcome recorder integration"
    )

else:

    print()

    print(
        "FAIL outcome recorder integration"
    )

    raise SystemExit(1)