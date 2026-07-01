from __future__ import annotations

from pathlib import Path
from typing import Dict, List


CLEANUP_CANDIDATES = [
    {
        "command": "autonomy-plan",
        "route": "autonomy_plan_command",
        "adapter_marker": "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
        "adapter_guard": "nova_autonomy_plan_adapter_guard_20260701",
        "fallback_marker": "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
        "fallback_guard": "nova_autonomy_plan_command_guard_20260630",
        "mode_note": "Adapter preserves proposal_only debug mode and patch_proposal_only assistant metadata.",
    },
    {
        "command": "patch-build",
        "route": "patch_build_command",
        "adapter_marker": "NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701",
        "adapter_guard": "nova_patch_build_adapter_guard_20260701",
        "fallback_marker": "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
        "fallback_guard": "nova_patch_build_command_guard_20260630",
        "mode_note": "Adapter preserves instructions_only mode.",
    },
]


REQUIRED_SMOKES = [
    "python -m py_compile .\\app.py",
    "python .\\tools\\nova_autonomy_plan_command_api_smoke.py",
    "python .\\tools\\nova_patch_build_command_api_smoke.py",
    "python .\\tools\\nova_autonomy_guard_cleanup_review_smoke.py",
    "python .\\tools\\nova_memory_quality_smoke.py",
]


FORBIDDEN_ACTIONS = [
    "Do not delete fallback guards in this plan step.",
    "Do not edit app.py in this plan step.",
    "Do not centralize all guards in one commit.",
    "Do not rename commands, routes, modes, prefixes, or debug fields.",
    "Do not touch mobile, image, web, upload, or attachment code.",
    "Do not weaken any smoke.",
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def create_fallback_guard_cleanup_plan(app_path: str = "app.py") -> Dict[str, object]:
    path = Path(app_path)
    text = _read_text(path)

    candidates: List[Dict[str, object]] = []

    for item in CLEANUP_CANDIDATES:
        adapter_present = item["adapter_marker"] in text and item["adapter_guard"] in text
        fallback_present = item["fallback_marker"] in text and item["fallback_guard"] in text

        candidates.append({
            **item,
            "adapter_present": adapter_present,
            "fallback_present": fallback_present,
            "cleanup_candidate": adapter_present and fallback_present,
        })

    return {
        "mode": "no_delete_fallback_guard_cleanup_plan",
        "status": "review_only_no_behavior_change",
        "target_file": str(path),
        "candidates": candidates,
        "required_smokes": REQUIRED_SMOKES,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "next_step": "Lock this no-delete cleanup plan first. If approved later, remove at most one old fallback guard per commit after clean smokes.",
    }


def format_fallback_guard_cleanup_plan(app_path: str = "app.py") -> str:
    plan = create_fallback_guard_cleanup_plan(app_path)

    lines = [
        "Nova autonomy fallback guard cleanup plan",
        "",
        f"Mode: {plan['mode']}",
        f"Status: {plan['status']}",
        f"Target file: {plan['target_file']}",
        "",
        "Cleanup candidates:",
    ]

    for item in plan["candidates"]:
        lines.extend([
            f"- {item['command']}",
            f"  - Route: {item['route']}",
            f"  - Adapter marker: {item['adapter_marker']}",
            f"  - Adapter guard: {item['adapter_guard']}",
            f"  - Adapter present: {item['adapter_present']}",
            f"  - Old fallback marker: {item['fallback_marker']}",
            f"  - Old fallback guard: {item['fallback_guard']}",
            f"  - Old fallback present: {item['fallback_present']}",
            f"  - Cleanup candidate: {item['cleanup_candidate']}",
            f"  - Mode note: {item['mode_note']}",
        ])

    lines.extend(["", "Required smokes before any future guard removal:"])
    lines.extend(f"- {item}" for item in plan["required_smokes"])

    lines.extend(["", "Forbidden actions:"])
    lines.extend(f"- {item}" for item in plan["forbidden_actions"])

    lines.extend(["", f"Next step: {plan['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_path = " ".join(sys.argv[1:]).strip() or "app.py"
    print(format_fallback_guard_cleanup_plan(input_path))
