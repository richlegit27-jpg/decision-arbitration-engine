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


def process_conversation_behavior(
    evaluation
):
    """
    Takes a conversation evaluation and:

    1. Finds behavior improvement
    2. Stores the event
    3. Returns learning report
    """

    upgrade = analyze_behavior_upgrade(
        evaluation
    )

    event = behavior_memory_store.add_event(
        upgrade.as_dict()
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
        "stored_event": event,
    }