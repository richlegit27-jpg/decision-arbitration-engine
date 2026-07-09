from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_patch_planner.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_patch_planner_smoke_service",
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
        raise AssertionError(
            f"{name} FAILED. Missing {missing}. Text was:\n{text}"
        )

    print(f"PASS {name}")


def main() -> int:
    service = load_service()

    create_plan = getattr(service, "create_autonomy_patch_plan", None)
    format_plan = getattr(service, "format_autonomy_patch_plan", None)

    if not callable(create_plan):
        raise AssertionError("create_autonomy_patch_plan is missing")

    if not callable(format_plan):
        raise AssertionError("format_autonomy_patch_plan is missing")

    image_text = format_plan("make Nova better at image descriptions")
    assert_contains(
        "image patch plan",
        image_text,
        [
            "nova supervised patch proposal",
            "proposal_only",
            "smallest safe patch strategy",
            "nova_backend/services/chat_service.py",
            "static/js/mobile/nova-mobile-images.js",
            "image prompts",
            "commit plan",
            "rollback plan",
        ],
    )

    memory_text = format_plan("improve project memory checkpoint recall")
    assert_contains(
        "memory patch plan",
        memory_text,
        [
            "project_state_service.py",
            "nova_memory_quality_smoke.py",
            "stale checkpoint",
            "project-context",
        ],
    )

    autonomy_text = format_plan("improve autonomy planner safely")
    assert_contains(
        "autonomy patch plan",
        autonomy_text,
        [
            "proposal-only",
            "autonomy_patch_planner.py",
            "nova_autonomy_patch_planner_smoke.py",
        ],
    )

    data = create_plan("fix mobile sessions switching safely")

    for key in (
        "goal",
        "mode",
        "likely_files",
        "risks",
        "patch_strategy",
        "tests",
        "commit_plan",
        "rollback_plan",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "proposal_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY PATCH PLANNER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
