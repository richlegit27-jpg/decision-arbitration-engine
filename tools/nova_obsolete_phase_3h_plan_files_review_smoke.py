from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CANDIDATE_FILES = [
    "nova_backend/services/autonomy_fallback_guard_cleanup_plan.py",
    "nova_backend/services/autonomy_plan_fallback_removal_plan.py",
    "nova_backend/services/patch_build_fallback_removal_plan.py",
    "tools/nova_autonomy_plan_fallback_removal_plan_smoke.py",
    "tools/nova_patch_build_fallback_removal_plan_smoke.py",
]


REQUIRED_LOCK_FILES = [
    "nova_backend/services/fallback_guard_cleanup_validation.py",
    "tools/nova_fallback_guard_cleanup_validation_smoke.py",
    "tools/nova_fallback_guard_cleanup_plan_smoke.py",
    "tools/nova_phase_3h_cleanup_lock_smoke.py",
    "tools/nova_master_quality_gate.py",
    "tools/nova_memory_quality_smoke.py",
]


REQUIRED_LOCK_MARKERS = [
    "nova_fallback_guard_cleanup_validation_smoke.py",
    "nova_fallback_guard_cleanup_plan_smoke.py",
    "nova_phase_3h_cleanup_lock_smoke.py",
    "nova_openai_key_log_safety_smoke.py",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _python_files():
    ignored_parts = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "nova_backups",
        "uploads",
    }

    for path in ROOT.rglob("*.py"):
        rel_parts = set(path.relative_to(ROOT).parts)
        if rel_parts & ignored_parts:
            continue
        yield path


def _reference_tokens(candidate: str) -> list[str]:
    path = Path(candidate)
    stem = path.stem
    dotted = candidate.replace("/", ".").replace("\\", ".")
    if dotted.endswith(".py"):
        dotted = dotted[:-3]

    return sorted(
        {
            candidate,
            candidate.replace("/", "\\"),
            path.name,
            stem,
            dotted,
        }
    )


def main():
    missing_lock_files = [
        item for item in REQUIRED_LOCK_FILES
        if not (ROOT / item).exists()
    ]
    assert_true("required lock files exist", not missing_lock_files, f"missing={missing_lock_files}")

    master_gate_text = _read(ROOT / "tools" / "nova_master_quality_gate.py")
    missing_gate_markers = [
        item for item in REQUIRED_LOCK_MARKERS
        if item not in master_gate_text
    ]
    assert_true("master quality gate has lock markers", not missing_gate_markers, f"missing={missing_gate_markers}")

    existing_candidates = [
        item for item in CANDIDATE_FILES
        if (ROOT / item).exists()
    ]
    assert_true("obsolete plan candidates found or already removed", True, f"existing={existing_candidates}")

    blockers = []

    this_file = Path(__file__).resolve()

    for candidate in existing_candidates:
        candidate_path = (ROOT / candidate).resolve()
        tokens = _reference_tokens(candidate)

        for py_file in _python_files():
            resolved = py_file.resolve()

            if resolved == this_file:
                continue

            if resolved == candidate_path:
                continue

            text = _read(py_file)
            hits = [token for token in tokens if token in text]

            if hits:
                blockers.append(
                    {
                        "candidate": candidate,
                        "referenced_by": str(py_file.relative_to(ROOT)),
                        "hits": hits,
                    }
                )

    assert_true("obsolete plan candidates unreferenced outside themselves", not blockers, f"blockers={blockers}")

    print("Existing obsolete Phase 3H plan-file candidates:")
    for item in existing_candidates:
        print(f"- {item}")

    print("NOVA OBSOLETE PHASE 3H PLAN FILES REVIEW SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

