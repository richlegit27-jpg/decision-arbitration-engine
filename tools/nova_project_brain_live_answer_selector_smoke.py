from nova_backend.services.project_brain_live_answer_selector import (
    build_project_brain_live_answer,
    should_use_project_brain_decision_context,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def check_selector(name, user_text, pasted_output, expected_use, expected_reason_terms):
    print("")
    print("SELECTOR CASE:", name)

    use_decision, reason = should_use_project_brain_decision_context(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    print("USE_DECISION:", use_decision)
    print("REASON:", reason)

    assert_true(f"{name} use decision", use_decision == expected_use, reason)

    reason_lower = reason.lower()
    for term in expected_reason_terms:
        assert_true(
            f"{name} reason includes {term}",
            term.lower() in reason_lower,
            reason,
        )


def check_answer(name, user_text, pasted_output, expected_route, expected_terms, blocked_terms=None):
    print("")
    print("ANSWER CASE:", name)

    answer = build_project_brain_live_answer(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    text = answer.text
    lower = text.lower()

    print("ROUTE:", answer.route)
    print("SOURCE:", answer.source)
    print("USED_DECISION_ENGINE:", answer.used_decision_engine)
    print("REASON:", answer.reason)
    print("ANSWER:", text[:1200])

    assert_true(f"{name} text exists", bool(text.strip()))
    assert_true(f"{name} route", answer.route == expected_route, answer.route)

    for term in expected_terms:
        assert_true(
            f"{name} includes {term}",
            term.lower() in lower,
            text,
        )

    for term in blocked_terms or []:
        assert_true(
            f"{name} avoids {term}",
            term.lower() not in lower,
            text,
        )


def main():
    print("NOVA PROJECT BRAIN LIVE ANSWER SELECTOR SMOKE")
    print("=============================================")

    check_selector(
        name="plain status stays freshness",
        user_text="where are we at?",
        pasted_output="",
        expected_use=False,
        expected_reason_terms=["plain"],
    )

    check_selector(
        name="next move uses decision",
        user_text="what should we do next?",
        pasted_output="",
        expected_use=True,
        expected_reason_terms=["next"],
    )

    check_selector(
        name="failure uses decision",
        user_text="what does this failure mean?",
        pasted_output="AssertionError: route FAILED",
        expected_use=True,
        expected_reason_terms=["failure"],
    )

    check_selector(
        name="app py risk uses decision",
        user_text="should we patch app.py or make a service?",
        pasted_output="before_request route wrapper",
        expected_use=True,
        expected_reason_terms=["safety"],
    )

    check_answer(
        name="plain project answer",
        user_text="where are we at?",
        pasted_output="",
        expected_route="project_brain_freshness_context",
        expected_terms=[
            "current nova project state",
            "project brain",
            "freshness snapshot",
        ],
        blocked_terms=[
            "project brain decision context",
            "intent:",
        ],
    )

    check_answer(
        name="next move decision answer",
        user_text="what should we do next?",
        pasted_output="",
        expected_route="project_brain_decision_context",
        expected_terms=[
            "project brain decision context",
            "intent: next_move_judgment",
            "risk:",
            "validation:",
            "avoid:",
        ],
    )

    check_answer(
        name="failed smoke decision answer",
        user_text="what does this failure mean?",
        pasted_output="AssertionError: safe move term FAILED",
        expected_route="project_brain_decision_context",
        expected_terms=[
            "intent: diagnose_failed_smoke",
            "failing assertion",
            "focused smoke",
            "do not weaken the smoke",
        ],
    )

    check_answer(
        name="app py risk decision answer",
        user_text="should we patch app.py or test first?",
        pasted_output="before_request wrapper route",
        expected_route="project_brain_decision_context",
        expected_terms=[
            "intent: route_layer_risk",
            "service-layer extraction",
            "guard-stack audit",
            "do not add another late hook",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN LIVE ANSWER SELECTOR SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
