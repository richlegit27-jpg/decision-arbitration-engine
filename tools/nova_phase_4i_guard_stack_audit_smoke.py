from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

REQUIRED_SINGLETONS = [
    "NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701",
]

FORBIDDEN_PHASE4F_RELICS = [
    "NOVA_PHASE4F_NORMAL_CHAT_PROJECT_STATE_BLEED_GUARD_20260701",
    "NOVA_PHASE4F_FINAL_NORMAL_CHAT_PROJECT_STATE_BLEED_GUARD_20260701",
]

KNOWN_DUPLICATE_CANDIDATES = [
    "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611",
    "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    assert_true("app.py exists", APP.exists())

    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    for marker in REQUIRED_SINGLETONS:
        count = text.count(marker)
        assert_true(f"required singleton {marker}", count >= 1, f"count={count}")

    for marker in FORBIDDEN_PHASE4F_RELICS:
        count = text.count(marker)
        assert_true(f"forbidden Phase 4F relic absent {marker}", count == 0, f"count={count}")

    main_lines = [
        i for i, line in enumerate(lines, start=1)
        if 'if __name__ == "__main__"' in line or "if __name__ == '__main__'" in line
    ]
    assert_true("main block exists", bool(main_lines), main_lines)

    first_main = main_lines[0]
    phase4f_lines = [
        i for i, line in enumerate(lines, start=1)
        if "NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701" in line
    ]
    assert_true(
        "Phase 4F guard above main",
        phase4f_lines and min(phase4f_lines) < first_main,
        f"phase4f_lines={phase4f_lines} main={first_main}",
    )

    marker_lines = defaultdict(list)
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("# NOVA_"):
            marker = stripped[2:].strip()
            marker_lines[marker].append(i)

    duplicates = {
        marker: locs
        for marker, locs in marker_lines.items()
        if len(locs) > 1
    }

    print("")
    print("Duplicate NOVA marker candidates:")
    if not duplicates:
        print("- none")
    else:
        for marker, locs in sorted(duplicates.items()):
            print(f"- {marker}: {len(locs)} occurrence(s) at lines {locs}")

    for marker in KNOWN_DUPLICATE_CANDIDATES:
        locs = marker_lines.get(marker, [])
        assert_true(
            f"known duplicate candidate visible {marker}",
            len(locs) >= 2,
            f"lines={locs}",
        )

    print("")
    print("NOVA PHASE 4I GUARD STACK AUDIT SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
