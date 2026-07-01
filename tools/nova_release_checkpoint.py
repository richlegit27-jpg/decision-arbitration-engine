from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]
NOTE_DIR = ROOT / "docs" / "nova_release_checkpoints"


@dataclass
class CheckResult:
    name: str
    command: List[str]
    returncode: int


def run_command(command: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        shell=False,
    )


def git_text(*args: str) -> str:
    proc = run_command(["git", *args])
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def git_status_short() -> str:
    return git_text("status", "--short")


def run_check(name: str, command: List[str]) -> CheckResult:
    print(f"\n=== {name} ===")
    proc = run_command(command)

    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")

    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")

    if proc.returncode == 0:
        print(f"PASS {name}")
    else:
        print(f"FAILED {name}")

    return CheckResult(
        name=name,
        command=command,
        returncode=proc.returncode,
    )


def write_release_note(
    *,
    results: List[CheckResult],
    next_move: str,
    current_focus: str,
    clean_before: bool,
    dirty_before: str,
) -> Path:
    NOTE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    branch = git_text("branch", "--show-current") or "unknown"
    head = git_text("rev-parse", "--short", "HEAD") or "unknown"
    subject = git_text("log", "-1", "--pretty=%s") or "unknown"
    full_head = git_text("rev-parse", "HEAD") or "unknown"

    filename = f"nova_release_checkpoint_{stamp}_{head}.md"
    path = NOTE_DIR / filename

    passed = all(result.returncode == 0 for result in results)

    lines: List[str] = [
        "# Nova Release Checkpoint",
        "",
        f"- Created UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Branch: `{branch}`",
        f"- Head: `{head}`",
        f"- Full head: `{full_head}`",
        f"- Subject: `{subject}`",
        f"- Clean before note write: `{str(clean_before).lower()}`",
        f"- Release checks passed: `{str(passed).lower()}`",
        f"- Runtime behavior changed by this checkpoint: `no`",
        f"- Current focus: {current_focus}",
        f"- Next move: {next_move}",
        "",
        "## Checks",
        "",
    ]

    for result in results:
        status = "PASS" if result.returncode == 0 else "FAIL"
        command = " ".join(result.command)
        lines.extend(
            [
                f"### {result.name}",
                "",
                f"- Status: `{status}`",
                f"- Command: `{command}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Git status before release note",
            "",
            "```txt",
            dirty_before if dirty_before.strip() else "clean",
            "```",
            "",
            "## Suggested backup tag",
            "",
            "```powershell",
            f'git tag -a nova-release-{stamp}-{head} -m "Nova release checkpoint {stamp} {head}"',
            "```",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Nova release checkpoint checks and write a release note.")
    parser.add_argument(
        "--next-move",
        default="Move to final Nova memory cleanup and release checkpoint.",
    )
    parser.add_argument(
        "--current-focus",
        default="Nova release checkpoint validation.",
    )
    args = parser.parse_args()

    dirty_before = git_status_short()
    clean_before = not dirty_before.strip()

    checks: List[tuple[str, List[str]]] = [
        (
            "nova_regression_smoke",
            [sys.executable, str(ROOT / "tools" / "nova_regression_smoke.py")],
        ),
        (
            "nova_memory_quality_smoke",
            [sys.executable, str(ROOT / "tools" / "nova_memory_quality_smoke.py")],
        ),
        (
            "nova_checkpoint_dry_run",
            [
                sys.executable,
                str(ROOT / "tools" / "nova_checkpoint.py"),
                "--next-move",
                args.next_move,
                "--current-focus",
                args.current_focus,
                "--completed",
                "Release checkpoint smoke passed",
                "--locked",
                "Release checkpoint",
                "--dry-run",
            ],
        ),
    ]

    results = [run_check(name, command) for name, command in checks]
    failed = [result.name for result in results if result.returncode != 0]

    note_path = write_release_note(
        results=results,
        next_move=args.next_move,
        current_focus=args.current_focus,
        clean_before=clean_before,
        dirty_before=dirty_before,
    )

    print(f"\nRelease note written: {note_path}")

    if failed:
        print("\nNOVA RELEASE CHECKPOINT FAILED")
        for name in failed:
            print(f"- {name}")
        return 1

    print("\nNOVA RELEASE CHECKPOINT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
