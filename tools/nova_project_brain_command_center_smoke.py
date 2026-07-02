from nova_backend.services.project_brain_command_center import (
    build_project_brain_command_center_answer,
    build_project_brain_command_center_card,
    build_project_brain_command_center_dict,
    classify_command_center_intent,
    format_project_brain_command_center,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN COMMAND CENTER SMOKE")
    print("=======================================")

    assert_true("classifies recent changes", classify_command_center_intent("what changed recently") == "recent_changes")
    assert_true("classifies failure", classify_command_center_intent("regression failed with traceback") == "failure")
    assert_true("classifies smoke selection", classify_command_center_intent("what smoke should we run") == "smoke_selection")
    assert_true("classifies operator", classify_command_center_intent("operator mode") == "operator_mode")
    assert_true("classifies next", classify_command_center_intent("next gangster upgrade") == "next_move")
    assert_true("classifies status", classify_command_center_intent("current blocker") == "status")

    card = build_project_brain_command_center_card("operator mode")

    assert_true("card intent", card.command_intent == "operator_mode", card)
    assert_true("card status", bool(card.status), card)
    assert_true("card blocker", bool(card.blocker), card)
    assert_true("card best move", bool(card.best_move), card)
    assert_true("card why", bool(card.why), card)
    assert_true("card risk", bool(card.risk), card)
    assert_true("card exact next command", bool(card.exact_next_command), card)
    assert_true("card focused smokes", bool(card.focused_smokes), card)
    assert_true("card stop rule", bool(card.stop_rule), card)
    assert_true("card loop guard", bool(card.loop_guard), card)
    assert_true("card recent changes", "Recent Decision Log:" in card.recent_changes, card.recent_changes)
    assert_true("card smoke reason", bool(card.smoke_reason), card)
    assert_true("card target files", bool(card.target_files), card)
    assert_true("card avoid rules", bool(card.avoid_rules), card)

    data = build_project_brain_command_center_dict("what smoke should we run")
    assert_true("dict intent", data.get("command_intent") == "smoke_selection", data)
    assert_true("dict has focused smokes", bool(data.get("focused_smokes")), data)

    formatted = format_project_brain_command_center(card)
    assert_true("formatted title", "Project Brain Command Center:" in formatted, formatted)
    assert_true("formatted command intent", "Command intent:" in formatted, formatted)
    assert_true("formatted status", "Status:" in formatted, formatted)
    assert_true("formatted best move", "Best Move:" in formatted, formatted)
    assert_true("formatted exact next command", "Exact Next Command:" in formatted, formatted)
    assert_true("formatted focused smokes", "Focused Smokes:" in formatted, formatted)
    assert_true("formatted smoke selector reason", "Smoke Selector Reason:" in formatted, formatted)
    assert_true("formatted stop rule", "Stop Rule:" in formatted, formatted)
    assert_true("formatted loop guard", "Loop Guard:" in formatted, formatted)
    assert_true("formatted recent changes", "Recent Changes:" in formatted, formatted)

    answer = build_project_brain_command_center_answer("next gangster upgrade")
    assert_true("answer title", "Project Brain Command Center:" in answer, answer)
    assert_true("answer intent next", "Command intent: next_move" in answer, answer)
    assert_true("answer has exact command", "Exact Next Command:" in answer, answer)

    print("")
    print("NOVA PROJECT BRAIN COMMAND CENTER SMOKE PASSED")


if __name__ == "__main__":
    main()
