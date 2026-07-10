from nova_backend.services.self_improvement_mission_adapter import (
    build_self_improvement_mission_request,
)


print(
    "NOVA SELF IMPROVEMENT MISSION ADAPTER SMOKE"
)

print(
    "=========================================="
)


request = build_self_improvement_mission_request(
    {
        "type":
            "mission_proposal",

        "goal":
            "Improve conversation recall and session continuity",

        "risk":
            "low",

        "approval_required":
            True,
    }
)


assert (
    request["goal"]
    ==
    "Improve conversation recall and session continuity"
)

print(
    "PASS preserves mission goal"
)


assert (
    request["metadata"]["approval_required"]
    is True
)

print(
    "PASS preserves approval boundary"
)


assert (
    request["metadata"]["source"]
    ==
    "self_improvement_pipeline"
)

print(
    "PASS identifies source"
)


print(
    "NOVA SELF IMPROVEMENT MISSION ADAPTER SMOKE PASSED"
)