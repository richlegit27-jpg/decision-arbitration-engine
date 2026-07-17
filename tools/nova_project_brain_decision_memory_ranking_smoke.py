from nova_backend.services.project_brain_decision_ranker import (
    score_decision_memory,
)


result = score_decision_memory(
    "Cleanup Strategy Engine v1"
)

assert result["memory_signal"] == 1
assert result["reason"] == "previous_success"

unknown = score_decision_memory(
    "Unknown Future Decision"
)

assert unknown["memory_signal"] == 0

print(
    "PROJECT BRAIN DECISION MEMORY RANKING SMOKE PASS"
)