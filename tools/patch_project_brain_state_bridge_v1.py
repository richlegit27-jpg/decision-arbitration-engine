from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_state_bridge.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_state_bridge_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path


DEFAULT_OPERATOR_MEMORY_PATH = Path("data/project_brain_operator_memory.json")
DEFAULT_NOVA_MEMORY_PATH = Path("data/nova_memory.json")


@dataclass(frozen=True)
class StateBridgeRecord:
    title: str
    current_checkpoint: str
    current_blocker: str
    next_move: str
    locked_stack: tuple[str, ...]
    source: str
    created_at_utc: str

    def as_dict(self) -> dict:
        data = asdict(self)
        data["locked_stack"] = list(self.locked_stack)
        return data


def _clean(value: str) -> str:
    return str(value or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def _load_json(path: str | Path, default):
    file_path = Path(path)

    if not file_path.exists():
        return default

    try:
        return json.loads(file_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def load_latest_operator_milestone(
    operator_memory_path: str | Path = DEFAULT_OPERATOR_MEMORY_PATH,
) -> dict:
    data = _load_json(operator_memory_path, {"milestones": []})

    if not isinstance(data, dict):
        return {}

    latest = data.get("latest")
    if isinstance(latest, dict):
        return latest

    milestones = data.get("milestones")
    if isinstance(milestones, list) and milestones:
        for item in reversed(milestones):
            if isinstance(item, dict):
                return item

    return {}


def build_state_bridge_record(
    milestone: dict | None = None,
    next_move: str = "Project Brain State Bridge v1",
) -> StateBridgeRecord:
    item = milestone or load_latest_operator_milestone()

    locked = _dedupe(
        item.get("locked_upgrades", [])
        if isinstance(item, dict)
        else []
    )

    if not locked:
        locked = (
            "Project Brain Upgrade Radar v1",
            "Auto-Debug Brain v1",
            "Self-Test Selector v1",
            "Patch Planner v1",
            "Operator Command Launcher v1",
            "Project Brain Action Card v1",
            "Project Brain Mission Autopilot v1 safe mode",
            "Project Brain Runtime Coach v1",
            "Project Brain Operator Memory Writer v1",
        )

    move = _clean(next_move)
    if isinstance(item, dict):
        move = _clean(item.get("next_move")) or move

    checkpoint = (
        "Project Brain gangster intelligence stack is locked through "
        + ", ".join(locked)
        + ". Command Center can rank upgrades, classify failures, plan patches, select smokes, "
        + "launch command blocks, run safe mission logic, coach runtime output, and write operator milestones."
    )

    blocker = (
        "No active Project Brain intelligence blocker is open. Remaining cleanup/consolidation is a known risk, "
        "but it is not the active next move while State Bridge is syncing the operator milestone state."
    )

    return StateBridgeRecord(
        title="Project Brain State Bridge v1",
        current_checkpoint=checkpoint,
        current_blocker=blocker,
        next_move=move,
        locked_stack=locked,
        source="project_brain_operator_memory_writer",
        created_at_utc=_utc_now(),
    )


def build_direct_recall_state_text(
    milestone: dict | None = None,
    next_move: str = "Project Brain State Bridge v1",
) -> str:
    record = build_state_bridge_record(
        milestone=milestone,
        next_move=next_move,
    )

    return (
        "Current Nova project state: Richard is working on the local Nova Flask app with Joe. "
        f"Current checkpoint: {record.current_checkpoint} "
        f"Current blocker: {record.current_blocker} "
        f"Next move: {record.next_move}. "
        "Direct project-state recall should use this State Bridge record instead of stale cleanup wording."
    )


def _memory_item(text: str, record: StateBridgeRecord) -> dict:
    now = _utc_now()

    return {
        "id": "project_brain_state_bridge_current",
        "key": "current_project_state",
        "type": "project_state",
        "category": "project_state",
        "source": "project_brain_state_bridge",
        "title": record.title,
        "text": text,
        "content": text,
        "value": text,
        "importance": 1.0,
        "priority": 999,
        "pinned": True,
        "tags": [
            "nova",
            "project_state",
            "project_brain",
            "state_bridge",
            "gangster_stack",
        ],
        "created_at": now,
        "updated_at": now,
        "created_at_utc": now,
        "updated_at_utc": now,
        "metadata": {
            "current_checkpoint": record.current_checkpoint,
            "current_blocker": record.current_blocker,
            "next_move": record.next_move,
            "locked_stack": list(record.locked_stack),
            "source": record.source,
        },
    }


def _upsert_into_list(items: list, item: dict) -> list:
    result = []
    replaced = False

    for existing in items:
        if not isinstance(existing, dict):
            result.append(existing)
            continue

        if (
            existing.get("id") == item["id"]
            or existing.get("key") == item["key"]
            or existing.get("source") == item["source"]
        ):
            if not replaced:
                result.append(item)
                replaced = True
            continue

        result.append(existing)

    if not replaced:
        result.append(item)

    return result


def write_state_bridge_memory(
    memory_path: str | Path = DEFAULT_NOVA_MEMORY_PATH,
    operator_memory_path: str | Path = DEFAULT_OPERATOR_MEMORY_PATH,
    next_move: str = "Project Brain State Bridge v1",
) -> dict:
    milestone = load_latest_operator_milestone(operator_memory_path)
    record = build_state_bridge_record(
        milestone=milestone,
        next_move=next_move,
    )
    text = build_direct_recall_state_text(
        milestone=milestone,
        next_move=next_move,
    )
    item = _memory_item(text, record)

    path = Path(memory_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = _load_json(path, {"memories": []})

    if isinstance(data, list):
        data = _upsert_into_list(data, item)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "shape": "list",
            "item": item,
            "memory": data,
        }

    if not isinstance(data, dict):
        data = {"memories": []}

    if isinstance(data.get("memories"), list):
        data["memories"] = _upsert_into_list(data.get("memories", []), item)
    elif isinstance(data.get("items"), list):
        data["items"] = _upsert_into_list(data.get("items", []), item)
    elif isinstance(data.get("entries"), list):
        data["entries"] = _upsert_into_list(data.get("entries", []), item)
    else:
        data["memories"] = [item]

    data["project_brain_state_bridge"] = item
    data["current_project_state"] = item
    data["updated_at_utc"] = _utc_now()

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "shape": "dict",
        "item": item,
        "memory": data,
    }


def build_state_bridge_answer(
    memory_path: str | Path = DEFAULT_NOVA_MEMORY_PATH,
    operator_memory_path: str | Path = DEFAULT_OPERATOR_MEMORY_PATH,
    next_move: str = "Project Brain State Bridge v1",
    write: bool = False,
) -> str:
    milestone = load_latest_operator_milestone(operator_memory_path)
    record = build_state_bridge_record(
        milestone=milestone,
        next_move=next_move,
    )
    text = build_direct_recall_state_text(
        milestone=milestone,
        next_move=next_move,
    )

    written = False
    if write:
        write_state_bridge_memory(
            memory_path=memory_path,
            operator_memory_path=operator_memory_path,
            next_move=next_move,
        )
        written = True

    return "\n".join([
        "Project Brain State Bridge:",
        f"Written: {written}",
        f"Next Move: {record.next_move}",
        "Locked Stack:",
        *[f"- {item}" for item in record.locked_stack],
        f"Direct Recall Text: {text}",
    ])
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_STATE_BRIDGE_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_STATE_BRIDGE_NEXT_V1_20260702
# After Operator Memory Writer is locked, rank State Bridge as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Project Brain State Bridge v1",
            why=(
                "Bridge operator milestone records into direct project-state recall so stale cleanup wording "
                "stops overriding the locked gangster upgrade stack."
            ),
            risk="medium",
            score=190,
            target_files=(
                "nova_backend/services/project_brain_state_bridge.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_state_bridge_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_state_bridge_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Project Brain State Recall Refresh v1",
            why="Teach direct project-state recall to prefer the State Bridge record over stale cleanup memory.",
            risk="medium",
            score=180,
            target_files=(
                "nova_backend/services/project_brain_state_bridge.py",
                "nova_backend/services/project_brain_freshness_snapshot.py",
                "tools/nova_project_brain_state_recall_refresh_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_state_recall_refresh_smoke.py",
            ),
            loses_to_best_because="State Bridge should land first so recall refresh has a clean source record.",
        ),
        UpgradeCandidate(
            name="Project Brain Operator Memory Writer v1",
            why="Operator Memory Writer is locked; keep it as the milestone writer.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_operator_memory_writer.py",
                "tools/nova_project_brain_operator_memory_writer_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_memory_writer_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is State Bridge v1.",
        ),
        UpgradeCandidate(
            name="Project Brain Runtime Coach v1",
            why="Runtime Coach is locked; keep it as the smoke/git-status interpreter.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_runtime_coach.py",
                "tools/nova_project_brain_runtime_coach_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
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
    print("patched Upgrade Radar to rank State Bridge next")
else:
    print("State Bridge next ranking already installed")

SMOKE.write_text(r'''
from pathlib import Path
import json
import tempfile

from nova_backend.services.project_brain_state_bridge import (
    build_direct_recall_state_text,
    build_state_bridge_answer,
    build_state_bridge_record,
    load_latest_operator_milestone,
    write_state_bridge_memory,
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
    print("NOVA PROJECT BRAIN STATE BRIDGE SMOKE")
    print("=====================================")

    milestone = {
        "next_move": "Project Brain State Bridge v1",
        "locked_upgrades": [
            "Project Brain Upgrade Radar v1",
            "Auto-Debug Brain v1",
            "Self-Test Selector v1",
            "Patch Planner v1",
            "Operator Command Launcher v1",
            "Project Brain Action Card v1",
            "Project Brain Mission Autopilot v1 safe mode",
            "Project Brain Runtime Coach v1",
            "Project Brain Operator Memory Writer v1",
        ],
    }

    record = build_state_bridge_record(milestone=milestone)
    text = build_direct_recall_state_text(milestone=milestone)

    assert_true("record title", record.title == "Project Brain State Bridge v1", record.title)
    assert_true("record next move", record.next_move == "Project Brain State Bridge v1", record.next_move)
    assert_true("record locked memory writer", "Project Brain Operator Memory Writer v1" in record.locked_stack, record.locked_stack)
    assert_true("text mentions gangster", "gangster intelligence stack" in text, text)
    assert_true("text avoids active cleanup", "Next move: Start Project Brain cleanup/consolidation" not in text, text)
    assert_true("text next state bridge", "Next move: Project Brain State Bridge v1" in text, text)

    with tempfile.TemporaryDirectory() as temp_dir:
        operator_path = Path(temp_dir) / "operator_memory.json"
        memory_path = Path(temp_dir) / "nova_memory.json"

        operator_path.write_text(
            json.dumps({"latest": milestone, "milestones": [milestone]}, indent=2),
            encoding="utf-8",
        )
        memory_path.write_text(json.dumps({"memories": []}, indent=2), encoding="utf-8")

        latest = load_latest_operator_milestone(operator_path)
        assert_true("latest milestone loaded", latest.get("next_move") == "Project Brain State Bridge v1", latest)

        written = write_state_bridge_memory(
            memory_path=memory_path,
            operator_memory_path=operator_path,
            next_move="Project Brain State Bridge v1",
        )
        item = written.get("item", {})

        assert_true("memory item project state", item.get("type") == "project_state", item)
        assert_true("memory item pinned", item.get("pinned") is True, item)
        assert_true("memory item source", item.get("source") == "project_brain_state_bridge", item)
        assert_true("memory item next", "Project Brain State Bridge v1" in item.get("text", ""), item)

        answer = build_state_bridge_answer(
            memory_path=memory_path,
            operator_memory_path=operator_path,
            write=True,
        )

        assert_true("answer title", "Project Brain State Bridge" in answer)
        assert_true("answer written", "Written: True" in answer)
        assert_true("answer direct recall text", "Direct Recall Text" in answer)

    best = select_best_upgrade()
    assert_true("radar best state bridge", best.name == "Project Brain State Bridge v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first state bridge", move_value(moves[0], "name") == "Project Brain State Bridge v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended state bridge", recommended_move == "Project Brain State Bridge v1", recommended_move)
    assert_true("recommended why direct recall", "direct project-state recall" in why or "stale cleanup" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_state_bridge.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN STATE BRIDGE SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_operator_memory_writer_smoke.py"),
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_operator_memory_writer_smoke.py",
        r"python .\tools\nova_project_brain_state_bridge_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Write locked operator milestones and state-update wording",
        "Bridge operator milestone records into direct project-state recall",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_operator_memory_writer.py",
        "nova_backend/services/project_brain_state_bridge.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain State Bridge v1")
