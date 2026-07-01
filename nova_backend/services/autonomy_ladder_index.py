from __future__ import annotations

from typing import Dict, List


COMMANDS: List[Dict[str, str]] = [
    {
        "command": "autonomy:",
        "mode": "task_brief",
        "purpose": "Create a safe autonomy task brief for a goal.",
        "safety": "No file edits, no command execution.",
        "example": "autonomy: improve image descriptions",
    },
    {
        "command": "autonomy-plan:",
        "mode": "patch_proposal_only",
        "purpose": "Create a supervised patch proposal with likely files, risks, tests, and rollback.",
        "safety": "Proposal only; no file edits, no command execution.",
        "example": "autonomy-plan: improve image descriptions",
    },
    {
        "command": "patch-build:",
        "mode": "instructions_only",
        "purpose": "Create exact manual PowerShell patch instructions from a goal.",
        "safety": "Instructions only; Richard runs commands manually.",
        "example": "patch-build: improve image descriptions",
    },
    {
        "command": "repair-plan:",
        "mode": "repair_proposal_only",
        "purpose": "Create a smallest safe repair proposal from failed smoke output.",
        "safety": "Proposal only; no file edits, no command execution.",
        "example": "repair-plan: FAILED nova_project_state_smoke",
    },
    {
        "command": "repair-build:",
        "mode": "repair_instructions_only",
        "purpose": "Create exact manual PowerShell repair steps from failed smoke output.",
        "safety": "Instructions only; Richard runs commands manually.",
        "example": "repair-build: FAILED nova_project_state_smoke",
    },
    {
        "command": "workflow-catalog:",
        "mode": "manual_workflow_catalog_only",
        "purpose": "List approved manual command groups, smoke order, rollback guidance, and forbidden actions.",
        "safety": "Catalog only; no file edits, no command execution.",
        "example": "workflow-catalog: repair-build failed smoke with project-state recall",
    },
]


def create_autonomy_ladder_index() -> Dict[str, object]:
    return {
        "mode": "autonomy_ladder_index_only",
        "status": "locked_manual_autonomy_ladder",
        "commands": COMMANDS,
        "global_safety_rules": [
            "Do not edit files automatically.",
            "Do not execute local commands automatically.",
            "Do not apply patches or repairs silently.",
            "Richard must run every command manually.",
            "Preserve project-state recall and locked smoke coverage.",
            "Use the smallest relevant smoke before broad smokes.",
            "Commit only after tests pass and git status is understood.",
        ],
        "recommended_order": [
            "autonomy:",
            "autonomy-plan:",
            "patch-build:",
            "repair-plan:",
            "repair-build:",
            "workflow-catalog:",
        ],
        "core_smokes": [
            "python .\\tools\\nova_memory_quality_smoke.py",
            "python .\\tools\\nova_autonomy_command_api_smoke.py",
            "python .\\tools\\nova_project_compact_context_api_smoke.py",
        ],
        "next_recommended_manual_command": "workflow-catalog: repair-build failed smoke with project-state recall",
    }


def format_autonomy_ladder_index() -> str:
    data = create_autonomy_ladder_index()

    lines = [
        "Nova autonomy ladder index",
        "",
        f"Mode: {data['mode']}",
        f"Status: {data['status']}",
        "",
        "Commands:",
    ]

    for item in data["commands"]:
        lines.extend([
            f"- {item['command']}",
            f"  - Mode: {item['mode']}",
            f"  - Purpose: {item['purpose']}",
            f"  - Safety: {item['safety']}",
            f"  - Example: {item['example']}",
        ])

    lines.extend(["", "Global safety rules:"])
    lines.extend(f"- {item}" for item in data["global_safety_rules"])

    lines.extend(["", "Recommended order:"])
    lines.extend(f"- {item}" for item in data["recommended_order"])

    lines.extend(["", "Core smokes:"])
    lines.extend(f"- {item}" for item in data["core_smokes"])

    lines.extend(["", f"Next recommended manual command: {data['next_recommended_manual_command']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_autonomy_ladder_index())
