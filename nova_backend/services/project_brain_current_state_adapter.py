from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


STALE_MARKERS = [
    "new blocker is general intelligence routing",
    "make `what's next?` return project context",
    "make what's next? return project context",
    "answer-policy intelligence is 100%",
    "real general intelligence still needs improvement",
    "moving direct policy behavior into cleaner prompt",
    "no active project brain intelligence blocker is open",
]


@dataclass(frozen=True)
class ProjectBrainCurrentState:
    source: str
    checkpoint: str
    blocker: str
    next_move: str
    used_memory: bool
    ignored_stale_values: List[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_memory_path() -> Path:
    return _repo_root() / "data" / "nova_memory.json"


def _safe_load_json(path: Path) -> Any:
    try:
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    except Exception:
        return None


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        text = value.strip()
        if text:
            yield text
        return

    if isinstance(value, dict):
        for key, nested_value in value.items():
            if isinstance(key, str) and isinstance(nested_value, (str, int, float)):
                combined = f"{key}: {nested_value}".strip()
                if combined:
                    yield combined

            yield from _flatten_strings(nested_value)

        return

    if isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)


def _is_stale(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in STALE_MARKERS)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:700]


def _label_value(text: str, labels: List[str]) -> Optional[str]:
    normalized = _clean_text(text)

    for label in labels:
        pattern = rf"{re.escape(label)}\s*:\s*(.+?)(?=(?: Current checkpoint:| Current blocker:| Next move:| Current task:|$))"
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            value = _clean_text(match.group(1))
            if value:
                return value

    return None


def _collect_candidates(memory: Any) -> Dict[str, List[str]]:
    candidates: Dict[str, List[str]] = {
        "checkpoint": [],
        "blocker": [],
        "next_move": [],
    }

    for text in _flatten_strings(memory):
        cleaned = _clean_text(text)
        lower = cleaned.lower()

        checkpoint = _label_value(cleaned, ["current checkpoint", "checkpoint"])
        if checkpoint:
            candidates["checkpoint"].append(checkpoint)

        blocker = _label_value(cleaned, ["current blocker", "blocker"])
        if blocker:
            candidates["blocker"].append(blocker)

        next_move = _label_value(cleaned, ["next concrete move", "next move", "safe move"])
        if next_move:
            candidates["next_move"].append(next_move)

        if "checkpoint" in lower and ":" in cleaned:
            candidates["checkpoint"].append(cleaned)

        if "blocker" in lower and ":" in cleaned:
            candidates["blocker"].append(cleaned)

        if ("next move" in lower or "safe move" in lower) and ":" in cleaned:
            candidates["next_move"].append(cleaned)

    return candidates


def _choose_candidate(values: List[str], ignored_stale_values: List[str]) -> Optional[str]:
    seen = set()

    for value in values:
        cleaned = _clean_text(value)
        key = cleaned.lower()

        if not cleaned or key in seen:
            continue

        seen.add(key)

        if _is_stale(cleaned):
            ignored_stale_values.append(cleaned)
            continue

        return cleaned

    return None


def build_project_brain_current_state(
    *,
    default_checkpoint: str,
    default_blocker: str,
    default_next_move: str,
    memory_path: Optional[Path] = None,
) -> ProjectBrainCurrentState:
    path = memory_path or _default_memory_path()
    memory = _safe_load_json(path)
    ignored_stale_values: List[str] = []

    if memory is None:
        return ProjectBrainCurrentState(
            source="snapshot_defaults",
            checkpoint=default_checkpoint,
            blocker=default_blocker,
            next_move=default_next_move,
            used_memory=False,
            ignored_stale_values=[],
        )

    candidates = _collect_candidates(memory)

    checkpoint = default_checkpoint
    blocker = _choose_candidate(candidates["blocker"], ignored_stale_values) or default_blocker
    next_move = _choose_candidate(candidates["next_move"], ignored_stale_values) or default_next_move

    used_memory = (
        checkpoint != default_checkpoint
        or blocker != default_blocker
        or next_move != default_next_move
    )

    return ProjectBrainCurrentState(
        source=str(path),
        checkpoint=checkpoint,
        blocker=blocker,
        next_move=next_move,
        used_memory=used_memory,
        ignored_stale_values=ignored_stale_values,
    )
