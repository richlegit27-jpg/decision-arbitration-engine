from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation
)


print(
    "NOVA SELF IMPROVEMENT RECOMMENDER SMOKE"
)

print(
    "======================================="
)


priority = {

    "focus":
        "continuity",

    "priority":
        "medium",

    "reason":
        "continuity detected 1 times."
}


result = create_self_improvement_recommendation(
    priority
)


assert result["problem"] == "continuity"

print(
    "PASS converts behavior problem"
)


assert (
    result["target_system"]
    ==
    "conversation memory system"
)

print(
    "PASS selects target system"
)


assert (
    result["confidence"]
    ==
    "medium"
)

print(
    "PASS calculates confidence"
)


print(
    "PASS creates improvement recommendation"
)


print(
    "NOVA SELF IMPROVEMENT RECOMMENDER SMOKE PASSED"
)