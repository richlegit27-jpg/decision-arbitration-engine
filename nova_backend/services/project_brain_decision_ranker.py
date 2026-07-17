from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)


def score_decision_memory(recommended_move: str) -> dict:

    events = project_brain_decision_memory.get_events()

    matches = [
        event
        for event in events
        if isinstance(
            event.get("decision"),
            dict,
        )
        and (
            event.get("decision", {})
            .get("recommended_move")
            == recommended_move
        )
    ]

    if not matches:
        return {
            "memory_signal": 0,
            "reason": "no_history",
        }

    latest = matches[-1]

    outcome = str(
        latest.get("outcome")
        or ""
    ).lower()

    if outcome in {
        "success",
        "smoke_passed",
        "completed",
    }:
        return {
            "memory_signal": 1,
            "reason": "previous_success",
        }

    if outcome in {
        "failed",
        "failure",
        "blocked",
    }:
        return {
            "memory_signal": -1,
            "reason": "previous_failure",
        }

    return {
        "memory_signal": 0,
        "reason": "neutral_history",
    }