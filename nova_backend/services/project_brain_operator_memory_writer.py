
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
