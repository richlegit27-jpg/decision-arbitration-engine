from __future__ import annotations

import json
from urllib import request


API_URL = "http://127.0.0.1:5001/api/chat"


def post_chat(user_text: str, session_id: str) -> dict:
    payload = {
        "user_text": user_text,
        "session_id": session_id,
        "attachments": [],
    }

    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def assert_contains(name: str, text: str, needles: list[str]) -> None:
    low = str(text or "").lower()
    missing = [needle for needle in needles if needle.lower() not in low]

    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")

    print(f"PASS {name}")


def main() -> int:
    failed_output = """FAILED: next command FAILED. Missing ['project-state']. Response was:
Next move:
- Wire patch-build command.
FAILED nova_project_state_smoke
"""

    data = post_chat(
        "repair-plan: " + failed_output,
        "repair_plan_command_smoke_001",
    )

    assistant = data.get("assistant_message") or {}
    text = str(assistant.get("text") or assistant.get("content") or "")

    assert_contains(
        "repair-plan command",
        text,
        [
            "Nova supervised repair proposal",
            "Mode: repair_proposal_only",
            "Failure type: missing_expected_text",
            "Files to inspect:",
            "data\\nova_project_state.json",
            "Smallest safe repair:",
            "Patch strategy:",
            "Do not execute commands automatically",
            "Tests:",
            "Rollback plan:",
        ],
    )

    debug = data.get("debug") or {}

    if debug.get("route") != "repair_plan_command":
        raise AssertionError(f"wrong route: {debug}")

    if debug.get("mode") != "repair_proposal_only":
        raise AssertionError(f"wrong mode: {debug}")

    print("NOVA REPAIR PLAN COMMAND API SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
