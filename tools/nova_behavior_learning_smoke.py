from nova_backend.services.nova_behavior_learning import (
    analyze_behavior_history
)


print(
    "NOVA BEHAVIOR LEARNING SMOKE"
)

print(
    "============================"
)


observations = [

    {
        "signals": {
            "category": "continuity",
            "issue": "weak recall"
        }
    },

    {
        "signals": {
            "category": "continuity",
            "issue": "missing context"
        }
    },

    {
        "signals": {
            "category": "attachments",
            "issue": "analysis failed"
        }
    },

]


report = analyze_behavior_history(
    observations
)


assert report[
    "observations_analyzed"
] == 3

print(
    "PASS loads observations"
)


assert len(
    report[
        "improvement_opportunities"
    ]
) > 0

print(
    "PASS creates improvement ranking"
)


top = report[
    "improvement_opportunities"
][0]


assert top["category"] == "continuity"

print(
    "PASS ranks highest issue"
)


print(
    "PASS creates learning report"
)

print(
    "NOVA BEHAVIOR LEARNING SMOKE PASSED"
)