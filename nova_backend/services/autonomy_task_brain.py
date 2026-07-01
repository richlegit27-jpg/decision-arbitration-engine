from __future__ import annotations

from typing import Dict, List


class AutonomyTaskBrief:
    def __init__(
        self,
        *,
        goal: str,
        mode: str,
        summary: str,
        likely_files: List[str],
        risks: List[str],
        safety_rules: List[str],
        tests: List[str],
        rollback: List[str],
        next_step: str,
    ) -> None:
        self.goal = goal
        self.mode = mode
        self.summary = summary
        self.likely_files = likely_files
        self.risks = risks
        self.safety_rules = safety_rules
        self.tests = tests
        self.rollback = rollback
        self.next_step = next_step

    def to_dict(self) -> Dict[str, object]:
        return {
            "goal": self.goal,
            "mode": self.mode,
            "summary": self.summary,
            "likely_files": self.likely_files,
            "risks": self.risks,
            "safety_rules": self.safety_rules,
            "tests": self.tests,
            "rollback": self.rollback,
            "next_step": self.next_step,
        }


def _clean_goal(goal: str) -> str:
    return " ".join(str(goal or "").strip().split())


def _contains_any(text: str, needles: List[str]) -> bool:
    low = text.lower()
    return any(needle in low for needle in needles)


def _unique(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []

    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)

    return out


def _likely_files_for_goal(goal: str) -> List[str]:
    low = goal.lower()
    files: List[str] = []

    if _contains_any(low, ["image", "images", "generated image", "description", "caption"]):
        files.extend(
            [
                "nova_backend/services/chat_service.py",
                "static/js/mobile/nova-mobile-images.js",
                "tools/nova_regression_smoke.py",
            ]
        )

    if _contains_any(low, ["memory", "recall", "project state", "checkpoint", "context"]):
        files.extend(
            [
                "nova_backend/services/project_state_service.py",
                "data/nova_project_state.json",
                "tools/nova_memory_quality_smoke.py",
                "tools/nova_project_state_smoke.py",
            ]
        )

    if _contains_any(low, ["session", "sessions", "rename", "switch"]):
        files.extend(
            [
                "static/js/mobile/nova-mobile-sessions.js",
                "nova_backend/services/session_service.py",
                "tools/nova_regression_smoke.py",
            ]
        )

    if _contains_any(low, ["mobile", "phone", "button", "composer", "ui"]):
        files.extend(
            [
                "templates/mobile.html",
                "static/css/nova-mobile.css",
                "static/js/mobile/nova-mobile-ui-utils.js",
            ]
        )

    if _contains_any(low, ["attachment", "upload", "file summary", "summarize file"]):
        files.extend(
            [
                "static/js/mobile/nova-mobile-upload.js",
                "nova_backend/services/chat_service.py",
                "tools/nova_regression_smoke.py",
            ]
        )

    if _contains_any(low, ["planner", "autonomy", "auto", "task", "execute"]):
        files.extend(
            [
                "nova_backend/services/planner_service.py",
                "nova_backend/services/chat_execution_service.py",
                "nova_backend/services/autonomy_task_brain.py",
            ]
        )

    if not files:
        files.extend(
            [
                "nova_backend/services/chat_service.py",
                "tools/nova_regression_smoke.py",
            ]
        )

    return _unique(files)


def _risks_for_goal(goal: str) -> List[str]:
    low = goal.lower()

    risks = [
        "Changing runtime behavior without a smoke test can break a locked path.",
        "Broad routing changes can hijack normal chat, image, web, or execution requests.",
    ]

    if _contains_any(low, ["session", "sessions"]):
        risks.append("Session changes can break switching, rename, or active-session restore.")

    if _contains_any(low, ["image", "images"]):
        risks.append("Image changes can accidentally route generation requests into normal chat.")

    if _contains_any(low, ["memory", "context", "project state"]):
        risks.append("Memory changes can reintroduce stale checkpoint text or noisy project recall.")

    if _contains_any(low, ["mobile", "ui", "button", "composer"]):
        risks.append("Mobile UI changes can break touch targets, sticky composer behavior, or button wiring.")

    return risks


def _tests_for_goal(goal: str) -> List[str]:
    low = goal.lower()

    tests = [
        "python -m py_compile .\\nova_backend\\services\\chat_service.py",
        "python .\\tools\\nova_regression_smoke.py",
    ]

    if _contains_any(low, ["memory", "context", "project state", "checkpoint", "autonomy"]):
        tests.extend(
            [
                "python .\\tools\\nova_project_state_smoke.py",
                "python .\\tools\\nova_project_context_smoke.py",
                "python .\\tools\\nova_memory_quality_smoke.py",
            ]
        )

    if _contains_any(low, ["image", "images"]):
        tests.append("python .\\tools\\nova_project_compact_context_api_smoke.py")

    if _contains_any(low, ["mobile", "session", "sessions", "button", "ui"]):
        tests.extend(
            [
                "node --check .\\static\\js\\mobile\\nova-mobile-sessions.js",
                "node --check .\\static\\js\\mobile\\nova-mobile-ui-utils.js",
                "node --check .\\static\\js\\mobile\\nova-mobile-images.js",
            ]
        )

    return _unique(tests)


def create_autonomy_task_brief(goal: str) -> AutonomyTaskBrief:
    clean_goal = _clean_goal(goal) or "Improve Nova safely."

    return AutonomyTaskBrief(
        goal=clean_goal,
        mode="proposal_only",
        summary=(
            "Create a safe implementation plan before changing code. "
            "Do not edit files until the task brief, risk list, tests, and rollback path are clear."
        ),
        likely_files=_likely_files_for_goal(clean_goal),
        risks=_risks_for_goal(clean_goal),
        safety_rules=[
            "Do not patch more than one subsystem at a time.",
            "Do not modify runtime routing unless a smoke test covers the route.",
            "Prefer tooling-only or guarded route-level changes before service rewrites.",
            "Run compile checks before runtime smoke checks.",
            "Commit only after green tests.",
            "Keep a rollback point with git status and git log.",
        ],
        tests=_tests_for_goal(clean_goal),
        rollback=[
            "git status --short",
            "git log --oneline -5",
            "git restore <changed-file> for uncommitted bad patches",
            "git reset --hard <stable-tag-or-commit> only if the whole patch must be abandoned",
        ],
        next_step="Review this brief, then create the smallest safe patch with matching smoke coverage.",
    )


def format_autonomy_task_brief(goal: str) -> str:
    brief = create_autonomy_task_brief(goal)

    lines = [
        "Nova autonomy task brief",
        "",
        f"Goal: {brief.goal}",
        f"Mode: {brief.mode}",
        "",
        "Summary:",
        f"- {brief.summary}",
        "",
        "Likely files:",
    ]

    lines.extend(f"- {file}" for file in brief.likely_files)

    lines.extend(["", "Risks:"])
    lines.extend(f"- {risk}" for risk in brief.risks)

    lines.extend(["", "Safety rules:"])
    lines.extend(f"- {rule}" for rule in brief.safety_rules)

    lines.extend(["", "Tests:"])
    lines.extend(f"- {test}" for test in brief.tests)

    lines.extend(["", "Rollback:"])
    lines.extend(f"- {step}" for step in brief.rollback)

    lines.extend(["", f"Next step: {brief.next_step}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a Nova autonomy task brief.")
    parser.add_argument("goal", nargs="*", help="Goal to analyze.")
    args = parser.parse_args()

    print(format_autonomy_task_brief(" ".join(args.goal)))
