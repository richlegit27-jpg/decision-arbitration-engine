from nova_backend.services.project_brain_decision_outcome_recorder import (
    project_brain_decision_outcome_recorder,
)

from nova_backend.services.project_brain_decision_memory import (
    ProjectBrainDecisionMemory,
)


TEST_PATH = "data/test_project_brain_decision_outcome_memory.json"


def main():
    recorder = project_brain_decision_outcome_recorder

    result = recorder.record_outcome(
        decision={
            "recommended_move": "Cleanup Strategy Engine v1",
            "risk": "medium",
            "command": "python .\\tools\\nova_finalizer_pipeline_audit.py",
        },
        outcome="smoke_passed",
        evidence=[
            "nova_answer_quality_smoke.py PASS",
        ],
    )

    assert result["recorded"] is True

    print("PROJECT BRAIN DECISION OUTCOME RECORDER SMOKE PASS")


if __name__ == "__main__":
    main()