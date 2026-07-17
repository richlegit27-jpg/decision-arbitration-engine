import os

from nova_backend.services.project_brain_decision_outcome_recorder import (
    project_brain_decision_outcome_recorder,
)

from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)

from nova_backend.services.project_brain_decision_ranker import (
    score_decision_memory,
)


TEST_DECISION = "Failure Interpreter v2"


def main():

    memory_path = str(
        project_brain_decision_memory.store.save(
    {
        "events": []
    }
)
    )

    if os.path.exists(
        memory_path
    ):
        os.remove(
            memory_path
        )

    empty = score_decision_memory(
        TEST_DECISION
    )

    print(
        "EMPTY MEMORY:",
        empty,
    )


    project_brain_decision_outcome_recorder.record_outcome(
        decision={
            "recommended_move": TEST_DECISION,
        },
        outcome="success",
        evidence=[
            "deterministic smoke success"
        ],
    )


    success_signal = score_decision_memory(
        TEST_DECISION
    )

    print(
        "AFTER SUCCESS:",
        success_signal,
    )

    assert success_signal.get(
        "memory_signal"
    ) == 1


    project_brain_decision_outcome_recorder.record_outcome(
        decision={
            "recommended_move": TEST_DECISION,
        },
        outcome="failed",
        evidence=[
            "deterministic smoke failure"
        ],
    )


    failure_signal = score_decision_memory(
        TEST_DECISION
    )

    print(
        "AFTER FAILURE:",
        failure_signal,
    )

    assert failure_signal.get(
        "memory_signal"
    ) == -1


    print(
        "PROJECT BRAIN MEMORY LEARNING BEHAVIOR SMOKE PASS"
    )


if __name__ == "__main__":
    main()


