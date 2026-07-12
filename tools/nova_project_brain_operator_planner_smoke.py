from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan,
    build_operator_plan_dict,
    classify_work_type,
    exact_next_command_for,
    format_operator_plan,
    rank_moves,
    select_smokes,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN OPERATOR PLANNER SMOKE")
    print("=========================================")

    assert_true(
        "classifies gangster next upgrade",
        classify_work_type("keep it gangster endgame this bitch") == "operator_planning",
    )

    assert_true(
        "classifies cleanup",
        classify_work_type("clean up app.py guards") == "cleanup_strategy",
    )

    assert_true(
        "classifies failure",
        classify_work_type("smoke failed with traceback") == "failure_repair",
    )

    assert_true(
        "classifies smoke selection",
        classify_work_type("which smoke should we run") == "smoke_selection",
    )

    from nova_backend.services.project_brain_smoke_selector import (
        select_focused_smokes as selector_select_focused_smokes,
    )

    app_smokes = select_smokes("route_cleanup", ["app.py"])
    assert_true(
        "planner delegates to smoke selector",
        app_smokes == selector_select_focused_smokes("route_cleanup", ["app.py"]),
        app_smokes,
    )
    assert_true(
        "route cleanup uses audit",
        "python .\\tools\\nova_finalizer_pipeline_audit.py" in app_smokes,
        app_smokes,
    )

    assert_true(
        "route cleanup uses regression",
        "python .\\tools\\nova_regression_smoke.py" in app_smokes,
        app_smokes,
    )


    plan = build_operator_plan("what is the next gangster upgrade")
    assert_true(
        "planner advances after completed field test",
        plan.recommended_move != "Nova Conversation Quality Field Test v1",
        plan,
    )
    assert_true(
        "planner risk is bounded",
        plan.risk in {"low", "medium"},
        plan,
    )
    assert_true(
        "planner has target files",
        bool(plan.ranked_moves)
        and bool(plan.target_files)
        and list(plan.target_files)
        == list(
            plan.ranked_moves[0].get(
                "target_files",
                [],
            )
            if isinstance(
                plan.ranked_moves[0],
                dict,
            )
            else getattr(
                plan.ranked_moves[0],
                "target_files",
                [],
            )
            or []
        ),
        plan,
    )
    assert_true(
        "planner has focused smoke",
        bool(plan.ranked_moves)
        and bool(plan.focused_smokes)
        and list(plan.focused_smokes)
        == list(
            plan.ranked_moves[0].get(
                "focused_smokes",
                [],
            )
            if isinstance(
                plan.ranked_moves[0],
                dict,
            )
            else getattr(
                plan.ranked_moves[0],
                "focused_smokes",
                [],
            )
            or []
        ),
        plan,
    )
    assert_true("planner blocks app.py guards", any("app.py route guards" in rule for rule in plan.avoid_rules), plan)
    assert_true(
        "planner exact next command",
        bool(plan.focused_smokes)
        and plan.exact_next_command
        == plan.focused_smokes[0],
        plan,
    )
    assert_true("planner loop guard", "already-passing lock" in plan.loop_guard, plan)
    assert_true("planner has ranked moves", len(plan.ranked_moves) == 4, plan)
    assert_true(
        "planner rank one skips completed moves",
        bool(plan.ranked_moves)
        and (
            plan.ranked_moves[0].get("name")
            if isinstance(plan.ranked_moves[0], dict)
            else getattr(plan.ranked_moves[0], "name", "")
        )
        == plan.recommended_move
        and plan.recommended_move
        != "Nova Conversation Quality Field Test v1",
        plan,
    )
    assert_true("planner has rejected moves", len(plan.rejected_moves) == 3, plan.rejected_moves)
    assert_true("planner rejected moves explain loss", all(move.get("loses_to_best_because") for move in plan.rejected_moves), plan.rejected_moves)

    cleanup_plan = build_operator_plan("extract app.py route guard")
    assert_true(
        "cleanup strategy recommended",
        cleanup_plan.recommended_move
        == "Cleanup Strategy Engine v1",
        cleanup_plan,
    )
    assert_true(
        "cleanup medium risk",
        cleanup_plan.risk == "medium",
        cleanup_plan,
    )
    assert_true("cleanup has one-family rule", any("one route/guard family" in rule for rule in cleanup_plan.avoid_rules), cleanup_plan)
    assert_true(
        "cleanup exact next command",
        bool(cleanup_plan.focused_smokes)
        and cleanup_plan.exact_next_command
        == cleanup_plan.focused_smokes[0],
        cleanup_plan,
    )

    failure_plan = build_operator_plan("regression failed")
    assert_true(
        "failure interpreter recommended",
        failure_plan.recommended_move
        == "Failure Interpreter v2",
        failure_plan,
    )
    assert_true(
        "failure reproduce rule",
        any(
            "failing contract is reproduced" in rule.lower()
            for rule in failure_plan.avoid_rules
        ),
        failure_plan,
    )
    assert_true(
        "failure exact next command",
        bool(failure_plan.focused_smokes)
        and failure_plan.exact_next_command
        == failure_plan.focused_smokes[0],
        failure_plan,
    )

    moves = rank_moves("operator_planning")
    assert_true("rank moves count", len(moves) == 4, moves)
    assert_true("rank moves first rank", moves[0]["rank"] == 1, moves)
    assert_true("rank moves first no loss reason", moves[0]["loses_to_best_because"] == "", moves)
    assert_true("rank moves lower explain loss", moves[1]["loses_to_best_because"], moves)

    assert_true(
        "exact next failure",
        exact_next_command_for("failure_repair") == "python .\\tools\\nova_project_brain_failure_interpreter_api_smoke.py",
    )

    data = build_operator_plan_dict("operator mode")
    assert_true(
        "dict has recommended move",
        data.get("recommended_move")
        == plan.recommended_move,
        data,
    )
    assert_true("dict has ranked moves", len(data.get("ranked_moves", [])) == 4, data)
    assert_true(
        "dict has exact next command",
        data.get("exact_next_command")
        == plan.exact_next_command,
        data,
    )

    card = format_operator_plan(plan)
    assert_true("card title", "Project Brain Operator Plan:" in card, card)
    assert_true(
        "card recommended move",
        f"Recommended move: {plan.recommended_move}"
        in card,
        card,
    )
    assert_true(
        "card exact next command",
        (
            "Exact next command: "
            +
            plan.exact_next_command
        )
        in card,
        card,
    )
    assert_true("card ranked moves", "Ranked moves:" in card, card)
    assert_true("card rejected moves", "Rejected moves:" in card, card)
    assert_true("card stop rule", "Stop rule:" in card, card)
    assert_true("card loop guard", "Loop guard:" in card, card)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR PLANNER SMOKE PASSED")


if __name__ == "__main__":
    main()


