from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ProjectBrainFailureInterpretation:
    failure_type: str
    severity: str
    likely_source: str
    patch_target: str
    do_not_touch: list[str]
    next_command: str
    evidence: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: object) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def _lower(value: object) -> str:
    return _clean(value).lower()


def _first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ""
    return str(match.group(1) or "").strip()


def _evidence_lines(text: str, needles: list[str], limit: int = 6) -> list[str]:
    lines = []
    lower_needles = [needle.lower() for needle in needles]

    for line in _clean(text).splitlines():
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if clean_line and any(needle in lower_line for needle in lower_needles):
            lines.append(clean_line)

        if len(lines) >= limit:
            break

    return lines


def interpret_project_brain_failure(
    user_text: str = "",
    pasted_output: str = "",
) -> ProjectBrainFailureInterpretation:
    combined = _clean(user_text) + "\n" + _clean(pasted_output)
    lower = combined.lower()

    default_do_not_touch = [
        "do not add a blind app.py guard",
        "do not weaken the smoke just to pass",
        "do not patch historical nova_backups hits",
        "do not commit before the focused smoke passes",
    ]

    if "winerror 10061" in lower or "actively refused" in lower or "connection refused" in lower:
        return ProjectBrainFailureInterpretation(
            failure_type="server_not_running",
            severity="low",
            likely_source="Nova Flask server is not running or not listening on the smoke BASE_URL.",
            patch_target="runtime only: start server, no code patch",
            do_not_touch=default_do_not_touch + [
                "do not edit code for a refused connection unless the server fails to boot",
            ],
            next_command="python app.py",
            evidence=_evidence_lines(combined, ["WinError 10061", "actively refused", "connection refused"]),
            rationale=(
                "The smoke could not connect to /api/chat, so this is an environment/runtime state "
                "failure before it is a product behavior failure."
            ),
        )

    if "indentationerror" in lower or "syntaxerror" in lower or "sorry:" in lower:
        file_name = _first_match(r"\(([^()]+\.py), line \d+\)", combined)
        if not file_name:
            file_name = _first_match(r'File "([^"]+\.py)"', combined)

        patch_target = file_name or "the Python file named in the traceback"

        return ProjectBrainFailureInterpretation(
            failure_type="python_compile_error",
            severity="high",
            likely_source="A changed Python file has invalid syntax or indentation.",
            patch_target=patch_target,
            do_not_touch=default_do_not_touch + [
                "do not run broader smokes until py_compile passes",
            ],
            next_command=f"python -m py_compile {patch_target}",
            evidence=_evidence_lines(combined, ["IndentationError", "SyntaxError", "Sorry:", "File "]),
            rationale=(
                "A compile error blocks runtime validation. Fix the exact file and line first, then rerun "
                "py_compile before any smoke."
            ),
        )

    if "missing=[" in lower and "includes expected signals failed" in lower:
        case_name = _first_match(r"^(.+?) includes expected signals FAILED", combined)
        missing = _first_match(r"missing=\[([^\]]+)\]", combined)

        return ProjectBrainFailureInterpretation(
            failure_type="smoke_contract_mismatch",
            severity="medium",
            likely_source="The runtime answer and smoke expected terms disagree.",
            patch_target="source wording if product answer is stale; smoke contract if expectation is stale",
            do_not_touch=default_do_not_touch + [
                "do not blindly remove expected terms",
                "do not patch app.py unless the route is wrong",
            ],
            next_command="python .\\tools\\nova_answer_quality_smoke.py",
            evidence=_evidence_lines(combined, ["includes expected signals FAILED", "missing=[", "CASE:", "ANSWER:"]),
            rationale=(
                f"The failing case {case_name or 'unknown'} is missing {missing or 'expected terms'}. "
                "Decide whether the product answer or the smoke contract is the stale side, then patch only that layer."
            ),
        )

    if "route" in lower and ("failed" in lower or "expected" in lower) and "project_" in lower:
        return ProjectBrainFailureInterpretation(
            failure_type="route_contract_mismatch",
            severity="high",
            likely_source="A live /api/chat route or debug.route_taken contract no longer matches the expected Project Brain path.",
            patch_target="classifier/selector service first; app.py only if locator proves route stealing",
            do_not_touch=default_do_not_touch + [
                "do not add another route-layer priority guard before locating the stealing route",
            ],
            next_command="python .\\tools\\nova_regression_smoke.py",
            evidence=_evidence_lines(combined, ["route", "FAILED", "expected", "project_"]),
            rationale=(
                "Route mismatches can indicate priority hijacking. Protect direct recall and broad Project Brain "
                "routing before changing answer wording."
            ),
        )

    if "git status --short" in lower and (" m " in lower or "?? " in lower):
        return ProjectBrainFailureInterpretation(
            failure_type="dirty_worktree",
            severity="medium",
            likely_source="There are uncommitted modified or untracked files.",
            patch_target="git staging/commit discipline",
            do_not_touch=default_do_not_touch + [
                "do not start a new patch while the tree is dirty unless intentionally stacking fixes",
            ],
            next_command="git diff --stat",
            evidence=_evidence_lines(combined, [" M ", "?? ", "git status --short"]),
            rationale=(
                "A dirty tree is not automatically bad, but it must be understood before another patch or commit."
            ),
        )

    if "failed" in lower or "traceback" in lower or "assertionerror" in lower:
        return ProjectBrainFailureInterpretation(
            failure_type="generic_failure",
            severity="medium",
            likely_source="A command failed, but the output does not match a more specific Project Brain failure pattern.",
            patch_target="the narrow file named by the traceback or focused smoke",
            do_not_touch=default_do_not_touch,
            next_command="rerun the smallest focused smoke with the full traceback visible",
            evidence=_evidence_lines(combined, ["FAILED", "Traceback", "AssertionError", "ERROR"]),
            rationale=(
                "The output has a real failure signal. Preserve the failing evidence and locate the narrowest source."
            ),
        )

    return ProjectBrainFailureInterpretation(
        failure_type="no_failure_detected",
        severity="low",
        likely_source="No clear failure pattern detected.",
        patch_target="none",
        do_not_touch=default_do_not_touch,
        next_command="git status --short",
        evidence=[],
        rationale="The pasted output does not contain a known failure marker.",
    )


def format_project_brain_failure_interpretation(result: ProjectBrainFailureInterpretation) -> str:
    return (
        "Project Brain Failure Interpreter:\n"
        f"Failure type: {result.failure_type}\n"
        f"Severity: {result.severity}\n"
        f"Likely source: {result.likely_source}\n"
        f"Patch target: {result.patch_target}\n"
        f"Do not touch: {'; '.join(result.do_not_touch)}\n"
        f"Next command: {result.next_command}\n"
        f"Evidence: {'; '.join(result.evidence) if result.evidence else 'none'}\n"
        f"Rationale: {result.rationale}"
    )


def build_project_brain_failure_interpreter_answer(
    user_text: str = "",
    pasted_output: str = "",
) -> str:
    result = interpret_project_brain_failure(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    return format_project_brain_failure_interpretation(result)
