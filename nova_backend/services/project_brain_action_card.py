
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectBrainActionCard:
    title: str
    move_name: str
    why: str
    risk: str
    target_files: tuple[str, ...]
    failure_type: str
    patch_move: str
    focused_smokes: tuple[str, ...]
    commands: tuple[str, ...]
    stop_rule: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "move_name": self.move_name,
            "why": self.why,
            "risk": self.risk,
            "target_files": list(self.target_files),
            "failure_type": self.failure_type,
            "patch_move": self.patch_move,
            "focused_smokes": list(self.focused_smokes),
            "commands": list(self.commands),
            "stop_rule": self.stop_rule,
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


def _best_move():
    try:
        from nova_backend.services.project_brain_operator_planner import choose_recommended_move

        move_name, why, risk, target_files = choose_recommended_move("next_move")
        return move_name, why, risk, list(target_files or [])
    except Exception:
        from nova_backend.services.project_brain_upgrade_radar import select_best_upgrade

        best = select_best_upgrade()
        return best.name, best.why, best.risk, list(best.target_files)


def build_project_brain_action_card(
    pasted_output: str = "",
    changed_files=None,
    user_text: str = "",
    route_risk: str = "",
) -> ProjectBrainActionCard:
    move_name, why, risk, target_files = _best_move()

    if route_risk:
        risk = route_risk

    files = list(changed_files or target_files or [])

    failure_type = ""
    patch_move = ""

    if _clean(pasted_output):
        try:
            from nova_backend.services.project_brain_patch_planner import build_patch_plan

            patch_plan = build_patch_plan(
                pasted_output=pasted_output,
                changed_files=files,
                user_intent=user_text or move_name,
                route_risk=risk,
            )
            failure_type = patch_plan.failure_type
            patch_move = patch_plan.patch_move
            files = list(patch_plan.target_file and [patch_plan.target_file] or files)
            focused_smokes = list(patch_plan.focused_smokes)
            stop_rule = patch_plan.stop_rule
            risk = patch_plan.risk
        except Exception:
            focused_smokes = []
            stop_rule = "Stop on the first failing command and patch only that layer."
    else:
        focused_smokes = []
        stop_rule = "Run the command block top-to-bottom; stop on the first failing command."

    if not focused_smokes:
        try:
            from nova_backend.services.project_brain_smoke_selector import select_focused_smokes

            focused_smokes = select_focused_smokes(
                work_type="next_move",
                changed_files=files,
                user_intent=user_text or move_name,
                route_risk=risk,
            )
        except Exception:
            focused_smokes = []

    try:
        from nova_backend.services.project_brain_operator_command_launcher import (
            build_operator_command_plan,
        )

        command_plan = build_operator_command_plan(
            move_name=move_name,
            target_files=files,
            focused_smokes=focused_smokes,
            risk=risk,
        )
        commands = list(command_plan.commands)
        stop_rule = command_plan.stop_rule or stop_rule
    except Exception:
        commands = list(focused_smokes)
        commands.append("git status --short")

    return ProjectBrainActionCard(
        title="Project Brain Action Card v1",
        move_name=_clean(move_name),
        why=_clean(why),
        risk=_clean(risk) or "low",
        target_files=_dedupe(files),
        failure_type=_clean(failure_type),
        patch_move=_clean(patch_move),
        focused_smokes=_dedupe(focused_smokes),
        commands=_dedupe(commands),
        stop_rule=_clean(stop_rule),
    )


def build_project_brain_action_card_dict(
    pasted_output: str = "",
    changed_files=None,
    user_text: str = "",
    route_risk: str = "",
) -> dict:
    return build_project_brain_action_card(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_text=user_text,
        route_risk=route_risk,
    ).as_dict()


def build_project_brain_action_card_answer(
    pasted_output: str = "",
    changed_files=None,
    user_text: str = "",
    route_risk: str = "",
) -> str:
    card = build_project_brain_action_card(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_text=user_text,
        route_risk=route_risk,
    )

    lines = [
        "Project Brain Action Card:",
        f"Move: {card.move_name}",
        f"Why: {card.why}",
        f"Risk: {card.risk}",
        "Target Files:",
        *[f"- {item}" for item in card.target_files],
    ]

    if card.failure_type:
        lines.extend([
            f"Failure Type: {card.failure_type}",
            f"Patch Move: {card.patch_move}",
        ])

    lines.extend([
        "Focused Smokes:",
        *[f"- {item}" for item in card.focused_smokes],
        "Command Block:",
        *[item for item in card.commands],
        f"Stop Rule: {card.stop_rule}",
    ])

    return "\n".join(lines)
