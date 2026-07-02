from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_runtime_coach.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_runtime_coach_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RuntimeCoachReport:
    title: str
    status: str
    passed_count: int
    failed_count: int
    has_traceback: bool
    working_tree_clean: bool
    recommended_action: str
    exact_next_command: str
    why: str
    stop_rule: str
    risk: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "status": self.status,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "has_traceback": self.has_traceback,
            "working_tree_clean": self.working_tree_clean,
            "recommended_action": self.recommended_action,
            "exact_next_command": self.exact_next_command,
            "why": self.why,
            "stop_rule": self.stop_rule,
            "risk": self.risk,
        }


def _clean(value: str) -> str:
    return str(value or "").strip()


def _count_passes(text: str) -> int:
    return len(re.findall(r"(?m)^\s*PASS\b", text or ""))


def _count_failures(text: str) -> int:
    explicit = len(re.findall(r"(?m)^\s*FAIL\b", text or ""))
    assertion = len(re.findall(r"AssertionError:", text or ""))
    traceback = len(re.findall(r"Traceback \(most recent call last\):", text or ""))
    import_error = len(re.findall(r"ImportError:", text or ""))
    type_error = len(re.findall(r"TypeError:", text or ""))
    syntax_error = len(re.findall(r"SyntaxError:", text or ""))

    return explicit + assertion + traceback + import_error + type_error + syntax_error


def _has_traceback(text: str) -> bool:
    value = text or ""
    return (
        "Traceback (most recent call last):" in value
        or "AssertionError:" in value
        or "TypeError:" in value
        or "ImportError:" in value
        or "SyntaxError:" in value
    )


def _working_tree_clean(text: str) -> bool:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    status_indexes = [
        index for index, line in enumerate(lines)
        if "git status --short" in line
    ]

    if not status_indexes:
        return False

    last = status_indexes[-1]
    following = []

    for line in lines[last + 1:]:
        stripped = line.strip()

        if stripped.startswith("PS "):
            continue

        if not stripped:
            continue

        if stripped.startswith("M ") or stripped.startswith("??") or stripped.startswith("A ") or stripped.startswith("D "):
            following.append(stripped)

    return not following


def _has_dirty_status(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*(M|A|D|\?\?)\s+", text or ""))


def _commit_hash(text: str) -> str:
    match = re.search(r"\[[^\]]+\s+([0-9a-f]{7,})\]\s+(.+)", text or "")
    if match:
        return match.group(1)
    return ""


def coach_runtime_output(pasted_output: str) -> RuntimeCoachReport:
    text = str(pasted_output or "")
    passes = _count_passes(text)
    failures = _count_failures(text)
    traceback = _has_traceback(text)
    dirty = _has_dirty_status(text)
    clean = _working_tree_clean(text)
    commit = _commit_hash(text)

    if failures or traceback:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="failed",
            passed_count=passes,
            failed_count=max(1, failures),
            has_traceback=traceback,
            working_tree_clean=clean,
            recommended_action="patch",
            exact_next_command=r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
            why="A smoke/test produced a failure or traceback; use Auto-Debug Brain and Patch Planner before continuing.",
            stop_rule="Stop immediately. Do not commit. Patch only the failing service layer, then rerun the focused smoke.",
            risk="medium",
        )

    if dirty and not commit:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="green_uncommitted",
            passed_count=passes,
            failed_count=0,
            has_traceback=False,
            working_tree_clean=False,
            recommended_action="commit",
            exact_next_command="git status --short",
            why="Smokes appear green, but the working tree has uncommitted changes.",
            stop_rule="Commit the green batch before starting another upgrade.",
            risk="low",
        )

    if commit and clean:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="locked_clean",
            passed_count=passes,
            failed_count=0,
            has_traceback=False,
            working_tree_clean=True,
            recommended_action="next_upgrade",
            exact_next_command=r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            why="The batch was committed and git status is clean.",
            stop_rule="Safe to start exactly one next bounded service-level upgrade.",
            risk="low",
        )

    if passes and clean:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="green_clean",
            passed_count=passes,
            failed_count=0,
            has_traceback=False,
            working_tree_clean=True,
            recommended_action="next_upgrade",
            exact_next_command=r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            why="Focused smokes passed and the working tree is clean.",
            stop_rule="Safe to continue with one bounded upgrade.",
            risk="low",
        )

    return RuntimeCoachReport(
        title="Project Brain Runtime Coach v1",
        status="unknown",
        passed_count=passes,
        failed_count=0,
        has_traceback=False,
        working_tree_clean=clean,
        recommended_action="inspect",
        exact_next_command="git status --short",
        why="Runtime Coach needs a clearer smoke/test or git-status output.",
        stop_rule="Inspect state before patching or committing.",
        risk="medium",
    )


def build_runtime_coach_dict(pasted_output: str) -> dict:
    return coach_runtime_output(pasted_output).as_dict()


