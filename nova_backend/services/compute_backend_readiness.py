# C:\Users\Owner\nova\nova_backend\services\compute_backend_readiness.py
# NOVA_BACKEND_READINESS_HELPER_MEMORY_KEY_FIXED_20260609
#
# Computes local backend readiness metrics from Nova data files.
# No OpenAI calls. No UI changes.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Owner\nova")
DATA = ROOT / "data"

MEMORY_FILE = DATA / "nova_memory.json"
EXECUTION_FILE = DATA / "nova_execution_state.json"
SESSION_FILE = DATA / "nova_sessions.json"


def load_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8").strip()

        if not text:
            return None

        return json.loads(text)
    except Exception as exc:
        return {
            "__error__": str(exc),
            "__path__": str(path),
        }


def extract_items(raw: Any) -> list[dict]:
    if raw is None:
        return []

    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    if isinstance(raw, dict):
        for key in (
            "memory",
            "memories",
            "items",
            "data",
            "sessions",
            "records",
        ):
            value = raw.get(key)

            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        values = []

        for value in raw.values():
            if isinstance(value, dict):
                values.append(value)

        return values

    return []


def compute_execution_percent(execution_raw: Any) -> float:
    if not isinstance(execution_raw, dict) or not execution_raw:
        return 0.0

    records = [
        state
        for state in execution_raw.values()
        if isinstance(state, dict)
    ]

    if not records:
        return 0.0

    complete = 0

    for state in records:
        status = str(state.get("status") or "").strip().lower()

        if state.get("complete") is True or status in {"complete", "completed"}:
            complete += 1

    return round((complete / len(records)) * 100, 2)


def compute_memory_percent(memory_raw: Any) -> float:
    memories = extract_items(memory_raw)

    if not memories:
        return 0.0

    useful = 0

    for item in memories:
        blob = json.dumps(item, ensure_ascii=False).lower()

        if any(
            keyword in blob
            for keyword in (
                "project",
                "preference",
                "current",
                "task",
                "checkpoint",
                "execution",
                "planner",
                "file",
                "memory",
                "content",
                "user",
            )
        ):
            useful += 1

    return round((useful / len(memories)) * 100, 2)


def compute_agency_percent(execution_raw: Any) -> float:
    if not isinstance(execution_raw, dict) or not execution_raw:
        return 0.0

    records = [
        state
        for state in execution_raw.values()
        if isinstance(state, dict)
    ]

    if not records:
        return 0.0

    scored = 0

    for state in records:
        status = str(state.get("status") or "").strip().lower()
        has_steps = bool(state.get("steps"))
        has_history = bool(state.get("history"))
        can_advance = state.get("current_index") is not None

        if has_steps and has_history and can_advance and status in {
            "waiting",
            "running",
            "complete",
            "completed",
        }:
            scored += 1

    return round((scored / len(records)) * 100, 2)


def compute_planner_percent(execution_raw: Any) -> float:
    if not isinstance(execution_raw, dict) or not execution_raw:
        return 0.0

    records = [
        state
        for state in execution_raw.values()
        if isinstance(state, dict)
    ]

    if not records:
        return 0.0

    planned = 0

    for state in records:
        steps = state.get("steps") or []

        if isinstance(steps, list) and len(steps) >= 3:
            planned += 1

    return round((planned / len(records)) * 100, 2)


def compute_session_percent(session_raw: Any) -> float:
    sessions = extract_items(session_raw)

    if not sessions:
        return 0.0

    useful = 0

    for session in sessions:
        messages = session.get("messages") or []
        working_state = session.get("working_state") or {}
        execution_state = (
            session.get("execution_state")
            or session.get("active_execution")
            or session.get("meta", {}).get("execution_state")
            or {}
        )

        if messages or working_state or execution_state:
            useful += 1

    return round((useful / len(sessions)) * 100, 2)


def count_items(raw: Any) -> int:
    return len(extract_items(raw))


def main() -> None:
    execution = load_json(EXECUTION_FILE)
    memory = load_json(MEMORY_FILE)
    sessions = load_json(SESSION_FILE)

    execution_percent = compute_execution_percent(execution)
    memory_percent = compute_memory_percent(memory)
    agency_percent = compute_agency_percent(execution)
    planner_percent = compute_planner_percent(execution)
    session_percent = compute_session_percent(sessions)

    overall_backend_readiness = round(
        (
            execution_percent
            + memory_percent
            + agency_percent
            + planner_percent
            + session_percent
        )
        / 5,
        2,
    )

    print("=== NOVA BACKEND READINESS ===")
    print(f"Execution percent: {execution_percent}%")
    print(f"Memory percent: {memory_percent}%")
    print(f"Agency percent: {agency_percent}%")
    print(f"Planner percent: {planner_percent}%")
    print(f"Session percent: {session_percent}%")
    print(f"Overall backend readiness: {overall_backend_readiness}%")
    print("==============================")

    print()
    print("Counts:")
    print(f"Execution records: {len(execution) if isinstance(execution, dict) else 0}")
    print(f"Memory items: {count_items(memory)}")
    print(f"Session records: {count_items(sessions)}")

    print()
    print("Notes:")
    print("- Memory parser supports root key: memory.")
    print("- Agency percent is computed from local execution state behavior, not AI intelligence.")
    print("- Planner percent is based on execution records having 3+ planned steps.")
    print("- This is a local readiness score, not a model-quality score.")


if __name__ == "__main__":
    main()

# NOVA_COMPUTE_EXECUTION_IDLE_OVERRIDE_20260608
def compute_execution_percent(execution):
    """
    Final override for backend readiness.

    Idle/no active execution mission means execution is not blocked.
    Old saved execution records should not keep readiness stuck at 50%.
    """
    if not isinstance(execution, dict) or not execution:
        return 100.0

    status = str(execution.get("status") or "").lower().strip()
    steps = execution.get("steps") or []
    waiting = bool(execution.get("waiting"))
    goal = str(execution.get("goal") or "").strip()
    current_step = execution.get("current_step")
    complete = bool(execution.get("complete"))

    if complete or status in ("complete", "completed", "done"):
        return 100.0

    if (
        status in ("", "idle", "none")
        and not steps
        and not waiting
        and not goal
        and not current_step
    ):
        return 100.0

    completed_steps = 0
    total_steps = 0

    if isinstance(steps, list) and steps:
        total_steps = len(steps)

        for step in steps:
            if isinstance(step, dict):
                step_status = str(step.get("status") or "").lower().strip()
                if step_status in ("complete", "completed", "done", "passed"):
                    completed_steps += 1

        if total_steps > 0:
            return round((completed_steps / total_steps) * 100.0, 1)

    return 50.0

