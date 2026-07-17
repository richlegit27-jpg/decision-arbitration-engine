from nova_backend.services.project_brain_operator_planner import (
    apply_decision_memory_ranking,
)


def main():

    moves = [
        {
            "name": "success_move",
            "rank": 1,
            "memory_signal": 1,
        },
        {
            "name": "unknown_move",
            "rank": 2,
            "memory_signal": 0,
        },
        {
            "name": "failed_move",
            "rank": 3,
            "memory_signal": -1,
        },
    ]

    result = apply_decision_memory_ranking(
        moves
    )

    assert result[0]["name"] == "success_move"
    assert result[0]["adjusted_rank"] == 0

    assert result[1]["name"] == "unknown_move"
    assert result[1]["adjusted_rank"] == 2

    assert result[2]["name"] == "failed_move"
    assert result[2]["adjusted_rank"] == 4

    print(
        "PROJECT BRAIN DECISION MEMORY RANKING ADJUSTMENT SMOKE PASS"
    )


if __name__ == "__main__":
    main()