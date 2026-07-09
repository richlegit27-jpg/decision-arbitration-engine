from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "nova_backend" / "services" / "project_state_service.py"


def load_service():
    spec = importlib.util.spec_from_file_location(
        "_nova_project_state_service_context_line_smoke",
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

    compact_fn = getattr(service, "compact_project_state_context", None)
    block_fn = getattr(service, "compact_project_state_context_block", None)

    if not callable(compact_fn):
        raise AssertionError("compact_project_state_context is missing")

    if not callable(block_fn):
        raise AssertionError("compact_project_state_context_block is missing")

    compact = compact_fn()
    block = block_fn()

    assert_contains(
        "compact context",
        compact,
        ["nova checkpoint", "focus", "next", "locked"],
    )

    assert_contains(
        "context block",
        block,
        ["current nova project state", "use this only"],
    )

    if len(compact) > 1200:
        raise AssertionError(f"compact context too long: {len(compact)} chars")

    print("PROJECT CONTEXT LINE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
