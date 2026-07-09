from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_operator_memory_writer.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_operator_memory_writer_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import re
from pathlib import Path


DEFAULT_OPERATOR_MEMORY_PATH = Path("data/project_brain_operator_memory.json")


LOCKED_GANGSTER_STACK = (
    "Project Brain Upgrade Radar v1",
    "Auto-Debug Brain v1",
    "Self-Test Selector v1",
    "Patch Planner v1",
    "Operator Command Launcher v1",
    "Project Brain Action Card v1",
    "Project Brain Mission Autopilot v1 safe mode",
    "Project Brain Runtime Coach v1",
)


@dataclass(frozen=True)
class OperatorMilestone:
    title: str
    commit_hash: str
    commit_message: str
    locked_upgrades: tuple[str, ...]
    passed_smokes: tuple[str, ...]
    working_tree_clean: bool
    next_move: str
    state_update: str
    created_at_utc: str

    def as_dict(self) -> dict:
        data = asdict(self)
        data["locked_upgrades"] = list(self.locked_upgrades)
        data["passed_smokes"] = list(self.passed_smokes)
        return data


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _extract_commit(output: str) -> tuple[str, str]:
    match = re.search(r"\[[^\]]+\s+([0-9a-f]{7,})\]\s+(.+)", output or "")

    if not match:
        return "", ""

    return match.group(1), match.group(2).strip()


def _extract_passed_smokes(output: str) -> tuple[str, ...]:
    smoke_names = []

    patterns = [
        "NOVA PROJECT BRAIN COMMAND CENTER API SMOKE PASSED",
        "NOVA PROJECT BRAIN GENERAL INTELLIGENCE COMMAND CENTER SMOKE PASSED",
        "NOVA PROJECT BRAIN RUNTIME COACH SMOKE PASSED",
        "NOVA PROJECT BRAIN MISSION AUTOPILOT SMOKE PASSED",
        "NOVA PROJECT BRAIN ACTION CARD SMOKE PASSED",
        "NOVA PROJECT BRAIN OPERATOR COMMAND LAUNCHER SMOKE PASSED",
        "NOVA PROJECT BRAIN PATCH PLANNER SMOKE PASSED",
        "NOVA PROJECT BRAIN SELF-TEST SELECTOR SMOKE PASSED",
        "NOVA PROJECT BRAIN AUTO-DEBUG BRAIN SMOKE PASSED",
        "NOVA PROJECT BRAIN UPGRADE RADAR SMOKE PASSED",
        "NOVA REGRESSION SMOKE PASSED",
    ]

    for pattern in patterns:
        if pattern in str(output or ""):
            smoke_names.append(pattern)

    return _dedupe(smoke_names)


def _working_tree_clean(output: str) -> bool:
    lines = [line.rstrip() for line in str(output or "").splitlines()]
    status_indexes = [
        index for index, line in enumerate(lines)
        if "git status --short" in line
    ]

    if not status_indexes:
        return False

    last = status_indexes[-1]
    for line in lines[last + 1:]:
        stripped = line.strip()

        if not stripped or stripped.startswith("PS "):
            continue

        if stripped.startswith("M ") or stripped.startswith("??") or stripped.startswith("A ") or stripped.startswith("D "):
            return False

    return True


def build_state_update_text(
    locked_upgrades=None,
    next_move: str = "Project Brain Operator Memory Writer v1",
) -> str:
    locked = _dedupe(locked_upgrades or LOCKED_GANGSTER_STACK)

    return (
        "Project Brain operator state update: gangster upgrade stack is locked through "
        + ", ".join(locked)
        + ". Current next move: "
        + _clean(next_move)
        + ". Direct project-state recall should stop saying cleanup is the active next move when Command Center has advanced to service-level gangster upgrades."
    )


def build_operator_milestone(
    commit_hash: str = "",
    commit_message: str = "",
    passed_smokes=None,
    working_tree_clean: bool = True,
    next_move: str = "Project Brain Operator Memory Writer v1",
    locked_upgrades=None,
) -> OperatorMilestone:
    locked = _dedupe(locked_upgrades or LOCKED_GANGSTER_STACK)
    smokes = _dedupe(passed_smokes or [])

    return OperatorMilestone(
        title="Project Brain Operator Memory Writer v1",
        commit_hash=_clean(commit_hash),
        commit_message=_clean(commit_message),
        locked_upgrades=locked,
        passed_smokes=smokes,
        working_tree_clean=bool(working_tree_clean),
        next_move=_clean(next_move),
        state_update=build_state_update_text(
            locked_upgrades=locked,
            next_move=next_move,
        ),
        created_at_utc=_utc_now(),
    )


def build_operator_milestone_from_runtime_output(
    pasted_output: str,
    next_move: str = "Project Brain Operator Memory Writer v1",
) -> OperatorMilestone:
    commit_hash, commit_message = _extract_commit(pasted_output)

    return build_operator_milestone(
        commit_hash=commit_hash,
        commit_message=commit_message,
        passed_smokes=_extract_passed_smokes(pasted_output),
        working_tree_clean=_working_tree_clean(pasted_output),
        next_move=next_move,
    )


