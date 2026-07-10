from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)

from nova_backend.services.nova_upgrade_decision_engine import (
    create_upgrade_decision,
)

from nova_backend.services.nova_improvement_proposal import (
    create_improvement_proposal,
)

from nova_backend.services.mission_proposal_service import (
    create_mission_proposal,
)


print(
    "NOVA SELF IMPROVEMENT FULL PIPELINE SMOKE"
)

print(
    "========================================="
)


behavior_priority = {

    "focus":
        "continuity",

    "priority":
        "medium",

    "reason":
        "continuity detected repeatedly",

}


recommendation = (
    create_self_improvement_recommendation(
        behavior_priority
    )
)


assert (
    recommendation["problem"]
    ==
    "continuity"
)

print(
    "PASS creates self improvement recommendation"
)


upgrade_decision = (
    create_upgrade_decision(
        recommendation
    )
)


assert (
    upgrade_decision["decision"]
    ==
    "consider_upgrade"
)

print(
    "PASS creates upgrade decision"
)


improvement_proposal = (
    create_improvement_proposal(
        recommendation
    )
)


assert (
    improvement_proposal["type"]
    ==
    "improvement_proposal"
)

print(
    "PASS creates improvement proposal"
)


mission_proposal = (
    create_mission_proposal(
        improvement_proposal
    )
)


assert (
    mission_proposal["type"]
    ==
    "mission_proposal"
)

print(
    "PASS creates mission proposal"
)


assert (
    mission_proposal["approval_required"]
    is True
)

print(
    "PASS keeps approval boundary"
)


assert (
    mission_proposal["status"]
    ==
    "proposal"
)

print(
    "PASS prevents automatic execution"
)


print(
    "NOVA SELF IMPROVEMENT FULL PIPELINE SMOKE PASSED"
)