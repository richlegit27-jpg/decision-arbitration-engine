from nova_backend.services.nova_mission_creator import (
    create_mission_payload
)


print(
    "NOVA MISSION CREATOR SMOKE"
)

print(
    "=========================="
)


planner_request = {

    "planner_action":
        "create_mission",

    "goal":
        "Improve conversation recall",

    "target_system":
        "conversation memory system",

    "priority":
        "medium",
}


mission = create_mission_payload(
    planner_request
)


assert (
    mission["created_by"]
    ==
    "nova_self_improvement"
)

print(
    "PASS creates mission payload"
)


assert (
    mission["requires_approval"]
    is True
)

print(
    "PASS keeps approval gate"
)


assert (
    mission["target_system"]
    ==
    "conversation memory system"
)

print(
    "PASS preserves target"
)


print(
    "NOVA MISSION CREATOR SMOKE PASSED"
)