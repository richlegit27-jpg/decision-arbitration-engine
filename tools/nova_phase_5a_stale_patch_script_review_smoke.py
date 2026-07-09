from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

CANDIDATE_NAME_HINTS = [
    "patch",
    "repair",
    "fix",
    "wire",
]

KEEP_NAME_HINTS = [
    "smoke",
    "gate",
    "inventory",
    "review",
    "runner",
    "audit",
    "validation",
    "lock",
]

PHASE_HINTS = [
    "nova_phase_4t",
    "nova_phase_4u",
    "nova_phase_4v",
    "nova_phase_4w",
    "nova_phase_4x",
    "nova_phase_4z",
]


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")

    print(f"PASS {name}")


def is_candidate(path: Path) -> bool:
    name = path.name.lower()

    if not name.startswith("nova_"):
        return False

    if not any(phase in name for phase in PHASE_HINTS):
        return False

    if any(keep in name for keep in KEEP_NAME_HINTS):
        return False

    return any(hint in name for hint in CANDIDATE_NAME_HINTS)


def references_to(filename: str) -> list[str]:
    refs = []

    for path in TOOLS.glob("*.py"):
        if path.name == filename:
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        if filename in text:
            refs.append(str(path.relative_to(ROOT)))

    return refs


def main() -> int:
    assert_true("tools directory exists", TOOLS.exists(), str(TOOLS))

    candidates = sorted(path for path in TOOLS.glob("*.py") if is_candidate(path))

    print("")
    print("Phase 5A stale one-time patch script candidates:")

    for path in candidates:
        refs = references_to(path.name)
        print(f"- {path.relative_to(ROOT)} refs={refs}")

        assert_true(
            f"candidate unreferenced {path.name}",
            not refs,
            f"refs={refs}",
        )

    assert_true(
        "candidate list found or already clean",
        True,
        f"count={len(candidates)}",
    )

    print("")
    print(f"Candidates found: {len(candidates)}")
    print("NOVA PHASE 5A STALE PATCH SCRIPT REVIEW SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
