from __future__ import annotations

from pathlib import Path


ROOT = Path(".")
MASTER = ROOT / "tools" / "nova_master_quality_gate.py"

SMOKES_TO_WIRE = [
    "nova_phase_5a_stale_patch_script_review_smoke.py",
    "nova_phase_5c_remaining_repair_script_review_smoke.py",
    "nova_phase_6a_active_tool_inventory_smoke.py",
    "nova_phase_6b_phase_4qr_helper_review_smoke.py",
]

ANCHOR = '    [str(ROOT / "tools" / "nova_phase_4y_quiet_boot_log_lock_smoke.py")],'


def main() -> int:
    text = MASTER.read_text(encoding="utf-8", errors="replace")

    if ANCHOR not in text:
        raise SystemExit("Could not find quiet boot lock smoke anchor")

    insert_lines = []

    for smoke in SMOKES_TO_WIRE:
        line = f'    [str(ROOT / "tools" / "{smoke}")],'

        if line in text:
            print(f"already wired: {smoke}")
            continue

        insert_lines.append(line)
        print(f"will wire: {smoke}")

    if not insert_lines:
        print("NOVA PHASE 6C CLEANUP LOCKS ALREADY WIRED")
        return 0

    replacement = ANCHOR + "\n" + "\n".join(insert_lines)
    text = text.replace(ANCHOR, replacement, 1)

    MASTER.write_text(text, encoding="utf-8")
    print("NOVA PHASE 6C CLEANUP LOCKS WIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
