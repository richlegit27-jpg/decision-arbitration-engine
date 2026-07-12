"""
NOVA BEHAVIOR LEARNING LOOP

Connects:
- conversation quality evaluation
- behavior upgrade engine
- behavior memory store

This is the integration point for Nova's
self-audit behavior cycle.
"""

from nova_backend.services.nova_behavior_upgrade_engine import (
    analyze_behavior_upgrade,
)

from nova_backend.services.nova_behavior_memory_store import (
    behavior_memory_store,
)

from nova_backend.services.nova_behavior_memory import (
    behavior_memory,
)

from nova_backend.services.nova_self_improvement_coordinator import (
    evaluate_self_improvement,
)


def process_conversation_behavior(
    evaluation
):
    """
    Takes a conversation evaluation and:

    1. Finds behavior improvement
    2. Stores the event
    3. Checks improvement priority
    4. Sends important patterns to self-improvement
    """

    upgrade = analyze_behavior_upgrade(
        evaluation
    )


    event = behavior_memory_store.add_event(
        upgrade.as_dict()
    )


    priority = (
        behavior_memory.create_improvement_priority()
    )


    improvement_result = None


    if priority.get(
        "priority"
    ) in (
        "critical",
        "high",
    ):

        improvement_result = (
            evaluate_self_improvement(
                {
                    "recommended_focus":
                        priority
                }
            )
        )

    priority = (
        behavior_memory.create_improvement_priority()
    )


    improvement_result = None


    if priority.get(
        "priority"
    ) in (
        "critical",
        "high",
    ):

        improvement_result = (
            evaluate_self_improvement(
                {
                    "recommended_focus":
                        priority
                }
            )
        )


    return {

        "behavior_problem": (
            upgrade.behavior_problem
        ),

        "severity": (
            upgrade.severity
        ),

        "upgrade": (
            upgrade.upgrade
        ),

        "stored_event": (
            event
        ),

        "improvement_priority": (
            priority
        ),

        "improvement_result": (
            improvement_result
        ),

    }
