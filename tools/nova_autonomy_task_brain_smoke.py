from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_task_brain.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_task_brain_smoke_service",
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

    create_brief = getattr(service, "create_autonomy_task_brief", None)
    format_brief = getattr(service, "format_autonomy_task_brief", None)

    if not callable(create_brief):
        raise AssertionError("create_autonomy_task_brief is missing")

    if not callable(format_brief):
        raise AssertionError("format_autonomy_task_brief is missing")

    image_text = format_brief("make Nova better at image descriptions")
    assert_contains(
        "image autonomy brief",
        image_text,
        [
            "nova autonomy task brief",
            "proposal_only",
            "nova_backend/services/chat_service.py",
            "static/js/mobile/nova-mobile-images.js",
            "risks",
            "tests",
            "rollback",
        ],
    )

    memory_text = format_brief("improve project memory recall and checkpoint context")
    assert_contains(
        "memory autonomy brief",
        memory_text,
        [
            "project_state_service.py",
            "nova_memory_quality_smoke.py",
            "stale checkpoint",
            "safety rules",
        ],
    )

    session_text = format_brief("fix mobile sessions switching safely")
    assert_contains(
        "session autonomy brief",
        session_text,
        [
            "nova-mobile-sessions.js",
            "session changes",
            "node --check",
        ],
    )

    brief = create_brief("improve autonomy planner")
    data = brief.to_dict()

    for key in (
        "goal",
        "mode",
        "summary",
        "likely_files",
        "risks",
        "safety_rules",
        "tests",
        "rollback",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"brief missing key: {key}")

    if data["mode"] != "proposal_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY TASK BRAIN SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
