"""
NOVA BEHAVIOR CONTEXT SERVICE

Converts stored behavior learning events
into useful response guidance.

This does not control answers.
It only provides context.
"""

from nova_backend.services.nova_behavior_memory_store import (
    behavior_memory_store,
)
from nova_backend.services.nova_behavior_memory import (
    behavior_memory
)

BEHAVIOR_UPGRADE_WORDING = {
    "increase_solution_depth_and_next_steps":
        "Prefer deeper solutions with concrete next actions.",
}

def build_behavior_context(
    limit=3
):
    """
    Build lightweight behavior guidance
    from learned patterns.

    Deduplicates learned guidance and ignores
    low-value collection events.
    """

    patterns = (
        behavior_memory_store.get_relevant_patterns(
            limit=limit
        )
    )

    guidance = []

    for pattern in patterns:

        problem = pattern.get(
            "behavior_problem",
            ""
        )

        upgrade = pattern.get(
            "upgrade",
            ""
        )

        if problem == "user_correction_received":
            guidance.append(
                "User has corrected target interpretation before. "
                "Prioritize identifying the exact requested area "
                "before giving a status or recommendation."
            )

        elif upgrade and upgrade != "continue_collecting_real_conversations":
            guidance.append(
                BEHAVIOR_UPGRADE_WORDING.get(
                    upgrade,
                    str(upgrade)
                )
            )

    try:

        improvement_priority = (
            behavior_memory
            .create_improvement_priority()
        )

        focus = improvement_priority.get(
            "focus",
            ""
        )

        if (
            focus
            and focus != "collect_behavior_data"
        ):

            guidance.append(
                (
                    "Current Nova improvement focus: "
                    f"{focus}."
                )
            )


    except Exception as exc:

        print(
            "[NOVA_BEHAVIOR_CONTEXT_PRIORITY_FAILED]",
            exc
        )


    return list(
        dict.fromkeys(guidance)
    )