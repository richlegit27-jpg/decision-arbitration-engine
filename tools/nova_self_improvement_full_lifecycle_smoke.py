"""
NOVA SELF IMPROVEMENT FULL LIFECYCLE SMOKE

Tests:

1. New improvement accepted
2. Outcome recorded
3. Same improvement blocked afterwards
"""


from nova_backend.services.nova_self_improvement_coordinator import (
    evaluate_self_improvement,
)

from nova_backend.services.nova_improvement_outcome_recorder import (
    improvement_outcome_recorder,
)


print(
    "NOVA SELF IMPROVEMENT FULL LIFECYCLE SMOKE"
)

print(
    "========================================="
)


problem = (
    "weak_reasoning_alignment_lifecycle_smoke"
)


signal = {

    "recommended_focus": {

        "focus":
            problem,

        "priority":
            "critical",

        "reason":
            "reasoning alignment needs improvement"

    }

}


print("\nSTEP 1: NEW IMPROVEMENT")

first = evaluate_self_improvement(
    signal
)

print(first)


if not first.get(
    "improved"
):

    raise Exception(
        "FAIL initial improvement rejected"
    )


print(
    "PASS initial improvement accepted"
)


mission_id = (
    first
    .get("mission", {})
    .get("mission", {})
    .get("id")
)


print(
    "\nSTEP 2: RECORD COMPLETION"
)


improvement_outcome_recorder.record_outcome(

    mission=(
        first
        .get("mission", {})
        .get("mission")
    ),

    outcome="completed"

)


print(
    "PASS outcome recorded"
)


print(
    "\nSTEP 3: RETRY SAME IMPROVEMENT"
)


second = evaluate_self_improvement(
    signal
)


print(second)


if second.get(
    "reason"
) not in (
    "improvement_already_completed",
    "similar_mission_already_exists",
):

    raise Exception(
        "FAIL wrong guard reason"
    )


if second.get(
    "reason"
) not in (
    "improvement_already_completed",
    "similar_mission_already_exists",
):

    raise Exception(
        "FAIL wrong guard reason"
    )

    raise Exception(
        "FAIL wrong guard reason"
    )


print(
    "PASS lifecycle guard works"
)

print(
    "PASS NOVA self improvement lifecycle complete"
)