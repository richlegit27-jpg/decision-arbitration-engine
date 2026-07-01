from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

TARGETS = [
    "nova_phase_4q_openai_key_log_cleanup.py",
    "nova_phase_4r_app_run_main_guard_fix.py",
]


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")

    print(f"PASS {name}")


def references_to(filename: str) -> list[str]:
    refs = []

    for path in TOOLS.glob("*.py"):
        if path.name == filename:
            continue

        if path.name == "nova_phase_6b_phase_4qr_helper_review_smoke.py":
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        if filename in text:
            refs.append(str(path.relative_to(ROOT)))

    return refs


def main() -> int:
    assert_true("tools directory exists", TOOLS.exists(), str(TOOLS))

    print("")
    print("Phase 6B Phase 4Q/4R one-time helper review:")

    found = 0

    for name in TARGETS:
        path = TOOLS / name
        exists = path.exists()

        print(f"- tools\\{name} exists={exists}")

        if not exists:
            continue

        found += 1
        refs = references_to(name)

        print(f"  refs={refs}")

        assert_true(
            f"phase 4 helper unreferenced {name}",
            not refs,
            f"refs={refs}",
        )

    print("")
    print(f"Phase 4Q/4R helpers found: {found}")
    print("NOVA PHASE 6B PHASE 4QR HELPER REVIEW SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
