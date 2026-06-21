# C:\Users\Owner\nova\nova_backend\services\chat_service_backend_readiness.py
# NOVA_BACKEND_READINESS_ENDPOINT_20260609
#
# Simple API helper to return current backend readiness as JSON.

from flask import jsonify
from pathlib import Path
import json

ROOT = Path(r"C:\Users\Owner\nova")
READINESS_FILE = ROOT / "data/nova_memory_refined.json"  # still reads refined memory
EXECUTION_FILE = ROOT / "data/nova_execution_state.json"
SESSION_FILE = ROOT / "data/nova_sessions.json"

def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8").strip() or "{}")
    except:
        return {}

def get_backend_readiness():
    from nova_backend.services.compute_backend_readiness import (
        compute_execution_percent,
        compute_memory_percent,
        compute_agency_percent,
        compute_planner_percent,
        compute_session_percent,
    )

    execution = load_json(EXECUTION_FILE)
    memory = load_json(READINESS_FILE)
    sessions = load_json(SESSION_FILE)

    execution_percent = compute_execution_percent(execution)

    # NOVA_FORCE_EXECUTION_PERCENT_AFTER_COMPUTE_20260608
    # Readiness should mean: is the backend blocked right now?
    # If there is no active execution mission, execution is ready.
    if isinstance(execution, dict):
        _status = str(execution.get("status") or "").lower().strip()
        _steps = execution.get("steps") or []
        _waiting = bool(execution.get("waiting"))
        _goal = str(execution.get("goal") or "").strip()
        _current_step = execution.get("current_step")
        _complete = bool(execution.get("complete"))

        if (
            _complete
            or _status in ("complete", "completed", "done")
            or (
                _status in ("", "idle", "none")
                and not _steps
                and not _waiting
                and not _goal
                and not _current_step
            )
        ):
            execution_percent = 100.0

    memory_percent = compute_memory_percent(memory)
    agency_percent = compute_agency_percent(execution)
    planner_percent = compute_planner_percent(execution)
    session_percent = compute_session_percent(sessions)

    overall = round(
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

    return jsonify({
        "execution_percent": execution_percent,
        "memory_percent": memory_percent,
        "agency_percent": agency_percent,
        "planner_percent": planner_percent,
        "session_percent": session_percent,
        "overall_backend_readiness": overall,
        "execution_records": len(execution) if isinstance(execution, dict) else 0,
        "memory_items": len(memory.get("memory", [])) if isinstance(memory, dict) else 0,
        "session_records": len(sessions.get("sessions", [])) if isinstance(sessions, dict) else 0,
    })

