from __future__ import annotations

from typing import Dict, List


LOCKED_COMMANDS: List[Dict[str, str]] = [
    {
        "command": "autonomy:",
        "route": "autonomy_command",
        "mode": "task_brief",
        "service": "nova_backend.services.autonomy_task_brain",
        "smoke": "python .\\tools\\nova_autonomy_command_api_smoke.py",
    },
    {
        "command": "autonomy-plan:",
        "route": "autonomy_plan_command",
        "mode": "patch_proposal_only",
        "service": "nova_backend.services.autonomy_patch_planner",
        "smoke": "python .\\tools\\nova_autonomy_plan_command_api_smoke.py",
    },
    {
        "command": "patch-build:",
        "route": "patch_build_command",
        "mode": "instructions_only",
        "service": "nova_backend.services.autonomy_patch_builder",
        "smoke": "python .\\tools\\nova_patch_build_command_api_smoke.py",
    },
    {
        "command": "repair-plan:",
        "route": "repair_plan_command",
        "mode": "repair_proposal_only",
        "service": "nova_backend.services.autonomy_repair_planner",
        "smoke": "python .\\tools\\nova_repair_plan_command_api_smoke.py",
    },
    {
        "command": "repair-build:",
        "route": "repair_build_command",
        "mode": "repair_instructions_only",
        "service": "nova_backend.services.autonomy_repair_builder",
        "smoke": "python .\\tools\\nova_repair_build_command_api_smoke.py",
    },
    {
        "command": "workflow-catalog:",
        "route": "workflow_catalog_command",
        "mode": "manual_workflow_catalog_only",
        "service": "nova_backend.services.autonomy_workflow_catalog",
        "smoke": "python .\\tools\\nova_workflow_catalog_command_api_smoke.py",
    },
    {
        "command": "autonomy-index:",
        "route": "autonomy_index_command",
        "mode": "autonomy_ladder_index_only",
        "service": "nova_backend.services.autonomy_ladder_index",
        "smoke": "python .\\tools\\nova_autonomy_index_command_api_smoke.py",
    },
]


def create_autonomy_command_registry_plan() -> Dict[str, object]:
    return {
        "mode": "registry_plan_only",
        "status": "no_behavior_change_plan",
        "purpose": "Plan a safe central command registry for locked autonomy commands currently guarded in app.py.",
        "owner_files": [
            "app.py",
            "nova_backend/services/autonomy_command_registry.py",
            "tools/nova_autonomy_command_registry_smoke.py",
        ],
        "locked_commands": LOCKED_COMMANDS,
        "non_negotiable_invariants": [
            "Do not change command text or prefixes.",
            "Do not change route names.",
            "Do not change response mode names.",
            "Do not change assistant_message text/content behavior.",
            "Do not weaken any API smoke.",
            "Do not remove project-state recall.",
            "Do not execute commands automatically.",
            "Do not edit files automatically.",
            "Richard must run every command manually.",
        ],
        "migration_steps": [
            "Create a registry service that only describes commands first.",
            "Add smoke coverage proving every locked command is listed with command, route, mode, service, and smoke.",
            "Do not remove app.py guards in the planning commit.",
            "In a later commit, move only one low-risk command into the registry adapter.",
            "Run that command smoke plus memory quality smoke.",
            "Repeat one command at a time only after clean status.",
        ],
        "verification_smokes": [
            "python -m py_compile .\\app.py",
            "python -m py_compile .\\nova_backend\\services\\autonomy_command_registry_plan.py",
            "python -m py_compile .\\tools\\nova_autonomy_command_registry_plan_smoke.py",
            "python .\\tools\\nova_autonomy_command_registry_plan_smoke.py",
            "python .\\tools\\nova_autonomy_command_api_smoke.py",
            "python .\\tools\\nova_autonomy_plan_command_api_smoke.py",
            "python .\\tools\\nova_patch_build_command_api_smoke.py",
            "python .\\tools\\nova_repair_plan_command_api_smoke.py",
            "python .\\tools\\nova_repair_build_command_api_smoke.py",
            "python .\\tools\\nova_workflow_catalog_command_api_smoke.py",
            "python .\\tools\\nova_autonomy_index_command_api_smoke.py",
            "python .\\tools\\nova_memory_quality_smoke.py",
        ],
        "rollback_commands": [
            "git restore app.py",
            "git restore nova_backend\\services\\autonomy_command_registry.py",
            "git restore tools\\nova_autonomy_command_registry_smoke.py",
            "git reset --hard HEAD",
            "git revert <commit>",
        ],
        "forbidden_actions": [
            "Do not centralize all guards in one untested commit.",
            "Do not delete existing app.py guards until replacement smoke is green.",
            "Do not rename commands, routes, or modes.",
            "Do not skip memory quality smoke.",
            "Do not touch unrelated mobile, image, web, or attachment code.",
        ],
        "next_step": "Lock this plan first, then build the read-only command registry service.",
    }


def format_autonomy_command_registry_plan() -> str:
    plan = create_autonomy_command_registry_plan()

    lines = [
        "Nova autonomy command registry plan",
        "",
        f"Mode: {plan['mode']}",
        f"Status: {plan['status']}",
        "",
        f"Purpose: {plan['purpose']}",
        "",
        "Owner files:",
    ]

    lines.extend(f"- {item}" for item in plan["owner_files"])

    lines.extend(["", "Locked commands:"])
    for item in plan["locked_commands"]:
        lines.extend([
            f"- {item['command']}",
            f"  - Route: {item['route']}",
            f"  - Mode: {item['mode']}",
            f"  - Service: {item['service']}",
            f"  - Smoke: {item['smoke']}",
        ])

    lines.extend(["", "Non-negotiable invariants:"])
    lines.extend(f"- {item}" for item in plan["non_negotiable_invariants"])

    lines.extend(["", "Migration steps:"])
    for index, item in enumerate(plan["migration_steps"], start=1):
        lines.append(f"{index}. {item}")

    lines.extend(["", "Verification smokes:"])
    lines.extend(f"- {item}" for item in plan["verification_smokes"])

    lines.extend(["", "Rollback commands:"])
    lines.extend(f"- {item}" for item in plan["rollback_commands"])

    lines.extend(["", "Forbidden actions:"])
    lines.extend(f"- {item}" for item in plan["forbidden_actions"])

    lines.extend(["", f"Next step: {plan['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_autonomy_command_registry_plan())
