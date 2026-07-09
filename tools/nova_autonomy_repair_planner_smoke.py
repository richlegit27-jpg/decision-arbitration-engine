from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_repair_planner.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_repair_planner_smoke_service",
        str(SERVICE_PATH),
    )

    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {SERVICE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_contains(name: str, text: str, needles: list[str]) -> None:
    low = text.lower()
    missing = [needle for needle in needles if needle.lower() not in low]

    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")

    print(f"PASS {name}")


def main() -> int:
    service = load_service()

    create_plan = getattr(service, "create_autonomy_repair_plan", None)
    format_plan = getattr(service, "format_autonomy_repair_plan", None)

    if not callable(create_plan):
        raise AssertionError("create_autonomy_repair_plan is missing")

    if not callable(format_plan):
        raise AssertionError("format_autonomy_repair_plan is missing")

    hanging_output = """
PASS autonomy image command
PASS autonomy memory command
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\tools\\nova_autonomy_command_api_smoke.py", line 95, in main
    normal_payload = post_chat("explain APIs like I'm new", session_id)
KeyboardInterrupt
"""

    text = format_plan(hanging_output)

    assert_contains(
        "hanging smoke repair plan",
        text,
        [
            "Nova supervised repair proposal",
            "repair_proposal_only",
            "interrupted_or_hanging_smoke",
            "deterministic fast guard input",
            "tools\\nova_autonomy_command_api_smoke.py",
            "Do not edit files automatically",
            "Rollback plan:",
        ],
    )

    missing_output = """
FAILED: next command FAILED. Missing ['project-state']. Response was:
Next move:
- Wire patch-build command.
FAILED nova_project_state_smoke
"""

    missing_text = format_plan(missing_output)

    assert_contains(
        "missing text repair plan",
        missing_text,
        [
            "missing_expected_text",
            "project_state_service.py",
            "data\\nova_project_state.json",
            "tools\\nova_project_state_smoke.py",
            "expected word appears",
        ],
    )

    data = create_plan(missing_output)

    for key in (
        "mode",
        "failure_type",
        "failure_summary",
        "likely_cause",
        "files_to_inspect",
        "smallest_safe_repair",
        "patch_strategy",
        "tests",
        "rollback_plan",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "repair_proposal_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY REPAIR PLANNER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
