
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissionAutopilotPlan:
    title: str
    mode: str
    selected_move: str
    why: str
    risk: str
    target_files: tuple[str, ...]
    commands: tuple[str, ...]
    stop_rule: str
    allowed: bool
    refusal_reason: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "mode": self.mode,
            "selected_move": self.selected_move,
            "why": self.why,
            "risk": self.risk,
            "target_files": list(self.target_files),
            "commands": list(self.commands),
            "stop_rule": self.stop_rule,
            "allowed": self.allowed,
            "refusal_reason": self.refusal_reason,
        }


def _clean(value: str) -> str:
    return str(value or "").strip()


def _dedupe(values) -> tuple[str, ...]:
    result = []
    seen = set()

    for item in values or []:
        value = _clean(item)

        if not value or value in seen:
            continue

        seen.add(value)
        result.append(value)

    return tuple(result)


def _is_risky_app_route_move(target_files, user_text: str = "") -> bool:
    text = " ".join([str(item or "") for item in target_files or []] + [str(user_text or "")]).lower()

    if "app.py" not in text:
        return False

    allowed_signals = [
        "route_contract_failure",
        "api_route_gate",
        "command_center_api",
        "route failed",
    ]

    return not any(signal in text for signal in allowed_signals)


def build_mission_autopilot_plan(
    pasted_output: str = "",
    changed_files=None,
    user_text: str = "",
    route_risk: str = "",
    safe_mode: bool = True,
) -> MissionAutopilotPlan:
    from nova_backend.services.project_brain_action_card import (
        build_project_brain_action_card,
    )
    from nova_backend.services.project_brain_operator_command_launcher import (
        build_operator_command_plan,
    )
    from nova_backend.services.project_brain_upgrade_radar import select_best_upgrade

    best = select_best_upgrade()

    card = build_project_brain_action_card(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_text=user_text or best.name,
        route_risk=route_risk or best.risk,
    )

    target_files = list(card.target_files or best.target_files)
    focused_smokes = list(card.focused_smokes or [])
    focused_smokes.extend(list(best.focused_smokes or []))

    risk = route_risk or card.risk or best.risk

    allowed = True
    refusal_reason = ""

    if not safe_mode:
        allowed = False
        refusal_reason = "Mission Autopilot v1 only supports safe_mode=True."

    if _is_risky_app_route_move(target_files, user_text=user_text):
        allowed = False
        refusal_reason = "Refusing non-explicit app.py route work. Use a service-level move or provide explicit route-risk evidence."

    command_plan = build_operator_command_plan(
        move_name=best.name,
        target_files=target_files,
        focused_smokes=focused_smokes,
        risk=risk,
    )

    stop_rule = (
        "Safe mode: run one bounded service-level move only. "
        "Stop on the first failing command. Do not continue into another patch without a new Action Card."
    )

    if not allowed:
        commands = ("git status --short",)
    else:
        commands = command_plan.commands

    return MissionAutopilotPlan(
        title="Project Brain Mission Autopilot v1",
        mode="safe_mode",
        selected_move=best.name,
        why=best.why,
        risk=risk,
        target_files=_dedupe(target_files),
        commands=_dedupe(commands),
        stop_rule=stop_rule,
        allowed=allowed,
        refusal_reason=refusal_reason,
    )


def build_mission_autopilot_dict(
    pasted_output: str = "",
    changed_files=None,
    user_text: str = "",
    route_risk: str = "",
    safe_mode: bool = True,
) -> dict:
    return build_mission_autopilot_plan(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_text=user_text,
        route_risk=route_risk,
        safe_mode=safe_mode,
    ).as_dict()


def build_mission_autopilot_answer(
    pasted_output: str = "",
    changed_files=None,
    user_text: str = "",
    route_risk: str = "",
    safe_mode: bool = True,
) -> str:
    plan = build_mission_autopilot_plan(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_text=user_text,
        route_risk=route_risk,
        safe_mode=safe_mode,
    )

    lines = [
        "Project Brain Mission Autopilot:",
        f"Mode: {plan.mode}",
        f"Allowed: {plan.allowed}",
        f"Selected Move: {plan.selected_move}",
        f"Why: {plan.why}",
        f"Risk: {plan.risk}",
    ]

    if plan.refusal_reason:
        lines.append(f"Refusal Reason: {plan.refusal_reason}")

    lines.extend([
        "Target Files:",
        *[f"- {item}" for item in plan.target_files],
        "Command Block:",
        *[item for item in plan.commands],
        f"Stop Rule: {plan.stop_rule}",
    ])

    return "\n".join(lines)
