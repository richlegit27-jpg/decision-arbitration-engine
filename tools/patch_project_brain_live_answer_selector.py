from pathlib import Path

service_path = Path("nova_backend/services/project_brain_live_answer_selector.py")
smoke_path = Path("tools/nova_project_brain_live_answer_selector_smoke.py")

service_code = r'''
"""Project Brain Live Answer Selector.

Service-only selector for choosing the best Project Brain answer style.

No Flask dependency.
No app.py wiring.
No runtime mutation.

Phase 3 goal:
- Decision-style questions use Decision Engine context.
- Plain project status questions use freshness/context builder answer.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ProjectBrainLiveAnswer:
    text: str
    route: str
    source: str
    used_decision_engine: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _clean(value).lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text for term in terms)


def should_use_project_brain_decision_context(user_text: str = "", pasted_output: str = "") -> tuple[bool, str]:
    """Decide whether a Project Brain answer should use the Decision Engine context."""

    user = _lower(user_text)
    output = _lower(pasted_output)
    combined = f"{user}\n{output}"

    if _contains_any(combined, [
        "traceback",
        "assertionerror",
        "smoke failed",
        "failed missing=",
        "failed bad=",
        "why did this fail",
        "what does this failure mean",
        "error and paste",
    ]):
        return True, "failure_or_log_diagnosis"

    if _contains_any(combined, [
        "should we patch",
        "should we test",
        "test first",
        "safe to code",
        "safest next move",
        "before touching code",
        "what test should we run",
    ]):
        return True, "safety_or_validation_judgment"

    if _contains_any(combined, [
        "app.py dangerous",
        "touch app.py",
        "patch app.py",
        "another guard",
        "late hook",
        "before_request",
        "after_request",
        "route stealing",
        "wrapper",
    ]):
        return True, "route_layer_risk"

    if _contains_any(combined, [
        "stale memory",
        "old memory",
        "memory hijacking",
        "source of truth",
        "data/nova_memory.json",
        "data/nova_sessions.json",
    ]):
        return True, "memory_freshness_judgment"

    if _contains_any(combined, [
        "make nova smarter",
        "decision engine",
        "intelligence",
        "smarter",
        "judgment layer",
    ]):
        return True, "intelligence_upgrade"

    if _contains_any(user, [
        "what should we do next",
        "what's next",
        "next concrete move",
        "next move",
        "what now",
    ]):
        return True, "next_move_judgment"

    return False, "plain_project_context"


def build_project_brain_live_answer(user_text: str = "", pasted_output: str = "") -> ProjectBrainLiveAnswer:
    """Build the selected Project Brain answer without touching Flask or app.py."""

    use_decision, reason = should_use_project_brain_decision_context(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    if use_decision:
        try:
            from nova_backend.services.project_brain_context_builder import (
                build_project_brain_decision_context_answer,
            )

            text = build_project_brain_decision_context_answer(
                user_text=user_text,
                pasted_output=pasted_output,
            )

            return ProjectBrainLiveAnswer(
                text=text,
                route="project_brain_decision_context",
                source="project_brain_context_builder.build_project_brain_decision_context_answer",
                used_decision_engine=True,
                reason=reason,
            )
        except Exception as exc:
            return ProjectBrainLiveAnswer(
                text=(
                    "Project Brain decision context unavailable. "
                    f"Reason: {type(exc).__name__}: {exc}"
                ),
                route="project_brain_decision_context_error",
                source="project_brain_live_answer_selector",
                used_decision_engine=True,
                reason=reason,
            )

    try:
        from nova_backend.services.project_brain_context_builder import (
            build_current_project_answer,
        )

        text = build_current_project_answer()

        return ProjectBrainLiveAnswer(
            text=text,
            route="project_brain_freshness_context",
            source="project_brain_context_builder.build_current_project_answer",
            used_decision_engine=False,
            reason=reason,
        )
    except Exception as exc:
        return ProjectBrainLiveAnswer(
            text=(
                "Current Nova project state is unavailable from the context builder. "
                f"Reason: {type(exc).__name__}: {exc}"
            ),
            route="project_brain_freshness_context_error",
            source="project_brain_live_answer_selector",
            used_decision_engine=False,
            reason=reason,
        )
'''

smoke_code = r'''
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
            "intent:",
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
'''

service_path.write_text(service_code.lstrip(), encoding="utf-8")
smoke_path.write_text(smoke_code.lstrip(), encoding="utf-8")

print(f"wrote {service_path}")
print(f"wrote {smoke_path}")
