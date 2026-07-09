from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_upgrade_radar.py")
PLANNER = Path("nova_backend/services/project_brain_operator_planner.py")
SMOKE = Path("tools/nova_project_brain_upgrade_radar_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
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
''', encoding="utf-8")

if not PLANNER.exists():
    raise SystemExit("missing operator planner service")

text = PLANNER.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_UPGRADE_RADAR_V1_20260702" not in text:
    block = r'''

# NOVA_PROJECT_BRAIN_UPGRADE_RADAR_V1_20260702
# Service-only upgrade ranking. No app.py route guard.
_NOVA_PRE_UPGRADE_RADAR_RANK_MOVES_20260702 = rank_moves

def _nova_upgrade_radar_value_20260702(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def _nova_upgrade_radar_list_20260702(value):
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    try:
        return [str(item) for item in value if str(item or "").strip()]
    except Exception:
        return []


def _nova_upgrade_radar_name_20260702(move):
    return str(_nova_upgrade_radar_value_20260702(move, "name", "") or "").strip()


def _nova_upgrade_radar_risk_20260702(move, default="low"):
    return str(_nova_upgrade_radar_value_20260702(move, "risk", default) or default).strip() or default


def _nova_upgrade_radar_move_20260702(rank=1):
    from nova_backend.services.project_brain_upgrade_radar import select_best_upgrade

    best = select_best_upgrade()

    return _move(
        rank=rank,
        name=best.name,
        why=best.why,
        risk=best.risk,
        target_files=list(best.target_files),
        focused_smokes=list(best.focused_smokes),
        loses_to_best_because=best.loses_to_best_because,
    )


def _nova_upgrade_radar_normalize_move_20260702(move, rank):
    return _move(
        rank=rank,
        name=_nova_upgrade_radar_name_20260702(move),
        why=str(_nova_upgrade_radar_value_20260702(move, "why", "") or "").strip(),
        risk=_nova_upgrade_radar_risk_20260702(move),
        target_files=_nova_upgrade_radar_list_20260702(
            _nova_upgrade_radar_value_20260702(move, "target_files", [])
        ),
        focused_smokes=_nova_upgrade_radar_list_20260702(
            _nova_upgrade_radar_value_20260702(move, "focused_smokes", [])
        ),
        loses_to_best_because=str(
            _nova_upgrade_radar_value_20260702(move, "loses_to_best_because", "") or ""
        ).strip(),
    )


def rank_moves(work_type: str, changed_files=None, **kwargs):
    try:
        base_moves = _NOVA_PRE_UPGRADE_RADAR_RANK_MOVES_20260702(
            work_type,
            changed_files=changed_files,
            **kwargs,
        )
    except TypeError:
        base_moves = _NOVA_PRE_UPGRADE_RADAR_RANK_MOVES_20260702(work_type)
    except Exception:
        base_moves = []

    radar = _nova_upgrade_radar_move_20260702(rank=1)

    combined = [radar]
    seen = {_nova_upgrade_radar_name_20260702(radar)}

    for move in base_moves or []:
        name = _nova_upgrade_radar_name_20260702(move)

        if not name or name in seen:
            continue

        if name == "Cleanup Strategy Engine v1":
            continue

        seen.add(name)
        combined.append(move)

    return [
        _nova_upgrade_radar_normalize_move_20260702(move, index)
        for index, move in enumerate(combined, start=1)
    ]


def choose_recommended_move(work_type: str):
    ranked = rank_moves(work_type)
    best = ranked[0] if ranked else _nova_upgrade_radar_move_20260702(rank=1)

    return (
        _nova_upgrade_radar_name_20260702(best),
        str(_nova_upgrade_radar_value_20260702(best, "why", "") or "").strip(),
        _nova_upgrade_radar_risk_20260702(best),
        _nova_upgrade_radar_list_20260702(
            _nova_upgrade_radar_value_20260702(best, "target_files", [])
        ),
    )
'''
    text = text.rstrip() + "\n" + block + "\n"
    PLANNER.write_text(text, encoding="utf-8")
    print("patched operator planner with Upgrade Radar v1")
else:
    print("Upgrade Radar v1 already installed in operator planner")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_upgrade_radar import (
    build_upgrade_radar_summary,
    get_upgrade_candidates,
    select_best_upgrade,
)
from nova_backend.services.project_brain_operator_planner import (
    choose_recommended_move,
    rank_moves,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def move_value(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def main():
    print("NOVA PROJECT BRAIN UPGRADE RADAR SMOKE")
    print("======================================")

    candidates = get_upgrade_candidates()
    best = select_best_upgrade()
    summary = build_upgrade_radar_summary()

    assert_true("candidates exist", len(candidates) >= 3)
    assert_true("best upgrade radar", best.name == "Project Brain Upgrade Radar v1", best.name)
    assert_true("best risk medium", best.risk == "medium", best.risk)
    assert_true("summary includes auto debug", "Auto-Debug Brain v1" in summary)
    assert_true("summary includes self-test selector", "Self-Test Selector v1" in summary)

    moves = rank_moves("next_move")
    first = moves[0]

    assert_true("rank moves exists", len(moves) >= 1)
    assert_true("rank first upgrade radar", move_value(first, "name") == "Project Brain Upgrade Radar v1", move_value(first, "name"))
    assert_true("cleanup skipped from top", move_value(first, "name") != "Cleanup Strategy Engine v1")

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")

    assert_true("recommended upgrade radar", recommended_move == "Project Brain Upgrade Radar v1", recommended_move)
    assert_true("recommended why gangster upgrades", "gangster upgrades" in why or "high-impact intelligence upgrades" in why, why)
    assert_true("recommended risk", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_upgrade_radar.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN UPGRADE RADAR SMOKE PASSED")


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
    smoke_text = smoke_text.replace("Cleanup Strategy Engine v1", "Project Brain Upgrade Radar v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_operator_planner_smoke.py",
        r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "bounded cleanup ranking",
        "high-impact intelligence upgrades",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Upgrade Radar v1")
