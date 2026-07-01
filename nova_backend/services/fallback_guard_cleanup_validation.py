from __future__ import annotations

from pathlib import Path
from typing import Dict, List


TARGETS = [
    {
        "name": "autonomy-plan",
        "route": "autonomy_plan_command",
        "adapter_tokens": [
            "autonomy_plan_command",
            "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
            "nova_autonomy_plan_adapter_guard_20260701",
        ],
        "fallback_tokens": [
            "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
            "_nova_extract_autonomy_plan_goal_20260630",
            "nova_autonomy_plan_command_guard_20260630",
        ],
    },
    {
        "name": "patch-build",
        "route": "patch_build_command",
        "adapter_tokens": [
            "patch_build_command",
            "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
            "nova_patch_build_adapter_guard_20260701",
        ],
        "fallback_tokens": [
            "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
            "_nova_extract_patch_build_goal_20260630",
            "nova_patch_build_command_guard_20260630",
        ],
    },
    {
        "name": "repair-plan",
        "route": "repair_plan_command",
        "adapter_tokens": [
            "repair_plan_command",
            "repair_plan_adapter",
        ],
        "fallback_tokens": [
            "NOVA_REPAIR_PLAN_COMMAND_GUARD_20260630",
            "_nova_extract_repair_plan_goal_20260630",
            "nova_repair_plan_command_guard_20260630",
        ],
    },
]


SERVICE_SURFACE_RELATIVE_PATHS = [
    Path("nova_backend") / "services" / "autonomy_command_registry.py",
    Path("nova_backend") / "services" / "autonomy_command_registry_plan.py",
    Path("nova_backend") / "services" / "autonomy_plan_adapter.py",
    Path("nova_backend") / "services" / "patch_build_adapter.py",
    Path("nova_backend") / "services" / "repair_plan_adapter.py",
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _read_existing(paths: List[Path]) -> str:
    chunks = []

    for path in paths:
        if path.exists():
            chunks.append(_read_text(path))

    return "\n".join(chunks)


def _project_root_for_app_path(app_path: Path) -> Path:
    resolved = app_path.resolve()

    if resolved.name == "app.py":
        return resolved.parent

    return Path.cwd().resolve()


def validate_fallback_guard_cleanup(app_path: str = "app.py") -> Dict[str, object]:
    path = Path(app_path)
    app_text = _read_text(path)

    project_root = _project_root_for_app_path(path)
    service_paths = [
        project_root / relative_path
        for relative_path in SERVICE_SURFACE_RELATIVE_PATHS
    ]

    service_text = _read_existing(service_paths)
    runtime_text = app_text + "\n" + service_text

    results: List[Dict[str, object]] = []

    for target in TARGETS:
        missing_adapter_tokens = [
            token
            for token in target["adapter_tokens"]
            if token not in runtime_text
        ]

        present_fallback_tokens = [
            token
            for token in target["fallback_tokens"]
            if token in app_text
        ]

        adapter_present = not missing_adapter_tokens
        fallback_gone = not present_fallback_tokens

        results.append(
            {
                "name": target["name"],
                "route": target["route"],
                "adapter_present": adapter_present,
                "fallback_gone": fallback_gone,
                "passed": adapter_present and fallback_gone,
                "missing_adapter_tokens": missing_adapter_tokens,
                "present_fallback_tokens": present_fallback_tokens,
            }
        )

    return {
        "mode": "fallback_guard_cleanup_validation",
        "status": "passed" if all(item["passed"] for item in results) else "failed",
        "target_file": str(path),
        "results": results,
    }


def format_fallback_guard_cleanup_validation(app_path: str = "app.py") -> str:
    validation = validate_fallback_guard_cleanup(app_path)

    lines = [
        "Nova fallback guard cleanup validation",
        "",
        f"Mode: {validation['mode']}",
        f"Status: {validation['status']}",
        f"Target file: {validation['target_file']}",
        "",
        "Results:",
    ]

    for item in validation["results"]:
        lines.extend(
            [
                f"- {item['name']}",
                f"  - Route: {item['route']}",
                f"  - Adapter present: {item['adapter_present']}",
                f"  - Old fallback gone: {item['fallback_gone']}",
                f"  - Passed: {item['passed']}",
            ]
        )

        if item.get("missing_adapter_tokens"):
            lines.append(f"  - Missing adapter tokens: {item['missing_adapter_tokens']}")

        if item.get("present_fallback_tokens"):
            lines.append(f"  - Present fallback tokens: {item['present_fallback_tokens']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_path = " ".join(sys.argv[1:]).strip() or "app.py"
    print(format_fallback_guard_cleanup_validation(input_path))

    result = validate_fallback_guard_cleanup(input_path)
    raise SystemExit(0 if result["status"] == "passed" else 1)
