
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
        + "launch command blocks, run safe mission logic, coach runtime output, "
        + "and write operator milestones. "
        + "Decision Engine can classify failures, rank moves, and choose the next safe operator action."
    )

    blocker = (
        "No active Project Brain intelligence blocker is open. Protected baseline: Project Brain context builder, freshness snapshot, and answer-quality policy are locked. Remaining cleanup/consolidation is a known risk, "
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
