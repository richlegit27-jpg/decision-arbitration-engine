from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CANDIDATE_DIRS = [
    "static/js_BACKUP_STABLE_20260310_2005",
    "static/js_BAK_WORKING_20260310",
    "static/js_backup_20260310_2004",
]


REFERENCE_SCAN_SUFFIXES = {
    ".py",
    ".html",
    ".js",
    ".css",
}


IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "nova_backups",
    "uploads",
    "data",
}


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _iter_scan_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in REFERENCE_SCAN_SUFFIXES:
            continue

        if set(path.relative_to(ROOT).parts) & IGNORED_DIRS:
            continue

        yield path


def main():
    existing_candidates = [
        item for item in CANDIDATE_DIRS
        if (ROOT / item).exists()
    ]

    assert_true(
        "static backup cleanup candidates found or already removed",
        True,
        f"existing={existing_candidates}",
    )

    blockers = []

    this_file = Path(__file__).resolve()

    for candidate in existing_candidates:
        candidate_path = (ROOT / candidate).resolve()
        tokens = [
            candidate,
            candidate.replace("/", "\\"),
            Path(candidate).name,
        ]

        for scan_file in _iter_scan_files():
            resolved = scan_file.resolve()

            if resolved == this_file:
                continue

            if candidate_path in resolved.parents:
                continue

            text = _read(scan_file)
            hits = [token for token in tokens if token in text]

            if hits:
                blockers.append(
                    {
                        "candidate": candidate,
                        "referenced_by": str(scan_file.relative_to(ROOT)),
                        "hits": hits,
                    }
                )

    assert_true(
        "static backup candidates unreferenced outside themselves",
        not blockers,
        f"blockers={blockers}",
    )

    print("Existing Phase 3I static backup cleanup candidates:")
    for item in existing_candidates:
        print(f"- {item}")

    print("NOVA PHASE 3I STATIC BACKUP REVIEW SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
