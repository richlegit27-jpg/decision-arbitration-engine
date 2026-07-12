"""
NOVA SELF IMPROVEMENT LIVE LOOP SMOKE

Validates:

behavior signal
        ->
behavior observer
        ->
behavior learning loop
"""

from nova_backend.services.nova_self_improvement_router import (
    build_self_improvement_signal,
)

from nova_backend.services.nova_behavior_memory import (
    NovaBehaviorMemory,
)

from nova_backend.services.nova_behavior_observer import (
    behavior_observer,
)

from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)

from nova_backend.services.nova_upgrade_mission_bridge import (
    create_upgrade_mission_proposal,
)


from nova_backend.services.nova_self_improvement_planner_bridge import (
    submit_improvement_mission,
)

print(
    "NOVA SELF IMPROVEMENT LIVE LOOP SMOKE"
)

print(
    "====================================="
)


def check(
    name,
    value=True
):

    if value:
        print(
            "PASS",
            name
        )

    else:
        print(
            "FAIL",
            name
        )

        raise SystemExit(1)



signal = {

    "continuity":
        100,

    "helpfulness":
        100,

    "reasoning":
        100,

    "actionability":
        40,

    "issues":
        [
            "generic_response"
        ],

    "user_correction":
        False,

}


check(
    "behavior signal created",
    bool(signal)
)



observer_result = None


for _ in range(3):

    observer_result = (
        behavior_observer.observe(
            signal
        )
    )


check(
    "observer accepted signal",
    observer_result.get(
        "observed"
    )
)


print()

print(
    "Observer result:"
)

print(
    observer_result
)

memory = NovaBehaviorMemory()


priority = (
    memory.create_improvement_priority()
)


print()

print(
    "Memory priority:"
)

print(
    priority
)


check(
    "memory detected improvement priority",
    priority.get(
        "focus"
    ) == "weak_actionability"
)

behavior_report = {

    "recommended_focus":
        priority

}


router_signal = (
    build_self_improvement_signal(
        behavior_report
    )
)


print()

print(
    "Router signal:"
)

print(
    router_signal
)


check(
    "router requested analysis",
    router_signal.get(
        "analyze"
    )
)

recommendation = (
    create_self_improvement_recommendation(
        priority
    )
)


print()

print(
    "Recommendation:"
)

print(
    recommendation
)


check(
    "recommender created upgrade",
    bool(
        recommendation.get(
            "recommended_upgrade"
        )
    )
)

upgrade_decision = {

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


mission_proposal = (
    create_upgrade_mission_proposal(
        upgrade_decision
    )
)


print()

print(
    "Mission proposal:"
)

print(
    mission_proposal
)


check(
    "mission bridge created proposal",
    mission_proposal.get(
        "mission_type"
    ) == "self_improvement"
)

mission = (
    submit_improvement_mission(
        mission_proposal
    )
)



print()

print(
    "Created mission:"
)

print(
    mission
)

check(
    "mission service accepted improvement mission",
    mission.get(
        "status"
    )
    == "created"
    and
    mission.get(
        "mission"
    )
    .get(
        "status"
    )
    == "ready"
)


print()

memory = NovaBehaviorMemory()

priority = (
    memory.create_improvement_priority()
)

print(
    "PASS complete self improvement pipeline"
)

print(
    "PASS observer -> memory -> router -> recommender -> mission"
)