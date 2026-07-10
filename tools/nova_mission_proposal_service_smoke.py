from nova_backend.services.mission_proposal_service import (
    create_mission_proposal,
)


print(
    "NOVA MISSION PROPOSAL SERVICE SMOKE"
)

print(
    "==================================="
)


proposal = create_mission_proposal(
    {
        "type":
            "improvement_proposal",

        "problem":
            "continuity",

        "recommended_upgrade":
            "Improve conversation recall and session continuity",

        "target_system":
            "conversation memory system",

        "confidence":
            0.85,

        "risk":
            "low",
    }
)


assert (
    proposal["type"]
    ==
    "mission_proposal"
)

print(
    "PASS creates mission proposal"
)


assert (
    proposal["status"]
    ==
    "proposal"
)

print(
    "PASS keeps proposal state"
)


assert (
    proposal["approval_required"]
    is True
)

print(
    "PASS requires approval"
)


assert (
    proposal["target"]
    ==
    "conversation memory system"
)

print(
    "PASS preserves target"
)


print(
    "NOVA MISSION PROPOSAL SERVICE SMOKE PASSED"
)
