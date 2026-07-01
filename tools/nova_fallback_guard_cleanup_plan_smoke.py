from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

RUNTIME_SURFACES = [
    APP,
    ROOT / "nova_backend" / "services" / "autonomy_command_registry.py",
    ROOT / "nova_backend" / "services" / "autonomy_command_registry_plan.py",
    ROOT / "nova_backend" / "services" / "autonomy_plan_adapter.py",
    ROOT / "nova_backend" / "services" / "patch_build_adapter.py",
    ROOT / "nova_backend" / "services" / "repair_plan_adapter.py",
]

ADAPTER_REQUIRED = [
    "autonomy_plan_command",
    "patch_build_command",
    "repair_plan_command",
    "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
    "nova_autonomy_plan_adapter_guard_20260701",
    "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
    "nova_patch_build_adapter_guard_20260701",
    "NOVA_REPAIR_PLAN_ADAPTER_GUARD_20260701",
    "nova_repair_plan_adapter_guard_20260701",
]

FALLBACK_FORBIDDEN_IN_APP = [
    "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_autonomy_plan_goal_20260630",
    "nova_autonomy_plan_command_guard_20260630",
    "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
    "_nova_extract_patch_build_goal_20260630",
    "nova_patch_build_command_guard_20260630",
    "NOVA_REPAIR_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_repair_plan_goal_20260630",
    "nova_repair_plan_command_guard_20260630",
]


def read_existing(paths):
    chunks = []

    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))

    return "\n".join(chunks)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    assert_true("app.py exists", APP.exists())

    app_text = APP.read_text(encoding="utf-8", errors="replace")
    runtime_text = read_existing(RUNTIME_SURFACES)

    missing_adapters = [
        marker
        for marker in ADAPTER_REQUIRED
        if marker not in runtime_text
    ]

    forbidden_present = [
        marker
        for marker in FALLBACK_FORBIDDEN_IN_APP
        if marker in app_text
    ]

    assert_true(
        "adapter guards preserved",
        not missing_adapters,
        f"missing={missing_adapters}",
    )

    assert_true(
        "old fallback app guards removed",
        not forbidden_present,
        f"present={forbidden_present}",
    )

    print("NOVA FALLBACK GUARD CLEANUP PLAN SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
