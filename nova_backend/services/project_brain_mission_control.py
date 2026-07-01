from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ProjectBrainMissionCard:
    current_state: str
    current_blocker: str
    intent: str
    confidence: float
    risk: str
    recommended_move: str
    target_layers: list[str]
    target_files: list[str]
    focused_smoke: str
    validation: list[str]
    avoid: list[str]
    commit_rule: str
    rationale: str
    failure_type: str
    failure_severity: str
    failure_patch_target: str
    failure_next_command: str
    failure_evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first_focused_smoke(validation: list[str]) -> str:
    for command in validation:
        text = str(command or "").strip()
        lower = text.lower()
        if text.startswith("python .\\tools\\") and "smoke" in lower:
            return text

    for command in validation:
        text = str(command or "").strip()
        if "focused smoke" in text.lower():
            return text

    return "run the smallest focused smoke first"


def build_project_brain_mission_card(
    user_text: str = "",
    pasted_output: str = "",
) -> ProjectBrainMissionCard:
    from nova_backend.services.project_brain_decision_engine import (
        decide_project_brain_next_move,
    )
    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )
    from nova_backend.services.project_brain_failure_interpreter import (
        interpret_project_brain_failure,
    )

    snapshot = build_project_brain_freshness_snapshot()
    decision = decide_project_brain_next_move(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    failure = interpret_project_brain_failure(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    return ProjectBrainMissionCard(
        current_state=str(snapshot.checkpoint or "").strip(),
        current_blocker=str(snapshot.blocker or "").strip(),
        intent=decision.intent,
        confidence=decision.confidence,
        risk=decision.risk,
        recommended_move=decision.recommended_next_move,
        target_layers=list(decision.target_layers),
        target_files=list(decision.target_files),
        focused_smoke=_first_focused_smoke(list(decision.validation)),
        validation=list(decision.validation),
        avoid=list(decision.avoid),
        commit_rule="Do not commit until py_compile and the focused smoke pass; then check git status --short.",
        rationale=decision.rationale,
        failure_type=failure.failure_type,
        failure_severity=failure.severity,
        failure_patch_target=failure.patch_target,
        failure_next_command=failure.next_command,
        failure_evidence=list(failure.evidence),
    )


def format_project_brain_mission_card(card: ProjectBrainMissionCard) -> str:
    target_layers = ", ".join(card.target_layers)
    target_files = ", ".join(card.target_files)
    avoid = "; ".join(card.avoid)
    failure_evidence = "; ".join(card.failure_evidence) if card.failure_evidence else "none"

    return (
        "Project Brain Mission Control:\n"
        f"Current state: {card.current_state}\n"
        f"Current blocker/risk: {card.current_blocker}\n"
        f"Intent: {card.intent}\n"
        f"Risk: {card.risk}\n"
        f"Confidence: {card.confidence:.2f}\n"
        f"Recommended move: {card.recommended_move}\n"
        f"Target layers: {target_layers}\n"
        f"Target files: {target_files}\n"
        f"Focused smoke: {card.focused_smoke}\n"
        f"Validation: {'; '.join(card.validation)}\n"
        f"Avoid: {avoid}\n"
        f"Commit rule: {card.commit_rule}\n"
        f"Failure type: {card.failure_type}\n"
        f"Failure severity: {card.failure_severity}\n"
        f"Failure patch target: {card.failure_patch_target}\n"
        f"Failure next command: {card.failure_next_command}\n"
        f"Failure evidence: {failure_evidence}\n"
        f"Rationale: {card.rationale}"
    )


def build_project_brain_mission_control_answer(
    user_text: str = "",
    pasted_output: str = "",
) -> str:
    card = build_project_brain_mission_card(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    return format_project_brain_mission_card(card)
