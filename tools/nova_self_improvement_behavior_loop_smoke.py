print("NOVA SELF IMPROVEMENT BEHAVIOR LOOP SMOKE")
print("========================================")

from nova_backend.services.nova_self_improvement_router import (
    build_self_improvement_signal,
)

from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)

print("STEP 1: BUILD BEHAVIOR SIGNAL")

behavior = build_self_improvement_signal(
    {
        "recommended_focus": {
            "focus": "continuity",
            "priority": "medium",
            "reason": "Repeated conversation recall weakness detected",
        }
    }
)

print(behavior)

assert behavior["analyze"] is True
assert behavior["reason"] == "Repeated conversation recall weakness detected"

print("PASS behavior signal")

print()

print("STEP 2: CREATE RECOMMENDATION")

recommendation = create_self_improvement_recommendation(
    behavior
)

print(recommendation)

assert recommendation["problem"] == "continuity"

print("PASS recommendation")

print()
print("NOVA SELF IMPROVEMENT BEHAVIOR LOOP SMOKE PASSED")
