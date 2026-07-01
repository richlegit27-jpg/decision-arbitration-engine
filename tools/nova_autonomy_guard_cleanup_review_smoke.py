from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_guard_cleanup_review.py"
APP_PATH = ROOT / "app.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_guard_cleanup_review_smoke_service",
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

    create_review = getattr(service, "create_autonomy_guard_cleanup_review", None)
    format_review = getattr(service, "format_autonomy_guard_cleanup_review", None)

    if not callable(create_review):
        raise AssertionError("create_autonomy_guard_cleanup_review is missing")

    if not callable(format_review):
        raise AssertionError("format_autonomy_guard_cleanup_review is missing")

    text = format_review(str(APP_PATH))

    assert_contains(
        "guard cleanup review",
        text,
        [
            "Nova autonomy guard cleanup review",
            "Mode: guard_cleanup_review_only",
            "Status: no_behavior_change_review",
            "app.py",
            "Command guard markers found:",
            "Before-request guards found:",
            "Safe migration plan:",
            "command-registry",
            "Do not centralize all guards in one commit",
            "Do not rename routes, modes, commands, or prefixes",
            "python .\\tools\\nova_command_registry_command_api_smoke.py",
            "python .\\tools\\nova_memory_quality_smoke.py",
            "Next step:",
        ],
    )

    data = create_review(str(APP_PATH))

    for key in (
        "mode",
        "status",
        "target_file",
        "guard_marker_count",
        "before_request_guard_count",
        "guard_markers",
        "before_request_guards",
        "route_presence",
        "mode_presence",
        "marker_presence",
        "missing_routes",
        "missing_modes",
        "missing_markers",
        "review_summary",
        "safe_migration_plan",
        "required_smokes_before_any_refactor",
        "forbidden_actions",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "guard_cleanup_review_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    if data["status"] != "no_behavior_change_review":
        raise AssertionError(f"wrong status: {data['status']}")

    if data["before_request_guard_count"] < 1:
        raise AssertionError("expected at least one before_request guard")

    print("NOVA AUTONOMY GUARD CLEANUP REVIEW SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
