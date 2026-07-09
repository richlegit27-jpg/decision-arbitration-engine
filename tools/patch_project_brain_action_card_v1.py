from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_action_card.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_action_card_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
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
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_ACTION_CARD_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_ACTION_CARD_NEXT_V1_20260702
# After Operator Command Launcher is locked, rank Action Card as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Project Brain Action Card v1",
            why=(
                "Merge Upgrade Radar, Auto-Debug Brain, Patch Planner, Self-Test Selector, "
                "and Operator Command Launcher into one operator card with exact commands."
            ),
            risk="medium",
            score=150,
            target_files=(
                "nova_backend/services/project_brain_action_card.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_action_card_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_action_card_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Project Brain Mission Autopilot v1",
            why="Use the Action Card to choose, patch, smoke, and stop at one bounded service-level move.",
            risk="high",
            score=140,
            target_files=(
                "nova_backend/services/project_brain_mission_autopilot.py",
                "tools/nova_project_brain_mission_autopilot_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
            ),
            loses_to_best_because="Autopilot should land after Action Card produces the full operator command contract.",
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Operator Command Launcher is locked; keep it as the command-block generator.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Project Brain Action Card v1.",
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Patch Planner is locked; keep it as the bounded patch-plan layer.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why="Self-Test Selector is locked; keep it as the smoke decision layer.",
            risk="low",
            score=70,
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
            score=60,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
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
    print("patched Upgrade Radar to rank Action Card next")
else:
    print("Action Card next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_action_card import (
    build_project_brain_action_card,
    build_project_brain_action_card_answer,
    build_project_brain_action_card_dict,
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
    print("NOVA PROJECT BRAIN ACTION CARD SMOKE")
    print("====================================")

    card = build_project_brain_action_card()
    card_dict = build_project_brain_action_card_dict()
    answer = build_project_brain_action_card_answer()

    assert_true("card title", card.title == "Project Brain Action Card v1", card.title)
    assert_true("card move action card", card.move_name == "Project Brain Action Card v1", card.move_name)
    assert_true("card target files", "nova_backend/services/project_brain_action_card.py" in card.target_files, card.target_files)
    assert_true("card focused smokes", any("action_card_smoke" in item for item in card.focused_smokes), card.focused_smokes)
    assert_true("card commands", any("action_card_smoke" in item for item in card.commands), card.commands)
    assert_true("card git status", card.commands[-1] == "git status --short", card.commands)
    assert_true("dict commands", bool(card_dict.get("commands")), card_dict)
    assert_true("answer title", "Project Brain Action Card" in answer)
    assert_true("answer command block", "Command Block" in answer)

    trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 304, in build_operator_plan
    moves = rank_moves(work_type, changed_files=changed_files)
TypeError: rank_moves() got an unexpected keyword argument 'changed_files'
"""

    failure_card = build_project_brain_action_card(
        pasted_output=trace,
        user_text="command center",
        route_risk="low",
    )

    assert_true("failure type carried", failure_card.failure_type == "signature_mismatch", failure_card.failure_type)
    assert_true("patch move carried", "signature" in failure_card.patch_move or "keyword" in failure_card.patch_move, failure_card.patch_move)
    assert_true("failure command smokes", any("general_intelligence_command_center_smoke" in item for item in failure_card.commands), failure_card.commands)

    best = select_best_upgrade()
    assert_true("radar best action card", best.name == "Project Brain Action Card v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first action card", move_value(moves[0], "name") == "Project Brain Action Card v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended action card", recommended_move == "Project Brain Action Card v1", recommended_move)
    assert_true("recommended why operator card", "operator card" in why or "exact commands" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_action_card.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN ACTION CARD SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_operator_command_launcher_smoke.py"),
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
    smoke_text = smoke_text.replace("Operator Command Launcher v1", "Project Brain Action Card v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
        r"python .\tools\nova_project_brain_action_card_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Convert best moves, target files, focused smokes, and route risk into exact PowerShell command blocks",
        "Merge Upgrade Radar, Auto-Debug Brain, Patch Planner, Self-Test Selector, and Operator Command Launcher into one operator card with exact commands",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_operator_command_launcher.py",
        "nova_backend/services/project_brain_action_card.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Action Card v1")
