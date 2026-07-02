
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperatorCommandPlan:
    title: str
    move_name: str
    target_files: tuple[str, ...]
    focused_smokes: tuple[str, ...]
    regression_required: bool
    commands: tuple[str, ...]
    stop_rule: str
    risk: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "move_name": self.move_name,
            "target_files": list(self.target_files),
            "focused_smokes": list(self.focused_smokes),
            "regression_required": self.regression_required,
            "commands": list(self.commands),
            "stop_rule": self.stop_rule,
            "risk": self.risk,
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


def _normalize_path(path: str) -> str:
    value = _clean(path).replace("\\", "/")

    for marker in ("nova_backend/", "tools/", "app.py"):
        if marker in value:
            if marker == "app.py":
                return "app.py"
            return value[value.index(marker):]

    return value


def _windows_path(path: str) -> str:
    normalized = _normalize_path(path)
    if normalized.startswith(".\\"):
        return normalized
    return ".\\" + normalized.replace("/", "\\")


def _py_compile_commands(target_files) -> list[str]:
    commands = []

    for path in target_files or []:
        normalized = _normalize_path(path)

        if normalized.endswith(".py"):
            commands.append(f"python -m py_compile {_windows_path(normalized)}")

    return commands


def _needs_regression(risk: str, focused_smokes) -> bool:
    risk_value = _clean(risk).lower()

    if risk_value in {"medium", "high"}:
        return True

    return any("api_smoke" in smoke or "regression" in smoke for smoke in focused_smokes or [])


def build_operator_command_plan(
    move_name: str,
    target_files=None,
    focused_smokes=None,
    risk: str = "low",
    include_git_status: bool = True,
) -> OperatorCommandPlan:
    move = _clean(move_name) or "Project Brain operator move"
    targets = _dedupe([_normalize_path(path) for path in target_files or []])
    smokes = _dedupe(focused_smokes or [])

    commands = []
    commands.extend(_py_compile_commands(targets))
    commands.extend(smokes)

    regression_required = _needs_regression(risk, smokes)

    if regression_required and not any("nova_regression_smoke.py" in command for command in commands):
        commands.append(r"python .\tools\nova_regression_smoke.py")

    if include_git_status:
        commands.append("git status --short")

    commands = list(_dedupe(commands))

    return OperatorCommandPlan(
        title="Project Brain Operator Command Launcher v1",
        move_name=move,
        target_files=targets,
        focused_smokes=smokes,
        regression_required=regression_required,
        commands=tuple(commands),
        stop_rule="Run the command block top-to-bottom; stop on the first failing command and patch only that layer.",
        risk=_clean(risk) or "low",
    )


def build_operator_command_plan_from_best_move() -> OperatorCommandPlan:
    from nova_backend.services.project_brain_operator_planner import choose_recommended_move

    move_name, _why, risk, target_files = choose_recommended_move("next_move")

    focused_smokes = []
    try:
        from nova_backend.services.project_brain_smoke_selector import select_focused_smokes

        focused_smokes = select_focused_smokes(
            work_type="next_move",
            changed_files=target_files,
            route_risk=risk,
        )
    except Exception:
        focused_smokes = []

    return build_operator_command_plan(
        move_name=move_name,
        target_files=target_files,
        focused_smokes=focused_smokes,
        risk=risk,
    )


def build_operator_command_launcher_answer(
    move_name: str = "",
    target_files=None,
    focused_smokes=None,
    risk: str = "low",
) -> str:
    if move_name:
        plan = build_operator_command_plan(
            move_name=move_name,
            target_files=target_files,
            focused_smokes=focused_smokes,
            risk=risk,
        )
    else:
        plan = build_operator_command_plan_from_best_move()

    return "\n".join([
        "Project Brain Operator Command Launcher:",
        f"Move: {plan.move_name}",
        f"Risk: {plan.risk}",
        f"Regression Required: {plan.regression_required}",
        "Target Files:",
        *[f"- {item}" for item in plan.target_files],
        "Command Block:",
        *[item for item in plan.commands],
        f"Stop Rule: {plan.stop_rule}",
    ])
