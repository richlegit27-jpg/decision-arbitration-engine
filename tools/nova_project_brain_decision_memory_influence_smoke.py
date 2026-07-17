from nova_backend.services.project_brain_decision_ranker import (
    score_decision_memory,
)


success = score_decision_memory(
    "Cleanup Strategy Engine v1"
)

assert success["memory_signal"] == 1
assert success["reason"] == "previous_success"


unknown = score_decision_memory(
    "Future Unknown Decision"
)

assert unknown["memory_signal"] == 0
assert unknown["reason"] == "no_history"


failure = score_decision_memory(
    "Failure Interpreter v2"
)

assert failure["memory_signal"] in (
    -1,
    0,
)

print(
    "PROJECT BRAIN DECISION MEMORY INFLUENCE SMOKE PASS"
)