from nova_backend.services.nova_planner_integration import (
    build_planner_request
)


print(
    "NOVA PLANNER INTEGRATION SMOKE"
)

print(
    "=============================="
)


mission = {

    "mission_type":
        "self_improvement",

    "goal":
        "Improve conversation recall",

    "target_system":
        "conversation memory system",

    "priority":
        "medium",
}


request = build_planner_request(
    mission
)


assert (
    request["planner_action"]
    ==
    "create_mission"
)

print(
    "PASS creates planner request"
)


assert (
    request["requires_approval"]
    is True
)

print(
    "PASS preserves approval gate"
)


assert (
    request["source"]
    ==
    "nova_self_improvement"
)

print(
    "PASS identifies source"
)


print(
    "PASS planner integration ready"
)


print(
    "NOVA PLANNER INTEGRATION SMOKE PASSED"
)