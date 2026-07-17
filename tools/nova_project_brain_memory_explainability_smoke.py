from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


def main():

    result = build_operator_plan_dict(
        user_text="fix the latest failure",
    )

    ranked_moves = result.get(
        "ranked_moves",
        [],
    )

    assert isinstance(
        ranked_moves,
        list,
    )

    assert len(
        ranked_moves
    ) > 0

    move = ranked_moves[0]

    assert "adjusted_rank" in move

    assert "memory_influence" in move

    assert isinstance(
        move["memory_influence"],
        dict,
    )

    print(
        "PROJECT BRAIN MEMORY EXPLAINABILITY SMOKE PASS"
    )


if __name__ == "__main__":
    main()