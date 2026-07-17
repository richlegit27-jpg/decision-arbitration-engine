"""
NOVA PROJECT BRAIN DECISION OUTCOME RECORDER V1

Records whether Project Brain decisions produced useful outcomes.

Separate from improvement missions:
- improvement recorder = did a mission succeed?
- decision recorder = was the judgment call correct?
"""


from datetime import datetime, timezone

from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)


class ProjectBrainDecisionOutcomeRecorder:

    def __init__(self):
        self.version = (
            "NOVA_PROJECT_BRAIN_DECISION_OUTCOME_RECORDER_V1_20260717"
        )

    def record_outcome(
        self,
        decision,
        outcome="unknown",
        evidence=None,
    ):

        if not decision:
            return {
                "recorded": False,
                "reason": "missing_decision",
            }

        entry = {
            "engine": self.version,
            "recorded_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "decision": decision,

            "outcome": outcome,

            "evidence": evidence or [],

        }

        stored = (
            project_brain_decision_memory.add_outcome(
                entry
            )
        )

        return {
            "recorded": True,
            "entry": stored,
        }


project_brain_decision_outcome_recorder = (
    ProjectBrainDecisionOutcomeRecorder()
)