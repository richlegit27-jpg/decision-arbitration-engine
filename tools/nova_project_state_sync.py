from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "nova_project_state.json"

PLACEHOLDER_VALUES = {
    "",
    "next task here",
    "todo",
    "tbd",
    "fix later",
    "placeholder",
    "replace me",
    "next",
}


def run_git(args: List[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if proc.returncode != 0:
            return ""

        return (proc.stdout or "").strip()
    except Exception:
        return ""


def git_snapshot() -> Dict[str, Any]:
    status_raw = run_git(["status", "--short"])
    dirty_files = [line.strip() for line in status_raw.splitlines() if line.strip()]

    return {
        "branch": run_git(["branch", "--show-current"]),
        "head": run_git(["rev-parse", "--short", "HEAD"]),
        "subject": run_git(["log", "-1", "--pretty=%s"]),
        "clean": not dirty_files,
        "dirty_files": dirty_files,
    }


def load_state() -> Dict[str, Any]:
    try:
        if not STATE_PATH.exists():
            return {}

        raw = STATE_PATH.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return {}

        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def as_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    return [text] if text else []


def merge_unique(existing: List[str], new_items: List[str]) -> List[str]:
    seen = set()
    merged: List[str] = []

    for item in [*existing, *new_items]:
        text = str(item).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            merged.append(text)

    return merged


def is_placeholder(value: str) -> bool:
    normalized = " ".join(str(value or "").strip().lower().split())
    return normalized in PLACEHOLDER_VALUES


def validate_args(args: argparse.Namespace) -> None:
    if args.next_move and is_placeholder(args.next_move):
        raise ValueError(
            f"Refusing placeholder --next-move value: {args.next_move!r}. "
            "Use a real next move or omit --next-move."
        )

    if args.current_focus and is_placeholder(args.current_focus):
        raise ValueError(
            f"Refusing placeholder --current-focus value: {args.current_focus!r}. "
            "Use a real current focus or omit --current-focus."
        )

    for item in args.remaining:
        if is_placeholder(item):
            raise ValueError(
                f"Refusing placeholder --remaining value: {item!r}. "
                "Use a real remaining item."
            )

    for item in args.completed:
        if is_placeholder(item):
            raise ValueError(
                f"Refusing placeholder --completed value: {item!r}. "
                "Use a real completed item."
            )


def build_state(args: argparse.Namespace) -> Dict[str, Any]:
    state = load_state()
    git = git_snapshot()

    head = git.get("head") or "unknown"
    subject = git.get("subject") or "unknown commit"

    state["project"] = state.get("project") or "Nova"
    state["checkpoint"] = f"{head} {subject}"

    if args.current_focus.strip():
        state["current_focus"] = args.current_focus.strip()

    if args.next_move.strip():
        state["next_move"] = args.next_move.strip()

    existing_locked = as_list(state.get("locked"))
    state["locked"] = merge_unique(existing_locked, args.locked)

    completed = list(args.completed)

    if args.regression_pass:
        completed.append("Regression smoke passed")

    if args.project_state_pass:
        completed.append("Project-state smoke passed")

    existing_completed = as_list(state.get("last_completed"))
    state["last_completed"] = merge_unique(existing_completed, completed)

    if args.replace_remaining:
        state["remaining"] = as_list(args.remaining)
    elif args.remaining:
        state["remaining"] = merge_unique(as_list(state.get("remaining")), args.remaining)

    state["git"] = git
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

    return state


def render_state(state: Dict[str, Any]) -> str:
    return json.dumps(state, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Nova project-state JSON from git/checkpoint info.")
    parser.add_argument("--current-focus", default="")
    parser.add_argument("--next-move", default="")
    parser.add_argument("--locked", action="append", default=[])
    parser.add_argument("--completed", action="append", default=[])
    parser.add_argument("--remaining", action="append", default=[])
    parser.add_argument("--replace-remaining", action="store_true")
    parser.add_argument("--regression-pass", action="store_true")
    parser.add_argument("--project-state-pass", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    validate_args(args)

    state = build_state(args)
    rendered = render_state(state)

    if args.dry_run:
        print("Project state dry run:")
        print(rendered)
        return 0

    old_raw = ""
    if STATE_PATH.exists():
        old_raw = STATE_PATH.read_text(encoding="utf-8-sig")

    if old_raw == rendered:
        print("Project state unchanged.")
        print(f"- checkpoint: {state['checkpoint']}")
        print(f"- clean: {state.get('git', {}).get('clean')}")
        print(f"- file: {STATE_PATH}")
        return 0

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(rendered, encoding="utf-8")

    print("Project state synced:")
    print(f"- checkpoint: {state['checkpoint']}")
    print(f"- clean: {state.get('git', {}).get('clean')}")
    print(f"- file: {STATE_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAILED: {exc}")
        raise SystemExit(1)
