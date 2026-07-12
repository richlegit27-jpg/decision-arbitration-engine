"""
NOVA SELF IMPROVEMENT END TO END SMOKE

Verifies:

behavior signal
-> recommendation
-> mission creation
-> mission completion
-> outcome recording
-> improvement history
"""


from nova_backend.services.nova_self_improvement_router import (
    build_self_improvement_signal,
)

from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)

from nova_backend.services.nova_upgrade_mission_bridge import (
    create_upgrade_mission_proposal,
)

from nova_backend.services.mission_service import (
    mission_service,
)

from nova_backend.services.nova_improvement_history_service import (
    improvement_history,
)


print(
    "NOVA SELF IMPROVEMENT END TO END SMOKE"
)

print(
    "====================================="
)

behavior_report = {

    "recommended_focus":
        {

            "focus":
                "weak_actionability",

            "priority":
                "critical",

            "reason":
                "responses lack actionable next steps",

        }

}



signal = (
    build_self_improvement_signal(
        behavior_report
    )
)


print()

print(
    "Signal:"
)

print(
    signal
)


recommendation = (
    create_self_improvement_recommendation(
        signal
    )
)


print()

print(
    "Recommendation:"
)

print(
    recommendation
)


decision = {

    "decision":
        "consider_upgrade",

    "recommended_upgrade":
        recommendation.get(
            "recommended_upgrade"
        ),

    "target_system":
        recommendation.get(
            "target_system"
        ),

    "priority":
        recommendation.get(
            "priority"
        ),

}


proposal = (
    create_upgrade_mission_proposal(
        decision
    )
)


print()

print(
    "Mission Proposal:"
)

print(
    proposal
)


mission = (
    mission_service.create_mission(
        proposal["goal"],

        [
            "design",
            "implement",
            "test",
        ],

        {
            "mission_type":
                "self_improvement",

            "problem":
                recommendation["problem"],
        },
    )
)


mission_id = mission["id"]


for _ in range(3):

    mission = (
        mission_service.advance_step(
            mission_id,
            {
                "status":
                    "passed"
            }
        )
    )


print()

print(
    "Completed Mission:"
)

print(
    mission
)


history = (
    improvement_history.find_previous(
        recommendation["problem"]
    )
)


if history:

    print()

    print(
        "PASS self improvement loop"
    )

else:

    print()

    print(
        "FAIL self improvement loop"
    )

    raise SystemExit(1)