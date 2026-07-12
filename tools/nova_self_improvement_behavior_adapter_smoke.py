from nova_backend.services.nova_self_improvement_router import (
    build_self_improvement_signal,
)

from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)


print("NOVA SELF IMPROVEMENT BEHAVIOR ADAPTER SMOKE")
print("============================================")


behavior_report = {
    "recommended_focus": {
        "priority": "medium",
        "reason": "Repeated conversation recall weakness detected",
    }
}


print("STEP 1: ROUTER SIGNAL")

signal = build_self_improvement_signal(
    behavior_report
)

print(signal)

assert signal["analyze"] is True

print("PASS router")


print()
print("STEP 2: BUILD RECOMMENDER INPUT")


priority = {
    "focus": "continuity",
    "priority": "medium",
    "reason": signal["reason"],
}


print(priority)


recommendation = create_self_improvement_recommendation(
    priority
)


print(recommendation)


assert recommendation["problem"] == "continuity"

print("PASS recommendation")


print()
print("NOVA SELF IMPROVEMENT BEHAVIOR ADAPTER SMOKE PASSED")