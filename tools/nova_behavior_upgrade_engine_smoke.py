from nova_backend.services.nova_behavior_upgrade_engine import (
    analyze_behavior_upgrade,
    create_behavior_card,
)


print("NOVA BEHAVIOR UPGRADE ENGINE SMOKE")
print("=" * 40)


continuity_case = {
    "continuity": 40,
    "helpfulness": 80,
    "reasoning": 90,
    "actionability": 90,
    "issues": [
        "User requested continuity but no previous context was available."
    ],
}


result = analyze_behavior_upgrade(
    continuity_case
).as_dict()


assert result["behavior_problem"] == "continuity_failure"
assert result["severity"] == "critical"

print("PASS continuity detection")


depth_case = {
    "continuity": 100,
    "helpfulness": 50,
    "reasoning": 90,
    "actionability": 90,
    "issues": [
        "Assistant response was too short."
    ],
}


result = analyze_behavior_upgrade(
    depth_case
).as_dict()


assert result["behavior_problem"] == "low_helpfulness_depth"

print("PASS helpfulness detection")


card = create_behavior_card(
    depth_case
)


assert "recommended_move" in card
assert "exact_next_action" in card

print("PASS behavior card")


print()
print("NOVA BEHAVIOR UPGRADE ENGINE SMOKE PASSED")