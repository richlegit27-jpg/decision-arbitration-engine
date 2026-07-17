from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)
from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


MOVE = "Cleanup Strategy Engine v1"


def find_move(plan, name):
    for move in plan.get("ranked_moves", []):
        if move.get("name") == name:
            return move
    return None


def reset_memory():
    project_brain_decision_memory.store.save(
        {
            "events": []
        }
    )


def assert_signal(move, expected):
    assert move is not None
    assert move["memory_signal"] == expected


reset_memory()

neutral = build_operator_plan_dict(
    user_text="fix the latest failure"
)

neutral_move = find_move(
    neutral,
    MOVE,
)

print(
    "NO MEMORY:",
    neutral_move,
)

assert_signal(
    neutral_move,
    0,
)


project_brain_decision_memory.record_outcome(
    recommended_move=MOVE,
    outcome="success",
)

success = build_operator_plan_dict(
    user_text="fix the latest failure"
)

success_move = find_move(
    success,
    MOVE,
)

print(
    "SUCCESS MEMORY:",
    success_move,
)

assert success_move["memory_signal"] == 1
assert success_move["memory_rank_bonus"] == 1


project_brain_decision_memory.record_outcome(
    recommended_move=MOVE,
    outcome="failure",
)

failure = build_operator_plan_dict(
    user_text="fix the latest failure"
)

failure_move = find_move(
    failure,
    MOVE,
)

print(
    "FAILURE MEMORY:",
    failure_move,
)

assert failure_move["memory_signal"] == -1
assert failure_move["memory_rank_penalty"] == 1


print(
    "PROJECT BRAIN DECISION MEMORY REGRESSION SMOKE PASS"
)