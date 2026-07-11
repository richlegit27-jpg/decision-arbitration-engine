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