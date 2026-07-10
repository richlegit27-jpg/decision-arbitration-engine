from nova_backend.services.nova_self_improvement_planner_bridge import (
    submit_improvement_mission
)


print(
    "NOVA SELF IMPROVEMENT PLANNER BRIDGE SMOKE"
)

print(
    "=========================================="
)


payload = {

    "goal":
        "Improve conversation recall",

    "target_system":
        "conversation memory system",

    "priority":
        "medium",

    "requires_approval":
        True
}


result = submit_improvement_mission(
    payload
)


assert (
    result["status"]
    ==
    "created"
)

print(
    "PASS creates planner mission"
)


assert (
    "mission"
    in result
)

print(
    "PASS returns planner result"
)


print(
    "NOVA SELF IMPROVEMENT PLANNER BRIDGE SMOKE PASSED"
)