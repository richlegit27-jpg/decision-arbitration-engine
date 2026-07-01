from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "autonomy_workflow_catalog.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_autonomy_workflow_catalog_smoke_service",
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

    create_catalog = getattr(service, "create_safe_workflow_catalog", None)
    format_catalog = getattr(service, "format_safe_workflow_catalog", None)

    if not callable(create_catalog):
        raise AssertionError("create_safe_workflow_catalog is missing")

    if not callable(format_catalog):
        raise AssertionError("format_safe_workflow_catalog is missing")

    repair_text = format_catalog("repair-build failed smoke with project-state recall")

    assert_contains(
        "repair-build workflow catalog",
        repair_text,
        [
            "Nova safe workflow catalog",
            "Mode: manual_workflow_catalog_only",
            "Workflow: repair_build",
            "Do not execute local commands automatically",
            "Approved manual command groups:",
            "repair-build: <failed smoke output>",
            "Rollback guidance",
            "Default smoke order:",
            "Forbidden actions:",
            "project-state recall",
        ],
    )

    state_text = format_catalog("sync project-state memory after command lock")

    assert_contains(
        "project-state workflow catalog",
        state_text,
        [
            "Workflow: project_state",
            "Project-state workflow",
            "data\\nova_project_state.json",
            "python .\\tools\\nova_memory_quality_smoke.py",
            "Memory quality smoke",
            "Project-state recall",
            "Regression runner",
        ],
    )

    data = create_catalog("patch-build image description polish")

    for key in (
        "mode",
        "workflow",
        "goal",
        "summary",
        "safety_rules",
        "approved_manual_command_groups",
        "forbidden_actions",
        "default_smoke_order",
        "next_step",
    ):
        if key not in data:
            raise AssertionError(f"missing key: {key}")

    if data["mode"] != "manual_workflow_catalog_only":
        raise AssertionError(f"wrong mode: {data['mode']}")

    print("NOVA AUTONOMY WORKFLOW CATALOG SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
