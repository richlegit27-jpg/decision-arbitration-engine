from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

HIGH_VALUE_SMOKES = [
    "nova_autonomy_command_api_smoke.py",
    "nova_command_registry_adapter_smoke.py",
    "nova_command_registry_command_api_smoke.py",
    "nova_autonomy_command_registry_smoke.py",
    "nova_autonomy_command_registry_plan_smoke.py",
    "nova_workflow_catalog_adapter_smoke.py",
    "nova_workflow_catalog_command_api_smoke.py",
    "nova_repair_plan_adapter_smoke.py",
    "nova_repair_plan_command_api_smoke.py",
    "nova_repair_build_adapter_smoke.py",
    "nova_repair_build_command_api_smoke.py",
    "nova_patch_build_command_api_smoke.py",
]


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")

    print(f"PASS {name}")


def run_smoke(name: str) -> None:
    path = ROOT / "tools" / name

    assert_true(f"smoke exists {name}", path.exists(), str(path))

    print("")
    print(f"=== {name} ===")

    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    assert_true(
        f"high value smoke passed {name}",
        result.returncode == 0,
        f"returncode={result.returncode}",
    )


def main() -> int:
    print("NOVA PHASE 6D HIGH VALUE SMOKE BUNDLE")
    print("")

    for name in HIGH_VALUE_SMOKES:
        run_smoke(name)

    print("")
    print(f"High value smokes checked: {len(HIGH_VALUE_SMOKES)}")
    print("NOVA PHASE 6D HIGH VALUE SMOKE BUNDLE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
