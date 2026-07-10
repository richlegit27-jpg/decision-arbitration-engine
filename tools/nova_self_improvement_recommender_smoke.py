from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)


print(
    "NOVA SELF IMPROVEMENT RECOMMENDER SMOKE"
)

print(
    "======================================="
)


result = create_self_improvement_recommendation(
    {
        "focus": "continuity",
        "priority": "medium",
        "reason": "continuity detected repeatedly",
    }
)


assert result["problem"] == "continuity"

print(
    "PASS preserves behavior problem"
)


assert (
    result["recommended_upgrade"]
    ==
    "Improve conversation recall and session continuity"
)

print(
    "PASS maps continuity upgrade"
)


assert (
    result["target_system"]
    ==
    "conversation memory system"
)

print(
    "PASS identifies target system"
)


assert "confidence" in result

print(
    "PASS creates confidence"
)


print(
    "NOVA SELF IMPROVEMENT RECOMMENDER SMOKE PASSED"
)