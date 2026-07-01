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
