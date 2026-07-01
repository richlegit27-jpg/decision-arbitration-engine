from __future__ import annotations

from typing import Dict, List, Optional


COMMAND_REGISTRY: List[Dict[str, object]] = [
    {
        "command": "autonomy:",
        "aliases": ["autonomy:"],
        "route": "autonomy_command",
        "mode": "task_brief",
        "service": "nova_backend.services.autonomy_task_brain",
        "formatter": "format_autonomy_task_brief",
        "api_smoke": "python .\\tools\\nova_autonomy_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_task_brain_smoke.py",
        "status": "locked",
        "purpose": "Create a safe autonomy task brief for a goal.",
        "safety": "No file edits, no command execution.",
    },
    {
        "command": "autonomy-plan:",
        "aliases": ["autonomy-plan:", "autonomy plan:", "plan-autonomy:", "plan autonomy:"],
        "route": "autonomy_plan_command",
        "mode": "patch_proposal_only",
        "service": "nova_backend.services.autonomy_patch_planner",
        "formatter": "format_autonomy_patch_plan",
        "api_smoke": "python .\\tools\\nova_autonomy_plan_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_patch_planner_smoke.py",
        "status": "locked",
        "purpose": "Create a supervised patch proposal with likely files, risks, tests, and rollback.",
        "safety": "Proposal only; no file edits, no command execution.",
    },
    {
        "command": "patch-build:",
        "aliases": ["patch-build:", "patch build:", "build-patch:", "build patch:"],
        "route": "patch_build_command",
        "mode": "instructions_only",
        "service": "nova_backend.services.autonomy_patch_builder",
        "formatter": "format_autonomy_patch_build",
        "api_smoke": "python .\\tools\\nova_patch_build_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_patch_builder_smoke.py",
        "status": "locked",
        "purpose": "Create exact manual PowerShell patch instructions from a goal.",
        "safety": "Instructions only; Richard runs commands manually.",
    },
    {
        "command": "repair-plan:",
        "aliases": ["repair-plan:", "repair plan:", "repair:", "fix-plan:", "fix plan:"],
        "route": "repair_plan_command",
        "mode": "repair_proposal_only",
        "service": "nova_backend.services.autonomy_repair_planner",
        "formatter": "format_autonomy_repair_plan",
        "api_smoke": "python .\\tools\\nova_repair_plan_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_repair_planner_smoke.py",
        "status": "locked",
        "purpose": "Create a smallest safe repair proposal from failed smoke output.",
        "safety": "Proposal only; no file edits, no command execution.",
    },
    {
        "command": "repair-build:",
        "aliases": ["repair-build:", "repair build:", "build-repair:", "build repair:"],
        "route": "repair_build_command",
        "mode": "repair_instructions_only",
        "service": "nova_backend.services.autonomy_repair_builder",
        "formatter": "format_autonomy_repair_build",
        "api_smoke": "python .\\tools\\nova_repair_build_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_repair_builder_smoke.py",
        "status": "locked",
        "purpose": "Create exact manual PowerShell repair steps from failed smoke output.",
        "safety": "Instructions only; Richard runs commands manually.",
    },
    {
        "command": "workflow-catalog:",
        "aliases": ["workflow-catalog:", "workflow catalog:", "safe-workflow:", "safe workflow:", "workflow:"],
        "route": "workflow_catalog_command",
        "mode": "manual_workflow_catalog_only",
        "service": "nova_backend.services.autonomy_workflow_catalog",
        "formatter": "format_safe_workflow_catalog",
        "api_smoke": "python .\\tools\\nova_workflow_catalog_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_workflow_catalog_smoke.py",
        "status": "locked",
        "purpose": "List approved manual command groups, smoke order, rollback guidance, and forbidden actions.",
        "safety": "Catalog only; no file edits, no command execution.",
    },
    {
        "command": "autonomy-index:",
        "aliases": ["autonomy-index:", "autonomy index:", "ladder-index:", "ladder index:", "autonomy ladder:"],
        "route": "autonomy_index_command",
        "mode": "autonomy_ladder_index_only",
        "service": "nova_backend.services.autonomy_ladder_index",
        "formatter": "format_autonomy_ladder_index",
        "api_smoke": "python .\\tools\\nova_autonomy_index_command_api_smoke.py",
        "service_smoke": "python .\\tools\\nova_autonomy_ladder_index_smoke.py",
        "status": "locked",
        "purpose": "Return the locked autonomy command map through chat.",
        "safety": "Index only; no file edits, no command execution.",
    },
]


