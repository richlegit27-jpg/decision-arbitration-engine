from nova_backend.services.project_brain_decision_engine import (
    decide_project_brain_next_move,
    format_project_brain_decision,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def check_case(name, user_text, pasted_output, expected_intent, expected_terms, avoided_terms=None):
    print("")
    print("CASE:", name)

    decision = decide_project_brain_next_move(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    rendered = format_project_brain_decision(decision)
    lower = rendered.lower()

    print(rendered)

    assert_true(
        f"{name} intent",
        decision.intent == expected_intent,
        f"expected={expected_intent} actual={decision.intent}",
    )

    for term in expected_terms:
        assert_true(
            f"{name} includes {term}",
            term.lower() in lower,
            rendered,
        )

    for term in avoided_terms or []:
        assert_true(
            f"{name} avoids {term}",
            term.lower() not in lower,
            rendered,
        )

    assert_true(f"{name} has validation", bool(decision.validation))
    assert_true(f"{name} has avoid rules", bool(decision.avoid))
    assert_true(f"{name} no blind app.py guard", "blind app.py guard" in lower)


def main():
    print("NOVA PROJECT BRAIN DECISION ENGINE SMOKE")
    print("========================================")

    check_case(
        name="failed smoke diagnosis",
        user_text="it failed",
        pasted_output="NOVA ANSWER QUALITY SMOKE FAILED missing=['safe move'] AssertionError",
        expected_intent="diagnose_failed_smoke",
        expected_terms=[
            "failing assertion",
            "focused smoke",
            "do not weaken the smoke",
        ],
    )

    check_case(
        name="route layer risk",
        user_text="app.py is dangerous and another guard might steal the route",
        pasted_output="before_request wrapper route app.py",
        expected_intent="route_layer_risk",
        expected_terms=[
            "service-layer extraction",
            "guard-stack audit",
            "late hook",
        ],
    )

    check_case(
        name="memory freshness",
        user_text="stale memory from data/nova_memory.json is hijacking the answer",
        pasted_output="data/nova_sessions.json old project state source of truth",
        expected_intent="memory_freshness_judgment",
        expected_terms=[
            "freshness snapshot",
            "source of truth",
            "ignored runtime data",
        ],
    )

    check_case(
        name="intelligence upgrade",
        user_text="make Nova smarter with a decision engine",
        pasted_output="",
        expected_intent="intelligence_upgrade",
        expected_terms=[
            "decision layer",
            "classify intent",
            "no app.py wiring",
        ],
    )

    check_case(
        name="code change request",
        user_text="patch the bug but do not touch app.py blindly",
        pasted_output="",
        expected_intent="route_layer_risk",
        expected_terms=[
            "service-layer",
            "app.py",
            "guard-stack",
        ],
    )

    check_case(
        name="general project answer",
        user_text="where are we at?",
        pasted_output="",
        expected_intent="general_project_answer",
        expected_terms=[
            "Project Brain context",
            "answer clearly",
        ],
        avoided_terms=[
            "execute all",
            "memory write",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN DECISION ENGINE SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
