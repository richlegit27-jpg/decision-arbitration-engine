from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    ["-m", "py_compile", str(ROOT / "app.py")],
    [str(ROOT / "tools" / "nova_secret_log_hygiene_smoke.py")],
    [str(ROOT / "tools" / "nova_phase_3i_static_backup_review_smoke.py")],
    [str(ROOT / "tools" / "nova_openai_key_log_safety_smoke.py")],
    "nova_phase_4y_quiet_boot_log_lock_smoke.py",
    [str(ROOT / "tools" / "nova_fallback_guard_cleanup_plan_smoke.py")],
    [str(ROOT / "tools" / "nova_fallback_guard_cleanup_validation_smoke.py")],
    [str(ROOT / "tools" / "nova_phase_3h_cleanup_lock_smoke.py")],
    [str(ROOT / "tools" / "nova_obsolete_phase_3h_plan_files_review_smoke.py")],
    [str(ROOT / "tools" / "nova_patch_build_adapter_smoke.py")],
    [str(ROOT / "tools" / "nova_autonomy_plan_adapter_smoke.py")],
    [str(ROOT / "tools" / "nova_autonomy_plan_command_api_smoke.py")],
    [str(ROOT / "tools" / "nova_memory_quality_smoke.py")],
]


def _label(command: list[str]) -> str:
    if command[:2] == ["-m", "py_compile"]:
        return "py_compile app.py"

    script = Path(command[0])
    return script.name


def main():
    print("Nova master quality gate")
    print("")

    for command in COMMANDS:
        label = _label(command)
        print(f"=== {label} ===")
        subprocess.run([sys.executable, *command], check=True)
        print(f"PASS {label}")
        print("")

    print("NOVA MASTER QUALITY GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
