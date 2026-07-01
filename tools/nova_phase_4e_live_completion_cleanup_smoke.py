from __future__ import annotations

import json
import sys
import time
from urllib import request, error


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


def nested(data: dict, *keys, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def text_of(data: dict) -> str:
    assistant = data.get("assistant_message")
    if isinstance(assistant, dict):
        return str(assistant.get("text") or assistant.get("content") or "")
    return str(data.get("text") or data.get("content") or "")


def route_of(data: dict) -> str:
    return str(nested(data, "debug", "route_taken", default="") or nested(data, "debug", "route", default=""))


def execution_of(data: dict) -> dict:
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
    session_id = f"phase_4e_live_completion_{int(time.time())}"

    start = post_chat("auto-plan clean up a test notes file", session_id)
    assert_true("mission starts", "Execution mission started" in text_of(start), text_of(start))

    post_chat("next", session_id)
    post_chat("next", session_id)
    completed = post_chat("next", session_id)
    completed_state = execution_of(completed)

    assert_true("mission complete flag", completed_state.get("complete") is True, str(completed_state))
    assert_true("mission complete status", str(completed_state.get("status")).lower() == "complete", str(completed_state))
    assert_true("mission not waiting", completed_state.get("waiting") is False, str(completed_state))

    status = post_chat("what are we working on?", session_id)
    status_text = text_of(status)

    assert_true("completed route", route_of(status) == "completed_execution_status", json.dumps(status, indent=2))
    assert_true("completed suppresses project recall", nested(status, "debug", "suppressed_project_state_recall") is True, json.dumps(status, indent=2))
    assert_true("completed says no active mission", "No active mission is running" in status_text, status_text)
    assert_true("completed remembers last mission", "Last completed mission: clean up a test notes file" in status_text, status_text)
    assert_true("completed does not show stale waiting step", "Status: waiting" not in status_text and "Step 3/3" not in status_text, status_text)

    pong = post_chat("say only pong", session_id)
    pong_text = text_of(pong).strip().lower()

    assert_true("pong route chat", route_of(pong) == "chat", json.dumps(pong, indent=2))
    assert_true("pong priority", nested(pong, "debug", "direct_pong_priority") is True, json.dumps(pong, indent=2))
    assert_true("pong text", pong_text == "pong", pong_text)

    print("NOVA PHASE 4E LIVE COMPLETION CLEANUP SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
