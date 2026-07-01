from __future__ import annotations

import re
from typing import Dict, List


def _clean_text(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _lines(text: str) -> List[str]:
    return [line.rstrip() for line in _clean_text(text).split("\n") if line.strip()]


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


def _extract_failed_checks(text: str) -> List[str]:
    found = []

    for line in _lines(text):
        low = line.lower().strip()

        if low.startswith("failed checks:"):
            continue

        if line.strip().startswith("- "):
            item = line.strip()[2:].strip()
            if item:
                found.append(item)

        if " failed" in low and "traceback" not in low:
            found.append(line.strip())

    return _unique(found)


def _extract_traceback_files(text: str) -> List[str]:
    found = []

    for match in re.finditer(r'File "([^"]+)"', text):
        file_path = match.group(1).strip()

        if not file_path:
            continue

        normalized = file_path.replace("\\", "/")

        if "/nova/" in normalized:
            normalized = normalized.split("/nova/", 1)[1]

        found.append(normalized.replace("/", "\\"))

    return _unique(found)


def _classify_failure(text: str) -> str:
    low = text.lower()

    if "keyboardinterrupt" in low:
        return "interrupted_or_hanging_smoke"

    if "timeout" in low or "timed out" in low:
        return "timeout_or_slow_route"

    if "missing [" in low or "missing '" in low or "missing " in low:
        return "missing_expected_text"

    if "assertionerror" in low:
        return "assertion_failure"

    if "syntaxerror" in low or "indentationerror" in low:
        return "syntax_failure"

    if "filenotfounderror" in low or "no such file" in low:
        return "missing_file_or_wrong_path"

    if "connection refused" in low or "unable to connect" in low:
        return "server_not_running"

    return "unknown_failure"


def _likely_cause(kind: str, text: str) -> str:
    low = text.lower()

    if kind == "interrupted_or_hanging_smoke":
        return (
            "A smoke test likely hit a slow live route, normal model call, or server wait "
            "instead of a deterministic fast path."
        )

    if kind == "timeout_or_slow_route":
        return (
            "A test route is taking too long or depends on live network/model behavior. "
            "The smallest repair is usually to make the smoke deterministic."
        )

    if kind == "missing_expected_text":
        return (
            "The feature may be working, but the rendered response does not contain one "
            "of the exact words the smoke expects."
        )

    if kind == "syntax_failure":
        return "A changed Python or JavaScript file has a syntax/indentation error."

    if kind == "missing_file_or_wrong_path":
        return (
            "The command was likely run from the wrong folder, or the expected file has "
            "not been created yet."
        )

    if kind == "server_not_running":
        return "The API smoke is trying to call Nova, but the local Flask server is not reachable."

    if "project_state" in low or "project-state" in low:
        return "Project-state recall output is out of sync with the smoke expectations."

    return "The failure needs a narrow inspection of the traceback, failed check name, and touched files."


def _files_to_inspect(kind: str, text: str) -> List[str]:
    files = _extract_traceback_files(text)
    low = text.lower()

    if "nova_memory_quality_smoke" in low:
        files.append("tools\\nova_memory_quality_smoke.py")

    if "nova_project_state_smoke" in low or "project-state" in low or "project_state" in low:
        files.extend([
            "data\\nova_project_state.json",
            "nova_backend\\services\\project_state_service.py",
            "tools\\nova_project_state_smoke.py",
        ])

    if "nova_autonomy_command_api_smoke" in low or "normal chat not hijacked" in low:
        files.append("tools\\nova_autonomy_command_api_smoke.py")

    if "nova_patch_build_command_api_smoke" in low or "patch-build" in low:
        files.extend([
            "app.py",
            "tools\\nova_patch_build_command_api_smoke.py",
            "nova_backend\\services\\autonomy_patch_builder.py",
        ])

    if "filenotfounderror" in low or "no such file" in low:
        files.append("PowerShell current directory / repo root")

    if not files:
        files.extend([
            "tools\\nova_regression_smoke.py",
            "app.py",
        ])

    return _unique(files)


def _smallest_safe_repair(kind: str, text: str) -> List[str]:
    if kind in {"interrupted_or_hanging_smoke", "timeout_or_slow_route"}:
        return [
            "Replace slow normal-chat or live-network smoke input with a deterministic fast guard input.",
            "Do not change production routing first.",
            "Re-run the specific smoke that hung before running the full memory quality smoke.",
        ]

    if kind == "missing_expected_text":
        return [
            "Identify the exact rendered response that the smoke checks.",
            "Patch the source field or formatter so the expected word appears in the visible output.",
            "Avoid weakening the smoke unless the expectation is obsolete.",
        ]

    if kind == "syntax_failure":
        return [
            "Run py_compile or node --check on the changed file.",
            "Fix only the syntax block shown by the compiler.",
            "Re-run the smallest service smoke before broader smokes.",
        ]

    if kind == "missing_file_or_wrong_path":
        return [
            "Run cd C:\\Users\\Owner\\nova before file commands.",
            "Verify the target directory exists.",
            "Create the missing file only if it is part of the intended patch.",
        ]

    if kind == "server_not_running":
        return [
            "Start the local Nova Flask server.",
            "Verify http://127.0.0.1:5001/api/backend/readiness returns 200.",
            "Re-run only the API smoke.",
        ]

    return [
        "Patch the smallest owner file identified by the failed check.",
        "Do not combine this repair with unrelated feature work.",
        "Re-run the failed smoke first, then memory quality smoke.",
    ]


def _tests(kind: str, text: str) -> List[str]:
    tests = []

    low = text.lower()

    if "nova_autonomy_command_api_smoke" in low:
        tests.append("python .\\tools\\nova_autonomy_command_api_smoke.py")

    if "nova_patch_build_command_api_smoke" in low or "patch-build" in low:
        tests.append("python .\\tools\\nova_patch_build_command_api_smoke.py")

    if "nova_project_state_smoke" in low or "project-state" in low or "project_state" in low:
        tests.append("python .\\tools\\nova_project_state_smoke.py")

    if "nova_memory_quality_smoke" in low or "memory quality" in low:
        tests.append("python .\\tools\\nova_memory_quality_smoke.py")

    if not tests:
        tests.extend([
            "python .\\tools\\nova_regression_smoke.py",
            "python .\\tools\\nova_memory_quality_smoke.py",
        ])

    return _unique(tests)


def create_autonomy_repair_plan(failed_output: str) -> Dict[str, object]:
    clean = _clean_text(failed_output)
    kind = _classify_failure(clean)
    failed_checks = _extract_failed_checks(clean)
    files = _files_to_inspect(kind, clean)

    return {
        "mode": "repair_proposal_only",
        "failure_type": kind,
        "failure_summary": failed_checks[:8] or ["No explicit failed check found; inspect traceback and last command output."],
        "likely_cause": _likely_cause(kind, clean),
        "files_to_inspect": files,
        "smallest_safe_repair": _smallest_safe_repair(kind, clean),
        "patch_strategy": [
            "Do not edit files automatically.",
            "Do not execute commands automatically.",
            "Make one narrow repair for the failed smoke only.",
            "Preserve project-state recall and existing locked autonomy commands.",
            "Commit only after the smallest relevant smoke passes.",
        ],
        "tests": _tests(kind, clean),
        "rollback_plan": [
            "Before commit: git restore <changed-file>",
            "After commit: git revert <commit>",
            "Emergency recovery: git reset --hard <stable-tag>",
        ],
        "next_step": "Create the smallest repair only after reviewing this proposal.",
    }


def format_autonomy_repair_plan(failed_output: str) -> str:
    plan = create_autonomy_repair_plan(failed_output)

    lines = [
        "Nova supervised repair proposal",
        "",
        f"Mode: {plan['mode']}",
        f"Failure type: {plan['failure_type']}",
        "",
        "Failure summary:",
    ]

    lines.extend(f"- {item}" for item in plan["failure_summary"])

    lines.extend(["", f"Likely cause: {plan['likely_cause']}"])

    lines.extend(["", "Files to inspect:"])
    lines.extend(f"- {item}" for item in plan["files_to_inspect"])

    lines.extend(["", "Smallest safe repair:"])
    lines.extend(f"- {item}" for item in plan["smallest_safe_repair"])

    lines.extend(["", "Patch strategy:"])
    lines.extend(f"- {item}" for item in plan["patch_strategy"])

    lines.extend(["", "Tests:"])
    lines.extend(f"- {item}" for item in plan["tests"])

    lines.extend(["", "Rollback plan:"])
    lines.extend(f"- {item}" for item in plan["rollback_plan"])

    lines.extend(["", f"Next step: {plan['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_text = " ".join(sys.argv[1:]).strip()

    if not input_text:
        input_text = sys.stdin.read()

    print(format_autonomy_repair_plan(input_text))
