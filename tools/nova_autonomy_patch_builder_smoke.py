from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_patch_builder.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_patch_builder_smoke_service",
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

    create_build = getattr(service, "create_autonomy_patch_build", None)
    format_build = getattr(service, "format_autonomy_patch_build", None)

    if not callable(create_build):
        raise AssertionError("create_autonomy_patch_build is missing")

    if not callable(format_build):
        raise AssertionError("format_autonomy_patch_build is missing")

    image_text = format_build("make Nova better at image descriptions")

    assert_contains(
        "image patch build",
        image_text,
        [
            "Nova supervised patch build",
            "Mode: instructions_only",
            "Safety rules:",
            "Do not edit files automatically",
            "PowerShell patch steps:",
            "nova_backend/services/chat_service.py",
            "static/js/mobile/nova-mobile-images.js",
            "Compile checks:",
            "Smokes:",
            "Commit commands:",
            "Rollback commands:",
        ],
    )

    data = create_build("improve autonomy planner safely")

    for key in (
        "goal",
        "mode",
        "safety_rules",
        "files_to_change",
        "powershell_steps",
        "compile_checks",
        "smokes",
        "commit_commands",
        "rollback_commands",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "instructions_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    if not any("do not execute" in str(rule).lower() for rule in data["safety_rules"]):
        raise AssertionError("missing no-execution safety rule")

    print("NOVA AUTONOMY PATCH BUILDER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
