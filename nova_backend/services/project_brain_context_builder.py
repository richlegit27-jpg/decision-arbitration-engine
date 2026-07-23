from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class ProjectBrainContext:
    project_name: str
    local_app: str
    completed: List[str]
    active_checkpoint: str
    blocker: str
    next_move: str
    validation: List[str]
    recent_commits: List[str]
    user_first_intent: str = ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _exists(relative_path: str) -> bool:
    return (_repo_root() / relative_path).exists()


def _recent_commits(limit: int = 4) -> List[str]:
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--pretty=%h %s"],
            cwd=str(_repo_root()),
            text=True,
            capture_output=True,
            timeout=1.5,
            check=False,
        )

        lines = [
            line.strip()
            for line in (result.stdout or "").splitlines()
            if line.strip()
        ]

        return lines[:limit]

    except Exception:
        return []


def build_project_brain_context() -> ProjectBrainContext:
    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )

    snapshot = build_project_brain_freshness_snapshot()

    user_first_intent = ""

    try:
        from nova_backend.services.onboarding_service import (
            OnboardingService,
        )

        user_first_intent = OnboardingService().get_first_intent(
            "richard"
        )

    except Exception:
        user_first_intent = ""

    return ProjectBrainContext(
        project_name="Nova",
        local_app="local Nova Flask app",
        completed=snapshot.completed,
        active_checkpoint=snapshot.checkpoint,
        blocker=snapshot.blocker,
        next_move=snapshot.next_move,
        validation=snapshot.validation,
        recent_commits=snapshot.recent_commits,
        user_first_intent=user_first_intent,
    )


def _completed_text(context: ProjectBrainContext) -> str:
    return ", ".join(context.completed)


def _recent_commit_text(context: ProjectBrainContext) -> str:
    if not context.recent_commits:
        return "Recent commits were not available from git at answer time."

    return "Recent commits: " + "; ".join(context.recent_commits) + "."

def _first_intent_text(context: ProjectBrainContext) -> str:
    if not context.user_first_intent:
        return ""

    return (
        f" User starting preference: {context.user_first_intent}."
    )


def build_current_project_answer() -> str:
    context = build_project_brain_context()

    return (
        "Source: Project Brain freshness snapshot. "
        f"Current {context.project_name} project state: Richard is working on the "
        f"{context.local_app} with Joe. Completed/protected pieces: {_completed_text(context)}. "
        f"Current checkpoint: {context.active_checkpoint} "
        f"Current blocker: {context.blocker} "
        f"Next move: {context.next_move} "
        f"{_recent_commit_text(context)}"
        f"{_first_intent_text(context)}"
    )


def build_safe_next_answer() -> str:
    return build_project_brain_decision_context_answer(
        user_text="what should we do next"
    )

def build_memory_execution_answer() -> str:
    return (
        "Memory is what Nova remembers: durable facts, preferences, "
        "project context, decisions, and stable information Nova keeps. "
        "Execution is what Nova is actively doing: running commands, "
        "patching files, testing behavior, building plans, and completing "
        "the current live task. Simple split: memory = what Nova knows; "
        "Execution = what Nova does. "
        "Memory should guide Execution, but memory and active work must stay "
        "separate so a concept question does not become a memory-save action."
    )


def build_app_py_risk_answer() -> str:
    context = build_project_brain_context()

    return (
        "`app.py` risk right now: it is too large and has too many stacked guards, wrappers, routes, "
        "`before_request` hooks, and `after_request` hooks competing for priority. The guard-stack audit "
        "protects the most dangerous structural issue: no late hooks below `app.run`. The remaining architecture "
        "risk is behavior priority and maintainability: lower-quality fallback, memory-write, or generic chat "
        "paths can compete with project-brain logic if priority is not protected. "
        f"Current safe direction: {context.next_move}"
        f"{_first_intent_text(context)}"
    )


def build_practical_project_answer() -> str:
    context = build_project_brain_context()

    return (
        "Project Brain context builder: "
        f"Practical {context.project_name} project answer: the project-state route, answer-quality board, "
        "route contract, and classifier broadening are green. "
        f"Current checkpoint: {context.active_checkpoint} "
        f"Current blocker: {context.blocker} "
        f"Next move: {context.next_move} "
        "Safe move: continue focused cleanup, validation, and bounded changes through the existing Project Brain smoke stack. "
        "Safe validation: run the context-builder smoke, project-state memory API smoke, general-intelligence smoke, "
        "route-contract smoke, classifier-broadening smoke, answer-quality smoke, and guard-stack audit. "
        "Then check `git status --short` and commit only after the board is green. "
        f"{_first_intent_text(context)}"
    )
# NOVA_PROJECT_BRAIN_DECISION_CONTEXT_BUILDER_20260702
# Service-only bridge from Project Brain context builder to Decision Engine.
# No Flask wiring, no app.py dependency, no runtime mutation.

def build_project_brain_decision_context_answer(
    user_text="",
    pasted_output="",
    intent=None,
):
    """Build a compact Project Brain decision answer from the Decision Engine."""

    try:
        from nova_backend.services.project_brain_decision_engine import (
            decide_project_brain_next_move,
            format_project_brain_decision,
        )

        from nova_backend.services.project_brain_command_center import (
            build_project_brain_command_center_answer,
        )

        decision = decide_project_brain_next_move(
            user_text=user_text,
            pasted_output=pasted_output,
            intent=intent,
        )

        command_answer = build_project_brain_command_center_answer(
            user_text=user_text,
            pasted_output=pasted_output,
        )

        return (
            "Project Brain decision context:\n"
            + command_answer
            + "\n\nDecision Engine recommendation:\n"
            + format_project_brain_decision(decision)
        )

    except Exception as exc:
        return (
            "Project Brain decision context unavailable. "
            f"Reason: {type(exc).__name__}: {exc}"
        )