
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








# NOVA_PROJECT_BRAIN_AUTO_DEBUG_NEXT_V1_20260702
# After Upgrade Radar is locked, rank Auto-Debug Brain as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_SELF_TEST_SELECTOR_NEXT_V1_20260702
# After Auto-Debug Brain is locked, rank Self-Test Selector as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_PATCH_PLANNER_NEXT_V1_20260702
# After Self-Test Selector is locked, rank Patch Planner as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_OPERATOR_COMMAND_LAUNCHER_NEXT_V1_20260702
# After Patch Planner is locked, rank Operator Command Launcher as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_ACTION_CARD_NEXT_V1_20260702
# After Operator Command Launcher is locked, rank Action Card as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_MISSION_AUTOPILOT_NEXT_V1_20260702
# After Action Card is locked, rank Mission Autopilot safe mode as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_RUNTIME_COACH_NEXT_V1_20260702
# After Mission Autopilot is locked, rank Runtime Coach as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_OPERATOR_MEMORY_WRITER_NEXT_V1_20260702
# After Runtime Coach is locked, rank Operator Memory Writer as the next gangster upgrade.






# NOVA_PROJECT_BRAIN_STATE_BRIDGE_NEXT_V1_20260702
# After Operator Memory Writer is locked, rank State Bridge as the next gangster upgrade.






# NOVA_CONVERSATION_QUALITY_FIELD_TEST_NEXT_20260702
# After backend stable tag, next best move is lived conversation quality testing.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Nova Conversation Quality Field Test v1",
            why=(
                "Backend is stable enough to stop blind surgery and collect real conversation examples "
                "where Nova feels shallow, confused, too bot-like, or loses continuation."
            ),
            risk="low",
            score=220,
            target_files=(
                "tools/nova_conversation_quality_field_test_smoke.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_conversation_quality_field_test_smoke.py",
                r"python .\tools\nova_final_response_shape_contract_smoke.py",
                r"python .\tools\nova_regression_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="App.py Guard Cleanup Pass 2",
            why="Continue removing one small redundant final JSON mutator at a time.",
            risk="medium",
            score=170,
            target_files=(
                "app.py",
                "tools/nova_finalizer_pipeline_audit.py",
                "tools/nova_regression_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_finalizer_pipeline_audit.py",
                r"python .\tools\nova_regression_smoke.py",
            ),
            loses_to_best_because="Conversation quality should be field-tested now that backend is tagged stable.",
        ),
        UpgradeCandidate(
            name="Project Brain State Bridge v1",
            why="Already locked; keep it visible only as completed infrastructure.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_state_bridge.py",
                "tools/nova_project_brain_state_bridge_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_state_bridge_smoke.py",
            ),
            loses_to_best_because="Already completed and stable-tagged.",
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

