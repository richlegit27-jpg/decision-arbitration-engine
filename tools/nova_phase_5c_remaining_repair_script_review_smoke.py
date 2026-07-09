from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

TARGETS = [
    "nova_phase_4x_inventory_classifier_patch.py",
    "nova_phase_4z_wire_quiet_boot_lock_into_master_gate.py",
    "nova_phase_4z_master_gate_command_repair.py",
]

SELF = "nova_phase_5c_remaining_repair_script_review_smoke.py"


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")

    print(f"PASS {name}")


def references_to(filename: str) -> list[str]:
    refs = []
    target_set = set(TARGETS)

    for path in TOOLS.glob("*.py"):
        if path.name == filename:
            continue

        if path.name == SELF:
            continue

        if path.name in target_set:
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        if filename in text:
            refs.append(str(path.relative_to(ROOT)))

    return refs


def main() -> int:
    assert_true("tools directory exists", TOOLS.exists(), str(TOOLS))

    print("")
    print("Phase 5C remaining one-time repair script review:")

    found = 0

    for name in TARGETS:
        path = TOOLS / name
        exists = path.exists()

        print(f"- tools\\{name} exists={exists}")

        if not exists:
            continue

        found += 1
        refs = references_to(name)

        print(f"  external_refs={refs}")

        assert_true(
            f"remaining repair script externally unreferenced {name}",
            not refs,
            f"external_refs={refs}",
        )

    assert_true(
        "remaining one-time repair scripts found or already clean",
        True,
        f"count={found}",
    )

    print("")
    print(f"Remaining one-time repair scripts found: {found}")
    print("NOVA PHASE 5C REMAINING REPAIR SCRIPT REVIEW SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
