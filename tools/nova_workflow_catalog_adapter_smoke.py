from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "workflow_catalog_adapter.py"


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
        "_nova_workflow_catalog_adapter_smoke_service",
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

    extract = getattr(service, "extract_workflow_catalog_input", None)
    build = getattr(service, "build_workflow_catalog_response", None)

    if not callable(extract):
        raise AssertionError("extract_workflow_catalog_input is missing")

    if not callable(build):
        raise AssertionError("build_workflow_catalog_response is missing")

    if extract("hello normal chat") is not None:
        raise AssertionError("normal chat should not match workflow-catalog")

    if extract("workflow-catalog: repair-build failed smoke") != "repair-build failed smoke":
        raise AssertionError("workflow-catalog extraction failed")

    if extract("workflow: memory quality") != "memory quality":
        raise AssertionError("workflow alias extraction failed")

    fake = FakeSessionService()

    result = build(
        {
            "user_text": "workflow-catalog: repair-build failed smoke with project-state recall",
            "session_id": "workflow_catalog_adapter_smoke_001",
            "attachments": [],
        },
        fake,
    )

    if not isinstance(result, dict):
        raise AssertionError("adapter did not return response dict")

    debug = result.get("debug") or {}

    if debug.get("route") != "workflow_catalog_command":
        raise AssertionError(f"wrong route: {debug}")

    if debug.get("mode") != "manual_workflow_catalog_only":
        raise AssertionError(f"wrong mode: {debug}")

    text = str((result.get("assistant_message") or {}).get("text") or "")

    assert_contains(
        "adapter workflow catalog response",
        text,
        [
            "workflow",
            "manual",
            "repair",
            "smoke",
            "memory",
        ],
    )

    if len(fake.messages.get("workflow_catalog_adapter_smoke_001", [])) != 2:
        raise AssertionError("expected adapter to store 2 messages")

    print("NOVA WORKFLOW CATALOG ADAPTER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
