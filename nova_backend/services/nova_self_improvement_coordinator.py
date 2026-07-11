"""
NOVA SELF IMPROVEMENT COORDINATOR V1

Connects live behavior observation
to improvement planning.

Advisory only.
Does not modify systems directly.
"""

from nova_backend.services.nova_behavior_memory import (
    behavior_memory,
)

from nova_backend.services.nova_self_improvement_router import (
    self_improvement_router,
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

from nova_backend.services.nova_self_improvement_planner_bridge import (
    submit_improvement_mission,
)

from nova_backend.services.nova_improvement_history_service import (
    improvement_history,
)


def _mission_already_exists(
    goal
):

    missions = (
        mission_service.list_missions()
    )

    for mission in missions:

        if mission.get(
            "goal"
        ) == goal:

            return True

    return False

def process_behavior_observation(
    behavior_report=None
):

    router_signal = (
        self_improvement_router
        .build_signal(
            behavior_report
        )
    )


    if not router_signal.get(
        "analyze"
    ):

        return {

            "improved": False,

            "reason":
                "router_declined",

        }

    behavior_priority = (
        behavior_report.get(
            "recommended_focus",
            {}
        )
    )


    priority = (
        behavior_priority.get(
            "priority",
            "low"
        )
    )


    recommendation = (
        create_self_improvement_recommendation(
            behavior_priority
        )
    )

    previous_attempts = (
        improvement_history.find_previous(
            recommendation.get(
                "problem"
            )
        )
    )


    if previous_attempts:

        successful_attempts = [

            attempt

            for attempt in previous_attempts

            if attempt.get(
                "outcome"
            ) == "completed"

            and attempt.get(
                "judgment"
            ) == "successful"

        ]


        if successful_attempts:

            return {

                "improved": False,

                "reason":
                    "improvement_already_completed",

                "problem":
                    recommendation.get(
                        "problem"
                    ),

                "previous_attempt":
                    successful_attempts[-1],

            }


        failed_attempts = [

            attempt

            for attempt in previous_attempts

            if (
                attempt.get(
                    "outcome"
                ) != "completed"

                or

                attempt.get(
                    "judgment"
                ) != "successful"
            )

        ]


        if failed_attempts:

            print(
                "[NOVA IMPROVEMENT HISTORY] previous failed improvement found:",
                recommendation.get(
                    "problem"
                )
            )


            recommendation["previous_failed_attempt"] = (
                failed_attempts[-1]
            )


            recommendation["retry_required"] = True



    decision = {

        "decision":
            "consider_upgrade",

        **recommendation,

    }

    mission_proposal = (
        create_upgrade_mission_proposal(
            decision
        )
    )

    if mission_proposal.get(
        "mission_type"
    ) != "self_improvement":

        return {
            "improved": False,
            "reason": "no_mission",
        }


    goal = mission_proposal.get(
        "goal"
    )


    if _mission_already_exists(
        goal
    ):

        return {

            "improved": False,

            "reason":
                "similar_mission_already_exists",

            "goal":
                goal,

        }

    mission = (
        submit_improvement_mission(
            mission_proposal
        )
    )

    improvement_history.record(
        recommendation
    )


    print(
        "[NOVA SELF IMPROVEMENT COORDINATOR] mission submitted:",
        goal
    )


    return {
        "improved": True,

        "priority":
            priority,

        "recommendation":
            recommendation,

        "mission":
            mission,

    }


def evaluate_self_improvement(
    behavior_report=None
):

    return (
        process_behavior_observation(
            behavior_report
        )
    )