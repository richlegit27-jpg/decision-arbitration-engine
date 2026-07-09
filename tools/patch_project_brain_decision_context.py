from pathlib import Path

context_path = Path("nova_backend/services/project_brain_context_builder.py")
smoke_path = Path("tools/nova_project_brain_decision_context_smoke.py")

context_text = context_path.read_text(encoding="utf-8")
marker = "# NOVA_PROJECT_BRAIN_DECISION_CONTEXT_BUILDER_20260702"

if marker not in context_text:
    patch = r'''

# NOVA_PROJECT_BRAIN_DECISION_CONTEXT_BUILDER_20260702
# Service-only bridge from Project Brain context builder to Decision Engine.
# No Flask wiring, no app.py dependency, no runtime mutation.
def build_project_brain_decision_context_answer(user_text="", pasted_output=""):
    """Build a compact Project Brain decision answer from the Decision Engine."""

    try:
        from nova_backend.services.project_brain_decision_engine import (
            decide_project_brain_next_move,
        )

        decision = decide_project_brain_next_move(
            user_text=user_text,
            pasted_output=pasted_output,
        )

        validation = "; ".join(decision.validation)
        avoid = "; ".join(decision.avoid)
        target_layers = ", ".join(decision.target_layers)
        target_files = ", ".join(decision.target_files)

        return (
            "Project Brain decision context:\n"
            f"Intent: {decision.intent}\n"
            f"Risk: {decision.risk}\n"
            f"Confidence: {decision.confidence:.2f}\n"
            f"Recommended next move: {decision.recommended_next_move}\n"
            f"Target layers: {target_layers}\n"
            f"Target files: {target_files}\n"
            f"Validation: {validation}\n"
            f"Avoid: {avoid}\n"
            f"Rationale: {decision.rationale}"
        )

    except Exception as exc:
        return (
            "Project Brain decision context unavailable. "
            f"Reason: {type(exc).__name__}: {exc}"
        )
'''
    context_path.write_text(context_text.rstrip() + "\n\n" + patch.lstrip(), encoding="utf-8")
    print(f"{context_path}: installed decision context bridge")
else:
    print(f"{context_path}: decision context bridge already installed")

smoke_code = r'''
from nova_backend.services.project_brain_context_builder import (
    build_project_brain_decision_context_answer,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def check_case(name, user_text, pasted_output, expected_terms, blocked_terms=None):
    print("")
    print("CASE:", name)

    answer = build_project_brain_decision_context_answer(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    lower = answer.lower()

    print(answer)

    assert_true(f"{name} answer exists", bool(answer.strip()))
    assert_true(f"{name} decision context", "project brain decision context" in lower)

    for term in expected_terms:
        assert_true(
            f"{name} includes {term}",
            term.lower() in lower,
            answer,
        )

    for term in blocked_terms or []:
        assert_true(
            f"{name} avoids {term}",
            term.lower() not in lower,
            answer,
        )


def main():
    print("NOVA PROJECT BRAIN DECISION CONTEXT SMOKE")
    print("=========================================")

    check_case(
        name="failed smoke context",
        user_text="this failed",
        pasted_output="AssertionError: safe move term FAILED",
        expected_terms=[
            "intent: diagnose_failed_smoke",
            "failing assertion",
            "focused smoke",
            "do not weaken the smoke",
        ],
    )

    check_case(
        name="route risk context",
        user_text="should we patch app.py or move this into a service layer?",
        pasted_output="before_request wrapper route priority",
        expected_terms=[
            "intent: route_layer_risk",
            "service-layer extraction",
            "guard-stack audit",
            "do not add another late hook",
        ],
    )

    check_case(
        name="memory freshness context",
        user_text="stale memory is hijacking the answer",
        pasted_output="data/nova_memory.json data/nova_sessions.json source of truth",
        expected_terms=[
            "intent: memory_freshness_judgment",
            "freshness snapshot",
            "source of truth",
            "ignored runtime data",
        ],
    )

    check_case(
        name="intelligence upgrade context",
        user_text="make Nova smarter with the decision engine",
        pasted_output="",
        expected_terms=[
            "intent: intelligence_upgrade",
            "decision layer",
            "classify intent",
            "no app.py wiring",
        ],
    )

    check_case(
        name="general context",
        user_text="where are we at?",
        pasted_output="",
        expected_terms=[
            "intent: general_project_answer",
            "project brain context",
            "answer clearly",
        ],
        blocked_terms=[
            "execute all",
            "save this memory",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN DECISION CONTEXT SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
'''

smoke_path.write_text(smoke_code.lstrip(), encoding="utf-8")
print(f"{smoke_path}: wrote decision context smoke")