def _clean_text(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _normalize_command(text: str) -> str:
    clean = _clean_text(text).lower()

    if not clean:
        return ""

    first_line = clean.split("\n", 1)[0].strip()

    if ":" in first_line:
        return first_line.split(":", 1)[0].strip() + ":"

    return first_line.strip()


def _copy_command(entry: Dict[str, object]) -> Dict[str, object]:
    return {
        "command": entry["command"],
        "aliases": list(entry.get("aliases") or []),
        "route": entry["route"],
        "mode": entry["mode"],
        "service": entry["service"],
        "formatter": entry["formatter"],
        "api_smoke": entry["api_smoke"],
        "service_smoke": entry["service_smoke"],
        "status": entry["status"],
        "purpose": entry["purpose"],
        "safety": entry["safety"],
    }


def list_autonomy_commands() -> List[Dict[str, object]]:
    return [_copy_command(item) for item in COMMAND_REGISTRY]


def find_autonomy_command(user_text: str) -> Optional[Dict[str, object]]:
    normalized = _normalize_command(user_text)

    if not normalized:
        return None

    for entry in COMMAND_REGISTRY:
        aliases = [str(item).lower().strip() for item in entry.get("aliases") or []]
        command = str(entry.get("command") or "").lower().strip()

        if normalized == command or normalized in aliases:
            return _copy_command(entry)

    return None


def create_autonomy_command_registry() -> Dict[str, object]:
    return {
        "mode": "read_only_command_registry",
        "status": "locked_descriptions_only",
        "commands": list_autonomy_commands(),
        "safety_rules": [
            "This registry is read-only.",
            "Do not edit files automatically.",
            "Do not execute local commands automatically.",
            "Do not apply patches or repairs silently.",
            "Do not change command text or prefixes.",
            "Do not change route names.",
            "Do not change response mode names.",
            "Do not weaken command API smokes.",
            "Preserve project-state recall.",
            "Richard must run every command manually.",
        ],
        "core_verification": [
            "python .\\tools\\nova_autonomy_command_registry_smoke.py",
            "python .\\tools\\nova_memory_quality_smoke.py",
        ],
        "next_step": "Use this registry as the read-only source of truth before any future command-router refactor.",
    }


def format_autonomy_command_registry(user_text: str = "") -> str:
    registry = create_autonomy_command_registry()
    selected = find_autonomy_command(user_text)

    lines = [
        "Nova autonomy command registry",
        "",
        f"Mode: {registry['mode']}",
        f"Status: {registry['status']}",
        "",
    ]

    if selected:
        lines.extend([
            "Matched command:",
            f"- Command: {selected['command']}",
            f"- Route: {selected['route']}",
            f"- Mode: {selected['mode']}",
            f"- Service: {selected['service']}",
            f"- Formatter: {selected['formatter']}",
            f"- API smoke: {selected['api_smoke']}",
            f"- Service smoke: {selected['service_smoke']}",
            f"- Status: {selected['status']}",
            f"- Purpose: {selected['purpose']}",
            f"- Safety: {selected['safety']}",
            "",
        ])

    lines.append("Locked commands:")

    for item in registry["commands"]:
        lines.extend([
            f"- {item['command']}",
            f"  - Route: {item['route']}",
            f"  - Mode: {item['mode']}",
            f"  - Service: {item['service']}",
            f"  - Formatter: {item['formatter']}",
            f"  - API smoke: {item['api_smoke']}",
            f"  - Service smoke: {item['service_smoke']}",
            f"  - Status: {item['status']}",
            f"  - Purpose: {item['purpose']}",
            f"  - Safety: {item['safety']}",
        ])

    lines.extend(["", "Safety rules:"])
    lines.extend(f"- {item}" for item in registry["safety_rules"])

    lines.extend(["", "Core verification:"])
    lines.extend(f"- {item}" for item in registry["core_verification"])

    lines.extend(["", f"Next step: {registry['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_text = " ".join(sys.argv[1:]).strip()
    print(format_autonomy_command_registry(input_text))
