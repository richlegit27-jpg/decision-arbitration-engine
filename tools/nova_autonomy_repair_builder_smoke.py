from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_repair_builder.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_repair_builder_smoke_service",
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

    create_build = getattr(service, "create_autonomy_repair_build", None)
    format_build = getattr(service, "format_autonomy_repair_build", None)

    if not callable(create_build):
        raise AssertionError("create_autonomy_repair_build is missing")

    if not callable(format_build):
        raise AssertionError("format_autonomy_repair_build is missing")

    missing_output = """
FAILED: next command FAILED. Missing ['project-state']. Response was:
Next move:
- Wire patch-build command.
FAILED nova_project_state_smoke
"""

    text = format_build(missing_output)

    assert_contains(
        "missing text repair build",
        text,
        [
            "Nova supervised repair build",
            "Mode: repair_instructions_only",
            "Failure type: missing_expected_text",
            "Safety rules:",
            "Do not execute local commands automatically",
            "Files to inspect:",
            "data\\nova_project_state.json",
            "nova_backend\\services\\project_state_service.py",
            "PowerShell repair steps:",
            "Compile checks:",
            "Smokes:",
            "python .\\tools\\nova_project_state_smoke.py",
            "Commit commands:",
            "Rollback commands:",
            "Next step:",
        ],
    )

    hanging_output = """
PASS autonomy image command
PASS autonomy memory command
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\tools\\nova_autonomy_command_api_smoke.py", line 95, in main
    normal_payload = post_chat("explain APIs like I'm new", session_id)
KeyboardInterrupt
"""

    hanging_text = format_build(hanging_output)

    assert_contains(
        "hanging smoke repair build",
        hanging_text,
        [
            "interrupted_or_hanging_smoke",
            "tools\\nova_autonomy_command_api_smoke.py",
            "deterministic",
            "python -m py_compile .\\tools\\nova_autonomy_command_api_smoke.py",
            "python .\\tools\\nova_autonomy_command_api_smoke.py",
        ],
    )

    data = create_build(missing_output)

    for key in (
        "mode",
        "failure_type",
        "failure_summary",
        "likely_cause",
        "files_to_inspect",
        "manual_repair_steps",
        "compile_checks",
        "smokes",
        "commit_commands",
        "rollback_commands",
        "safety_rules",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "repair_instructions_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY REPAIR BUILDER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
