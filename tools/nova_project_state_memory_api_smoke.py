import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5001"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    payload = {
        "message": "what are we working on now",
        "session_id": "memory_project_state_regression_smoke_001",
        "attachments": [],
    }

    response = requests.post(
        f"{BASE}/api/chat",
        json=payload,
        timeout=20,
    )
    assert_true("api status", response.status_code == 200, response.text[:500])

    data = response.json()
    assistant = data.get("assistant_message") or {}
    debug = data.get("debug") or {}

    text = str(assistant.get("text") or "")
    content = str(assistant.get("content") or "")
    top_text = str(data.get("text") or "")

    expected = "Current Nova project state:"
    route_taken = str(debug.get("route_taken") or data.get("route_taken") or "")

    assert_true("project state text", expected in text, text[:300])
    assert_true("project state content", expected in content, content[:300])
    assert_true("project state top text", expected in top_text, top_text[:300])
    assert_true(
        "project state route",
        route_taken == "project_state_current_memory_direct_recall",
        route_taken,
    )

    print("")
    print("NOVA PROJECT STATE MEMORY API SMOKE PASSED")


if __name__ == "__main__":
    main()
