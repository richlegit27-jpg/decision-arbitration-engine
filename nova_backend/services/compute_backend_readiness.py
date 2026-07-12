from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(
    os.environ.get("NOVA_DATA_DIR")
    or PROJECT_ROOT / "data"
).resolve()

MEMORY_FILE = DATA_DIR / "nova_memory.json"
EXECUTION_FILE = DATA_DIR / "nova_execution_state.json"
SESSION_FILE = DATA_DIR / "nova_sessions.json"


def load_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        text = path.read_text(
            encoding="utf-8",
        ).strip()

        if not text:
            return {}

        return json.loads(
            text
        )

    except Exception as exc:
        return {
            "__error__": str(exc),
            "__path__": str(path),
        }


def extract_items(raw: Any) -> list[dict]:
    if isinstance(raw, list):
        return [
            item
            for item in raw
            if isinstance(item, dict)
        ]

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
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

        return [
            value
            for value in raw.values()
            if isinstance(value, dict)
        ]

    return []


def count_items(raw: Any) -> int:
    return len(
        extract_items(raw)
    )


def store_is_healthy(raw: Any) -> bool:
    if raw is None:
        return False

    if isinstance(raw, dict):
        return "__error__" not in raw

    return isinstance(raw, list)


def module_available(
    module_name: str,
) -> bool:
    try:
        return (
            importlib.util.find_spec(
                module_name
            )
            is not None
        )

    except Exception:
        return False


def compute_execution_percent(
    execution_raw: Any,
) -> float:
    if execution_raw is None:
        return 100.0

    if (
        isinstance(execution_raw, dict)
        and "__error__" in execution_raw
    ):
        return 0.0

    if (
        not isinstance(execution_raw, dict)
        or not execution_raw
    ):
        return 100.0

    status = str(
        execution_raw.get("status")
        or ""
    ).lower().strip()

    steps = (
        execution_raw.get("steps")
        or []
    )

    if (
        execution_raw.get("complete") is True
        or status in (
            "complete",
            "completed",
            "done",
        )
    ):
        return 100.0

    if (
        status in (
            "",
            "idle",
            "none",
        )
        and not steps
        and not execution_raw.get("waiting")
        and not execution_raw.get("goal")
        and not execution_raw.get("current_step")
    ):
        return 100.0

    if isinstance(steps, list) and steps:
        completed = 0

        for step in steps:
            if not isinstance(step, dict):
                continue

            step_status = str(
                step.get("status")
                or ""
            ).lower().strip()

            if step_status in (
                "complete",
                "completed",
                "done",
                "passed",
            ):
                completed += 1

        return round(
            completed
            /
            len(steps)
            *
            100.0,
            1,
        )

    return 50.0


def compute_memory_percent(
    memory_raw: Any,
) -> float:
    service_ready = module_available(
        "nova_backend.services.memory_service"
    )

    return (
        100.0
        if service_ready
        and store_is_healthy(memory_raw)
        else 0.0
    )


def compute_agency_percent(
    execution_raw: Any,
) -> float:
    del execution_raw

    required = (
        "nova_backend.services.autonomy_task_brain",
        "nova_backend.services.chat_execution_service",
    )

    return (
        100.0
        if all(
            module_available(name)
            for name in required
        )
        else 0.0
    )


def compute_planner_percent(
    execution_raw: Any,
) -> float:
    del execution_raw

    return (
        100.0
        if module_available(
            "nova_backend.services.planner_service"
        )
        else 0.0
    )


def compute_session_percent(
    session_raw: Any,
) -> float:
    return (
        100.0
        if store_is_healthy(session_raw)
        else 0.0
    )


def build_backend_readiness() -> dict:
    execution = load_json(
        EXECUTION_FILE
    )

    memory = load_json(
        MEMORY_FILE
    )

    sessions = load_json(
        SESSION_FILE
    )

    execution_percent = compute_execution_percent(
        execution
    )

    memory_percent = compute_memory_percent(
        memory
    )

    agency_percent = compute_agency_percent(
        execution
    )

    planner_percent = compute_planner_percent(
        execution
    )

    session_percent = compute_session_percent(
        sessions
    )

    overall = round(
        (
            execution_percent
            +
            memory_percent
            +
            agency_percent
            +
            planner_percent
            +
            session_percent
        )
        /
        5.0,
        2,
    )

    return {
        "execution_percent": execution_percent,
        "memory_percent": memory_percent,
        "agency_percent": agency_percent,
        "planner_percent": planner_percent,
        "session_percent": session_percent,
        "overall_backend_readiness": overall,
        "execution_records": count_items(execution),
        "memory_items": count_items(memory),
        "session_records": count_items(sessions),
        "metric_semantics":
            "operational_capability_not_activity",
        "data_dir": str(DATA_DIR),
        "data_sources": {
            "execution": str(EXECUTION_FILE),
            "memory": str(MEMORY_FILE),
            "sessions": str(SESSION_FILE),
        },
    }
