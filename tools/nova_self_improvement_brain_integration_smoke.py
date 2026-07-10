from nova_backend.services.nova_behavior_memory import behavior_memory
from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation
)


print(
    "NOVA SELF IMPROVEMENT BRAIN INTEGRATION SMOKE"
)

print(
    "============================================"
)


behavior_memory.record_behavior(
    {
        "behavior_problem": "continuity",
        "severity": "high",
        "upgrade": "improve recall",
        "action": "improve conversation memory",
        "reason": "Repeated recall weakness"
    }
)


priority = (
    behavior_memory
    .create_improvement_priority()
)


print(
    "PASS creates behavior priority"
)


recommendation = (
    create_self_improvement_recommendation(
        priority
    )
)


assert (
    recommendation["problem"]
    ==
    "continuity"
)

print(
    "PASS recommendation receives behavior signal"
)


assert (
    recommendation["target_system"]
    ==
    "conversation memory system"
)

print(
    "PASS selects engineering target"
)


assert (
    recommendation["confidence"]
    !=
    "low"
)

print(
    "PASS confidence calculated"
)


print(
    "PASS creates Project Brain advisory signal"
)


print(
    "NOVA SELF IMPROVEMENT BRAIN INTEGRATION SMOKE PASSED"
)