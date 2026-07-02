
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpgradeCandidate:
    name: str
    why: str
    risk: str
    score: int
    target_files: tuple[str, ...]
    focused_smokes: tuple[str, ...]
    loses_to_best_because: str = ""


def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Project Brain Upgrade Radar v1",
            why=(
                "Nova now ranks high-impact intelligence upgrades when no active blocker is open, "
                "so Command Center can continue gangster upgrades instead of defaulting to cleanup."
            ),
            risk="medium",
            score=100,
            target_files=(
                "nova_backend/services/project_brain_upgrade_radar.py",
                "nova_backend/services/project_brain_operator_planner.py",
                "tools/nova_project_brain_upgrade_radar_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why=(
                "Classify tracebacks, identify the failing service layer, and recommend the smallest "
                "safe patch plus focused smoke."
            ),
            risk="medium",
            score=95,
            target_files=(
                "nova_backend/services/project_brain_failure_interpreter.py",
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
            loses_to_best_because="Upgrade Radar should land first so later upgrades are ranked instead of guessed.",
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why=(
                "Choose the smallest correct smoke set from changed files, intent, and route risk."
            ),
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
            loses_to_best_because="Upgrade Radar should own the ranking layer before test selection expands.",
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why=(
                "Turn failures into bounded file-level patch plans without adding new app.py route guards."
            ),
            risk="medium",
            score=85,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Patch Planner is stronger after Upgrade Radar can choose it intentionally.",
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


# NOVA_PROJECT_BRAIN_AUTO_DEBUG_NEXT_V1_20260702
# After Upgrade Radar is locked, rank Auto-Debug Brain as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why=(
                "Classify tracebacks, identify the failing service layer, name the likely broken symbol, "
                "recommend the smallest safe patch, and choose the focused smoke automatically."
            ),
            risk="medium",
            score=110,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why="Choose the smallest correct smoke set from changed files, intent, and route risk.",
            risk="low",
            score=100,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
            loses_to_best_because="Auto-Debug Brain should land first so test selection can use failure classifications.",
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Turn failures into bounded file-level patch plans without adding new app.py route guards.",
            risk="medium",
            score=95,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Patch Planner becomes stronger after Auto-Debug Brain names the failure pattern.",
        ),
        UpgradeCandidate(
            name="Project Brain Upgrade Radar v1",
            why="Upgrade Radar is locked; keep it as the ranking layer but do not repeat it as the next move.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_upgrade_radar_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Auto-Debug Brain v1.",
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


# NOVA_PROJECT_BRAIN_SELF_TEST_SELECTOR_NEXT_V1_20260702
# After Auto-Debug Brain is locked, rank Self-Test Selector as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why=(
                "Choose the smallest correct smoke set from changed files, failure layer, "
                "intent, and route risk so Nova proves upgrades without wasting cycles."
            ),
            risk="low",
            score=120,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Turn failures into bounded file-level patch plans without adding new app.py route guards.",
            risk="medium",
            score=110,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Self-Test Selector should land first so Patch Planner can attach correct smokes to patches.",
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Convert Command Center recommendations into exact operator command blocks.",
            risk="medium",
            score=100,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
            loses_to_best_because="Launcher is stronger after Self-Test Selector decides the command list.",
        ),
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why="Auto-Debug Brain is locked; keep it available as the traceback classifier.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Self-Test Selector v1.",
        ),
        UpgradeCandidate(
            name="Project Brain Upgrade Radar v1",
            why="Upgrade Radar is locked; keep it as the ranking layer.",
            risk="low",
            score=70,
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


# NOVA_PROJECT_BRAIN_PATCH_PLANNER_NEXT_V1_20260702
# After Self-Test Selector is locked, rank Patch Planner as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Patch Planner v1",
            why=(
                "Turn failures into bounded file-level patch plans with target file, likely cause, "
                "guardrails, focused smokes, and stop rule without adding new app.py route guards."
            ),
            risk="medium",
            score=130,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Convert Command Center recommendations into exact operator command blocks.",
            risk="medium",
            score=120,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
            loses_to_best_because="Patch Planner should land first so launched commands are based on bounded patch plans.",
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why="Self-Test Selector is locked; keep it as the smoke decision layer.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Patch Planner v1.",
        ),
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why="Auto-Debug Brain is locked; keep it as the traceback classifier.",
            risk="low",
            score=80,
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
            score=70,
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

