from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class DecisionLogEntry:
    short_hash: str
    subject: str
    category: str
    locked_signal: bool


_LOCK_SIGNALS = (
    "lock",
    "locked",
    "contract",
    "contracts",
    "smoke",
    "regression",
    "mission control",
    "failure interpreter",
    "decision engine",
    "project brain",
    "state sync",
)

_CATEGORY_RULES = (
    ("failure_interpreter", ("failure interpreter",)),
    ("mission_control", ("mission control",)),
    ("decision_engine", ("decision engine",)),
    ("project_brain", ("project brain",)),
    ("regression", ("regression", "smoke")),
    ("state_sync", ("state sync", "sync")),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_git_log(limit: int) -> list[str]:
    root = _repo_root()
    cmd = [
        "git",
        "log",
        f"-n{max(1, int(limit))}",
        "--pretty=format:%h%x09%s",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=6,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _category_for(subject: str) -> str:
    lowered = subject.lower()
    for category, needles in _CATEGORY_RULES:
        if any(needle in lowered for needle in needles):
            return category
    return "commit"


def _locked_signal(subject: str) -> bool:
    lowered = subject.lower()
    return any(signal in lowered for signal in _LOCK_SIGNALS)


def get_recent_decisions(limit: int = 8) -> list[dict]:
    entries: list[DecisionLogEntry] = []

    for line in _run_git_log(limit):
        if "\t" not in line:
            continue

        short_hash, subject = line.split("\t", 1)
        subject = subject.strip()

        if not short_hash or not subject:
            continue

        entries.append(
            DecisionLogEntry(
                short_hash=short_hash.strip(),
                subject=subject,
                category=_category_for(subject),
                locked_signal=_locked_signal(subject),
            )
        )

    return [asdict(entry) for entry in entries]


def format_decision_timeline(limit: int = 6) -> str:
    decisions = get_recent_decisions(limit=limit)

    if not decisions:
        return (
            "Recent Decision Log:\n"
            "- No recent Git decision entries were available. "
            "Use direct project-state recall for current state."
        )

    lines = ["Recent Decision Log:"]
    for decision in decisions:
        lock_note = " locked-signal" if decision["locked_signal"] else ""
        lines.append(
            f"- {decision['short_hash']} {decision['subject']} "
            f"[{decision['category']}{lock_note}]"
        )

    return "\n".join(lines)


def answer_recent_changes(limit: int = 6) -> str:
    timeline = format_decision_timeline(limit=limit)

    return (
        "What changed recently:\n"
        f"{timeline}\n\n"
        "Use this as the operator timeline only. "
        "Direct project-state recall remains the source of truth for the current blocker/current work."
    )


__all__ = [
    "DecisionLogEntry",
    "get_recent_decisions",
    "format_decision_timeline",
    "answer_recent_changes",
]
