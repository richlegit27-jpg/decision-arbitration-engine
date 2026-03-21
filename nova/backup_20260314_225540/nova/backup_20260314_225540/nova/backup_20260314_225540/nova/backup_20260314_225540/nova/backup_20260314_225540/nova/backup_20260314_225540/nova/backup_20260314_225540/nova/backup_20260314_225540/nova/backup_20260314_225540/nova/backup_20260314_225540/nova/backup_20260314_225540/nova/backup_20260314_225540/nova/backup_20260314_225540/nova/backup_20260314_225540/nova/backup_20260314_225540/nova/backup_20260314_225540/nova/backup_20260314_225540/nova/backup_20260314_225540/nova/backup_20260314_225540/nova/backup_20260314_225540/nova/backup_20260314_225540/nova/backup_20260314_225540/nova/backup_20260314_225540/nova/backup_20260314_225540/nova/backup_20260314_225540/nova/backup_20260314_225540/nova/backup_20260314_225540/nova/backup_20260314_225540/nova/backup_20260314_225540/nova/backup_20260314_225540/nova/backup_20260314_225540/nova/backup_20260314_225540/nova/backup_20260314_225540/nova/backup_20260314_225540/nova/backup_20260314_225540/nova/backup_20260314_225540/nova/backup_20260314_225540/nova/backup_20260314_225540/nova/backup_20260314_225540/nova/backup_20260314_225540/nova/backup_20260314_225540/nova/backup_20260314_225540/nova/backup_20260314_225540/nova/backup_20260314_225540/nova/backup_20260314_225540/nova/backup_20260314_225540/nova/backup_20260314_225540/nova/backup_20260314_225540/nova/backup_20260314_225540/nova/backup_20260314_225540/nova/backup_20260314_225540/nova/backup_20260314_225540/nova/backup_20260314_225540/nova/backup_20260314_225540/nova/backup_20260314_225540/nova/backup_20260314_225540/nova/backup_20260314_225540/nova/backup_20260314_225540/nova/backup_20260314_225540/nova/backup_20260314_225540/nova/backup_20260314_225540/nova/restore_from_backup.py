from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = PROJECT_ROOT / "runtime" / "backups"


def copy_back(src: Path, dst: Path) -> None:
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            copy_back(child, dst / child.name)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: py C:\\Users\\Owner\\nova\\restore_from_backup.py <restore_point_folder_name>")
        return 1

    restore_name = sys.argv[1].strip()
    restore_dir = BACKUP_ROOT / restore_name

    if not restore_dir.exists():
        print(f"Restore point not found: {restore_dir}")
        return 1

    for child in restore_dir.iterdir():
        if child.name == "manifest.txt":
            continue

        target = PROJECT_ROOT / child.relative_to(restore_dir)
        copy_back(child, target)

    print(f"RESTORED FROM: {restore_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())