from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = PROJECT_ROOT / "runtime" / "backups"
MAX_BACKUPS = 15

INCLUDE_PATHS = [
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "static",
    PROJECT_ROOT / "templates",
    PROJECT_ROOT / "start_nova.py",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "launch_nova.ps1",
]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def copy_item(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def trim_old_backups() -> None:
    if not BACKUP_ROOT.exists():
        return

    restore_dirs = sorted(
        [path for path in BACKUP_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.name,
        reverse=True,
    )

    for old_dir in restore_dirs[MAX_BACKUPS:]:
        shutil.rmtree(old_dir, ignore_errors=True)


def main() -> int:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

    restore_name = f"restore_point_{timestamp()}"
    restore_dir = BACKUP_ROOT / restore_name
    restore_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    for item in INCLUDE_PATHS:
        if not item.exists():
            continue

        target = restore_dir / item.relative_to(PROJECT_ROOT)
        copy_item(item, target)
        copied.append(str(item.relative_to(PROJECT_ROOT)))

    manifest = restore_dir / "manifest.txt"
    manifest.write_text(
        "Nova Restore Point\n"
        f"Created: {datetime.now().isoformat()}\n"
        f"Project: {PROJECT_ROOT}\n\n"
        "Included:\n"
        + "\n".join(f"- {entry}" for entry in copied),
        encoding="utf-8",
    )

    trim_old_backups()

    print(f"RESTORE POINT CREATED: {restore_dir}")
    print(f"MAX BACKUPS KEPT: {MAX_BACKUPS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())