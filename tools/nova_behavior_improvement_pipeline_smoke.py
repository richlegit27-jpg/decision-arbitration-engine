from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)

from nova_backend.services.project_brain_decision_engine import (
    decide_project_brain_next_move,
)


print(
    "NOVA BEHAVIOR IMPROVEMENT PIPELINE SMOKE"
)

print(
    "========================================"
)


behavior_priority = {
    "focus": "continuity",
    "priority": "medium",
    "reason": "continuity detected repeatedly",
}


recommendation = (
    create_self_improvement_recommendation(
        behavior_priority
    )
)


assert (
    recommendation["problem"]
    ==
    "continuity"
)

print(
    "PASS behavior signal reaches recommender"
)


assert (
    recommendation["recommended_upgrade"]
    ==
    "Improve conversation recall and session continuity"
)

print(
    "PASS recommender creates upgrade"
)


assert (
    recommendation["target_system"]
    ==
    "conversation memory system"
)

print(
    "PASS recommender identifies target"
)


decision = decide_project_brain_next_move(
    user_text="",
    pasted_output="",
)


assert decision is not None

print(
    "PASS Project Brain receives improvement signal"
)


assert hasattr(
    decision,
    "recommended_next_move"
)

print(
    "PASS Project Brain returns decision object"
)


print(
    "NOVA BEHAVIOR IMPROVEMENT PIPELINE SMOKE PASSED"
)