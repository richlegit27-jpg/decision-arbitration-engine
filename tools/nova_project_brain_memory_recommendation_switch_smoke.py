import os

from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)

from nova_backend.services.project_brain_decision_outcome_recorder import (
    project_brain_decision_outcome_recorder,
)

from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


TEST_MOVE = "Cleanup Strategy Engine v1"


def reset_memory():

    path = str(
        project_brain_decision_memory.store.save(
    {
        "events": []
    }
)
    )

    if os.path.exists(path):
        os.remove(path)


def main():

    reset_memory()

    baseline = build_operator_plan_dict(
        user_text="fix the latest failure",
    )

    baseline_moves = baseline.get(
        "ranked_moves",
        [],
    )

    baseline_top = baseline_moves[0]["name"]

    print(
        "BASELINE TOP:",
        baseline_top,
    )


    project_brain_decision_outcome_recorder.record_outcome(
        decision={
            "recommended_move": TEST_MOVE,
        },
        outcome="success",
        evidence=[
            "recommendation switch smoke"
        ],
    )


    learned = build_operator_plan_dict(
        user_text="fix the latest failure",
    )

    learned_moves = learned.get(
        "ranked_moves",
        [],
    )

    learned_top = learned_moves[0]["name"]

    print(
        "LEARNED TOP:",
        learned_top,
    )

    cleanup = [
        move
        for move in learned_moves
        if move.get("name") == TEST_MOVE
    ][0]

    print(
        "LEARNED TARGET:",
        cleanup,
    )


    assert cleanup.get(
        "memory_rank_bonus"
    ) == 1


    assert cleanup.get(
        "adjusted_rank"
    ) < cleanup.get(
        "rank"
    )


    print(
        "PROJECT BRAIN MEMORY RECOMMENDATION SWITCH SMOKE PASS"
    )


if __name__ == "__main__":
    main()