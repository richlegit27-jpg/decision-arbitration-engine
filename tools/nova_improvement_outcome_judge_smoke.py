"""
NOVA IMPROVEMENT OUTCOME JUDGE SMOKE

Verifies mission outcome evaluation.
"""


from nova_backend.services.nova_improvement_outcome_judge import (
    improvement_outcome_judge,
)


print(
    "NOVA IMPROVEMENT OUTCOME JUDGE SMOKE"
)

print(
    "===================================="
)


completed_result = (
    improvement_outcome_judge.evaluate(
        {
            "status":
                "completed",

            "results":
                [
                    "test passed",
                    "behavior improved",
                ],
        }
    )
)


print()

print(
    "COMPLETED RESULT:"
)

print(
    completed_result
)


if (
    completed_result.get(
        "judgment"
    )
    !=
    "successful"
):

    print(
        "FAIL completed mission judgment"
    )

    raise SystemExit(1)


failed_result = (
    improvement_outcome_judge.evaluate(
        {
            "status":
                "failed",

            "results":
                [
                    "regression detected",
                ],
        }
    )
)


print()

print(
    "FAILED RESULT:"
)

print(
    failed_result
)


if (
    failed_result.get(
        "judgment"
    )
    !=
    "unsuccessful"
):

    print(
        "FAIL failed mission judgment"
    )

    raise SystemExit(1)


unknown_result = (
    improvement_outcome_judge.evaluate(
        {}
    )
)


print()

print(
    "UNKNOWN RESULT:"
)

print(
    unknown_result
)


if (
    unknown_result.get(
        "judgment"
    )
    !=
    "uncertain"
):

    print(
        "FAIL unknown mission judgment"
    )

    raise SystemExit(1)


print()

print(
    "PASS improvement outcome judge"
)