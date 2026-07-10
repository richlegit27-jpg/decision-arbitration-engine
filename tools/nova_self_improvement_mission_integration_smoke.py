from nova_backend.services.self_improvement_mission_adapter import (
    build_self_improvement_mission_request,
)

from nova_backend.services.planner_service import (
    planner_service,
)


print(
    "NOVA SELF IMPROVEMENT MISSION INTEGRATION SMOKE"
)

print(
    "=============================================="
)


mission_proposal = {

    "type":
        "mission_proposal",

    "goal":
        "Improve conversation recall and session continuity",

    "risk":
        "low",

    "approval_required":
        True,

}


request = (
    build_self_improvement_mission_request(
        mission_proposal
    )
)


assert (
    request["goal"]
    ==
    "Improve conversation recall and session continuity"
)

print(
    "PASS adapter creates mission request"
)


mission = planner_service.create_mission(
    request["goal"]
)


assert (
    mission["goal"]
    ==
    "Improve conversation recall and session continuity"
)

print(
    "PASS planner creates mission"
)


assert (
    mission["status"]
    in
    [
        "planning",
        "ready",
    ]
)

print(
    "PASS mission enters valid state"
)


assert (
    "metadata"
    in
    mission
)

print(
    "PASS mission keeps metadata contract"
)


print(
    "NOVA SELF IMPROVEMENT MISSION INTEGRATION SMOKE PASSED"
)