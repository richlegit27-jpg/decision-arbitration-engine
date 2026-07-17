from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


def get_top_move():

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

    assert ranked_moves

    return ranked_moves[0]


def main():

    first = get_top_move()

    assert "name" in first

    assert "adjusted_rank" in first

    assert "memory_influence" in first

    before_rank = first["adjusted_rank"]

    before_memory = first["memory_influence"]


    second = get_top_move()

    after_rank = second["adjusted_rank"]

    after_memory = second["memory_influence"]


    assert isinstance(
        before_memory,
        dict,
    )

    assert isinstance(
        after_memory,
        dict,
    )


    print(
        "FIRST TOP MOVE:",
        first["name"],
    )

    print(
        "FIRST MEMORY:",
        before_memory,
    )

    print(
        "SECOND TOP MOVE:",
        second["name"],
    )

    print(
        "SECOND MEMORY:",
        after_memory,
    )

    print(
        "RANK VALUES:",
        before_rank,
        after_rank,
    )

    print(
        "PROJECT BRAIN MEMORY RANKING BEHAVIOR SMOKE PASS"
    )


if __name__ == "__main__":
    main()