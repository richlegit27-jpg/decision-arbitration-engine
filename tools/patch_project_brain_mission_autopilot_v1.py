from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_mission_autopilot.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_mission_autopilot_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
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
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_MISSION_AUTOPILOT_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_MISSION_AUTOPILOT_NEXT_V1_20260702
# After Action Card is locked, rank Mission Autopilot safe mode as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Project Brain Mission Autopilot v1",
            why=(
                "Use the Action Card to choose one bounded service-level move, output exact commands, "
                "enforce stop-on-failure, and refuse risky app.py route work unless route risk is explicit."
            ),
            risk="medium",
            score=160,
            target_files=(
                "nova_backend/services/project_brain_mission_autopilot.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_mission_autopilot_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Project Brain Runtime Coach v1",
            why="Turn Mission Autopilot output into short operator coaching after each smoke result.",
            risk="medium",
            score=150,
            target_files=(
                "nova_backend/services/project_brain_runtime_coach.py",
                "tools/nova_project_brain_runtime_coach_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            ),
            loses_to_best_because="Runtime Coach should land after Mission Autopilot produces the safe mission contract.",
        ),
        UpgradeCandidate(
            name="Project Brain Action Card v1",
            why="Action Card is locked; keep it as the unified operator card.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_action_card.py",
                "tools/nova_project_brain_action_card_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_action_card_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Mission Autopilot v1 safe mode.",
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Operator Command Launcher is locked; keep it as the command-block generator.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Patch Planner is locked; keep it as the bounded patch-plan layer.",
            risk="low",
            score=70,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
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
    print("patched Upgrade Radar to rank Mission Autopilot next")
else:
    print("Mission Autopilot next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_mission_autopilot import (
    build_mission_autopilot_answer,
    build_mission_autopilot_dict,
    build_mission_autopilot_plan,
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
    print("NOVA PROJECT BRAIN MISSION AUTOPILOT SMOKE")
    print("==========================================")

    plan = build_mission_autopilot_plan()
    plan_dict = build_mission_autopilot_dict()
    answer = build_mission_autopilot_answer()

    assert_true("plan title", plan.title == "Project Brain Mission Autopilot v1", plan.title)
    assert_true("safe mode", plan.mode == "safe_mode", plan.mode)
    assert_true("allowed", plan.allowed is True, plan.allowed)
    assert_true("selected autopilot", plan.selected_move == "Project Brain Mission Autopilot v1", plan.selected_move)
    assert_true("target file", "nova_backend/services/project_brain_mission_autopilot.py" in plan.target_files, plan.target_files)
    assert_true("autopilot smoke command", any("mission_autopilot_smoke" in item for item in plan.commands), plan.commands)
    assert_true("git status command", plan.commands[-1] == "git status --short", plan.commands)
    assert_true("stop on failure", "Stop on the first failing command" in plan.stop_rule, plan.stop_rule)
    assert_true("dict commands", bool(plan_dict.get("commands")), plan_dict)
    assert_true("answer title", "Project Brain Mission Autopilot" in answer)
    assert_true("answer command block", "Command Block" in answer)

    refused = build_mission_autopilot_plan(
        changed_files=["app.py"],
        user_text="cleanup app.py wrappers",
        route_risk="low",
    )

    assert_true("refuses risky app route", refused.allowed is False, refused)
    assert_true("refusal reason app.py", "app.py" in refused.refusal_reason, refused.refusal_reason)
    assert_true("refusal only git status", refused.commands == ("git status --short",), refused.commands)

    explicit_route = build_mission_autopilot_plan(
        changed_files=["app.py"],
        user_text="route_contract_failure command_center_api",
        route_risk="medium",
    )

    assert_true("explicit route allowed", explicit_route.allowed is True, explicit_route.refusal_reason)
    assert_true("explicit route regression", any("nova_regression_smoke" in item for item in explicit_route.commands), explicit_route.commands)

    best = select_best_upgrade()
    assert_true("radar best autopilot", best.name == "Project Brain Mission Autopilot v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first autopilot", move_value(moves[0], "name") == "Project Brain Mission Autopilot v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended autopilot", recommended_move == "Project Brain Mission Autopilot v1", recommended_move)
    assert_true("recommended why stop failure", "stop-on-failure" in why or "bounded service-level move" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_mission_autopilot.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN MISSION AUTOPILOT SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Project Brain Action Card v1", "Project Brain Mission Autopilot v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_action_card_smoke.py",
        r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Merge Upgrade Radar, Auto-Debug Brain, Patch Planner, Self-Test Selector, and Operator Command Launcher into one operator card with exact commands",
        "Use the Action Card to choose one bounded service-level move",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_action_card.py",
        "nova_backend/services/project_brain_mission_autopilot.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched Command Center smoke expectations: {smoke_path}")

print("installed Project Brain Mission Autopilot v1 safe mode")
