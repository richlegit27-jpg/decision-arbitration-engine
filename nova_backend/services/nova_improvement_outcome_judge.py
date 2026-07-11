"""
NOVA IMPROVEMENT OUTCOME JUDGE V1

Evaluates whether an improvement mission
actually produced a successful outcome.

Advisory only.
Does not modify systems.
"""


from datetime import datetime, timezone


class NovaImprovementOutcomeJudge:


    def __init__(self):

        self.version = (
            "NOVA_IMPROVEMENT_OUTCOME_JUDGE_V1_20260711"
        )


    def evaluate(
        self,
        mission_result=None
    ):

        if not mission_result:

            return self._uncertain(
                "missing mission result"
            )


        status = (
            mission_result.get(
                "status",
                ""
            )
        )


        results = (
            mission_result.get(
                "results",
                []
            )
        )


        if status == "completed":

            return {

                "engine":
                    self.version,

                "evaluated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "outcome":
                    "completed",

                "judgment":
                    "successful",

                "confidence":
                    "high",

                "evidence":
                    results,

            }


        if status in (
            "failed",
            "error",
        ):

            return {

                "engine":
                    self.version,

                "evaluated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "outcome":
                    "failed",

                "judgment":
                    "unsuccessful",

                "confidence":
                    "high",

                "evidence":
                    results,

            }


        return self._uncertain(
            "insufficient mission evidence"
        )


    def _uncertain(
        self,
        reason
    ):

        return {

            "engine":
                self.version,

            "evaluated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "outcome":
                "unknown",

            "judgment":
                "uncertain",

            "confidence":
                "low",

            "reason":
                reason,

        }



improvement_outcome_judge = (
    NovaImprovementOutcomeJudge()
)