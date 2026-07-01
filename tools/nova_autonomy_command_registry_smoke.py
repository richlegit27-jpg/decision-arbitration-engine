from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_command_registry.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_command_registry_smoke_service",
        str(SERVICE_PATH),
    )

    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {SERVICE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_contains(name: str, text: str, needles: list[str]) -> None:
    low = str(text or "").lower()
    missing = [needle for needle in needles if needle.lower() not in low]

    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")

    print(f"PASS {name}")


def main() -> int:
    service = load_service()

    create_registry = getattr(service, "create_autonomy_command_registry", None)
    format_registry = getattr(service, "format_autonomy_command_registry", None)
    find_command = getattr(service, "find_autonomy_command", None)
    list_commands = getattr(service, "list_autonomy_commands", None)

    for name, value in (
        ("create_autonomy_command_registry", create_registry),
        ("format_autonomy_command_registry", format_registry),
        ("find_autonomy_command", find_command),
        ("list_autonomy_commands", list_commands),
    ):
        if not callable(value):
            raise AssertionError(f"{name} is missing")

    text = format_registry()

    assert_contains(
        "read-only command registry",
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
            "autonomy_command",
            "autonomy_plan_command",
            "patch_build_command",
            "repair_plan_command",
            "repair_build_command",
            "workflow_catalog_command",
            "autonomy_index_command",
            "Do not execute local commands automatically",
            "Do not change route names",
            "Richard must run every command manually",
            "python .\\tools\\nova_memory_quality_smoke.py",
        ],
    )

    match_text = format_registry("repair-build: FAILED nova_project_state_smoke")

    assert_contains(
        "registry command match",
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

    data = create_registry()

    for key in (
        "mode",
        "status",
        "commands",
        "safety_rules",
        "core_verification",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "read_only_command_registry":
        raise AssertionError(f"wrong mode: {data['mode']}")

    commands = [item.get("command") for item in list_commands()]

    for command in (
        "autonomy:",
        "autonomy-plan:",
        "patch-build:",
        "repair-plan:",
        "repair-build:",
        "workflow-catalog:",
        "autonomy-index:",
    ):
        if command not in commands:
            raise AssertionError(f"missing command: {command}")

    if not find_command("autonomy index:"):
        raise AssertionError("alias lookup failed for autonomy index:")

    if not find_command("workflow: repair"):
        raise AssertionError("alias lookup failed for workflow:")

    print("NOVA AUTONOMY COMMAND REGISTRY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
