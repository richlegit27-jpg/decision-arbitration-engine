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

    return ProjectBrainContext(
        project_name="Nova",
        local_app="local Nova Flask app",
        completed=snapshot.completed,
        active_checkpoint=snapshot.checkpoint,
        blocker=snapshot.blocker,
        next_move=snapshot.next_move,
        validation=snapshot.validation,
        recent_commits=snapshot.recent_commits,
    )


def _completed_text(context: ProjectBrainContext) -> str:
    return ", ".join(context.completed)


def _recent_commit_text(context: ProjectBrainContext) -> str:
    if not context.recent_commits:
        return "Recent commits were not available from git at answer time."

    return "Recent commits: " + "; ".join(context.recent_commits) + "."


def build_current_project_answer() -> str:
    context = build_project_brain_context()

    return (
        f"Current {context.project_name} project state: Richard is working on the "
        f"{context.local_app} with Joe. Completed/protected pieces: {_completed_text(context)}. "
        f"Current checkpoint: {context.active_checkpoint} "
        f"Current blocker: {context.blocker} "
        f"Next move: {context.next_move} "
        f"{_recent_commit_text(context)}"
    )


def build_safe_next_answer() -> str:
    context = build_project_brain_context()

    return (
        "Safest next move before changing more code: verify the working tree, compile only the files "
        "being touched, then run the smallest targeted smoke before the full board. Use `git status --short`, "
        "`python -m py_compile`, and the focused smoke first. For this checkpoint, run: "
        + "; ".join(context.validation[:5])
        + ". If those pass, run the remaining project-brain, answer-quality, and guard-stack smokes. "
        "Keep the patch small and targeted; commit only after the board is green."
    )


def build_memory_execution_answer() -> str:
    return (
        "Memory is what Nova remembers, knows, retains, and uses as durable project context: "
        "Richard's preferences, the current Nova checkpoint, project-state facts, blockers, and decisions. "
        "Execution is what Nova is actively doing live: running commands, patching files, calling `/api/chat`, "
        "testing behavior, building a plan, or returning an output. Simple split: memory = what Nova knows; "
        "execution = what Nova does. Memory should guide execution, but it should not hijack a concept question "
        "and turn it into a memory-save response."
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
    )


def build_practical_project_answer() -> str:
    context = build_project_brain_context()

    return (
        f"Practical {context.project_name} project answer: the project-state route, answer-quality board, "
        "route contract, and classifier broadening are green. "
        f"Current blocker: {context.blocker} "
        f"Next concrete move / safe move: {context.next_move} "
        "Safe validation: run the context-builder smoke, project-state memory API smoke, general-intelligence smoke, "
        "route-contract smoke, classifier-broadening smoke, answer-quality smoke, and guard-stack audit. "
        "Then check `git status --short` and commit only after the board is green."
    )
