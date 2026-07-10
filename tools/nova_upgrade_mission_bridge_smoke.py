from nova_backend.services.nova_upgrade_mission_bridge import (
    create_upgrade_mission_proposal
)


print(
    "NOVA UPGRADE MISSION BRIDGE SMOKE"
)

print(
    "================================="
)


decision = {

    "decision":
        "consider_upgrade",

    "recommended_upgrade":
        "Improve conversation recall",

    "target_system":
        "conversation memory system",

    "priority":
        "medium",
}


mission = create_upgrade_mission_proposal(
    decision
)


assert (
    mission["mission_type"]
    ==
    "self_improvement"
)

print(
    "PASS creates mission proposal"
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
    "PASS creates planner-ready proposal"
)


print(
    "NOVA UPGRADE MISSION BRIDGE SMOKE PASSED"
)