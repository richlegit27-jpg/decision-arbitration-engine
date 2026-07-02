from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProjectBrainCommandCenterCard:
    command_intent: str
    status: str
    blocker: str
    best_move: str
    why: str
    risk: str
    exact_next_command: str
    focused_smokes: list[str]
    stop_rule: str
    loop_guard: str
    recent_changes: str
    failure_type: str
    failure_severity: str
    failure_patch_target: str
    failure_next_command: str
    smoke_reason: str
    target_files: list[str]
    avoid_rules: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def classify_command_center_intent(
    user_text: str = "",
    pasted_output: str = "",
) -> str:
    text = normalize_text(f"{user_text}\n{pasted_output}")

    if any(token in text for token in ("what changed", "recent changes", "recent decisions", "decision log", "what did we lock")):
        return "recent_changes"

    if any(token in text for token in ("fail", "failed", "traceback", "assertionerror", "broken")):
        return "failure"

    if any(token in text for token in ("what smoke", "which smoke", "smoke should", "run checks", "validation")):
        return "smoke_selection"

    if any(token in text for token in ("operator", "mission control", "mission card", "command center")):
        return "operator_mode"

    if any(token in text for token in ("next", "what should we do", "best move", "upgrade")):
        return "next_move"

    if any(token in text for token in ("status", "current", "blocker", "what are we working on")):
        return "status"

    return "command_center"


def _safe_list(values: Any) -> list[str]:
    result = []

    for value in values or []:
        text = str(value or "").strip()
        if text:
            result.append(text)

    return result


def _join(values: Any, separator: str = "; ") -> str:
    return separator.join(_safe_list(values))


def build_project_brain_command_center_card(
    user_text: str = "",
    pasted_output: str = "",
    changed_files: list[str] | None = None,
) -> ProjectBrainCommandCenterCard:
    from nova_backend.services.project_brain_decision_engine import (
        decide_project_brain_next_move,
    )
    from nova_backend.services.project_brain_decision_log import (
        answer_recent_changes,
    )
    from nova_backend.services.project_brain_failure_interpreter import (
        interpret_project_brain_failure,
    )
    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )
    from nova_backend.services.project_brain_operator_planner import (
        build_operator_plan_dict,
    )
    from nova_backend.services.project_brain_smoke_selector import (
        build_smoke_selection_dict,
    )

    command_intent = classify_command_center_intent(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    snapshot = build_project_brain_freshness_snapshot()
    decision = decide_project_brain_next_move(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    operator_plan = build_operator_plan_dict(
        user_text=user_text,
        changed_files=changed_files or list(decision.target_files),
        project_state=str(snapshot.checkpoint or ""),
    )
    failure = interpret_project_brain_failure(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    smoke_selection = build_smoke_selection_dict(
        user_text=user_text,
        changed_files=changed_files or list(decision.target_files),
        work_type=decision.intent,
    )

    focused_smokes = _safe_list(
        smoke_selection.get("focused_smokes", [])
        or operator_plan.get("focused_smokes", [])
        or decision.validation
    )

    target_files = _safe_list(
        operator_plan.get("target_files", [])
        or decision.target_files
    )

    avoid_rules = _safe_list(
        operator_plan.get("avoid_rules", [])
        or decision.avoid
    )

    return ProjectBrainCommandCenterCard(
        command_intent=command_intent,
        status=str(snapshot.checkpoint or "").strip(),
        blocker=str(snapshot.blocker or "").strip(),
        best_move=str(operator_plan.get("recommended_move") or decision.recommended_next_move).strip(),
        why=str(operator_plan.get("why") or decision.rationale).strip(),
        risk=str(operator_plan.get("risk") or decision.risk).strip(),
        exact_next_command=str(operator_plan.get("exact_next_command") or failure.next_command or "").strip(),
        focused_smokes=focused_smokes,
        stop_rule=str(operator_plan.get("stop_rule") or smoke_selection.get("stop_rule") or "").strip(),
        loop_guard=str(operator_plan.get("loop_guard") or "").strip(),
        recent_changes=answer_recent_changes(limit=6),
        failure_type=str(failure.failure_type or "").strip(),
        failure_severity=str(failure.severity or "").strip(),
        failure_patch_target=str(failure.patch_target or "").strip(),
        failure_next_command=str(failure.next_command or "").strip(),
        smoke_reason=str(smoke_selection.get("reason") or "").strip(),
        target_files=target_files,
        avoid_rules=avoid_rules,
    )


def build_project_brain_command_center_dict(
    user_text: str = "",
    pasted_output: str = "",
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    return build_project_brain_command_center_card(
        user_text=user_text,
        pasted_output=pasted_output,
        changed_files=changed_files,
    ).to_dict()


def format_project_brain_command_center(card: ProjectBrainCommandCenterCard | dict[str, Any]) -> str:
    data = card.to_dict() if isinstance(card, ProjectBrainCommandCenterCard) else dict(card)

    focused_smokes = _join(data.get("focused_smokes", []))
    target_files = _join(data.get("target_files", []))
    avoid_rules = _join(data.get("avoid_rules", []))

    return (
        "Project Brain Command Center:\n"
        f"Command intent: {data.get('command_intent', '')}\n"
        f"Status: {data.get('status', '')}\n"
        f"Blocker/Risk: {data.get('blocker', '')}\n"
        f"Best Move: {data.get('best_move', '')}\n"
        f"Why: {data.get('why', '')}\n"
        f"Risk: {data.get('risk', '')}\n"
        f"Exact Next Command: {data.get('exact_next_command', '')}\n"
        f"Focused Smokes: {focused_smokes}\n"
        f"Smoke Selector Reason: {data.get('smoke_reason', '')}\n"
        f"Target Files: {target_files}\n"
        f"Avoid Rules: {avoid_rules}\n"
        f"Stop Rule: {data.get('stop_rule', '')}\n"
        f"Loop Guard: {data.get('loop_guard', '')}\n"
        f"Failure Type: {data.get('failure_type', '')}\n"
        f"Failure Severity: {data.get('failure_severity', '')}\n"
        f"Failure Patch Target: {data.get('failure_patch_target', '')}\n"
        f"Failure Next Command: {data.get('failure_next_command', '')}\n"
        f"Recent Changes: {data.get('recent_changes', '')}"
    )


def build_project_brain_command_center_answer(
    user_text: str = "",
    pasted_output: str = "",
    changed_files: list[str] | None = None,
) -> str:
    return format_project_brain_command_center(
        build_project_brain_command_center_card(
            user_text=user_text,
            pasted_output=pasted_output,
            changed_files=changed_files,
        )
    )


__all__ = [
    "ProjectBrainCommandCenterCard",
    "build_project_brain_command_center_answer",
    "build_project_brain_command_center_card",
    "build_project_brain_command_center_dict",
    "classify_command_center_intent",
    "format_project_brain_command_center",
]
