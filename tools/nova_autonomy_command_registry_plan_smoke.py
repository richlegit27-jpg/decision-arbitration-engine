from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_command_registry_plan.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_command_registry_plan_smoke_service",
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

    create_plan = getattr(service, "create_autonomy_command_registry_plan", None)
    format_plan = getattr(service, "format_autonomy_command_registry_plan", None)

    if not callable(create_plan):
        raise AssertionError("create_autonomy_command_registry_plan is missing")

    if not callable(format_plan):
        raise AssertionError("format_autonomy_command_registry_plan is missing")

    text = format_plan()

    assert_contains(
        "command registry plan",
        text,
        [
            "Nova autonomy command registry plan",
            "Mode: registry_plan_only",
            "Status: no_behavior_change_plan",
            "app.py",
            "autonomy:",
            "autonomy-plan:",
            "patch-build:",
            "repair-plan:",
            "repair-build:",
            "workflow-catalog:",
            "autonomy-index:",
            "Do not change route names",
            "Do not change response mode names",
            "Do not execute commands automatically",
            "Richard must run every command manually",
            "python .\\tools\\nova_autonomy_index_command_api_smoke.py",
            "python .\\tools\\nova_memory_quality_smoke.py",
            "Do not centralize all guards in one untested commit",
            "Rollback commands:",
        ],
    )

    data = create_plan()

    for key in (
        "mode",
        "status",
        "purpose",
        "owner_files",
        "locked_commands",
        "non_negotiable_invariants",
        "migration_steps",
        "verification_smokes",
        "rollback_commands",
        "forbidden_actions",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    commands = [item.get("command") for item in data["locked_commands"]]

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

    if data["mode"] != "registry_plan_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY COMMAND REGISTRY PLAN SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
