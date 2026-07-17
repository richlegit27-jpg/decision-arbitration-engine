from nova_backend.services.project_brain_operator_planner import (
    apply_decision_memory_ranking,
)


def main():

    baseline = apply_decision_memory_ranking(
        [
            {
                "name": "normal_move",
                "rank": 1,
                "memory_signal": 0,
            },
            {
                "name": "second_move",
                "rank": 2,
                "memory_signal": 0,
            },
        ]
    )

    assert baseline[0]["name"] == "normal_move"

    success_memory = apply_decision_memory_ranking(
        [
            {
                "name": "normal_move",
                "rank": 2,
                "memory_signal": 0,
            },
            {
                "name": "successful_move",
                "rank": 2,
                "memory_signal": 1,
            },
        ]
    )

    assert (
        success_memory[0]["adjusted_rank"]
        == 1
    )

    failure_memory = apply_decision_memory_ranking(
        [
            {
                "name": "failed_move",
                "rank": 1,
                "memory_signal": -1,
            },
            {
                "name": "safe_move",
                "rank": 3,
                "memory_signal": 0,
            },
        ]
    )

    assert (
        failure_memory[0]["adjusted_rank"]
        == 2
    )

    assert (
        failure_memory[1]["adjusted_rank"]
        == 3
    )

    print(
        "PROJECT BRAIN ADAPTIVE RANKING BEHAVIOR SMOKE PASS"
    )


if __name__ == "__main__":
    main()