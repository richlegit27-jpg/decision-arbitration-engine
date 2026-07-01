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
        "command-registry:",
        "command_registry_command_smoke_001",
    )

    assistant = data.get("assistant_message") or {}
    text = str(assistant.get("text") or assistant.get("content") or "")

    assert_contains(
        "command-registry command",
        text,
        [
            "Nova autonomy command registry",
            "Mode: read_only_command_registry",
            "Status: locked_descriptions_only",
            "autonomy:",
            "autonomy-plan:",
            "patch-build:",
            "repair-plan:",
            "repair-build:",
            "workflow-catalog:",
            "autonomy-index:",
            "Do not execute local commands automatically",
            "Do not change route names",
            "Richard must run every command manually",
            "python .\\tools\\nova_memory_quality_smoke.py",
        ],
    )

    debug = data.get("debug") or {}

    if debug.get("route") != "command_registry_command":
        raise AssertionError(f"wrong route: {debug}")

    if debug.get("mode") != "read_only_command_registry":
        raise AssertionError(f"wrong mode: {debug}")

    match_data = post_chat(
        "command-registry: repair-build: FAILED nova_project_state_smoke",
        "command_registry_command_smoke_002",
    )

    match_assistant = match_data.get("assistant_message") or {}
    match_text = str(match_assistant.get("text") or match_assistant.get("content") or "")

    assert_contains(
        "command-registry matched command",
        match_text,
        [
            "Matched command:",
            "Command: repair-build:",
            "Route: repair_build_command",
            "Mode: repair_instructions_only",
            "nova_backend.services.autonomy_repair_builder",
            "python .\\tools\\nova_repair_build_command_api_smoke.py",
        ],
    )

    print("NOVA COMMAND REGISTRY COMMAND API SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
