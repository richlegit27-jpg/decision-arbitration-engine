from nova_backend.services.project_brain_decision_memory import (
    ProjectBrainDecisionMemory,
)


TEST_PATH = "data/test_project_brain_decision_memory.json"


def main():
    store = ProjectBrainDecisionMemory(TEST_PATH)

    event = store.add_outcome(
        {
            "recommended_move": "Cleanup Strategy Engine v1",
            "risk": "medium",
            "outcome": "smoke_passed",
            "impact": "decision memory storage works",
        }
    )

    events = store.get_events()

    assert event["event_type"] == "decision_outcome"
    assert event["recommended_move"] == "Cleanup Strategy Engine v1"
    assert len(events) == 1

    print("PROJECT BRAIN DECISION MEMORY SMOKE PASS")


if __name__ == "__main__":
    main()