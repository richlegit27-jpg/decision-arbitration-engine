from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


ROOT = Path(__file__).resolve().parents[1]


CHECKS: List[Tuple[str, List[str]]] = [
    (
        "nova_memory_hygiene_audit",
        [sys.executable, str(ROOT / "tools" / "nova_memory_hygiene_audit.py")],
    ),
    (
        "nova_project_context_line_smoke",
        [sys.executable, str(ROOT / "tools" / "nova_project_context_line_smoke.py")],
    ),
    (
        "nova_project_state_smoke",
        [sys.executable, str(ROOT / "tools" / "nova_project_state_smoke.py")],
    ),
    (
        "nova_project_context_smoke",
        [sys.executable, str(ROOT / "tools" / "nova_project_context_smoke.py")],
    ),
    (
        "nova_project_compact_context_api_smoke",
        [sys.executable, str(ROOT / "tools" / "nova_project_compact_context_api_smoke.py")],
    ),
    (
        "nova_autonomy_task_brain_smoke",
        [sys.executable, str(ROOT / "tools" / "nova_autonomy_task_brain_smoke.py")],
    ),
    (
        "nova_autonomy_command_api_smoke",
        [sys.executable, str(ROOT / "tools" / "nova_autonomy_command_api_smoke.py")],
    ),
]


def run_check(name: str, command: List[str]) -> bool:
    print(f"\n=== {name} ===")

    proc = subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        shell=False,
    )

    if proc.returncode != 0:
        print(f"\nFAILED {name}")
        return False

    print(f"PASS {name}")
    return True


def main() -> int:
    failed: List[str] = []

    for name, command in CHECKS:
        if not run_check(name, command):
            failed.append(name)

    if failed:
        print("\nNOVA MEMORY QUALITY SMOKE FAILED")
        print("Failed checks:")
        for name in failed:
            print(f"- {name}")
        return 1

        print("\n=== nova_openai_key_log_safety_smoke ===")
    _nova_key_log_smoke = Path(__file__).with_name("nova_openai_key_log_safety_smoke.py")
    subprocess.run([sys.executable, str(_nova_key_log_smoke)], check=True)
    print("PASS nova_openai_key_log_safety_smoke")

print("\n=== nova_fallback_guard_cleanup_plan_smoke ===")
_nova_fallback_plan_smoke = Path(__file__).with_name("nova_fallback_guard_cleanup_plan_smoke.py")
subprocess.run([sys.executable, str(_nova_fallback_plan_smoke)], check=True)
print("PASS nova_fallback_guard_cleanup_plan_smoke")

print("\n=== nova_fallback_guard_cleanup_validation_smoke ===")
_nova_fallback_validation_smoke = Path(__file__).with_name("nova_fallback_guard_cleanup_validation_smoke.py")
subprocess.run([sys.executable, str(_nova_fallback_validation_smoke)], check=True)
print("PASS nova_fallback_guard_cleanup_validation_smoke")

print("\nNOVA MEMORY QUALITY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

