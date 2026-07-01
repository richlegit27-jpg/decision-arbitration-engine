from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


INACTIVE_EXECUTION_STATUSES = {
    "",
    "idle",
    "done",
    "complete",
    "completed",
    "stopped",
    "cancelled",
    "canceled",
    "failed",
    "error",
    "none",
}

ACTIVE_EXECUTION_STATUSES = {
    "active",
    "running",
    "waiting",
    "processing",
    "in_progress",
        "executing",
}


DEFAULT_PROJECT_STATE: Dict[str, Any] = {
    "project": "Nova",
    "checkpoint": "f046754 Add Nova project state recall",
    "current_focus": "Nova brain / memory quality upgrade: memory + project-state recall",
    "last_completed": [
        "Router cleanup locked",
        "Web/live price routing locked",
        "Image text polish locked",
        "Attachment cleanup locked",
        "Execution safety locked",
        "Regression runner committed and working tree clean",
    ],
    "locked": [
        "Router cleanup",
        "Web/live price",
        "Image text polish",
        "Attachment cleanup",
        "Execution safety",
        "Regression runner",
    ],
    "remaining": [
        "Repair project-state recall service export",
        "Smoke test project-state answers",
        "Amend the project-state recall commit",
        "Move to memory quality upgrade phase two",
    ],
    "next_move": "Repair project-state service export, then run both smoke tests.",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    return _repo_root() / "data"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}

        raw = path.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return {}

        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        items: List[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                items.append(text)
        return items

    text = str(value).strip()
    return [text] if text else []


def _state_value(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)

    return getattr(state, key, default)


def _read_execution_state() -> Dict[str, Any]:
    candidates = [
        _data_dir() / "nova_execution_state.json",
        _data_dir() / "execution_state.json",
    ]

    for path in candidates:
        data = _load_json(path)
        if data:
            return data

    return {}


def _is_active_execution_state(state: Any) -> bool:
    if not state:
        return False

    status = str(_state_value(state, "status", "") or "").strip().lower()
    complete = bool(_state_value(state, "complete", False)) or bool(_state_value(state, "completed", False))

    if complete:
        return False

    if status in INACTIVE_EXECUTION_STATUSES:
        return False

    if status in ACTIVE_EXECUTION_STATUSES:
        return True

    waiting = bool(_state_value(state, "waiting", False))
    processing = bool(_state_value(state, "processing", False))

    if waiting or processing:
        return True

    return False


def _has_active_execution(runtime_execution_state: Optional[Any] = None) -> bool:
    if _is_active_execution_state(runtime_execution_state):
        return True

    return _is_active_execution_state(_read_execution_state())


def _run_git(args: List[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )

        if proc.returncode != 0:
            return ""

        return (proc.stdout or "").strip()
    except Exception:
        return ""


def _git_snapshot() -> Dict[str, Any]:
    branch = _run_git(["branch", "--show-current"])
    head = _run_git(["rev-parse", "--short", "HEAD"])
    subject = _run_git(["log", "-1", "--pretty=%s"])
    status_raw = _run_git(["status", "--short"])

    dirty_files = [line.strip() for line in status_raw.splitlines() if line.strip()]

    return {
        "branch": branch,
        "head": head,
        "subject": subject,
        "clean": not dirty_files,
        "dirty_files": dirty_files,
    }


def get_project_state() -> Dict[str, Any]:
    state = dict(DEFAULT_PROJECT_STATE)

    stored = _load_json(_data_dir() / "nova_project_state.json")
    for key, value in stored.items():
        if value not in (None, ""):
            state[key] = value

    state["git"] = _git_snapshot()
    return state


def _normalize_text(text: Any) -> str:
    lowered = str(text or "").strip().lower()
    lowered = lowered.replace("’", "'")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _question_kind(user_text: Any) -> str:
    text = _normalize_text(user_text)

    if not text:
        return ""

    if text in {"k", "ok", "okay", "next", "continue", "go next", "go for next"}:
        return "next"

    current_patterns = [
        "what are we working on",
        "what are we doing",
        "where are we",
        "current checkpoint",
        "current status",
        "project status",
        "what is the checkpoint",
        "what's the checkpoint",
    ]

    fixed_patterns = [
        "what did we just fix",
        "what was just fixed",
        "what did we fix",
        "last fix",
        "what got fixed",
        "what did we commit",
        "latest commit",
    ]

    remaining_patterns = [
        "what is left",
        "what's left",
        "what else is left",
        "what still needs",
        "what remains",
        "remaining work",
        "to do",
        "todo",
    ]

    next_patterns = [
        "what next",
        "what is next",
        "what's next",
        "next move",
        "next step",
        "what should we do next",
        "where do we go next",
    ]

    if any(pattern in text for pattern in current_patterns):
        return "current"

    if any(pattern in text for pattern in fixed_patterns):
        return "fixed"

    if any(pattern in text for pattern in remaining_patterns):
        return "remaining"

    if any(pattern in text for pattern in next_patterns):
        return "next"

    return ""


def _repo_line(git: Dict[str, Any]) -> str:
    branch = git.get("branch") or "unknown-branch"
    head = git.get("head") or "unknown-head"
    clean = "clean" if git.get("clean") else "dirty"
    subject = git.get("subject") or ""

    if subject:
        return f"{branch} @ {head} ({clean}) - {subject}"

    return f"{branch} @ {head} ({clean})"


def _format_locked(items: List[str]) -> str:
    if not items:
        return "none listed"

    return ", ".join(items[:8])


def _format_current(state: Dict[str, Any]) -> str:
    git = state.get("git") or {}
    locked = _as_list(state.get("locked"))
    last_completed = _as_list(state.get("last_completed"))
    remaining = _as_list(state.get("remaining"))

    lines = [
        "Current Nova checkpoint:",
        f"- Working on: {state.get('current_focus') or 'unknown'}",
        f"- Checkpoint: {state.get('checkpoint') or 'unknown'}",
        f"- Repo: {_repo_line(git)}",
        f"- Locked: {_format_locked(locked)}",
    ]

    if last_completed:
        lines.append(f"- Just fixed: {last_completed[-1]}")

    if remaining:
        lines.append(f"- Left: {remaining[0]}")

    next_move = str(state.get("next_move") or "").strip()
    if next_move:
        lines.append(f"- Next: {next_move}")

    dirty_files = _as_list(git.get("dirty_files"))
    if dirty_files:
        lines.append(f"- Dirty files: {', '.join(dirty_files[:6])}")

    return "\n".join(lines)


def _format_fixed(state: Dict[str, Any]) -> str:
    git = state.get("git") or {}
    last_completed = _as_list(state.get("last_completed"))

    lines = ["Just fixed / locked:"]

    if last_completed:
        for item in last_completed[:10]:
            lines.append(f"- {item}")
    else:
        lines.append("- No completed project-state items are listed yet.")

    lines.append(f"- Latest repo commit: {_repo_line(git)}")
    return "\n".join(lines)


def _format_remaining(state: Dict[str, Any]) -> str:
    remaining = _as_list(state.get("remaining"))
    next_move = str(state.get("next_move") or "").strip()

    lines = ["What is left:"]

    if remaining:
        for item in remaining[:10]:
            lines.append(f"- {item}")
    else:
        lines.append("- No remaining project-state items are listed.")

    if next_move:
        lines.append(f"\nNext move: {next_move}")

    return "\n".join(lines)


def _format_next(state: Dict[str, Any]) -> str:
    next_move = str(state.get("next_move") or "").strip()
    current_focus = str(state.get("current_focus") or "").strip()
    remaining = _as_list(state.get("remaining"))

    lines = ["Next move:"]

    if next_move:
        lines.append(f"- {next_move}")
    elif remaining:
        lines.append(f"- {remaining[0]}")
    else:
        lines.append("- No next project-state item is listed.")

    if current_focus:
        lines.append(f"- Current focus: {current_focus}")

    if remaining:
        lines.append(f"- First remaining item: {remaining[0]}")

    return "\n".join(lines)


def answer_project_state_question(
    user_text: Any,
    runtime_execution_state: Optional[Any] = None,
) -> Optional[str]:
    kind = _question_kind(user_text)

    if not kind:
        return None

    if kind == "next" and _has_active_execution(runtime_execution_state):
        return None

    state = get_project_state()

    if kind == "current":
        return _format_current(state)

    if kind == "fixed":
        return _format_fixed(state)

    if kind == "remaining":
        return _format_remaining(state)

    if kind == "next":
        return _format_next(state)

    return None


# NOVA_PROJECT_STATE_ACTIVE_EXECUTION_GUARD_FINAL_20260630
# Tightens "next/k" protection so stale runtime execution state does not block project-state recall.
# A mission only counts as active when it has both a live status and a real goal/step marker.
def _nova_project_state_has_execution_marker_final_20260630(state: Any) -> bool:
    if not state:
        return False

    goal = (
        _state_value(state, "goal", None)
        or _state_value(state, "original_user_text", None)
        or _state_value(state, "active_task", None)
    )

    current_step = (
        _state_value(state, "current_step", None)
        or _state_value(state, "current_step_title", None)
        or _state_value(state, "current_title", None)
    )

    current_index = _state_value(state, "current_index", None)

    has_goal = bool(str(goal or "").strip())
    has_step_text = bool(str(current_step or "").strip())
    has_index = current_index not in (None, "", -1, "none", "None")

    return has_goal and (has_step_text or has_index)


def _is_active_execution_state(state: Any) -> bool:
    if not state:
        return False

    status = str(_state_value(state, "status", "") or "").strip().lower()
    complete = bool(_state_value(state, "complete", False)) or bool(_state_value(state, "completed", False))

    if complete:
        return False

    if status in INACTIVE_EXECUTION_STATUSES:
        return False

    if status in ACTIVE_EXECUTION_STATUSES:
        return _nova_project_state_has_execution_marker_final_20260630(state)

    waiting = bool(_state_value(state, "waiting", False))
    processing = bool(_state_value(state, "processing", False))

    if waiting or processing:
        return _nova_project_state_has_execution_marker_final_20260630(state)

    return False


def _has_active_execution(runtime_execution_state: Optional[Any] = None) -> bool:
    if _is_active_execution_state(runtime_execution_state):
        return True

    return _is_active_execution_state(_read_execution_state())


# NOVA_PROJECT_STATE_COMPACT_CONTEXT_20260701
# Compact formatter for safe project-state injection.
# This does not change routing. It only exposes a short, bounded context line.
def compact_project_state_context(max_locked: int = 6) -> str:
    state = get_project_state()

    checkpoint = str(state.get("checkpoint") or "").strip()
    current_focus = str(state.get("current_focus") or "").strip()
    next_move = str(state.get("next_move") or "").strip()
    locked = _as_list(state.get("locked"))[:max_locked]

    parts = []

    if checkpoint:
        parts.append(f"Nova checkpoint: {checkpoint}")

    if current_focus:
        parts.append(f"Focus: {current_focus}")

    if next_move:
        parts.append(f"Next: {next_move}")

    if locked:
        parts.append(f"Locked: {', '.join(locked)}")

    text = ". ".join(parts).strip()

    if text and not text.endswith("."):
        text += "."

    return text


def compact_project_state_context_block(max_locked: int = 6) -> str:
    text = compact_project_state_context(max_locked=max_locked)

    if not text:
        return ""

    return (
        "Current Nova project state:\n"
        f"{text}\n"
        "Use this only when the user asks about Nova/project status, progress, next steps, or current work."
    )

try:
    print("[NOVA_PROJECT_STATE_COMPACT_CONTEXT_20260701] installed")
except Exception:
    pass

