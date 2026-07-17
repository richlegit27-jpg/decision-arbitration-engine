from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)

from nova_backend.services.project_brain_decision_outcome_recorder import (
    project_brain_decision_outcome_recorder,
)

from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


TEST_MOVE = "Failure Interpreter v2"


def reset_memory():

    project_brain_decision_memory.store.save(
        {
            "events": []
        }
    )





def get_failure_move(plan):

    for move in plan.get(
        "ranked_moves",
        [],
    ):
        if move.get(
            "name"
        ) == TEST_MOVE:
            return move

    return None


def main():

    reset_memory()


    baseline = build_operator_plan_dict(
        user_text="fix the latest failure",
    )

    baseline_move = get_failure_move(
        baseline
    )

    assert baseline_move is not None


    print(
        "BASELINE MOVE:",
        baseline_move,
    )


    baseline_rank = baseline_move.get(
        "adjusted_rank"
    )


    project_brain_decision_outcome_recorder.record_outcome(
        decision={
            "recommended_move": TEST_MOVE,
        },
        outcome="success",
        evidence=[
            "ranking delta smoke"
        ],
    )


    learned = build_operator_plan_dict(
        user_text="fix the latest failure",
    )

    learned_move = get_failure_move(
        learned
    )

    assert learned_move is not None


    print(
        "LEARNED MOVE:",
        learned_move,
    )


    learned_rank = learned_move.get(
        "adjusted_rank"
    )

    assert learned_rank < baseline_rank

    assert learned_move.get(
        "memory_rank_bonus"
    ) == 1

    assert learned_move.get(
        "memory_influence"
    )

    print(
        "PROJECT BRAIN MEMORY RANKING DELTA SMOKE PASS"
    )


if __name__ == "__main__":
    main()