from __future__ import annotations

from pathlib import Path

from nova_backend.services.autonomy_fallback_guard_cleanup_plan import (
    create_fallback_guard_cleanup_plan,
    format_fallback_guard_cleanup_plan,
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
    plan = create_fallback_guard_cleanup_plan(str(APP_PATH))
    text = format_fallback_guard_cleanup_plan(str(APP_PATH))

    assert_true("plan mode", plan.get("mode") == "no_delete_fallback_guard_cleanup_plan")
    assert_true("plan status", plan.get("status") == "review_only_no_behavior_change")

    candidates = plan.get("candidates") or []
    by_command = {item.get("command"): item for item in candidates}

    assert_true("autonomy-plan candidate exists", "autonomy-plan" in by_command)
    assert_true("patch-build candidate exists", "patch-build" in by_command)

    assert_true(
        "autonomy-plan cleanup candidate",
        by_command["autonomy-plan"].get("cleanup_candidate") is True,
        by_command["autonomy-plan"],
    )
    assert_true(
        "patch-build cleanup candidate",
        by_command["patch-build"].get("cleanup_candidate") is True,
        by_command["patch-build"],
    )

    assert_contains(
        "fallback cleanup plan text",
        text,
        [
            "Nova autonomy fallback guard cleanup plan",
            "Mode: no_delete_fallback_guard_cleanup_plan",
            "Status: review_only_no_behavior_change",
            "Cleanup candidates:",
            "autonomy-plan",
            "patch-build",
            "nova_autonomy_plan_adapter_guard_20260701",
            "nova_autonomy_plan_command_guard_20260630",
            "nova_patch_build_adapter_guard_20260701",
            "nova_patch_build_command_guard_20260630",
            "Do not delete fallback guards in this plan step.",
            "Do not edit app.py in this plan step.",
            "Required smokes before any future guard removal:",
            "Next step:",
        ],
    )

    print("NOVA FALLBACK GUARD CLEANUP PLAN SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
