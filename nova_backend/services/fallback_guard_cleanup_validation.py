from __future__ import annotations

from pathlib import Path
from typing import Dict, List


TARGETS = [
    {
        "name": "autonomy-plan",
        "route": "autonomy_plan_command",
        "adapter_marker": "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
        "adapter_guard": "nova_autonomy_plan_adapter_guard_20260701",
        "fallback_marker": "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
        "fallback_extractor": "_nova_extract_autonomy_plan_goal_20260630",
        "fallback_guard": "nova_autonomy_plan_command_guard_20260630",
    },
    {
        "name": "patch-build",
        "route": "patch_build_command",
        "adapter_marker": "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
        "adapter_guard": "nova_patch_build_adapter_guard_20260701",
        "fallback_marker": "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
        "fallback_extractor": "_nova_extract_patch_build_goal_20260630",
        "fallback_guard": "nova_patch_build_command_guard_20260630",
    },
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def validate_fallback_guard_cleanup(app_path: str = "app.py") -> Dict[str, object]:
    path = Path(app_path)
    text = _read_text(path)

    results: List[Dict[str, object]] = []

    for target in TARGETS:
        adapter_present = (
            target["adapter_marker"] in text
            and target["adapter_guard"] in text
            and target["route"] in text
        )

        fallback_gone = (
            target["fallback_marker"] not in text
            and target["fallback_extractor"] not in text
            and target["fallback_guard"] not in text
        )

        results.append(
            {
                "name": target["name"],
                "route": target["route"],
                "adapter_present": adapter_present,
                "fallback_gone": fallback_gone,
                "passed": adapter_present and fallback_gone,
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

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_path = " ".join(sys.argv[1:]).strip() or "app.py"
    print(format_fallback_guard_cleanup_validation(input_path))

    result = validate_fallback_guard_cleanup(input_path)
    raise SystemExit(0 if result["status"] == "passed" else 1)
