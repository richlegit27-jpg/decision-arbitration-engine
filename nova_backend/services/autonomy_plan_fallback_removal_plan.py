from __future__ import annotations

from pathlib import Path
from typing import Dict


TARGET = {
    "command": "autonomy-plan",
    "route": "autonomy_plan_command",
    "adapter_marker": "NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701",
    "adapter_guard": "nova_autonomy_plan_adapter_guard_20260701",
    "fallback_marker": "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
    "fallback_extractor": "_nova_extract_autonomy_plan_goal_20260630",
    "fallback_guard": "nova_autonomy_plan_command_guard_20260630",
}


REQUIRED_SMOKES = [
    "python -m py_compile .\\app.py",
    "python .\\tools\\nova_autonomy_plan_adapter_smoke.py",
    "python .\\tools\\nova_autonomy_plan_command_api_smoke.py",
    "python .\\tools\\nova_fallback_guard_cleanup_plan_smoke.py",
    "python .\\tools\\nova_autonomy_guard_cleanup_review_smoke.py",
    "python .\\tools\\nova_memory_quality_smoke.py",
]


FORBIDDEN_ACTIONS = [
    "Do not delete anything in this planning step.",
    "Do not edit app.py in this planning step.",
    "Do not touch patch-build fallback guard yet.",
    "Do not remove adapter-owned autonomy-plan guard.",
    "Do not rename routes, modes, commands, prefixes, or debug fields.",
    "Do not touch mobile, image, web, upload, or attachment code.",
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def create_autonomy_plan_fallback_removal_plan(app_path: str = "app.py") -> Dict[str, object]:
    path = Path(app_path)
    text = _read_text(path)

    adapter_marker_index = text.find(TARGET["adapter_marker"])
    fallback_marker_index = text.find(TARGET["fallback_marker"])

    return {
        "mode": "autonomy_plan_fallback_removal_plan_only",
        "status": "review_only_no_behavior_change",
        "target_file": str(path),
        "target": TARGET,
        "adapter_present": TARGET["adapter_marker"] in text and TARGET["adapter_guard"] in text,
        "fallback_present": (
            TARGET["fallback_marker"] in text
            and TARGET["fallback_extractor"] in text
            and TARGET["fallback_guard"] in text
        ),
        "adapter_before_fallback": (
            adapter_marker_index >= 0
            and fallback_marker_index >= 0
            and adapter_marker_index < fallback_marker_index
        ),
        "removal_scope": [
            "Only the old autonomy-plan fallback block is eligible for future removal.",
            "The future removal block starts at NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630.",
            "The future removal block includes _nova_extract_autonomy_plan_goal_20260630.",
            "The future removal block includes nova_autonomy_plan_command_guard_20260630.",
            "The future removal must stop before NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701.",
        ],
        "required_smokes": REQUIRED_SMOKES,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "next_step": "Lock this plan first. If approved later, remove only the autonomy-plan fallback block and run the required smokes before commit.",
    }


def format_autonomy_plan_fallback_removal_plan(app_path: str = "app.py") -> str:
    plan = create_autonomy_plan_fallback_removal_plan(app_path)
    target = plan["target"]

    lines = [
        "Nova autonomy-plan fallback removal plan",
        "",
        f"Mode: {plan['mode']}",
        f"Status: {plan['status']}",
        f"Target file: {plan['target_file']}",
        "",
        "Target:",
        f"- Command: {target['command']}",
        f"- Route: {target['route']}",
        f"- Adapter marker: {target['adapter_marker']}",
        f"- Adapter guard: {target['adapter_guard']}",
        f"- Old fallback marker: {target['fallback_marker']}",
        f"- Old fallback extractor: {target['fallback_extractor']}",
        f"- Old fallback guard: {target['fallback_guard']}",
        "",
        f"Adapter present: {plan['adapter_present']}",
        f"Old fallback present: {plan['fallback_present']}",
        f"Adapter before fallback: {plan['adapter_before_fallback']}",
        "",
        "Future removal scope:",
    ]

    lines.extend(f"- {item}" for item in plan["removal_scope"])

    lines.extend(["", "Required smokes before future removal commit:"])
    lines.extend(f"- {item}" for item in plan["required_smokes"])

    lines.extend(["", "Forbidden actions:"])
    lines.extend(f"- {item}" for item in plan["forbidden_actions"])

    lines.extend(["", f"Next step: {plan['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_path = " ".join(sys.argv[1:]).strip() or "app.py"
    print(format_autonomy_plan_fallback_removal_plan(input_path))
