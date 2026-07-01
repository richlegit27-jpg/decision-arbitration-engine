from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


ADAPTER_REQUIRED = [
    "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
    "nova_autonomy_plan_adapter_guard_20260701",
    "autonomy_plan_command",
    "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
    "nova_patch_build_adapter_guard_20260701",
    "patch_build_command",
]


FALLBACK_FORBIDDEN = [
    "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_autonomy_plan_goal_20260630",
    "nova_autonomy_plan_command_guard_20260630",
    "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
    "_nova_extract_patch_build_goal_20260630",
    "nova_patch_build_command_guard_20260630",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    text = APP_PATH.read_text(encoding="utf-8-sig")

    missing_adapters = [item for item in ADAPTER_REQUIRED if item not in text]
    forbidden_fallbacks = [item for item in FALLBACK_FORBIDDEN if item in text]

    assert_true("adapter guards preserved", not missing_adapters, f"missing={missing_adapters}")
    assert_true("old fallback guards removed", not forbidden_fallbacks, f"still_present={forbidden_fallbacks}")

    print("NOVA FALLBACK GUARD CLEANUP PLAN SMOKE PASSED")
    print("Mode: post-removal compatibility validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
