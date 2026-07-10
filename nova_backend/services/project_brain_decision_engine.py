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


def _decide_project_brain_next_move_base(user_text: str = "", pasted_output: str = "") -> ProjectBrainDecision:
    """Return a structured next-step decision for Nova project work."""

    user = _lower(user_text)
    output = _lower(pasted_output)
    combined = f"{user}\n{output}"

    if _contains_any(combined, [
        "mission control",
        "mission card",
        "operator mode",
        "operator card",
        "mission brief",
        "mission plan",
        "give me mission",
        "show mission",
        "show me the mission",
    ]):
        return ProjectBrainDecision(
            intent="mission_control",
            confidence=0.93,
            risk="low",
            recommended_next_move=(
                "Use Project Brain Mission Control as the operator card: summarize current state, "
                "classify the request, choose the focused smoke, list target files, and preserve "
                "avoid-rules before any commit."
            ),
            target_layers=[
                "mission control service",
                "general intelligence bridge",
                "api contract smoke",
            ],
            target_files=[
                "nova_backend/services/project_brain_mission_control.py",
                "nova_backend/services/project_brain_general_intelligence.py",
                "tools/nova_project_brain_mission_control_smoke.py",
                "tools/nova_project_brain_mission_control_general_smoke.py",
                "tools/nova_project_brain_mission_control_api_smoke.py",
            ],
            validation=_base_validation() + [
                "python .\\tools\\nova_project_brain_mission_control_smoke.py",
                "python .\\tools\\nova_project_brain_mission_control_general_smoke.py",
                "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
                "python .\\tools\\nova_regression_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not route explicit operator requests to general_project_answer",
                "do not add app.py wiring for Mission Control",
            ],
            rationale=(
                "Explicit operator requests should return the Mission Control card itself, not the "
                "generic Project Brain answer intent."
            ),
        )

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
        "what should we do next",
        "what's next",
        "next concrete move",
        "next move",
        "what now",
        "what should we do",
    ]):
        return ProjectBrainDecision(
            intent="next_move_judgment",
            confidence=0.88,
            risk="medium",
            recommended_next_move=(
                "Use the Project Brain live answer selector as the decision gate: plain status stays "
                "on freshness context, while next-move, safety, failure, memory, and app.py risk "
                "questions use Decision Engine context."
            ),
            target_layers=[
                "live answer selector",
                "decision context",
                "decision engine",
                "smoke board",
            ],
            target_files=[
                "nova_backend/services/project_brain_live_answer_selector.py",
                "nova_backend/services/project_brain_context_builder.py",
                "nova_backend/services/project_brain_decision_engine.py",
                "tools/nova_project_brain_live_answer_selector_smoke.py",
            ],
            validation=_base_validation() + [
                "python .\\tools\\nova_project_brain_live_answer_selector_smoke.py",
                "python .\\tools\\nova_project_brain_decision_context_smoke.py",
                "python .\\tools\\nova_project_brain_decision_engine_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not wire app.py until the selector intent is precise",
                "do not classify ordinary next-move questions as intelligence upgrades",
            ],
            rationale=(
                "Next-move questions should use judgment about current project state and validation, "
                "not be mistaken for a meta request to improve Nova intelligence."
            ),
        )

    if _contains_any(combined, [
        "make nova smarter",
        "decision engine",
        "intelligence",
        "smarter",
        "judgment",
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



def _unique_text(values):
    result = []
    seen = set()

    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return result


def _build_decision_smoke_selection(
    decision: ProjectBrainDecision,
    user_text: str = "",
) -> dict:
    try:
        from nova_backend.services.project_brain_smoke_selector import (
            build_smoke_selection_dict,
        )

        return build_smoke_selection_dict(
            user_text=user_text,
            changed_files=list(decision.target_files),
            work_type=decision.intent,
        )
    except Exception:
        return {}


def _apply_operator_plan_to_decision(
    decision: ProjectBrainDecision,
    user_text: str = "",
) -> ProjectBrainDecision:
    try:
        from nova_backend.services.project_brain_operator_planner import (
            build_operator_plan_dict,
        )

        operator_plan = build_operator_plan_dict(
            user_text=user_text,
            changed_files=list(decision.target_files),
            project_state=decision.recommended_next_move,
        )
    except Exception:
        return decision

    smoke_selection = _build_decision_smoke_selection(
        decision=decision,
        user_text=user_text,
    )

    recommended_move = str(operator_plan.get("recommended_move") or "").strip()
    operator_why = str(operator_plan.get("why") or "").strip()
    exact_next_command = str(operator_plan.get("exact_next_command") or "").strip()
    loop_guard = str(operator_plan.get("loop_guard") or "").strip()
    smoke_reason = str(smoke_selection.get("reason") or "").strip()

    ranked_moves = operator_plan.get("ranked_moves", []) or []
    rejected_moves = operator_plan.get("rejected_moves", []) or []

    ranked_summary = "; ".join(
        f"#{move.get('rank')}: {move.get('name')}"
        for move in ranked_moves
        if move.get("name")
    )

    rejected_summary = "; ".join(
        f"{move.get('name')} loses because {move.get('loses_to_best_because')}"
        for move in rejected_moves
        if move.get("name")
    )

    next_move = decision.recommended_next_move
    if recommended_move and recommended_move not in next_move:
        next_move = (
            f"{next_move} Operator Planner v2 recommends: "
            f"{recommended_move} - {operator_why}"
        ).strip()

    validation = _unique_text(
        list(decision.validation)
        + list(smoke_selection.get("focused_smokes", []) or [])
        + list(operator_plan.get("focused_smokes", []) or [])
        + ([exact_next_command] if exact_next_command else [])
    )

    avoid = _unique_text(
        list(decision.avoid)
        + list(operator_plan.get("avoid_rules", []) or [])
        + ([f"Operator loop guard: {loop_guard}"] if loop_guard else [])
    )

    target_layers = _unique_text(
        list(decision.target_layers)
        + [
            "operator planner",
            "smoke selector",
            "cleanup strategy",
        ]
    )

    target_files = _unique_text(
        list(decision.target_files)
        + list(operator_plan.get("target_files", []) or [])
    )

    rationale_parts = [
        decision.rationale,
        f"Operator Planner v2 selected {recommended_move}." if recommended_move else "",
        f"Exact next command: {exact_next_command}" if exact_next_command else "",
        f"Smoke Selector reason: {smoke_reason}" if smoke_reason else "",
        f"Ranked moves: {ranked_summary}" if ranked_summary else "",
        f"Rejected moves: {rejected_summary}" if rejected_summary else "",
        f"Loop guard: {loop_guard}" if loop_guard else "",
    ]

    rationale = " ".join(part for part in rationale_parts if part).strip()

    return ProjectBrainDecision(
        intent=decision.intent,
        confidence=decision.confidence,
        risk=decision.risk,
        recommended_next_move=next_move,
        target_layers=target_layers,
        target_files=target_files,
        validation=validation,
        avoid=avoid,
        rationale=rationale,
    )

def _apply_behavior_improvement_signal(
    decision: ProjectBrainDecision,
) -> ProjectBrainDecision:
    """
    Adds Nova learning awareness to low-risk decisions.

    Does not override:
    - failures
    - safety decisions
    - route risks
    - explicit operator requests
    """

    if decision.risk != "low":
        return decision


    try:

        from nova_backend.services.nova_behavior_memory import (
            behavior_memory,
        )


        priority = (
            behavior_memory
            .create_improvement_priority()
        )


        focus = priority.get(
            "focus",
            ""
        )


        if (
            not focus
            or focus == "collect_behavior_data"
        ):
            return decision


        rationale = (
            decision.rationale
            + " "
            + (
                "Behavior learning signal: "
                f"current improvement focus is {focus}."
            )
        )


        return ProjectBrainDecision(
            intent=decision.intent,
            confidence=decision.confidence,
            risk=decision.risk,
            recommended_next_move=decision.recommended_next_move,
            target_layers=decision.target_layers,
            target_files=decision.target_files,
            validation=decision.validation,
            avoid=decision.avoid,
            rationale=rationale,
        )


    except Exception as exc:

        print(
            "[NOVA_BEHAVIOR_DECISION_SIGNAL_FAILED]",
            exc,
        )

        return decision

def decide_project_brain_next_move(
    user_text: str = "",
    pasted_output: str = "",
) -> ProjectBrainDecision:
    decision = _decide_project_brain_next_move_base(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    decision = _apply_operator_plan_to_decision(
        decision,
        user_text=user_text,
    )

    return _apply_behavior_improvement_signal(
        decision
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
