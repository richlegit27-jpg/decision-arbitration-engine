from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "repair_build_adapter.py"


class FakeSessionService:
    def __init__(self) -> None:
        self.active_session_id = "fake_active_session"
        self.messages = {}

    def add_message(self, session_id, message):
        self.messages.setdefault(session_id, []).append(message)

    def get_session(self, session_id):
        return {
            "id": session_id,
            "messages": self.messages.get(session_id, []),
        }


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_repair_build_adapter_smoke_service",
        str(SERVICE_PATH),
    )

    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {SERVICE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_contains(name: str, text: str, needles: list[str]) -> None:
    low = str(text or "").lower()
    missing = [needle for needle in needles if needle.lower() not in low]

    if missing:
        raise AssertionError(f"{name} FAILED. Missing {missing}. Text was:\n{text}")

    print(f"PASS {name}")


def main() -> int:
    service = load_service()

    extract = getattr(service, "extract_repair_build_input", None)
    build = getattr(service, "build_repair_build_response", None)

    if not callable(extract):
        raise AssertionError("extract_repair_build_input is missing")

    if not callable(build):
        raise AssertionError("build_repair_build_response is missing")

    if extract("hello normal chat") is not None:
        raise AssertionError("normal chat should not match repair-build")

    if extract("repair-build: FAILED nova_project_state_smoke") != "FAILED nova_project_state_smoke":
        raise AssertionError("repair-build extraction failed")

    if extract("build repair: FAILED api smoke") != "FAILED api smoke":
        raise AssertionError("build repair alias extraction failed")

    fake = FakeSessionService()

    result = build(
        {
            "user_text": "repair-build: FAILED nova_project_state_smoke missing project-state",
            "session_id": "repair_build_adapter_smoke_001",
            "attachments": [],
        },
        fake,
    )

    if not isinstance(result, dict):
        raise AssertionError("adapter did not return response dict")

    debug = result.get("debug") or {}

    if debug.get("route") != "repair_build_command":
        raise AssertionError(f"wrong route: {debug}")

    if debug.get("mode") != "repair_instructions_only":
        raise AssertionError(f"wrong mode: {debug}")

    text = str((result.get("assistant_message") or {}).get("text") or "")

    assert_contains(
        "adapter repair-build response",
        text,
        [
            "Nova supervised repair build",
            "Mode: repair_instructions_only",
            "Failure type:",
            "PowerShell repair steps:",
            "python",
            "Smokes:",
            "Rollback commands:",
            "Richard must run every command manually",
        ],
    )

    if len(fake.messages.get("repair_build_adapter_smoke_001", [])) != 2:
        raise AssertionError("expected adapter to store 2 messages")

    print("NOVA REPAIR BUILD ADAPTER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
