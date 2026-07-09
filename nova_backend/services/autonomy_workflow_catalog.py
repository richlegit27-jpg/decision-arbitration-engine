from __future__ import annotations

from typing import Dict, List


def _clean_text(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _unique(items: List[str]) -> List[str]:
    seen = set()
    out = []

    for item in items:
        clean = str(item or "").strip()

        if not clean:
            continue

        key = clean.lower()

        if key in seen:
            continue

        seen.add(key)
        out.append(clean)

    return out


def _detect_workflow(goal: str) -> str:
    low = _clean_text(goal).lower()

    if "repair-build" in low or "repair build" in low or "exact repair" in low:
        return "repair_build"

    if "repair-plan" in low or "repair plan" in low or "failed smoke" in low or "failure" in low:
        return "repair_plan"

    if "patch-build" in low or "patch build" in low or "instructions" in low:
        return "patch_build"

    if "autonomy-plan" in low or "autonomy plan" in low or "proposal" in low:
        return "autonomy_plan"

    if "state" in low or "project-state" in low or "memory" in low:
        return "project_state"

    if "commit" in low or "git" in low:
        return "commit_flow"

    return "standard_safe_workflow"


def _workflow_summary(kind: str) -> str:
    summaries = {
        "repair_build": "Use repair-build output to manually apply the smallest safe repair from failed smoke output.",
        "repair_plan": "Use repair-plan output to identify failure type, likely cause, owner files, tests, and rollback.",
        "patch_build": "Use patch-build output to manually create a narrow supervised patch.",
        "autonomy_plan": "Use autonomy-plan output to produce a proposal before patch instructions.",
        "project_state": "Preserve project-state recall while syncing checkpoint, focus, locked work, and next move.",
        "commit_flow": "Use a clean git workflow: inspect, test, add exact files, commit, verify clean status.",
        "standard_safe_workflow": "Use manual commands only, run smallest smokes first, and preserve locked behavior.",
    }

    return summaries.get(kind, summaries["standard_safe_workflow"])


def _command_groups(kind: str) -> Dict[str, List[str]]:
    groups = {
        "Repository status": [
            "cd C:\\Users\\Owner\\nova",
            "git status --short",
            "git branch --show-current",
        ],
        "Compile checks": [
            "python -m py_compile .\\app.py",
            "python -m py_compile .\\nova_backend\\services\\<changed_service>.py",
            "python -m py_compile .\\tools\\<changed_smoke>.py",
            "node --check .\\static\\js\\mobile\\<changed_file>.js",
        ],
        "Core smokes": [
            "python .\\tools\\nova_memory_quality_smoke.py",
            "python .\\tools\\nova_project_compact_context_api_smoke.py",
            "python .\\tools\\nova_autonomy_command_api_smoke.py",
        ],
        "Autonomy ladder smokes": [
            "python .\\tools\\nova_autonomy_repair_planner_smoke.py",
            "python .\\tools\\nova_autonomy_repair_builder_smoke.py",
            "python .\\tools\\nova_patch_build_command_api_smoke.py",
            "python .\\tools\\nova_repair_plan_command_api_smoke.py",
            "python .\\tools\\nova_repair_build_command_api_smoke.py",
        ],
        "Commit flow": [
            "git status --short",
            "git add <changed-files>",
            "git commit -m \"<narrow commit message>\"",
            "git status --short",
        ],
        "Rollback guidance": [
            "git restore <changed-file>",
            "git reset --hard HEAD",
            "git revert <commit>",
        ],
    }

    if kind == "repair_plan":
        groups["Repair-plan workflow"] = [
            "repair-plan: <failed smoke output>",
            "Review failure type, likely cause, owner files, tests, and rollback.",
            "Do not edit files from repair-plan output alone.",
        ]

    if kind == "repair_build":
        groups["Repair-build workflow"] = [
            "repair-build: <failed smoke output>",
            "Use the generated PowerShell repair steps manually.",
            "Run the listed compile checks and smokes before commit.",
        ]

    if kind == "patch_build":
        groups["Patch-build workflow"] = [
            "patch-build: <goal>",
            "Use the generated PowerShell patch steps manually.",
            "Keep the patch narrow and reversible.",
        ]

    if kind == "autonomy_plan":
        groups["Autonomy-plan workflow"] = [
            "autonomy-plan: <goal>",
            "Review likely files, risks, patch strategy, tests, and rollback.",
            "Only move to patch-build after the proposal looks right.",
        ]

    if kind == "project_state":
        groups["Project-state workflow"] = [
            "Update data\\nova_project_state.json only after feature smoke passes.",
            "Run python .\\tools\\nova_memory_quality_smoke.py before commit.",
            "Keep Memory quality smoke, Project-state recall, and Regression runner visible in locked state.",
        ]

    return groups


def create_safe_workflow_catalog(goal: str) -> Dict[str, object]:
    clean_goal = _clean_text(goal)
    kind = _detect_workflow(clean_goal)
    groups = _command_groups(kind)

    return {
        "mode": "manual_workflow_catalog_only",
        "workflow": kind,
        "goal": clean_goal or "General safe Nova workflow",
        "summary": _workflow_summary(kind),
        "safety_rules": [
            "Do not edit files automatically.",
            "Do not execute local commands automatically.",
            "Do not apply patches or repairs silently.",
            "Richard must run every command manually.",
            "Prefer the smallest relevant smoke before broad smokes.",
            "Preserve project-state recall and locked autonomy commands.",
            "Commit only after smoke output is green and git status is understood.",
        ],
        "approved_manual_command_groups": groups,
        "forbidden_actions": [
            "Automatic command execution",
            "Automatic file edits",
            "Silent git add or commit",
            "Broad unrelated rewrites",
            "Skipping rollback guidance",
            "Weakening smokes to hide real failures",
        ],
        "default_smoke_order": [
            "Smallest changed service smoke",
            "Changed command API smoke",
            "python .\\tools\\nova_memory_quality_smoke.py",
            "git status --short",
        ],
        "next_step": "Choose the matching command group and run commands manually.",
    }


def format_safe_workflow_catalog(goal: str) -> str:
    catalog = create_safe_workflow_catalog(goal)

    lines = [
        "Nova safe workflow catalog",
        "",
        f"Mode: {catalog['mode']}",
        f"Workflow: {catalog['workflow']}",
        f"Goal: {catalog['goal']}",
        "",
        f"Summary: {catalog['summary']}",
        "",
        "Safety rules:",
    ]

    lines.extend(f"- {item}" for item in catalog["safety_rules"])

    lines.extend(["", "Approved manual command groups:"])

    groups = catalog["approved_manual_command_groups"]
    for group_name, commands in groups.items():
        lines.append(f"- {group_name}:")
        for command in commands:
            lines.append(f"  - {command}")

    lines.extend(["", "Default smoke order:"])
    lines.extend(f"- {item}" for item in catalog["default_smoke_order"])

    lines.extend(["", "Forbidden actions:"])
    lines.extend(f"- {item}" for item in catalog["forbidden_actions"])

    lines.extend(["", f"Next step: {catalog['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_text = " ".join(sys.argv[1:]).strip()

    if not input_text:
        input_text = sys.stdin.read()

    print(format_safe_workflow_catalog(input_text))
