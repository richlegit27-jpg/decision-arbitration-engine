"""
NOVA IMPROVEMENT OUTCOME RECORDER V1

Records completed self-improvement mission outcomes.

Closes the learning loop:
mission -> outcome -> history

Advisory only.
"""


from datetime import datetime, timezone

from nova_backend.services.nova_improvement_history_service import (
    improvement_history,
)

from nova_backend.services.nova_improvement_outcome_judge import (
    improvement_outcome_judge,
)

class NovaImprovementOutcomeRecorder:


    def __init__(self):

        self.version = (
            "NOVA_IMPROVEMENT_OUTCOME_RECORDER_V1_20260711"
        )


    def record_outcome(
        self,
        mission,
        outcome="completed",
    ):

        if not mission:

            return {

                "recorded": False,

                "reason":
                    "missing_mission",

            }


        problem = (
            mission.get(
                "metadata",
                {}
            )
            .get(
                "problem"
            )
        )


        if not problem:

            problem = (
                mission.get(
                    "goal",
                    "unknown"
                )
            )


        entry = {

            "engine":
                self.version,

            "recorded_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "mission_id":
                mission.get(
                    "id"
                ),

            "problem":
                problem,

            "outcome":
                outcome,

            "status":
                "completed",

        }


        judgment = (
            improvement_outcome_judge.evaluate(
                {
                    "status":
                        outcome,

                    "results":
                        mission.get(
                            "results",
                            []
                        ),
                }
            )
        )


        entry.update(
            {

                "judgment":
                    judgment.get(
                        "judgment"
                    ),

                "confidence":
                    judgment.get(
                        "confidence"
                    ),

            }
        )

        improvement_history.record(
            entry
        )


        return {

            "recorded": True,

            "entry":
                entry,

        }


improvement_outcome_recorder = (
    NovaImprovementOutcomeRecorder()
)