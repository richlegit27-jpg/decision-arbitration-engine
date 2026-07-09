from nova_backend.services.project_brain_completed_move_filter import (
    completed_move_names,
    detect_completed_move,
    filter_completed_moves,
    is_move_completed,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN COMPLETED MOVE FILTER SMOKE")
    print("==============================================")

    operator = detect_completed_move("Operator Plan Quality v2")
    assert_true("operator quality completed", operator.completed, operator)
    assert_true("operator quality evidence", "ranked_moves" in operator.evidence, operator)

    selector = detect_completed_move("Smoke Selector v1")
    assert_true("smoke selector completed", selector.completed, selector)
    assert_true("smoke selector evidence", "project_brain_smoke_selector.py" in selector.evidence, selector)

    command_center = detect_completed_move("Command Center v2")
    assert_true("command center completed", command_center.completed, command_center)
    assert_true("command center evidence", "Command Center" in command_center.evidence, command_center)

    unknown = detect_completed_move("Cleanup Strategy Engine v1")
    assert_true("unknown not completed", not unknown.completed, unknown)

    assert_true("is move completed true", is_move_completed("Operator Plan Quality v2"))
    assert_true("is move completed false", not is_move_completed("Cleanup Strategy Engine v1"))

    completed = completed_move_names([
        "Operator Plan Quality v2",
        "Smoke Selector v1",
        "Cleanup Strategy Engine v1",
    ])
    assert_true("completed names include operator", "Operator Plan Quality v2" in completed, completed)
    assert_true("completed names include selector", "Smoke Selector v1" in completed, completed)
    assert_true("completed names exclude cleanup", "Cleanup Strategy Engine v1" not in completed, completed)

    filtered = filter_completed_moves([
        "Operator Plan Quality v2",
        "Smoke Selector v1",
        "Cleanup Strategy Engine v1",
    ])

    assert_true("filtered active keeps cleanup", filtered["active_moves"] == ["Cleanup Strategy Engine v1"], filtered)
    assert_true("filtered completed has two", len(filtered["completed_moves"]) >= 2, filtered)
    assert_true("filtered reason", "already-locked" in filtered["reason"], filtered)

    all_done = filter_completed_moves([
        "Operator Plan Quality v2",
        "Smoke Selector v1",
    ])

    assert_true("all done uses fallback", all_done["active_moves"] == ["Cleanup Strategy Engine v1"], all_done)

    print("")
    print("NOVA PROJECT BRAIN COMPLETED MOVE FILTER SMOKE PASSED")


if __name__ == "__main__":
    main()
