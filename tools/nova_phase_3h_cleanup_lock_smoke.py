from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

RUNTIME_SURFACES = [
    APP,
    ROOT / "nova_backend" / "services" / "autonomy_command_registry.py",
    ROOT / "nova_backend" / "services" / "autonomy_command_registry_plan.py",
    ROOT / "nova_backend" / "services" / "autonomy_plan_adapter.py",
    ROOT / "nova_backend" / "services" / "patch_build_adapter.py",
    ROOT / "nova_backend" / "services" / "repair_plan_adapter.py",
]

REQUIRED_RUNTIME = [
    "autonomy_plan_command",
    "patch_build_command",
    "repair_plan_command",
    "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
    "nova_autonomy_plan_adapter_guard_20260701",
    "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
    "nova_patch_build_adapter_guard_20260701",
    "repair_plan_adapter",
]

REQUIRED_ABSENT_IN_APP = [
    "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_autonomy_plan_goal_20260630",
    "nova_autonomy_plan_command_guard_20260630",
    "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
    "_nova_extract_patch_build_goal_20260630",
    "nova_patch_build_command_guard_20260630",
    "NOVA_REPAIR_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_repair_plan_goal_20260630",
    "nova_repair_plan_command_guard_20260630",
]

ALLOWED_OPENAI_KEY_LOGS = {
    'print("[Nova OpenAI Key] loaded")',
    'print("[Nova OpenAI Key] not configured")',
}

FORBIDDEN_KEY_PATTERNS = [
    "sk-proj",
    "sk-",
]


def read_existing(paths):
    chunks = []

    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))

    return "\n".join(chunks)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    assert_true("app.py exists", APP.exists())

    app_text = APP.read_text(encoding="utf-8", errors="replace")
    runtime_text = read_existing(RUNTIME_SURFACES)

    missing = [
        marker
        for marker in REQUIRED_RUNTIME
        if marker not in runtime_text
    ]

    present_forbidden = [
        marker
        for marker in REQUIRED_ABSENT_IN_APP
        if marker in app_text
    ]

    key_log_lines = [
        line.strip()
        for line in runtime_text.splitlines()
        if "[Nova OpenAI Key]" in line
    ]

    unsafe_key_logs = []

    for line in key_log_lines:
        if line not in ALLOWED_OPENAI_KEY_LOGS:
            unsafe_key_logs.append(line)

        for pattern in FORBIDDEN_KEY_PATTERNS:
            if pattern in line and line not in ALLOWED_OPENAI_KEY_LOGS:
                unsafe_key_logs.append(line)

    assert_true(
        "required adapter/key markers present",
        not missing,
        f"missing={missing}",
    )

    assert_true(
        "old fallback guards absent",
        not present_forbidden,
        f"present={present_forbidden}",
    )

    assert_true(
        "OpenAI key boot log safe or absent",
        not unsafe_key_logs,
        f"unsafe={sorted(set(unsafe_key_logs))}",
    )

    print("NOVA PHASE 3H CLEANUP LOCK SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

