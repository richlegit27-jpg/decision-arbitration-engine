from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


SNAPSHOT_VERSION = "project-brain-freshness-v2"


SMOKE_FILES: Dict[str, str] = {
    "project-state memory API smoke": "tools/nova_project_state_memory_api_smoke.py",
    "general intelligence smoke": "tools/nova_general_intelligence_smoke.py",
    "project-brain route contract smoke": "tools/nova_project_brain_route_contract_smoke.py",
    "project-brain classifier broadening smoke": "tools/nova_project_brain_classifier_broadening_smoke.py",
    "project-brain context builder smoke": "tools/nova_project_brain_context_builder_smoke.py",
    "answer-quality smoke": "tools/nova_answer_quality_smoke.py",
    "guard-stack audit smoke": "tools/nova_phase_4i_guard_stack_audit_smoke.py",
}


@dataclass(frozen=True)
class ProjectBrainFreshnessSnapshot:
    version: str
    checkpoint: str
    blocker: str
    next_move: str
    completed: List[str]
    validation: List[str]
    available_smoke_files: List[str]
    missing_smoke_files: List[str]
    recent_commits: List[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _exists(relative_path: str) -> bool:
    return (_repo_root() / relative_path).exists()


def _recent_commits(limit: int = 5) -> List[str]:
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--pretty=%h %s"],
            cwd=str(_repo_root()),
            text=True,
            capture_output=True,
            timeout=1.5,
            check=False,
        )

        return [
            line.strip()
            for line in (result.stdout or "").splitlines()
            if line.strip()
        ][:limit]

    except Exception:
        return []


def _available_smoke_files() -> List[str]:
    return [
        name
        for name, relative_path in SMOKE_FILES.items()
        if _exists(relative_path)
    ]


def _missing_smoke_files() -> List[str]:
    return [
        name
        for name, relative_path in SMOKE_FILES.items()
        if not _exists(relative_path)
    ]


def _completed_items(available_smokes: List[str]) -> List[str]:
    completed = [
        "project-state memory recall fix",
        "answer-quality 95 policy",
        "Project Brain general-intelligence service layer",
        "Project Brain context builder",
        "Project Brain freshness v2 wording lock",
    ]

    completed.extend(available_smokes)

    return completed


def _validation_commands(available_smokes: List[str]) -> List[str]:
    commands = [
        "python -m py_compile .\\nova_backend\\services\\project_brain_freshness_snapshot.py",
        "python -m py_compile .\\nova_backend\\services\\project_brain_context_builder.py",
        "python -m py_compile .\\nova_backend\\services\\project_brain_general_intelligence.py",
    ]

    smoke_command_map = {
        "project-state memory API smoke": "python .\\tools\\nova_project_state_memory_api_smoke.py",
        "general intelligence smoke": "python .\\tools\\nova_general_intelligence_smoke.py",
        "project-brain route contract smoke": "python .\\tools\\nova_project_brain_route_contract_smoke.py",
        "project-brain classifier broadening smoke": "python .\\tools\\nova_project_brain_classifier_broadening_smoke.py",
        "project-brain context builder smoke": "python .\\tools\\nova_project_brain_context_builder_smoke.py",
        "answer-quality smoke": "python .\\tools\\nova_answer_quality_smoke.py",
        "guard-stack audit smoke": "python .\\tools\\nova_phase_4i_guard_stack_audit_smoke.py",
    }

    for smoke_name in available_smokes:
        command = smoke_command_map.get(smoke_name)
        if command:
            commands.append(command)

    commands.append("git status --short")

    return commands


def build_project_brain_freshness_snapshot() -> ProjectBrainFreshnessSnapshot:
    available_smokes = _available_smoke_files()

    from nova_backend.services.project_brain_state_bridge import (
        build_state_bridge_record,
    )

    state_bridge = build_state_bridge_record()

    checkpoint = state_bridge.current_checkpoint

    blocker = (
        "No active Project Brain intelligence blocker is open. "
        "No active Decision Engine blocker is open, no active Mission Control blocker is open, "
        "no active Failure Interpreter blocker is open, and no active Decision Log blocker is open. "
        "The remaining work is pre-launch stabilization: validate user flows, desktop/mobile reliability, onboarding, and launch readiness."
    )

    next_move = (
        "Complete the Nova pre-launch quality pass while preserving the locked Decision Engine v1 and "
        "Mission Control v1.2 / Failure Interpreter API behavior, preserve direct recall, "
        "broad Project Brain routing, and explicit operator prompts."
    )

    return ProjectBrainFreshnessSnapshot(
        version=SNAPSHOT_VERSION,
        checkpoint=checkpoint,
        blocker=blocker,
        next_move=next_move,
        completed=[],
        validation=[],
        available_smoke_files=available_smokes,
        missing_smoke_files=_missing_smoke_files(),
        recent_commits=_recent_commits(),
    )

    _NOVA_PRE_SANITIZED_BUILD_PROJECT_BRAIN_FRESHNESS_SNAPSHOT_20260702 = (
        build_project_brain_freshness_snapshot
    )

    _NOVA_CLEAN_CHECKPOINT_20260702 = (
        "Protected systems: Decision Engine v1, Project Brain routing, "
        "Mission Control, Failure Interpreter API, and Decision Log API route remain locked: "
        "exact project-state recall stays on direct recall, broad Nova project paraphrases route through "
        "Project Brain general intelligence, explicit operator prompts route to Mission Control, answer "
        "quality is 100%, and regression now protects the route contracts."
    )

_NOVA_CLEAN_BLOCKER_20260702 = (
    "No active Project Brain intelligence blocker is open. "
    "No active Decision Engine blocker is open, no active Mission Control blocker is open, "
    "no active Failure Interpreter blocker is open, and no active Decision Log blocker is open. "
    "The remaining work is pre-launch stabilization: validate user flows, desktop/mobile reliability, onboarding, and launch readiness."
)

_NOVA_CLEAN_NEXT_MOVE_20260702 = (
    "Complete the Nova pre-launch quality pass while preserving the locked Decision Engine v1 "
    "and Mission Control v1.2 / Failure Interpreter API behavior."
)


