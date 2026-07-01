from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "tools" / "nova_phase_4t_boot_log_inventory.py"


FORBIDDEN_OUTPUT = [
    "DEBUG GOAL:",
    "DEBUG CLEAN:",
    "DEBUG LOWER:",
    "RESTORED RUNTIME OK",
    "LAST COMPRESSED OK",
    "ARTIFACT FILE PATH =",
    "wrapped endpoints:",
    "127.0.0.1 - -",
]

REQUIRED_OUTPUT = [
    "NOVA PHASE 4T LIVE BOOT LOG INVENTORY",
    "- 002 boot",
    "[Nova OpenAI Key] loaded",
    "[Nova OpenAI Key] not configured",
    "NOVA PHASE 4T LIVE BOOT LOG INVENTORY DONE",
]


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")

    print(f"PASS {name}")


def main() -> int:
    assert_true("inventory exists", INVENTORY.exists(), str(INVENTORY))

    result = subprocess.run(
        [sys.executable, str(INVENTORY)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    output = result.stdout + result.stderr

    for required in REQUIRED_OUTPUT:
        assert_true(
            f"required inventory output {required}",
            required in output,
        )

    for forbidden in FORBIDDEN_OUTPUT:
        assert_true(
            f"forbidden quiet-log output absent {forbidden}",
            forbidden not in output,
        )

    assert_true(
        "active execution failure classified as debug/error",
        "Debug/error print locations:" in output
        and "[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] print(" in output,
    )

    assert_true(
        "active execution failure absent from boot section",
        "Boot-like print locations:\napp.py:" not in output,
    )

    print("")
    print("NOVA PHASE 4Y QUIET BOOT LOG LOCK SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
