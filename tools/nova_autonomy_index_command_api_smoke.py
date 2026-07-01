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
    data = post_chat(
        "autonomy-index:",
        "autonomy_index_command_smoke_001",
    )

    assistant = data.get("assistant_message") or {}
    text = str(assistant.get("text") or assistant.get("content") or "")

    assert_contains(
        "autonomy-index command",
        text,
        [
            "Nova autonomy ladder index",
            "Mode: autonomy_ladder_index_only",
            "Status: locked_manual_autonomy_ladder",
            "autonomy:",
            "autonomy-plan:",
            "patch-build:",
            "repair-plan:",
            "repair-build:",
            "workflow-catalog:",
            "Do not execute local commands automatically",
            "Richard must run every command manually",
            "python .\\tools\\nova_memory_quality_smoke.py",
            "Next recommended manual command:",
        ],
    )

    debug = data.get("debug") or {}

    if debug.get("route") != "autonomy_index_command":
        raise AssertionError(f"wrong route: {debug}")

    if debug.get("mode") != "autonomy_ladder_index_only":
        raise AssertionError(f"wrong mode: {debug}")

    print("NOVA AUTONOMY INDEX COMMAND API SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
