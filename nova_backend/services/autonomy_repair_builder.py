from __future__ import annotations

from typing import Dict, List

from nova_backend.services.autonomy_repair_planner import create_autonomy_repair_plan


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


def _compile_checks(files: List[str]) -> List[str]:
    checks = []

    for file_path in files:
        normalized = str(file_path or "").replace("/", "\\").strip()
        low = normalized.lower()

        if not normalized:
            continue

        if low.endswith(".py"):
            checks.append(f"python -m py_compile .\\{normalized}")

        if low.endswith(".js"):
            checks.append(f"node --check .\\{normalized}")

    if not checks:
        checks.append("# No compile-only check for JSON/data-only repair.")

    return _unique(checks)


def _manual_review_steps(files: List[str]) -> List[str]:
    steps = [
        "cd C:\\Users\\Owner\\nova",
        "git status --short",
        "# Read the failed smoke output again and confirm the exact failed check.",
    ]

    for file_path in files:
        normalized = str(file_path or "").replace("/", "\\").strip()

        if not normalized:
            continue

        if normalized.lower().startswith("powershell current directory"):
            steps.append("# Confirm PowerShell is already at C:\\Users\\Owner\\nova")
        else:
            steps.append(f"# Inspect owner file: {normalized}")

    steps.extend([
        "# Apply one narrow repair only.",
        "# Do not change unrelated routing, UI, memory, or smoke behavior.",
        "# Preserve project-state recall wording if this is a project-state failure.",
        "# Re-run the smallest failed smoke first.",
    ])

    return _unique(steps)


def _smoke_steps(plan: Dict[str, object]) -> List[str]:
    tests = plan.get("tests")

    if isinstance(tests, list):
        out = [str(item).strip() for item in tests if str(item).strip()]
    else:
        out = []

    if "python .\\tools\\nova_memory_quality_smoke.py" not in [x.lower() for x in out]:
        out.append("python .\\tools\\nova_memory_quality_smoke.py")

    return _unique(out)


def create_autonomy_repair_build(failed_output: str) -> Dict[str, object]:
    clean = _clean_text(failed_output)
    plan = create_autonomy_repair_plan(clean)

    files = plan.get("files_to_inspect")
    if not isinstance(files, list):
        files = []

    files = _unique([str(item) for item in files])

    return {
        "mode": "repair_instructions_only",
        "failure_type": plan.get("failure_type", "unknown_failure"),
        "failure_summary": plan.get("failure_summary", []),
        "likely_cause": plan.get("likely_cause", ""),
        "files_to_inspect": files,
        "manual_repair_steps": _manual_review_steps(files),
        "compile_checks": _compile_checks(files),
        "smokes": _smoke_steps(plan),
        "commit_commands": [
            "git status --short",
            "git add <changed-files>",
            "git commit -m \"<narrow repair commit message>\"",
            "git status --short",
        ],
        "rollback_commands": [
            "git restore <changed-file>",
            "git reset --hard HEAD",
            "git revert <commit>",
        ],
        "safety_rules": [
            "Do not edit files automatically.",
            "Do not execute local commands automatically.",
            "Do not apply repairs silently.",
            "Richard must run every command manually.",
            "Keep the repair narrow and reversible.",
            "Preserve project-state recall and locked autonomy commands.",
        ],
        "next_step": "Use these instructions manually, then run the listed smokes before committing.",
    }


def format_autonomy_repair_build(failed_output: str) -> str:
    build = create_autonomy_repair_build(failed_output)

    lines = [
        "Nova supervised repair build",
        "",
        f"Mode: {build['mode']}",
        f"Failure type: {build['failure_type']}",
        "",
        "Safety rules:",
    ]

    lines.extend(f"- {item}" for item in build["safety_rules"])

    lines.extend(["", "Failure summary:"])
    lines.extend(f"- {item}" for item in build["failure_summary"])

    lines.extend(["", f"Likely cause: {build['likely_cause']}"])

    lines.extend(["", "Files to inspect:"])
    lines.extend(f"- {item}" for item in build["files_to_inspect"])

    lines.extend(["", "PowerShell repair steps:"])
    for index, step in enumerate(build["manual_repair_steps"], start=1):
        lines.append(f"{index}. {step}")

    lines.extend(["", "Compile checks:"])
    lines.extend(f"- {item}" for item in build["compile_checks"])

    lines.extend(["", "Smokes:"])
    lines.extend(f"- {item}" for item in build["smokes"])

    lines.extend(["", "Commit commands:"])
    lines.extend(f"- {item}" for item in build["commit_commands"])

    lines.extend(["", "Rollback commands:"])
    lines.extend(f"- {item}" for item in build["rollback_commands"])

    lines.extend(["", f"Next step: {build['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_text = " ".join(sys.argv[1:]).strip()

    if not input_text:
        input_text = sys.stdin.read()

    print(format_autonomy_repair_build(input_text))
