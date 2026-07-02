
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

