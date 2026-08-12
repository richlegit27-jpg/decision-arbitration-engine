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
    active_project_id: str = ""
    active_project_title: str = ""
    active_project_status: str = ""
    active_project_description: str = ""

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


def build_project_brain_context(user_id=None) -> ProjectBrainContext:
    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )

    snapshot = build_project_brain_freshness_snapshot()

    active_project_id = ""
    active_project_title = ""
    active_project_status = ""
    active_project_description = ""

    try:
        from nova_backend.services.project_workspace_service import (
            ProjectWorkspaceService,
        )

        active_project = (
            ProjectWorkspaceService()
            .get_active_project()
        )

        if active_project:
            active_project_id = str(
                active_project.get(
                    "id",
                    ""
                )
            )

            active_project_title = str(
                active_project.get(
                    "title",
                    active_project.get(
                        "name",
                        ""
                    )
                )
            )

            active_project_status = str(
                active_project.get(
                    "status",
                    ""
                )
            )

            active_project_description = str(
                active_project.get(
                    "description",
                    ""
                )
            )

    except Exception:
        pass

    user_first_intent = ""

    try:
        if user_id:
            from nova_backend.services.onboarding_service import (
                OnboardingService,
            )

            user_first_intent = OnboardingService().get_first_intent(
                user_id
            )

    except Exception:
        user_first_intent = ""

    return ProjectBrainContext(
        project_name="Nova",
        local_app="local Nova Flask app",
        completed=snapshot.completed,
        active_checkpoint=snapshot.checkpoint,
        blocker=snapshot.blocker,
        next_move=snapshot.next_move.replace("Next move: ", ""),
        validation=snapshot.validation,
        recent_commits=snapshot.recent_commits,
        user_first_intent=user_first_intent,
        active_project_id=active_project_id,
        active_project_title=active_project_title,
        active_project_status=active_project_status,
        active_project_description=active_project_description,
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


def build_current_project_answer(user_id=None) -> str:
    context = build_project_brain_context(
        user_id=user_id
    )

    return (
        "Project Brain Context Builder:\n\n"
        f"Current checkpoint:\n"
        f"{context.active_checkpoint}\n\n"
        f"Current blocker:\n"
        f"{context.blocker}\n\n"
        f"Next move:\n"
        f"{context.next_move}\n\n"
        "Validation:\n"
        f"{', '.join(context.validation) if context.validation else 'No validation items loaded.'}"
    )

def build_safe_next_answer() -> str:
    return build_project_brain_decision_context_answer(
        user_text="what should we do next"
    )

def build_memory_execution_answer() -> str:
    return (
        "Memory and Execution are separate Nova layers.\n\n"
        "Memory = what Nova remembers, knows, retains, and stores as durable information:\n"
        "facts, preferences, project history, and stable decisions.\n\n"
        "Execution = what Nova does live:\n"
        "running commands, taking actions, applying patches, testing behavior, "
        "and completing the current objective.\n\n"
        "Active context connects them:\n"
        "current task, blocker, latest correction, and next move.\n\n"
        "Rule:\n"
        "Memory guides Execution, but memory should never become an automatic execution command."
    )


def build_app_py_risk_answer() -> str:
    return (
        "`app.py` risk right now:\n\n"
        "The main architecture risk is that app.py has become too large with too many "
        "stacked guards, wrappers, hooks, and route decisions.\n\n"
        "Risk areas:\n"
        "- before_request hooks and after_request hooks can create ordering problems.\n"
        "- app.run and late hooks can hide runtime behavior.\n"
        "- Too many route guards make ownership unclear.\n\n"
        "Recommended move:\n"
        "Run an architecture audit and focused smoke tests before cleanup.\n\n"
        "Goal:\n"
        "Protect against regression while doing cleanup and reducing complexity."
    )

def build_practical_project_answer() -> str:
    return (
        "Practical Nova project answer:\n\n"
        "Current checkpoint:\n"
        "Pre-launch stabilization.\n\n"
        "Current project state:\n"
        "Nova is focused on reliability, user flows, memory recall, and answer quality.\n\n"
        "Current blocker:\n"
        "Finish validation and remove remaining launch blockers.\n\n"
        "Next move:\n"
        "Make the smallest safe change, test it, and check git status.\n\n"
        "Answer quality and memory recall matter more than adding new features.\n\n"
        "Run the relevant smoke test after changes."
    )

# NOVA_PROJECT_BRAIN_DECISION_CONTEXT_BUILDER_20260702
# Service-only bridge from Project Brain context builder to Decision Engine.
# No Flask wiring, no app.py dependency, no runtime mutation.

    return (
        "Nova Project Brain Decision:\n\n"
        f"{decision_text}\n\n"
        "Current phase:\n"
        "Pre-launch stabilization.\n\n"
        "Priority:\n"
        "Protect reliability, validate user flows, and remove remaining launch blockers.\n\n"
        "Rule:\n"
        "Prefer the smallest safe change that improves launch readiness."
    )

def build_project_brain_decision_context_answer(
    user_text="",
    pasted_output="",
    intent=None,
):
    try:
        from nova_backend.services.project_brain_decision_engine import (
            decide_project_brain_next_move,
            format_project_brain_decision,
        )

        decision = decide_project_brain_next_move(
            user_text=user_text,
            pasted_output=pasted_output,
            intent=intent,
        )

        decision_text = format_project_brain_decision(
            decision
        )

        return (
            "Project Brain Context Builder\n\n"
            "Command intent: "
            f"{intent or decision.get('intent', 'general_project_answer')}\n\n"
            "Nova Project Brain Decision:\n\n"
            f"{decision_text}\n\n"
            "Current checkpoint:\n"
            "Pre-launch stabilization.\n\n"
            "Current project state:\n"
            "Protect reliability, validate user flows, and remove remaining launch blockers.\n\n"
            "Current blocker:\n"
            "No critical blocker. Remaining work is validation, regression protection, and launch cleanup.\n\n"
            "Next move:\n"
            "Run the smallest focused smoke test after each safe change.\n\n"
            "Target Files:\n"
            "Use only the files directly involved in the current behavior change.\n\n"
            "Rule:\n"
            "Prefer the smallest safe change that improves Nova launch readiness."
        )

    except Exception as exc:
        return (
            "Project Brain decision context unavailable. "
            f"Reason: {type(exc).__name__}: {exc}"
        )