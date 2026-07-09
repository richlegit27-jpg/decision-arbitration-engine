from __future__ import annotations

from pathlib import Path

from nova_backend.services.fallback_guard_cleanup_validation import (
    format_fallback_guard_cleanup_validation,
    validate_fallback_guard_cleanup,
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
    validation = validate_fallback_guard_cleanup(str(APP_PATH))
    text = format_fallback_guard_cleanup_validation(str(APP_PATH))

    assert_true("validation mode", validation.get("mode") == "fallback_guard_cleanup_validation")
    assert_true("validation status", validation.get("status") == "passed")

    results = {item["name"]: item for item in validation["results"]}

    assert_true("autonomy-plan result exists", "autonomy-plan" in results)
    assert_true("patch-build result exists", "patch-build" in results)

    assert_true("autonomy-plan adapter present", results["autonomy-plan"]["adapter_present"] is True)
    assert_true("autonomy-plan fallback gone", results["autonomy-plan"]["fallback_gone"] is True)
    assert_true("autonomy-plan validation passed", results["autonomy-plan"]["passed"] is True)

    assert_true("patch-build adapter present", results["patch-build"]["adapter_present"] is True)
    assert_true("patch-build fallback gone", results["patch-build"]["fallback_gone"] is True)
    assert_true("patch-build validation passed", results["patch-build"]["passed"] is True)

    assert_contains(
        "fallback guard cleanup validation text",
        text,
        [
            "Nova fallback guard cleanup validation",
            "Mode: fallback_guard_cleanup_validation",
            "Status: passed",
            "autonomy-plan",
            "patch-build",
            "Adapter present: True",
            "Old fallback gone: True",
            "Passed: True",
        ],
    )

    print("NOVA FALLBACK GUARD CLEANUP VALIDATION SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
