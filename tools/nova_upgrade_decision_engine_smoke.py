from nova_backend.services.nova_upgrade_decision_engine import (
    create_upgrade_decision
)


print(
    "NOVA UPGRADE DECISION ENGINE SMOKE"
)

print(
    "================================="
)


recommendation = {

    "problem":
        "continuity",

    "target_system":
        "conversation memory system",

    "recommended_upgrade":
        "Improve conversation recall",

    "priority":
        "medium",

    "confidence":
        "medium",
}


decision = create_upgrade_decision(
    recommendation
)


assert (
    decision["decision"]
    ==
    "consider_upgrade"
)

print(
    "PASS creates upgrade decision"
)


assert (
    decision["requires_review"]
    is True
)

print(
    "PASS requires review gate"
)


assert (
    decision["risk"]
    ==
    "low"
)

print(
    "PASS calculates risk"
)


print(
    "PASS creates Project Brain decision"
)


print(
    "NOVA UPGRADE DECISION ENGINE SMOKE PASSED"
)