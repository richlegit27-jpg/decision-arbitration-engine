from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

BAD_PARTS = [
    "static/js_backup_",
]

BAD_MARKERS = [
    ".bak",
    ".BAK",
    "BROKEN",
    "STABLE",
]


def run_git(args):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.splitlines()


def is_bad_path(path):
    normalized = path.replace("\\", "/")

    for part in BAD_PARTS:
        if part in normalized:
            return True

    if normalized.startswith("static/"):
        name = Path(normalized).name
        for marker in BAD_MARKERS:
            if marker in name:
                return True

    return False


def main():
    tracked = run_git(["ls-files"])
    bad_tracked = [p for p in tracked if is_bad_path(p)]

    status = run_git(["status", "--porcelain"])
    untracked = []
    for line in status:
        if line.startswith("?? "):
            untracked.append(line[3:])

    bad_untracked = [p for p in untracked if is_bad_path(p)]

    failures = []

    if bad_tracked:
        failures.append("Tracked backup/relic files found:")
        failures.extend(f"  - {p}" for p in bad_tracked)

    if bad_untracked:
        failures.append("Untracked backup/relic files found:")
        failures.extend(f"  - {p}" for p in bad_untracked)

    if failures:
        print("NOVA PHASE 3J BACKUP GUARD FAILED")
        print("\n".join(failures))
        return 1

    print("NOVA PHASE 3J BACKUP GUARD PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
