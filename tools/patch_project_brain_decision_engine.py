from pathlib import Path

service_path = Path("nova_backend/services/project_brain_decision_engine.py")
smoke_path = Path("tools/nova_project_brain_decision_engine_smoke.py")

service_code = r'''
"""Project Brain Decision Engine.

Service-only intelligence layer.
It does not call Flask, mutate runtime data, or patch app.py.

Goal:
Given a user request or pasted output, decide:
- what kind of situation this is
- what Nova should do next
- what files/layers are likely involved
- what validation should run
- what to avoid
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ProjectBrainDecision:
    intent: str
    confidence: float
    risk: str
    recommended_next_move: str
    target_layers: list[str]
    target_files: list[str]
    validation: list[str]
    avoid: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _clean(value).lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _base_validation() -> list[str]:
    return [
        "git status --short",
        "python -m py_compile <changed python files>",
        "run the smallest focused smoke first",
    ]


def _project_brain_validation() -> list[str]:
    return [
        "python .\\tools\\nova_project_brain_freshness_snapshot_smoke.py",
        "python .\\tools\\nova_answer_quality_smoke.py",
        "python .\\tools\\nova_project_state_direct_freshness_smoke.py",
        "python .\\tools\\nova_phase_4i_guard_stack_audit_smoke.py",
    ]


def _default_avoid() -> list[str]:
    return [
        "do not add a blind app.py guard",
        "do not commit before the focused smoke passes",
        "do not use stale data/nova_sessions.json as source of truth",
        "do not force-add ignored runtime memory unless explicitly required",
    ]


def decide_project_brain_next_move(user_text: str = "", pasted_output: str = "") -> ProjectBrainDecision:
    """Return a structured next-step decision for Nova project work."""

    user = _lower(user_text)
    output = _lower(pasted_output)
    combined = f"{user}\n{output}"

    if _contains_any(combined, [
        "traceback",
        "assertionerror",
        "smoke failed",
        "failed missing=",
        "failed bad=",
        "nova answer quality smoke failed",
    ]):
        return ProjectBrainDecision(
            intent="diagnose_failed_smoke",
            confidence=0.92,
            risk="medium",
            recommended_next_move=(
                "Treat the failure as a product or test-contract signal. Identify the exact failing "
                "assertion, patch the narrow source layer, then rerun the focused smoke before any commit."
            ),
            target_layers=[
                "focused smoke",
                "source service",
                "runtime route only if the service cannot win",
            ],
            target_files=[
                "tools/<failing_smoke>.py",
                "nova_backend/services/<related_service>.py",
                "app.py only if locator proves an existing route is stealing priority",
            ],
            validation=_base_validation() + _project_brain_validation(),
            avoid=_default_avoid() + [
                "do not weaken the smoke just to pass",
                "do not patch historical nova_backups hits",
            ],
            rationale=(
                "A failing smoke is useful only if it points to a real contract. First preserve the "
                "failure, then patch the source that violates the contract."
            ),
        )

    if _contains_any(combined, [
        "git status --short",
        "nothing to commit",
        "working tree clean",
        "commit",
        "committed",
    ]):
        return ProjectBrainDecision(
            intent="checkpoint_or_commit_review",
            confidence=0.86,
            risk="low",
            recommended_next_move=(
                "Verify whether the last validation board was fully green. If yes, commit the focused "
                "scope. If not, treat the commit as a checkpoint with known debt and patch on top."
            ),
            target_layers=[
                "git checkpoint",
                "smoke evidence",
            ],
            target_files=[
                "changed files from git status",
                "tools/<new_or_changed_smoke>.py",
            ],
            validation=[
                "git status --short",
                "review last failed smoke before committing",
                "rerun the focused smoke after commit if the server restarted",
            ],
            avoid=_default_avoid() + [
                "do not call a commit green if a smoke failed before it",
            ],
            rationale=(
                "A clean git tree is not the same as a clean validation state. Nova must separate "
                "repository state from product correctness."
            ),
        )

    if _contains_any(combined, [
        "app.py dangerous",
        "app.py",
        "guard",
        "before_request",
        "after_request",
        "wrapper",
        "route stealing",
    ]):
        return ProjectBrainDecision(
            intent="route_layer_risk",
            confidence=0.88,
            risk="high",
            recommended_next_move=(
                "Prefer service-layer extraction or source-service patching. Touch app.py only as a thin "
                "adapter or when a locator proves an existing app.py route is stealing priority."
            ),
            target_layers=[
                "service layer",
                "route adapter",
                "guard-stack audit",
            ],
            target_files=[
                "nova_backend/services/<new_or_existing_service>.py",
                "app.py only for existing thin wiring",
                "tools/nova_phase_4i_guard_stack_audit_smoke.py",
            ],
            validation=_base_validation() + [
                "python .\\tools\\nova_phase_4i_guard_stack_audit_smoke.py",
                "python .\\tools\\nova_project_brain_route_contract_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not add another late hook",
                "do not add duplicate NOVA markers",
            ],
            rationale=(
                "app.py already has many stacked hooks and wrappers. Intelligence should move upward "
                "into services, not deeper into route clutter."
            ),
        )

    if _contains_any(combined, [
        "stale memory",
        "old memory",
        "runtime memory",
        "data/nova_memory.json",
        "data/nova_sessions.json",
        "source of truth",
    ]):
        return ProjectBrainDecision(
            intent="memory_freshness_judgment",
            confidence=0.87,
            risk="medium",
            recommended_next_move=(
                "Treat structured Project Brain freshness snapshot as the source of truth. Runtime "
                "memory can inform answers, but stale memory must be sanitized or ignored."
            ),
            target_layers=[
                "freshness snapshot",
                "context builder",
                "memory ranking",
            ],
            target_files=[
                "nova_backend/services/project_brain_freshness_snapshot.py",
                "nova_backend/services/project_brain_context_builder.py",
                "data/nova_memory.json only as ignored runtime data",
            ],
            validation=_base_validation() + [
                "python .\\tools\\nova_project_brain_freshness_snapshot_smoke.py",
                "python .\\tools\\nova_project_answer_readability_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not make ignored runtime data the required repo fix",
            ],
            rationale=(
                "Stale memory is expected in a long-running assistant. The fix is durable ranking and "
                "sanitization, not pretending old memory will disappear."
            ),
        )

    if _contains_any(combined, [
        "make nova smarter",
        "decision engine",
        "intelligence",
        "smarter",
        "judgment",
        "what should we do",
        "next move",
    ]):
        return ProjectBrainDecision(
            intent="intelligence_upgrade",
            confidence=0.9,
            risk="medium",
            recommended_next_move=(
                "Add intelligence as a service-only decision layer first. It should classify intent, "
                "risk, target layer, validation, and avoid-rules with no app.py wiring until the service smoke is stable."
            ),
            target_layers=[
                "Project Brain service",
                "decision engine",
                "smoke contract",
            ],
            target_files=[
                "nova_backend/services/project_brain_decision_engine.py",
                "tools/nova_project_brain_decision_engine_smoke.py",
            ],
            validation=_base_validation() + [
                "python .\\tools\\nova_project_brain_decision_engine_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not wire into /api/chat until service smoke is stable",
            ],
            rationale=(
                "Nova gets smarter when it can choose the right action and validation path, not just "
                "return fresher project wording."
            ),
        )

    if _contains_any(combined, [
        "patch",
        "fix",
        "repair",
        "implement",
        "change code",
        "touch code",
    ]):
        return ProjectBrainDecision(
            intent="code_change_request",
            confidence=0.78,
            risk="medium",
            recommended_next_move=(
                "Locate the source first, patch the smallest service or tool file, compile changed "
                "files, then run the focused smoke before broader validation."
            ),
            target_layers=[
                "source locator",
                "service layer",
                "focused smoke",
            ],
            target_files=[
                "file proven by locator",
                "tools/<focused_smoke>.py",
            ],
            validation=_base_validation() + [
                "run focused smoke",
                "run route/answer-quality smoke if behavior changed",
            ],
            avoid=_default_avoid() + [
                "do not patch backups",
                "do not patch by string replacement unless locator proves the string source",
            ],
            rationale=(
                "A code-change request needs a locator-first workflow so Nova does not make broad or "
                "misplaced changes."
            ),
        )

    return ProjectBrainDecision(
        intent="general_project_answer",
        confidence=0.64,
        risk="low",
        recommended_next_move=(
            "Answer from Project Brain context. If the user wants action, convert the answer into a "
            "decision with target layer, validation, and avoid-rules."
        ),
        target_layers=[
            "Project Brain context",
            "answer layer",
        ],
        target_files=[
            "nova_backend/services/project_brain_context_builder.py",
            "nova_backend/services/project_brain_freshness_snapshot.py",
        ],
        validation=_base_validation(),
        avoid=_default_avoid(),
        rationale=(
            "No strong action signal was detected, so Nova should answer clearly without triggering "
            "planning, memory writes, or code execution."
        ),
    )


def format_project_brain_decision(decision: ProjectBrainDecision) -> str:
    """Human-readable compact rendering for Nova responses and smoke snapshots."""

    return (
        f"Intent: {decision.intent}\n"
        f"Confidence: {decision.confidence:.2f}\n"
        f"Risk: {decision.risk}\n"
        f"Recommended next move: {decision.recommended_next_move}\n"
        f"Target layers: {', '.join(decision.target_layers)}\n"
        f"Target files: {', '.join(decision.target_files)}\n"
        f"Validation: {'; '.join(decision.validation)}\n"
        f"Avoid: {'; '.join(decision.avoid)}\n"
        f"Rationale: {decision.rationale}"
    )
'''

smoke_code = r'''
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
            "save this memory",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN DECISION ENGINE SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
'''

service_path.write_text(service_code.lstrip(), encoding="utf-8")
smoke_path.write_text(smoke_code.lstrip(), encoding="utf-8")

print(f"wrote {service_path}")
print(f"wrote {smoke_path}")
