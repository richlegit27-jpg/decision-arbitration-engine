from nova_backend.services.nova_improvement_proposal import (
    create_improvement_proposal,
)


print(
    "NOVA IMPROVEMENT PROPOSAL SMOKE"
)

print(
    "==============================="
)


proposal = create_improvement_proposal(
    {
        "problem": "continuity",
        "reason": (
            "continuity detected repeatedly"
        ),
        "recommended_upgrade":
            "Improve conversation recall and session continuity",
        "target_system":
            "conversation memory system",
        "confidence":
            0.85,
    }
)


assert (
    proposal["type"]
    ==
    "improvement_proposal"
)

print(
    "PASS creates proposal type"
)


assert (
    proposal["problem"]
    ==
    "continuity"
)

print(
    "PASS preserves problem"
)


assert (
    proposal["risk"]
    ==
    "low"
)

print(
    "PASS assigns safety risk"
)


assert (
    proposal["confidence"]
    ==
    0.85
)

print(
    "PASS preserves confidence"
)


print(
    "NOVA IMPROVEMENT PROPOSAL SMOKE PASSED"
)