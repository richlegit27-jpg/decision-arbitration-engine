from __future__ import annotations

from pathlib import Path


ROOT = Path(".")
MASTER = ROOT / "tools" / "nova_master_quality_gate.py"
PATCHER = ROOT / "tools" / "nova_phase_4z_wire_quiet_boot_lock_into_master_gate.py"

SMOKE = "nova_phase_4y_quiet_boot_log_lock_smoke.py"
GOOD_LINE = '    [str(ROOT / "tools" / "nova_phase_4y_quiet_boot_log_lock_smoke.py")],'


def fix_master() -> bool:
    text = MASTER.read_text(encoding="utf-8", errors="replace")
    before = text

    bad_lines = [
        f'    "{SMOKE}",',
        f"    '{SMOKE}',",
        f'"{SMOKE}",',
        f"'{SMOKE}',",
    ]

    for bad in bad_lines:
        if bad in text:
            text = text.replace(bad, GOOD_LINE)

    if SMOKE not in text:
        anchor = '    [str(ROOT / "tools" / "nova_openai_key_log_safety_smoke.py")],'

        if anchor not in text:
            raise SystemExit("Could not find OpenAI key safety smoke anchor in master gate")

        text = text.replace(anchor, anchor + "\n" + GOOD_LINE, 1)

    if GOOD_LINE not in text:
        raise SystemExit("Master gate still does not contain correct quiet boot lock command")

    if text != before:
        MASTER.write_text(text, encoding="utf-8")
        print("FIXED tools/nova_master_quality_gate.py")
        return True

    print("UNCHANGED tools/nova_master_quality_gate.py")
    return False


def fix_patcher() -> bool:
    if not PATCHER.exists():
        print("SKIP patcher not found")
        return False

    text = PATCHER.read_text(encoding="utf-8", errors="replace")
    before = text

    broken = '''        if line.rstrip().endswith("),"):
            # Tuple/list style, example:
            # ("name", ["script.py"]),
            new_lines.append(f'{indent}("{smoke}", ["{smoke}"]),')
        elif line.rstrip().endswith('",') or line.rstrip().endswith("',"):
            # Plain list of smoke filenames.
            quote = '"' if '"' in line else "'"
            new_lines.append(f"{indent}{quote}{smoke}{quote},")
        else:
            # Fallback: insert as a sibling script string.
            new_lines.append(f'{indent}"{smoke}",')'''

    fixed = '''        new_lines.append(f'{indent}[str(ROOT / "tools" / "{smoke}")],')'''

    if broken in text:
        text = text.replace(broken, fixed)

    if text != before:
        PATCHER.write_text(text, encoding="utf-8")
        print("FIXED tools/nova_phase_4z_wire_quiet_boot_lock_into_master_gate.py")
        return True

    print("UNCHANGED tools/nova_phase_4z_wire_quiet_boot_lock_into_master_gate.py")
    return False


def main() -> int:
    changed = False
    changed = fix_master() or changed
    changed = fix_patcher() or changed

    if not changed:
        print("No files changed; verifying existing state")

    print("NOVA PHASE 4Z MASTER GATE COMMAND REPAIR DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
