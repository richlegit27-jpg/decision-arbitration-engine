
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RuntimeCoachReport:
    title: str
    status: str
    passed_count: int
    failed_count: int
    has_traceback: bool
    working_tree_clean: bool
    recommended_action: str
    exact_next_command: str
    why: str
    stop_rule: str
    risk: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "status": self.status,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "has_traceback": self.has_traceback,
            "working_tree_clean": self.working_tree_clean,
            "recommended_action": self.recommended_action,
            "exact_next_command": self.exact_next_command,
            "why": self.why,
            "stop_rule": self.stop_rule,
            "risk": self.risk,
        }


def _clean(value: str) -> str:
    return str(value or "").strip()


def _count_passes(text: str) -> int:
    return len(re.findall(r"(?m)^\s*PASS\b", text or ""))


def _count_failures(text: str) -> int:
    explicit = len(re.findall(r"(?m)^\s*FAIL\b", text or ""))
    assertion = len(re.findall(r"AssertionError:", text or ""))
    traceback = len(re.findall(r"Traceback \(most recent call last\):", text or ""))
    import_error = len(re.findall(r"ImportError:", text or ""))
    type_error = len(re.findall(r"TypeError:", text or ""))
    syntax_error = len(re.findall(r"SyntaxError:", text or ""))

    return explicit + assertion + traceback + import_error + type_error + syntax_error


def _has_traceback(text: str) -> bool:
    value = text or ""
    return (
        "Traceback (most recent call last):" in value
        or "AssertionError:" in value
        or "TypeError:" in value
        or "ImportError:" in value
        or "SyntaxError:" in value
    )


def _working_tree_clean(text: str) -> bool:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    status_indexes = [
        index for index, line in enumerate(lines)
        if "git status --short" in line
    ]

    if not status_indexes:
        return False

    last = status_indexes[-1]
    following = []

    for line in lines[last + 1:]:
        stripped = line.strip()

        if stripped.startswith("PS "):
            continue

        if not stripped:
            continue

        if stripped.startswith("M ") or stripped.startswith("??") or stripped.startswith("A ") or stripped.startswith("D "):
            following.append(stripped)

    return not following


def _has_dirty_status(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*(M|A|D|\?\?)\s+", text or ""))


def _commit_hash(text: str) -> str:
    match = re.search(r"\[[^\]]+\s+([0-9a-f]{7,})\]\s+(.+)", text or "")
    if match:
        return match.group(1)
    return ""


def coach_runtime_output(pasted_output: str) -> RuntimeCoachReport:
    text = str(pasted_output or "")
    passes = _count_passes(text)
    failures = _count_failures(text)
    traceback = _has_traceback(text)
    dirty = _has_dirty_status(text)
    clean = _working_tree_clean(text)
    commit = _commit_hash(text)

    if failures or traceback:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="failed",
            passed_count=passes,
            failed_count=max(1, failures),
            has_traceback=traceback,
            working_tree_clean=clean,
            recommended_action="patch",
            exact_next_command=r"python .\tools\nova_project_brain_mission_autopilot_smoke.py",
            why="A smoke/test produced a failure or traceback; use Auto-Debug Brain and Patch Planner before continuing.",
            stop_rule="Stop immediately. Do not commit. Patch only the failing service layer, then rerun the focused smoke.",
            risk="medium",
        )

    if dirty and not commit:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="green_uncommitted",
            passed_count=passes,
            failed_count=0,
            has_traceback=False,
            working_tree_clean=False,
            recommended_action="commit",
            exact_next_command="git status --short",
            why="Smokes appear green, but the working tree has uncommitted changes.",
            stop_rule="Commit the green batch before starting another upgrade.",
            risk="low",
        )

    if commit and clean:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="locked_clean",
            passed_count=passes,
            failed_count=0,
            has_traceback=False,
            working_tree_clean=True,
            recommended_action="next_upgrade",
            exact_next_command=r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            why="The batch was committed and git status is clean.",
            stop_rule="Safe to start exactly one next bounded service-level upgrade.",
            risk="low",
        )

    if passes and clean:
        return RuntimeCoachReport(
            title="Project Brain Runtime Coach v1",
            status="green_clean",
            passed_count=passes,
            failed_count=0,
            has_traceback=False,
            working_tree_clean=True,
            recommended_action="next_upgrade",
            exact_next_command=r"python .\tools\nova_project_brain_runtime_coach_smoke.py",
            why="Focused smokes passed and the working tree is clean.",
            stop_rule="Safe to continue with one bounded upgrade.",
            risk="low",
        )

    return RuntimeCoachReport(
        title="Project Brain Runtime Coach v1",
        status="unknown",
        passed_count=passes,
        failed_count=0,
        has_traceback=False,
        working_tree_clean=clean,
        recommended_action="inspect",
        exact_next_command="git status --short",
        why="Runtime Coach needs a clearer smoke/test or git-status output.",
        stop_rule="Inspect state before patching or committing.",
        risk="medium",
    )


def build_runtime_coach_dict(pasted_output: str) -> dict:
    return coach_runtime_output(pasted_output).as_dict()


def build_runtime_coach_answer(pasted_output: str) -> str:
    report = coach_runtime_output(pasted_output)

    return "\n".join([
        "Project Brain Runtime Coach:",
        f"Status: {report.status}",
        f"Passed Count: {report.passed_count}",
        f"Failed Count: {report.failed_count}",
        f"Has Traceback: {report.has_traceback}",
        f"Working Tree Clean: {report.working_tree_clean}",
        f"Recommended Action: {report.recommended_action}",
        f"Exact Next Command: {report.exact_next_command}",
        f"Why: {report.why}",
        f"Stop Rule: {report.stop_rule}",
        f"Risk: {report.risk}",
    ])