def build_runtime_coach_answer(pasted_output: str) -> str:
    report = coach_runtime_output(pasted_output)

    return "\n".join([
        "Project Brain Runtime Coach:",
        f"Status: {report.status}",
        f"Passed Count: {report.passed_count}",
        f"Failed Count: {report.failed_count}",
        f"Has Traceback: {report.has_traceback}",
        f"Working Tree Clean: {report.working_tree_clean}",
        f"Recommended Action: {report.recommended_action}",
        f"Exact Next Command: {report.exact_next_command}",
        f"Why: {report.why}",
        f"Stop Rule: {report.stop_rule}",
        f"Risk: {report.risk}",
    ])
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_RUNTIME_COACH_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_RUNTIME_COACH_NEXT_V1_20260702
# After Mission Autopilot is locked, rank Runtime Coach as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Project Brain Runtime Coach v1",
            why=(
                "Read smoke/test/git-status output and decide whether to patch, commit, stop, "
                "or continue with the next bounded upgrade."
            ),
            risk="medium",
            score=170,
            target_files=(
                "nova_backend/services/project_brain_runtime_coach.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_runtime_coach_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Project Brain Operator Memory Writer v1",
            why="Write locked upgrade milestones back into Project Brain memory/state after green commits.",
            risk="medium",
            score=160,
            target_files=(
                "nova_backend/services/project_brain_operator_memory_writer.py",
                "tools/nova_project_brain_operator_memory_writer_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_memory_writer_smoke.py",
            ),
            loses_to_best_because="Memory Writer should land after Runtime Coach can decide when a commit is truly locked.",
        ),
        UpgradeCandidate(
            name="Project Brain Mission Autopilot v1",
            why="Mission Autopilot is locked; keep it as the safe mission planner.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_mission_autopilot.py",
                "tools/nova_project_brain_mission_autopilot_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Runtime Coach v1.",
        ),
        UpgradeCandidate(
            name="Project Brain Action Card v1",
            why="Action Card is locked; keep it as the unified operator card.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_action_card.py",
                "tools/nova_project_brain_action_card_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_action_card_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Operator Command Launcher is locked; keep it as the command-block generator.",
            risk="low",
            score=70,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
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
    print("patched Upgrade Radar to rank Runtime Coach next")
else:
    print("Runtime Coach next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_runtime_coach import (
    build_runtime_coach_answer,
    build_runtime_coach_dict,
    coach_runtime_output,
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
    print("NOVA PROJECT BRAIN RUNTIME COACH SMOKE")
    print("======================================")

    failure_output = """
PASS first
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\tools\\x.py", line 10, in main
    run()
TypeError: thing() got an unexpected keyword argument 'changed_files'
"""

    failure = coach_runtime_output(failure_output)
    assert_true("failure status", failure.status == "failed", failure.status)
    assert_true("failure recommends patch", failure.recommended_action == "patch", failure.recommended_action)
    assert_true("failure stop rule", "Do not commit" in failure.stop_rule, failure.stop_rule)

    dirty_output = """
PASS smoke
NOVA REGRESSION SMOKE PASSED
PS C:\\Users\\Owner\\nova> git status --short
 M nova_backend/services/project_brain_runtime_coach.py
?? tools/nova_project_brain_runtime_coach_smoke.py
"""

    dirty = coach_runtime_output(dirty_output)
    assert_true("dirty status", dirty.status == "green_uncommitted", dirty.status)
    assert_true("dirty recommends commit", dirty.recommended_action == "commit", dirty.recommended_action)

    clean_commit_output = """
PASS smoke
NOVA REGRESSION SMOKE PASSED
[post-frontend-polish-phase abc1234] Add Project Brain runtime coach
 3 files changed, 100 insertions(+)
PS C:\\Users\\Owner\\nova> git status --short
PS C:\\Users\\Owner\\nova>
"""

    locked = coach_runtime_output(clean_commit_output)
    locked_dict = build_runtime_coach_dict(clean_commit_output)
    answer = build_runtime_coach_answer(clean_commit_output)

    assert_true("locked status", locked.status == "locked_clean", locked.status)
    assert_true("locked recommends next", locked.recommended_action == "next_upgrade", locked.recommended_action)
    assert_true("locked clean", locked.working_tree_clean is True, locked.working_tree_clean)
    assert_true("dict status", locked_dict.get("status") == "locked_clean", locked_dict)
    assert_true("answer title", "Project Brain Runtime Coach" in answer)
    assert_true("answer next command", "Exact Next Command" in answer)

    best = select_best_upgrade()
    assert_true("radar best runtime coach", best.name == "Project Brain Runtime Coach v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first runtime coach", move_value(moves[0], "name") == "Project Brain Runtime Coach v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended runtime coach", recommended_move == "Project Brain Runtime Coach v1", recommended_move)
    assert_true("recommended why smoke output", "smoke" in why or "git-status" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_runtime_coach.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN RUNTIME COACH SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_mission_autopilot_smoke.py"),
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Project Brain Mission Autopilot v1", "Project Brain Runtime Coach v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
        r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Use the Action Card to choose one bounded service-level move",
        "Read smoke/test/git-status output",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_mission_autopilot.py",
        "nova_backend/services/project_brain_runtime_coach.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Runtime Coach v1")
