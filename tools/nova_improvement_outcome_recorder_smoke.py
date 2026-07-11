"""
NOVA IMPROVEMENT OUTCOME RECORDER SMOKE

Validates mission outcome recording.
"""


from nova_backend.services.nova_improvement_outcome_recorder import (
    improvement_outcome_recorder,
)


print(
    "NOVA IMPROVEMENT OUTCOME RECORDER SMOKE"
)

print(
    "======================================="
)


mission = {

    "id":
        "mission_test_001",

    "goal":
        "Improve weak_memory_recall behavior",

    "metadata": {

        "problem":
            "weak_memory_recall",

    },

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


if result.get(
    "recorded"
):

    print()

    print(
        "PASS improvement outcome recorded"
    )

else:

    print()

    print(
        "FAIL improvement outcome not recorded"
    )