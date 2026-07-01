from nova_backend.services.project_brain_mission_control import (
    build_project_brain_mission_card,
    build_project_brain_mission_control_answer,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def run_case(name, user_text, pasted_output, expected_intent, expected_terms):
    print("")
    print(f"CASE: {name}")

    card = build_project_brain_mission_card(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    answer = build_project_brain_mission_control_answer(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    lower = answer.lower()

    print(answer)

    assert_true(f"{name} intent", card.intent == expected_intent, card.intent)
    assert_true(f"{name} has current state", bool(card.current_state), card)
    assert_true(f"{name} has blocker/risk", bool(card.current_blocker), card)
    assert_true(f"{name} has recommended move", bool(card.recommended_move), card)
    assert_true(f"{name} has focused smoke", bool(card.focused_smoke), card)
    assert_true(f"{name} has validation", bool(card.validation), card)
    assert_true(f"{name} has avoid rules", bool(card.avoid), card)
    assert_true(f"{name} has commit rule", "do not commit" in card.commit_rule.lower(), card.commit_rule)

    for term in expected_terms:
        assert_true(
            f"{name} includes {term}",
            term.lower() in lower,
            answer,
        )

    assert_true(f"{name} formatted title", "project brain mission control" in lower, answer)
    assert_true(f"{name} formatted intent", "intent:" in lower, answer)
    assert_true(f"{name} formatted risk", "risk:" in lower, answer)
    assert_true(f"{name} formatted focused smoke", "focused smoke:" in lower, answer)
    assert_true(f"{name} formatted avoid", "avoid:" in lower, answer)
    assert_true(f"{name} formatted commit rule", "commit rule:" in lower, answer)


def main():
    print("NOVA PROJECT BRAIN MISSION CONTROL SMOKE")
    print("========================================")

    run_case(
        name="explicit mission control",
        user_text="give me mission control",
        pasted_output="",
        expected_intent="mission_control",
        expected_terms=[
            "Decision Engine v1",
            "Project Brain Mission Control",
            "mission_control",
            "focused smoke",
            "do not commit",
        ],
    )

    run_case(
        name="next move mission",
        user_text="what should we do next?",
        pasted_output="",
        expected_intent="next_move_judgment",
        expected_terms=[
            "Decision Engine v1",
            "Project Brain routing",
            "next_move_judgment",
            "focused smoke",
            "do not commit",
        ],
    )

    run_case(
        name="failed smoke mission",
        user_text="why did this fail?",
        pasted_output="NOVA ANSWER QUALITY SMOKE FAILED missing expected signals",
        expected_intent="diagnose_failed_smoke",
        expected_terms=[
            "diagnose_failed_smoke",
            "failing",
            "focused smoke",
            "do not weaken the smoke",
        ],
    )

    run_case(
        name="app py risk mission",
        user_text="should we patch app.py or avoid route hooks?",
        pasted_output="",
        expected_intent="route_layer_risk",
        expected_terms=[
            "route_layer_risk",
            "app.py",
            "guard-stack audit",
            "do not add another late hook",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN MISSION CONTROL SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
