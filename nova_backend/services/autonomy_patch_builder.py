from __future__ import annotations

from typing import Dict, List

from nova_backend.services.autonomy_patch_planner import create_autonomy_patch_plan


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


def _win_path(file_path: str) -> str:
    return str(file_path or "").replace("/", "\\")


def _compile_checks(files: List[str]) -> List[str]:
    checks = []

    for file_path in files:
        win_path = _win_path(file_path)

        if file_path.endswith(".py"):
            checks.append(f"python -m py_compile .\\{win_path}")
        elif file_path.endswith(".js"):
            checks.append(f"node --check .\\{win_path}")

    return _unique(checks)


def _powershell_steps(goal: str, files: List[str], tests: List[str]) -> List[str]:
    file_list = ", ".join(files) if files else "target files from planner output"

    return [
        "cd C:\\Users\\Owner\\nova",
        "git status --short",
        f"# Review likely files before editing: {file_list}",
        "# Create a narrow patch only for the listed subsystem.",
        "# Do not run generated commands automatically inside Nova.",
        "# After editing, run compile checks for changed Python/JS files.",
        *tests,
        "git status --short",
    ]


def create_autonomy_patch_build(goal: str) -> Dict[str, object]:
    plan = create_autonomy_patch_plan(goal)

    files = list(plan.get("likely_files") or [])
    tests = list(plan.get("tests") or [])

    compile_checks = _compile_checks(files)

    return {
        "goal": plan.get("goal") or str(goal or "").strip() or "Improve Nova safely.",
        "mode": "instructions_only",
        "safety_rules": [
            "Do not edit files automatically.",
            "Do not execute local commands automatically.",
            "Do not apply patches silently.",
            "Richard must run every command manually.",
            "Keep the patch narrow and reversible.",
        ],
        "files_to_change": files,
        "powershell_steps": _powershell_steps(str(plan.get("goal") or goal), files, tests),
        "compile_checks": compile_checks,
        "smokes": tests,
        "commit_commands": [
            "git status --short",
            "git add <changed-files>",
            "git commit -m \"<narrow subsystem commit message>\"",
            "git status --short",
        ],
        "rollback_commands": [
            "git restore <changed-file>",
            "git reset --hard HEAD",
            "git revert <commit>",
        ],
        "planner_summary": plan,
        "next_step": "Use these instructions to create the smallest supervised patch. Do not execute anything automatically.",
    }


def format_autonomy_patch_build(goal: str) -> str:
    build = create_autonomy_patch_build(goal)

    lines = [
        "Nova supervised patch build",
        "",
        f"Goal: {build['goal']}",
        f"Mode: {build['mode']}",
        "",
        "Safety rules:",
    ]

    lines.extend(f"- {item}" for item in build["safety_rules"])

    lines.extend(["", "Files to change:"])
    lines.extend(f"- {item}" for item in build["files_to_change"])

    lines.extend(["", "PowerShell patch steps:"])
    lines.extend(f"{index}. {item}" for index, item in enumerate(build["powershell_steps"], start=1))

    lines.extend(["", "Compile checks:"])

    if build["compile_checks"]:
        lines.extend(f"- {item}" for item in build["compile_checks"])
    else:
        lines.append("- No Python/JS compile checks inferred from likely files.")

    lines.extend(["", "Smokes:"])
    lines.extend(f"- {item}" for item in build["smokes"])

    lines.extend(["", "Commit commands:"])
    lines.extend(f"- {item}" for item in build["commit_commands"])

    lines.extend(["", "Rollback commands:"])
    lines.extend(f"- {item}" for item in build["rollback_commands"])

    lines.extend(["", f"Next step: {build['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create Nova supervised patch-build instructions.")
    parser.add_argument("goal", nargs="*", help="Goal to build patch instructions for.")
    args = parser.parse_args()

    print(format_autonomy_patch_build(" ".join(args.goal)))
