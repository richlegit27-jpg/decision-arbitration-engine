from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]


PLACEHOLDER_VALUES = {
    "",
    "next task here",
    "todo",
    "tbd",
    "placeholder",
    "replace me",
    "next",
}


def is_placeholder(value: str) -> bool:
    normalized = " ".join(str(value or "").strip().lower().split())
    return normalized in PLACEHOLDER_VALUES


def run_command(name: str, command: List[str]) -> bool:
    print(f"\n=== {name} ===")
    proc = subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        shell=False,
    )

    if proc.returncode != 0:
        print(f"\nFAILED {name}")
        return False

    print(f"PASS {name}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Nova checkpoint checks and sync project state only after green tests."
    )
    parser.add_argument("--next-move", required=True)
    parser.add_argument("--current-focus", default="")
    parser.add_argument("--remaining", action="append", default=[])
    parser.add_argument("--completed", action="append", default=[])
    parser.add_argument("--locked", action="append", default=[])
    parser.add_argument("--replace-remaining", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if is_placeholder(args.next_move):
        print(f"FAILED: refusing placeholder --next-move value: {args.next_move!r}")
        return 1

    checks = [
        (
            "nova_regression_smoke",
            [sys.executable, str(ROOT / "tools" / "nova_regression_smoke.py")],
        ),
        (
            "nova_project_state_smoke",
            [sys.executable, str(ROOT / "tools" / "nova_project_state_smoke.py")],
        ),
    ]

    for name, command in checks:
        if not run_command(name, command):
            print("\nCheckpoint aborted. Project state was not synced.")
            return 1

    sync_cmd = [
        sys.executable,
        str(ROOT / "tools" / "nova_project_state_sync.py"),
        "--regression-pass",
        "--project-state-pass",
        "--next-move",
        args.next_move,
    ]

    if args.current_focus.strip():
        sync_cmd.extend(["--current-focus", args.current_focus.strip()])

    for item in args.completed:
        sync_cmd.extend(["--completed", item])

    for item in args.locked:
        sync_cmd.extend(["--locked", item])

    for item in args.remaining:
        sync_cmd.extend(["--remaining", item])

    if args.replace_remaining:
        sync_cmd.append("--replace-remaining")

    if args.dry_run:
        sync_cmd.append("--dry-run")

    if not run_command("nova_project_state_sync", sync_cmd):
        print("\nCheckpoint failed during project-state sync.")
        return 1

    print("\nNOVA CHECKPOINT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