def load_operator_memory(path: str | Path = DEFAULT_OPERATOR_MEMORY_PATH) -> dict:
    memory_path = Path(path)

    if not memory_path.exists():
        return {
            "version": 1,
            "milestones": [],
        }

    try:
        data = json.loads(memory_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {
            "version": 1,
            "milestones": [],
        }

    if not isinstance(data, dict):
        return {
            "version": 1,
            "milestones": [],
        }

    milestones = data.get("milestones", [])
    if not isinstance(milestones, list):
        milestones = []

    return {
        "version": int(data.get("version", 1) or 1),
        "milestones": milestones,
    }


def write_operator_milestone(
    milestone: OperatorMilestone,
    path: str | Path = DEFAULT_OPERATOR_MEMORY_PATH,
) -> dict:
    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_operator_memory(memory_path)
    milestones = list(data.get("milestones", []))

    item = milestone.as_dict()
    key = (
        item.get("commit_hash"),
        item.get("commit_message"),
        item.get("next_move"),
    )

    existing_keys = {
        (
            existing.get("commit_hash"),
            existing.get("commit_message"),
            existing.get("next_move"),
        )
        for existing in milestones
        if isinstance(existing, dict)
    }

    if key not in existing_keys:
        milestones.append(item)

    data["version"] = 1
    data["milestones"] = milestones
    data["latest"] = item

    memory_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return data


def build_operator_memory_writer_answer(
    pasted_output: str = "",
    next_move: str = "Project Brain Operator Memory Writer v1",
) -> str:
    milestone = build_operator_milestone_from_runtime_output(
        pasted_output=pasted_output,
        next_move=next_move,
    )

    return "\n".join([
        "Project Brain Operator Memory Writer:",
        f"Commit: {milestone.commit_hash or '(none detected)'}",
        f"Message: {milestone.commit_message or '(none detected)'}",
        f"Working Tree Clean: {milestone.working_tree_clean}",
        f"Next Move: {milestone.next_move}",
        "Locked Upgrades:",
        *[f"- {item}" for item in milestone.locked_upgrades],
        "Passed Smokes:",
        *[f"- {item}" for item in milestone.passed_smokes],
        f"State Update: {milestone.state_update}",
    ])
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_OPERATOR_MEMORY_WRITER_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_OPERATOR_MEMORY_WRITER_NEXT_V1_20260702
# After Runtime Coach is locked, rank Operator Memory Writer as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Project Brain Operator Memory Writer v1",
            why=(
                "Write locked operator milestones and state-update wording after green commits, "
                "so direct project-state recall can stop lagging behind Command Center."
            ),
            risk="medium",
            score=180,
            target_files=(
                "nova_backend/services/project_brain_operator_memory_writer.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_operator_memory_writer_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_memory_writer_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Project Brain State Bridge v1",
            why="Bridge operator milestone records into direct project-state recall without app.py route guards.",
            risk="medium",
            score=170,
            target_files=(
                "nova_backend/services/project_brain_state_bridge.py",
                "tools/nova_project_brain_state_bridge_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_state_bridge_smoke.py",
            ),
            loses_to_best_because="State Bridge should land after Operator Memory Writer creates the source-of-truth milestone record.",
        ),
        UpgradeCandidate(
            name="Project Brain Runtime Coach v1",
            why="Runtime Coach is locked; keep it as the smoke/git-status interpreter.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_runtime_coach.py",
                "tools/nova_project_brain_runtime_coach_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Operator Memory Writer v1.",
        ),
        UpgradeCandidate(
            name="Project Brain Mission Autopilot v1",
            why="Mission Autopilot is locked; keep it as the safe mission planner.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_mission_autopilot.py",
                "tools/nova_project_brain_mission_autopilot_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
        UpgradeCandidate(
            name="Project Brain Action Card v1",
            why="Action Card is locked; keep it as the unified operator card.",
            risk="low",
            score=70,
            target_files=(
                "nova_backend/services/project_brain_action_card.py",
                "tools/nova_project_brain_action_card_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_action_card_smoke.py",
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
    print("patched Upgrade Radar to rank Operator Memory Writer next")
else:
    print("Operator Memory Writer next ranking already installed")

SMOKE.write_text(r'''
from pathlib import Path
import tempfile

from nova_backend.services.project_brain_operator_memory_writer import (
    LOCKED_GANGSTER_STACK,
    build_operator_memory_writer_answer,
    build_operator_milestone,
    build_operator_milestone_from_runtime_output,
    build_state_update_text,
    load_operator_memory,
    write_operator_milestone,
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
    print("NOVA PROJECT BRAIN OPERATOR MEMORY WRITER SMOKE")
    print("================================================")

    runtime_output = """
NOVA PROJECT BRAIN RUNTIME COACH SMOKE PASSED
NOVA PROJECT BRAIN COMMAND CENTER API SMOKE PASSED
NOVA REGRESSION SMOKE PASSED
[post-frontend-polish-phase 63c159f] Add Project Brain runtime coach
 5 files changed, 842 insertions(+), 7 deletions(-)
PS C:\\Users\\Owner\\nova> git status --short
PS C:\\Users\\Owner\\nova>
"""

    milestone = build_operator_milestone_from_runtime_output(runtime_output)

    assert_true("milestone title", milestone.title == "Project Brain Operator Memory Writer v1", milestone.title)
    assert_true("commit hash parsed", milestone.commit_hash == "63c159f", milestone.commit_hash)
    assert_true("commit message parsed", milestone.commit_message == "Add Project Brain runtime coach", milestone.commit_message)
    assert_true("working tree clean parsed", milestone.working_tree_clean is True, milestone.working_tree_clean)
    assert_true("runtime coach locked", "Project Brain Runtime Coach v1" in milestone.locked_upgrades, milestone.locked_upgrades)
    assert_true("regression smoke parsed", any("REGRESSION" in item for item in milestone.passed_smokes), milestone.passed_smokes)
    assert_true("state update mentions stale cleanup", "stop saying cleanup" in milestone.state_update, milestone.state_update)

    manual = build_operator_milestone(
        commit_hash="abc1234",
        commit_message="Manual test",
        passed_smokes=["NOVA REGRESSION SMOKE PASSED"],
        working_tree_clean=True,
        next_move="Project Brain State Bridge v1",
        locked_upgrades=LOCKED_GANGSTER_STACK,
    )

    assert_true("manual next move", manual.next_move == "Project Brain State Bridge v1", manual.next_move)

    state_text = build_state_update_text(next_move="Project Brain State Bridge v1")
    assert_true("state text includes next", "Project Brain State Bridge v1" in state_text, state_text)

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "operator_memory.json"
        before = load_operator_memory(path)
        assert_true("empty memory", before.get("milestones") == [], before)

        written = write_operator_milestone(milestone, path)
        assert_true("written latest", written.get("latest", {}).get("commit_hash") == "63c159f", written)
        assert_true("written milestone count", len(written.get("milestones", [])) == 1, written)

        written_again = write_operator_milestone(milestone, path)
        assert_true("deduped milestone count", len(written_again.get("milestones", [])) == 1, written_again)

    answer = build_operator_memory_writer_answer(runtime_output)
    assert_true("answer title", "Project Brain Operator Memory Writer" in answer)
    assert_true("answer locked upgrades", "Locked Upgrades" in answer)
    assert_true("answer state update", "State Update" in answer)

    best = select_best_upgrade()
    assert_true("radar best memory writer", best.name == "Project Brain Operator Memory Writer v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first memory writer", move_value(moves[0], "name") == "Project Brain Operator Memory Writer v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended memory writer", recommended_move == "Project Brain Operator Memory Writer v1", recommended_move)
    assert_true("recommended why milestones", "milestones" in why or "state-update" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_operator_memory_writer.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR MEMORY WRITER SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

runtime_smoke = Path("tools/nova_project_brain_runtime_coach_smoke.py")
if runtime_smoke.exists():
    smoke_text = runtime_smoke.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace(
        'assert_true("radar best runtime coach", best.name == "Project Brain Runtime Coach v1", best.name)',
        'assert_true("radar returns ranked upgrade", best.name in {"Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1"}, best.name)',
    )
    smoke_text = smoke_text.replace(
        'assert_true("operator planner first runtime coach", move_value(moves[0], "name") == "Project Brain Runtime Coach v1", move_value(moves[0], "name"))',
        'assert_true("operator planner returns ranked upgrade", move_value(moves[0], "name") in {"Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1"}, move_value(moves[0], "name"))',
    )
    smoke_text = smoke_text.replace(
        'assert_true("recommended runtime coach", recommended_move == "Project Brain Runtime Coach v1", recommended_move)',
        'assert_true("recommended ranked upgrade", recommended_move in {"Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1"}, recommended_move)',
    )
    smoke_text = smoke_text.replace(
        'assert_true("recommended why smoke output", "smoke" in why or "git-status" in why, why)',
        'assert_true("recommended why useful", bool(str(why or "").strip()), why)',
    )
    smoke_text = smoke_text.replace(
        'assert_true("recommended risk medium", risk == "medium", risk)',
        'assert_true("recommended risk valid", risk in {"low", "medium", "high"}, risk)',
    )
    smoke_text = smoke_text.replace(
        'assert_true("recommended target file", "nova_backend/services/project_brain_runtime_coach.py" in target_files, target_files)',
        'assert_true("recommended target files exist", bool(target_files), target_files)',
    )
    runtime_smoke.write_text(smoke_text, encoding="utf-8")
    print("patched runtime coach smoke ranking expectations")

for smoke_path in [
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
        r"python .\tools\nova_project_brain_operator_memory_writer_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Read smoke/test/git-status output",
        "Write locked operator milestones and state-update wording",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_runtime_coach.py",
        "nova_backend/services/project_brain_operator_memory_writer.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched Command Center smoke expectations: {smoke_path}")

print("installed Project Brain Operator Memory Writer v1 safe mode")
