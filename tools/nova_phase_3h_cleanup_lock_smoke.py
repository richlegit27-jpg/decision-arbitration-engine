from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


REQUIRED_PRESENT = [
    "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
    "nova_autonomy_plan_adapter_guard_20260701",
    "autonomy_plan_command",
    "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
    "nova_patch_build_adapter_guard_20260701",
    "patch_build_command",
    'print("[Nova OpenAI Key] loaded")',
]


REQUIRED_ABSENT = [
    "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_autonomy_plan_goal_20260630",
    "nova_autonomy_plan_command_guard_20260630",
    "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
    "_nova_extract_patch_build_goal_20260630",
    "nova_patch_build_command_guard_20260630",
    "sk-proj",
]


REQUIRED_MEMORY_GATE_SMOKES = [
    "nova_openai_key_log_safety_smoke.py",
    "nova_fallback_guard_cleanup_plan_smoke.py",
    "nova_fallback_guard_cleanup_validation_smoke.py",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def run_smoke(script_name: str) -> None:
    script_path = ROOT / "tools" / script_name
    subprocess.run([sys.executable, str(script_path)], check=True)


def main():
    app_text = APP_PATH.read_text(encoding="utf-8-sig")
    memory_gate_text = (ROOT / "tools" / "nova_memory_quality_smoke.py").read_text(encoding="utf-8-sig")

    missing = [item for item in REQUIRED_PRESENT if item not in app_text]
    still_present = [item for item in REQUIRED_ABSENT if item in app_text]
    gate_missing = [item for item in REQUIRED_MEMORY_GATE_SMOKES if item not in memory_gate_text]

    assert_true("required adapter/key markers present", not missing, f"missing={missing}")
    assert_true("old fallback/key leak markers absent", not still_present, f"still_present={still_present}")
    assert_true("memory quality gate includes cleanup smokes", not gate_missing, f"missing={gate_missing}")

    run_smoke("nova_openai_key_log_safety_smoke.py")
    run_smoke("nova_fallback_guard_cleanup_plan_smoke.py")
    run_smoke("nova_fallback_guard_cleanup_validation_smoke.py")

    print("NOVA PHASE 3H CLEANUP LOCK SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
