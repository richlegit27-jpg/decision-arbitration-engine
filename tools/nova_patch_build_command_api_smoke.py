from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


def load_app():
    spec = importlib.util.spec_from_file_location(
        "_nova_patch_build_command_app",
        str(APP_PATH),
    )

    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {APP_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def assert_contains(name: str, text: str, needles: list[str]) -> None:
    low = str(text or "").lower()
    missing = [needle for needle in needles if needle.lower() not in low]

    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")

    print(f"PASS {name}")


def main() -> int:
    app = load_app()

    with app.test_client() as client:
        response = client.post(
            "/api/chat",
            json={
                "user_text": "patch-build: make Nova better at image descriptions",
                "session_id": "patch_build_command_smoke_001",
                "attachments": [],
            },
        )

    if response.status_code != 200:
        raise AssertionError(
            f"patch-build request failed with {response.status_code}: {response.get_data(as_text=True)}"
        )

    data = response.get_json(silent=True) or {}
    assistant = data.get("assistant_message") or {}
    text = str(assistant.get("text") or assistant.get("content") or "")

    assert_contains(
        "patch-build command",
        text,
        [
            "Nova supervised patch build",
            "Goal: make Nova better at image descriptions",
            "Mode: instructions_only",
            "Safety rules:",
            "Files to change:",
            "PowerShell patch steps:",
            "Compile checks:",
            "Smokes:",
            "Commit commands:",
            "Rollback commands:",
            "Do not execute local commands automatically",
        ],
    )

    debug = data.get("debug") or {}

    if debug.get("route") != "patch_build_command":
        raise AssertionError(f"wrong route: {debug}")

    if debug.get("mode") != "instructions_only":
        raise AssertionError(f"wrong mode: {debug}")

    print("NOVA PATCH BUILD COMMAND API SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
