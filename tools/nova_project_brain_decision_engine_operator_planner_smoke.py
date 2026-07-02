from nova_backend.services.project_brain_decision_engine import (
    decide_project_brain_next_move,
    format_project_brain_decision,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN DECISION ENGINE OPERATOR PLANNER SMOKE")
    print("=========================================================")

    decision = decide_project_brain_next_move("what should we do next")

    assert_true("decision intent preserved", decision.intent == "next_move_judgment", decision)
    assert_true("decision has operator planner layer", "operator planner" in decision.target_layers, decision)
    assert_true("decision has smoke selector layer", "smoke selector" in decision.target_layers, decision)
    assert_true("decision has cleanup strategy layer", "cleanup strategy" in decision.target_layers, decision)
    assert_true(
        "decision has operator planner file",
        "nova_backend/services/project_brain_operator_planner.py" in decision.target_files,
        decision.target_files,
    )
    assert_true(
        "decision has exact next command in validation",
        any("nova_project_brain_operator_planner_smoke.py" in item for item in decision.validation),
        decision.validation,
    )
    assert_true(
        "decision has operator loop guard",
        any("Operator loop guard:" in item for item in decision.avoid),
        decision.avoid,
    )
    assert_true(
        "decision recommended move mentions operator planner",
        "Operator Planner v2 recommends:" in decision.recommended_next_move,
        decision.recommended_next_move,
    )
    assert_true("decision rationale has ranked moves", "Ranked moves:" in decision.rationale, decision.rationale)
    assert_true("decision rationale has rejected moves", "Rejected moves:" in decision.rationale, decision.rationale)
    assert_true("decision rationale has exact next command", "Exact next command:" in decision.rationale, decision.rationale)
    assert_true("decision rationale has smoke selector reason", "Smoke Selector reason:" in decision.rationale, decision.rationale)

    rendered = format_project_brain_decision(decision)

    assert_true("rendered has intent", "Intent: next_move_judgment" in rendered, rendered)
    assert_true("rendered has operator planner", "operator planner" in rendered, rendered)
    assert_true("rendered has loop guard", "Operator loop guard:" in rendered, rendered)
    assert_true("rendered has ranked moves", "Ranked moves:" in rendered, rendered)

    failure = decide_project_brain_next_move("regression failed with traceback")
    assert_true("failure intent", failure.intent in {"failure_analysis", "code_change_request", "next_move_judgment", "general_project_answer"}, failure)
    assert_true(
        "failure gets failure interpreter smoke",
        any("failure_interpreter" in item.lower() for item in failure.validation),
        failure.validation,
    )

    print("")
    print("NOVA PROJECT BRAIN DECISION ENGINE OPERATOR PLANNER SMOKE PASSED")


if __name__ == "__main__":
    main()

