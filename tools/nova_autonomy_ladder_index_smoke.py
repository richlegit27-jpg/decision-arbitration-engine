from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_ladder_index.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_ladder_index_smoke_service",
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

    create_index = getattr(service, "create_autonomy_ladder_index", None)
    format_index = getattr(service, "format_autonomy_ladder_index", None)

    if not callable(create_index):
        raise AssertionError("create_autonomy_ladder_index is missing")

    if not callable(format_index):
        raise AssertionError("format_autonomy_ladder_index is missing")

    text = format_index()

    assert_contains(
        "ladder index",
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
            "No file edits",
            "Do not execute local commands automatically",
            "Richard must run every command manually",
            "python .\\tools\\nova_memory_quality_smoke.py",
            "Next recommended manual command:",
        ],
    )

    data = create_index()

    for key in (
        "mode",
        "status",
        "commands",
        "global_safety_rules",
        "recommended_order",
        "core_smokes",
        "next_recommended_manual_command",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    commands = [item.get("command") for item in data["commands"]]

    for command in (
        "autonomy:",
        "autonomy-plan:",
        "patch-build:",
        "repair-plan:",
        "repair-build:",
        "workflow-catalog:",
    ):
        if command not in commands:
            raise AssertionError(f"missing command: {command}")

    if data["mode"] != "autonomy_ladder_index_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY LADDER INDEX SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
