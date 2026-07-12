from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CompletedMoveSignal:
    move_name: str
    completed: bool
    evidence: str
    replacement_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _repo_path(relative_path: str) -> Path:
    return ROOT / relative_path


def _file_contains(relative_path: str, needle: str) -> bool:
    path = _repo_path(relative_path)
    if not path.exists():
        return False

    try:
        return needle in path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return False


def _file_exists(relative_path: str) -> bool:
    return _repo_path(relative_path).exists()


def detect_completed_move(move_name: str) -> CompletedMoveSignal:
    name = normalize_text(move_name)

    if "operator plan quality" in name or "operator planner quality" in name:
        completed = (
            _file_contains("nova_backend/services/project_brain_operator_planner.py", "ranked_moves")
            and _file_contains("nova_backend/services/project_brain_operator_planner.py", "exact_next_command")
            and _file_contains("nova_backend/services/project_brain_operator_planner.py", "rejected_moves")
        )
        return CompletedMoveSignal(
            move_name=move_name,
            completed=completed,
            evidence="operator planner has ranked_moves, rejected_moves, and exact_next_command",
            replacement_hint="Choose a downstream behavior upgrade, not Operator Plan Quality v2 again.",
        )

    if "smoke selector" in name:
        completed = _file_exists("nova_backend/services/project_brain_smoke_selector.py")
        return CompletedMoveSignal(
            move_name=move_name,
            completed=completed,
            evidence="project_brain_smoke_selector.py exists",
            replacement_hint="Use Smoke Selector; do not recommend building Smoke Selector v1 again.",
        )

    if "command center" in name:
        completed = (
            _file_exists("nova_backend/services/project_brain_command_center.py")
            and _file_contains("nova_backend/services/project_brain_command_center.py", "Command Center v2 Intent Console")
        )
        return CompletedMoveSignal(
            move_name=move_name,
            completed=completed,
            evidence="Command Center service exists and has v2 Intent Console",
            replacement_hint="Improve Command Center behavior instead of rebuilding it.",
        )

    if "mission control" in name and ("console" in name or "format" in name):
        completed = _file_contains(
            "nova_backend/services/project_brain_mission_control.py",
            "Mission Control v1.4 Operator Console",
        )
        return CompletedMoveSignal(
            move_name=move_name,
            completed=completed,
            evidence="Mission Control v1.4 Operator Console marker exists",
            replacement_hint="Do not reformat Mission Control unless the API output regressed.",
        )

    if "decision engine" in name and "smoke selector" in name:
        completed = _file_contains(
            "nova_backend/services/project_brain_decision_engine.py",
            "_build_decision_smoke_selection",
        )
        return CompletedMoveSignal(
            move_name=move_name,
            completed=completed,
            evidence="Decision Engine has direct Smoke Selector wiring",
            replacement_hint="Use the direct Smoke Selector path instead of rebuilding it.",
        )

    return CompletedMoveSignal(
        move_name=move_name,
        completed=False,
        evidence="no completed-move signal matched",
        replacement_hint="Move is not known complete.",
    )


def filter_completed_moves(
    move_names: list[str],
    fallback_move: str = "Cleanup Strategy Engine v1",
) -> dict[str, Any]:
    checked = [detect_completed_move(name) for name in move_names]
    active = [signal.move_name for signal in checked if not signal.completed]
    completed = [signal for signal in checked if signal.completed]

    if not active and fallback_move:
        active = [fallback_move]

    return {
        "active_moves": active,
        "completed_moves": [signal.to_dict() for signal in completed],
        "checked_moves": [signal.to_dict() for signal in checked],
        "fallback_move": fallback_move,
        "reason": "Completed moves are removed from recommendation ranking so Nova does not suggest already-locked upgrades.",
    }


def completed_move_names(move_names: list[str]) -> list[str]:
    return [
        signal.move_name
        for signal in (detect_completed_move(name) for name in move_names)
        if signal.completed
    ]


def is_move_completed(move_name: str) -> bool:
    return detect_completed_move(move_name).completed


__all__ = [
    "CompletedMoveSignal",
    "completed_move_names",
    "detect_completed_move",
    "filter_completed_moves",
    "is_move_completed",
]



# NOVA_PROJECT_BRAIN_OPERATOR_MEMORY_COMPLETION_BRIDGE_20260711
# Lets completed-move filtering consume durable Operator Memory smoke evidence.
# Service-only. No Flask wiring and no app.py guard.
_NOVA_PRE_OPERATOR_MEMORY_COMPLETION_DETECT_20260711 = detect_completed_move


def _nova_operator_memory_completion_blob_20260711():
    try:
        from nova_backend.services.project_brain_operator_memory_writer import (
            load_operator_memory,
        )

        memory = load_operator_memory()
    except Exception:
        return ""

    if not isinstance(
        memory,
        dict,
    ):
        return ""

    milestones = list(
        memory.get(
            "milestones",
            [],
        )
        or []
    )

    latest = memory.get(
        "latest"
    )

    if isinstance(
        latest,
        dict,
    ):
        milestones.append(
            latest
        )

    return repr(
        milestones
    ).lower()


def detect_completed_move(move_name: str) -> CompletedMoveSignal:
    base_signal = (
        _NOVA_PRE_OPERATOR_MEMORY_COMPLETION_DETECT_20260711(
            move_name
        )
    )

    if base_signal.completed:
        return base_signal

    clean_name = str(
        move_name
        or ""
    ).strip()

    normalized_name = clean_name.lower()

    if normalized_name == (
        "nova conversation quality field test v1"
    ):
        memory_blob = (
            _nova_operator_memory_completion_blob_20260711()
        )

        completion_signals = (
            "nova conversation quality field test smoke passed",
            "nova_conversation_quality_field_test_smoke.py",
        )

        if any(
            signal in memory_blob
            for signal in completion_signals
        ):
            return CompletedMoveSignal(
                move_name=clean_name,
                completed=True,
                evidence=(
                    "Operator Memory records the Nova Conversation "
                    "Quality Field Test smoke as passed"
                ),
                replacement_hint=(
                    "Re-rank unfinished Project Brain moves instead "
                    "of recommending the completed field test again."
                ),
            )

    return base_signal
