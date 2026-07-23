from __future__ import annotations

import json
import sys
import time
import atexit
from pathlib import Path
from urllib import request, error


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:5001"


def post_chat(message: str, session_id: str) -> dict:
    payload = {
        "message": message,
        "session_id": session_id,
        "attachments": [],
    }

    req = request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except error.URLError as exc:
        raise AssertionError(f"API request failed for {message!r}: {exc}") from exc

def delete_session(session_id: str) -> dict:
    payload = {
        "session_id": session_id,
    }

    req = request.Request(
        f"{BASE_URL}/api/sessions/delete",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=20) as resp:
        return json.loads(
            resp.read().decode(
                "utf-8",
                errors="replace",
            )
        )


def get_nested(data: dict, *keys, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def assistant_text(data: dict) -> str:
    assistant = data.get("assistant_message")
    if isinstance(assistant, dict):
        return str(assistant.get("text") or assistant.get("content") or "")
    return str(data.get("text") or data.get("content") or "")


def route_taken(data: dict) -> str:
    return str(get_nested(data, "debug", "route_taken", default="") or get_nested(data, "debug", "route", default=""))


def execution_state(data: dict) -> dict:
    state = data.get("execution_state")
    if isinstance(state, dict):
        return state

    assistant = data.get("assistant_message")
    if isinstance(assistant, dict) and isinstance(assistant.get("execution_state"), dict):
        return assistant.get("execution_state")

    return {}


def assert_true(name: str, condition: bool, detail: str = ""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main() -> int:
    session_id = f"phase_4b_live_autonomy_lifecycle_{int(time.time())}"

    def cleanup_execution():
        try:
            post_chat(
                "stop",
                session_id,
            )
        except Exception:
            pass

        try:
            delete_session(
                session_id,
            )
        except Exception:
            pass

    atexit.register(
        cleanup_execution
    )

    start = post_chat("auto-plan clean up a test notes file", session_id)
    start_text = assistant_text(start)
    start_state = execution_state(start)

    assert_true("mission created", "Execution mission started" in start_text, start_text)
    assert_true("mission goal set", start_state.get("goal") == "clean up a test notes file", str(start_state))
    assert_true("mission starts step 1", int(start_state.get("current_index", 0) or 0) == 0, str(start_state))

    status = post_chat("what are we working on?", session_id)
    status_text = assistant_text(status)

    assert_true("status route active execution", route_taken(status) == "active_execution_status", json.dumps(status, indent=2))
    assert_true("status suppresses project recall", get_nested(status, "debug", "suppressed_project_state_recall") is True, json.dumps(status, indent=2))
    assert_true("status says active mission", "Active mission: clean up a test notes file" in status_text, status_text)
    assert_true("status says step 1", "Step 1/3" in status_text, status_text)

    advanced = post_chat("next", session_id)
    advanced_state = execution_state(advanced)

    assert_true("next advances mission", int(advanced_state.get("current_index", 0) or 0) == 1, str(advanced_state))
    assert_true("next keeps mission goal", advanced_state.get("goal") == "clean up a test notes file", str(advanced_state))

    next_status = post_chat("what comes next?", session_id)
    next_status_text = assistant_text(next_status)

    assert_true("next status route active execution", route_taken(next_status) == "active_execution_status", json.dumps(next_status, indent=2))
    assert_true("next status suppresses project recall", get_nested(next_status, "debug", "suppressed_project_state_recall") is True, json.dumps(next_status, indent=2))
    assert_true("next status says step 2", "Step 2/3" in next_status_text, next_status_text)
    assert_true("next status not stale project recall", "Phase 3H" not in next_status_text, next_status_text)

    normal = post_chat("say only pong", session_id)
    normal_text = assistant_text(normal).strip().lower()

    assert_true("normal chat still works", normal_text == "pong", normal_text)

    print("NOVA PHASE 4B LIVE AUTONOMY LIFECYCLE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
