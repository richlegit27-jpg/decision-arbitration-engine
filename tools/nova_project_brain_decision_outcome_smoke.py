from nova_backend.services.project_brain_decision_outcome_recorder import (
    project_brain_decision_outcome_recorder,
)

from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)


decision = {
    "recommended_move": "Smoke Test Decision",
    "risk": "low",
    "command": "python smoke_test.py",
}

result = project_brain_decision_outcome_recorder.record_outcome(
    decision,
    "smoke_passed",
    evidence=[
        "nova_project_brain_decision_outcome_smoke.py PASS"
    ],
)

assert result.get("recorded") is True

events = project_brain_decision_memory.get_events()

latest = events[-1]

assert (
    latest["decision"]["recommended_move"]
    == "Smoke Test Decision"
)

assert latest["outcome"] == "smoke_passed"

print("PROJECT BRAIN DECISION OUTCOME SMOKE PASS")