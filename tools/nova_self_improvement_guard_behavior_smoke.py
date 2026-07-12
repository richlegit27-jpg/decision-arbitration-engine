"""
NOVA SELF IMPROVEMENT GUARD BEHAVIOR SMOKE

Verifies:

new problem
-> improvement mission created

completed problem
-> duplicate improvement blocked
"""


from nova_backend.services.nova_self_improvement_coordinator import (
    process_behavior_observation,
)


print(
    "NOVA SELF IMPROVEMENT GUARD BEHAVIOR SMOKE"
)

print(
    "=========================================="
)


new_observation = {

    "recommended_focus":
        {

            "focus":
                "weak_tool_selection_confidence",

            "priority":
                "critical",

            "reason":
                    "tool selection confidence needs improvement",

        }

}


print()

print(
    "NEW OBSERVATION:"
)

print(
    new_observation
)


new_result = (
    process_behavior_observation(
        new_observation
    )
)


print()

print(
    "NEW RESULT:"
)

print(
    new_result
)


if new_result.get(
    "reason"
) == "improvement_already_completed":

    print()

    print(
        "FAIL new problem was blocked"
    )

    raise SystemExit(1)


print()

print(
    "PASS new improvement accepted"
)


existing_observation = {

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
    "EXISTING OBSERVATION:"
)

print(
    existing_observation
)


existing_result = (
    process_behavior_observation(
        existing_observation
    )
)


print()

print(
    "EXISTING RESULT:"
)

print(
    existing_result
)


if existing_result.get(
    "reason"
) != "improvement_already_completed":

    print()

    print(
        "FAIL duplicate guard failed"
    )

    raise SystemExit(1)


print()

print(
    "PASS duplicate improvement guard"
)