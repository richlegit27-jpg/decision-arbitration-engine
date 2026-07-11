"""
NOVA IMPROVEMENT FAILURE RETRY SMOKE

Verifies that failed previous improvements
are allowed to retry.
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
        "NOVA IMPROVEMENT FAILURE RETRY SMOKE"
    )

    print(
        "==================================="
    )


    problem = "test_failure_retry_behavior"


    # Seed failed previous improvement
    improvement_history.record(
        {

            "problem":
                problem,

            "upgrade":
                "Improve memory recall",

            "priority":
                "critical",

            "mission_id":
                "mission_failed_001",

            "outcome":
                "failed",

            "status":
                "failed",

            "judgment":
                "unsuccessful",

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
                        "test failed retry path",

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
            "improved"
        )
        is True

        and

        result.get(
            "recommendation",
            {}
        ).get(
            "retry_required"
        )
        is True
    ):

        print()

        print(
            "PASS failed improvement retry allowed"
        )

    else:

        print()

        print(
            "FAIL failed improvement retry path"
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