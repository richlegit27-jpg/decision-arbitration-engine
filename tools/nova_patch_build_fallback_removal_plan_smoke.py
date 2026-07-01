from __future__ import annotations

from pathlib import Path

from nova_backend.services.patch_build_fallback_removal_plan import (
    create_patch_build_fallback_removal_plan,
    format_patch_build_fallback_removal_plan,
)


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def assert_contains(name, text, needles):
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")
    print(f"PASS {name}")


def main():
    plan = create_patch_build_fallback_removal_plan(str(APP_PATH))
    text = format_patch_build_fallback_removal_plan(str(APP_PATH))

    assert_true("plan mode", plan.get("mode") == "patch_build_fallback_removal_plan_only")
    assert_true("plan status", plan.get("status") == "review_only_no_behavior_change")
    assert_true("adapter present", plan.get("adapter_present") is True)
    assert_true("fallback present", plan.get("fallback_present") is True)
    assert_true("adapter before fallback", plan.get("adapter_before_fallback") is True)

    assert_contains(
        "patch-build fallback removal plan text",
        text,
        [
            "Nova patch-build fallback removal plan",
            "Mode: patch_build_fallback_removal_plan_only",
            "Status: review_only_no_behavior_change",
            "Command: patch-build",
            "Route: patch_build_command",
            "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
            "nova_patch_build_adapter_guard_20260701",
            "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
            "_nova_extract_patch_build_goal_20260630",
            "nova_patch_build_command_guard_20260630",
            "Adapter present: True",
            "Old fallback present: True",
            "Adapter before fallback: True",
            "Do not delete anything in this planning step.",
            "Do not remove adapter-owned patch-build guard.",
            "Next step:",
        ],
    )

    print("NOVA PATCH BUILD FALLBACK REMOVAL PLAN SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
