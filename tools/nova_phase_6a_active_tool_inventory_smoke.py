from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MASTER = TOOLS / "nova_master_quality_gate.py"

REQUIRED_ACTIVE_TOOLS = [
    "nova_phase_4t_boot_log_inventory.py",
    "nova_phase_4y_quiet_boot_log_lock_smoke.py",
    "nova_phase_5a_stale_patch_script_review_smoke.py",
    "nova_phase_5c_remaining_repair_script_review_smoke.py",
]

ONE_TIME_HINTS = [
    "patch",
    "repair",
    "wire",
    "fix",
]

SAFE_PERMANENT_HINTS = [
    "smoke",
    "gate",
    "inventory",
    "review",
    "runner",
    "audit",
    "validation",
    "lock",
]


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")

    print(f"PASS {name}")


def main() -> int:
    assert_true("tools directory exists", TOOLS.exists(), str(TOOLS))
    assert_true("master gate exists", MASTER.exists(), str(MASTER))

    master_text = MASTER.read_text(encoding="utf-8", errors="replace")

    tools = sorted(path.name for path in TOOLS.glob("*.py"))

    wired = []
    unwired_smokes_or_reviews = []
    one_time_like = []

    for name in tools:
        lower = name.lower()

        if name in master_text:
            wired.append(name)

        if any(hint in lower for hint in ["smoke", "review", "lock", "inventory"]) and name not in master_text:
            unwired_smokes_or_reviews.append(name)

        if any(hint in lower for hint in ONE_TIME_HINTS) and not any(hint in lower for hint in SAFE_PERMANENT_HINTS):
            one_time_like.append(name)

    print("")
    print("Required active tools:")

    for name in REQUIRED_ACTIVE_TOOLS:
        exists = name in tools
        wired_status = name in wired

        print(f"- {name} exists={exists} wired={wired_status}")

        assert_true(
            f"required active tool exists {name}",
            exists,
        )

    assert_true(
        "quiet boot lock wired into master gate",
        "nova_phase_4y_quiet_boot_log_lock_smoke.py" in wired,
    )

    print("")
    print("Master-gate wired tool files:")

    for name in wired:
        print(f"- {name}")

    print("")
    print("Unwired smoke/review/lock/inventory tools:")

    for name in unwired_smokes_or_reviews:
        print(f"- {name}")

    print("")
    print("One-time-looking non-permanent helper candidates:")

    for name in one_time_like:
        print(f"- {name}")

    assert_true(
        "no obvious one-time helper candidates",
        not one_time_like,
        f"candidates={one_time_like}",
    )

    print("")
    print(f"Tools scanned: {len(tools)}")
    print(f"Master-gate wired tools: {len(wired)}")
    print(f"Unwired smoke/review/lock/inventory tools: {len(unwired_smokes_or_reviews)}")
    print("NOVA PHASE 6A ACTIVE TOOL INVENTORY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
