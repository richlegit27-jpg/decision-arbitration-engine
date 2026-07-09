from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_operator_command_launcher.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_operator_command_launcher_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
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
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_OPERATOR_COMMAND_LAUNCHER_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_OPERATOR_COMMAND_LAUNCHER_NEXT_V1_20260702
# After Patch Planner is locked, rank Operator Command Launcher as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why=(
                "Convert best moves, target files, focused smokes, and route risk into exact "
                "PowerShell command blocks so Nova can operate from one clean action card."
            ),
            risk="medium",
            score=140,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Project Brain Action Card v1",
            why="Merge Upgrade Radar, Auto-Debug, Patch Planner, Smoke Selector, and Launcher into one operator card.",
            risk="medium",
            score=130,
            target_files=(
                "nova_backend/services/project_brain_action_card.py",
                "tools/nova_project_brain_action_card_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_action_card_smoke.py",
            ),
            loses_to_best_because="Action Card should land after Launcher can generate the command block.",
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Patch Planner is locked; keep it as the bounded patch-plan layer.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Operator Command Launcher v1.",
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why="Self-Test Selector is locked; keep it as the smoke decision layer.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why="Auto-Debug Brain is locked; keep it as the traceback classifier.",
            risk="low",
            score=70,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
        UpgradeCandidate(
            name="Project Brain Upgrade Radar v1",
            why="Upgrade Radar is locked; keep it as the ranking layer.",
            risk="low",
            score=60,
            target_files=(
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_upgrade_radar_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
    ]


def select_best_upgrade() -> UpgradeCandidate:
    candidates = get_upgrade_candidates()
    return sorted(candidates, key=lambda item: item.score, reverse=True)[0]


def build_upgrade_radar_summary() -> str:
    candidates = get_upgrade_candidates()
    lines = ["Project Brain Upgrade Radar:"]
    for index, candidate in enumerate(sorted(candidates, key=lambda item: item.score, reverse=True), start=1):
        lines.append(f"{index}. {candidate.name} — {candidate.why}")
    return "\n".join(lines)
'''
    RADAR.write_text(radar_text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    print("patched Upgrade Radar to rank Operator Command Launcher next")
else:
    print("Operator Command Launcher next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_operator_command_launcher import (
    build_operator_command_launcher_answer,
    build_operator_command_plan,
    build_operator_command_plan_from_best_move,
)
from nova_backend.services.project_brain_upgrade_radar import select_best_upgrade
from nova_backend.services.project_brain_operator_planner import choose_recommended_move, rank_moves


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def move_value(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def main():
    print("NOVA PROJECT BRAIN OPERATOR COMMAND LAUNCHER SMOKE")
    print("==================================================")

    plan = build_operator_command_plan(
        move_name="Patch Planner v1",
        target_files=[
            "nova_backend/services/project_brain_patch_planner.py",
            "tools/nova_project_brain_patch_planner_smoke.py",
        ],
        focused_smokes=[
            r"python .\tools\nova_project_brain_patch_planner_smoke.py",
        ],
        risk="medium",
    )

    assert_true("plan title", plan.title == "Project Brain Operator Command Launcher v1", plan.title)
    assert_true("move carried", plan.move_name == "Patch Planner v1", plan.move_name)
    assert_true("py compile service", any("project_brain_patch_planner.py" in item and "py_compile" in item for item in plan.commands), plan.commands)
    assert_true("py compile smoke", any("nova_project_brain_patch_planner_smoke.py" in item and "py_compile" in item for item in plan.commands), plan.commands)
    assert_true("focused smoke included", any("nova_project_brain_patch_planner_smoke.py" in item and "py_compile" not in item for item in plan.commands), plan.commands)
    assert_true("regression included medium", any("nova_regression_smoke.py" in item for item in plan.commands), plan.commands)
    assert_true("git status included", plan.commands[-1] == "git status --short", plan.commands)
    assert_true("stop rule exists", "stop" in plan.stop_rule.lower(), plan.stop_rule)

    low_plan = build_operator_command_plan(
        move_name="Self-Test Selector v1",
        target_files=["nova_backend/services/project_brain_smoke_selector.py"],
        focused_smokes=[r"python .\tools\nova_project_brain_smoke_selector_smoke.py"],
        risk="low",
    )

    assert_true("low risk no regression by default", not any("nova_regression_smoke.py" in item for item in low_plan.commands), low_plan.commands)

    answer = build_operator_command_launcher_answer(
        move_name="Patch Planner v1",
        target_files=["nova_backend/services/project_brain_patch_planner.py"],
        focused_smokes=[r"python .\tools\nova_project_brain_patch_planner_smoke.py"],
        risk="medium",
    )

    assert_true("answer title", "Project Brain Operator Command Launcher" in answer)
    assert_true("answer command block", "Command Block" in answer)
    assert_true("answer regression", "nova_regression_smoke.py" in answer)

    best = select_best_upgrade()
    assert_true("radar best launcher", best.name == "Operator Command Launcher v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first launcher", move_value(moves[0], "name") == "Operator Command Launcher v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended launcher", recommended_move == "Operator Command Launcher v1", recommended_move)
    assert_true("recommended why command blocks", "command blocks" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_operator_command_launcher.py" in target_files, target_files)

    best_plan = build_operator_command_plan_from_best_move()
    assert_true("best plan launcher move", best_plan.move_name == "Operator Command Launcher v1", best_plan.move_name)
    assert_true("best plan has commands", bool(best_plan.commands), best_plan.commands)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR COMMAND LAUNCHER SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_patch_planner_smoke.py"),
    Path("tools/nova_project_brain_smoke_selector_smoke.py"),
    Path("tools/nova_project_brain_upgrade_radar_smoke.py"),
    Path("tools/nova_project_brain_auto_debug_brain_smoke.py"),
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Patch Planner v1", "Operator Command Launcher v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_patch_planner_smoke.py",
        r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Turn failures into bounded file-level patch plans",
        "Convert best moves, target files, focused smokes, and route risk into exact PowerShell command blocks",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_patch_planner.py",
        "nova_backend/services/project_brain_operator_command_launcher.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Operator Command Launcher v1")
