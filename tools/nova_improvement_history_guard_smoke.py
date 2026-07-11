"""
NOVA IMPROVEMENT HISTORY GUARD SMOKE

Verifies that successful previous improvements
prevent duplicate improvement missions.
"""


import json


HISTORY_FILE = (
    r"C:\Users\Owner\nova\data\nova_improvement_history.json"
)


with open(
    HISTORY_FILE,
    "r",
    encoding="utf-8"
) as f:

    history_backup = json.load(
        f
    )


try:

    from nova_backend.services.nova_improvement_history_service import (
        improvement_history,
    )

    from nova_backend.services.nova_self_improvement_coordinator import (
        process_behavior_observation,
    )


    print(
        "NOVA IMPROVEMENT HISTORY GUARD SMOKE"
    )

    print(
        "===================================="
    )


    problem = "weak_memory_recall"


    improvement_history.record(
        {

            "problem":
                problem,

            "upgrade":
                "Improve memory recall",

            "priority":
                "critical",

            "mission_id":
                "mission_test_001",

            "outcome":
                "completed",

            "status":
                "completed",

            "judgment":
                "successful",

            "confidence":
                "high",

        }
    )


    result = (
        process_behavior_observation(
            {
                "recommended_focus": {

                    "focus":
                        problem,

                    "priority":
                        "critical",

                    "reason":
                        "test history guard",

                }
            }
        )
    )


    print()

    print(
        "Result:"
    )

    print(
        result
    )


    if (
        result.get(
            "reason"
        )
        ==
        "improvement_already_completed"
    ):

        print()

        print(
            "PASS duplicate improvement blocked"
        )

    else:

        print()

        print(
            "FAIL history guard did not trigger"
        )

        raise SystemExit(1)


finally:

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history_backup,
            f,
            indent=2
        )