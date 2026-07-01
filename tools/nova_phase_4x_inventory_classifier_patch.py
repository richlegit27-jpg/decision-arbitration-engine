from pathlib import Path


path = Path("tools/nova_phase_4t_boot_log_inventory.py")
text = path.read_text(encoding="utf-8", errors="replace")

old = '''def classify_print(line: str) -> str:
    upper = line.upper()

    if any(hint.upper() in upper for hint in BOOT_HINTS):
        return "boot"

    if any(hint.upper() in upper for hint in DEBUG_HINTS):
        return "debug/error"

    return "other"
'''

new = '''def classify_print(line: str) -> str:
    upper = line.upper()

    if any(hint.upper() in upper for hint in DEBUG_HINTS):
        return "debug/error"

    if any(hint.upper() in upper for hint in BOOT_HINTS):
        return "boot"

    return "other"
'''

if old not in text:
    raise SystemExit("classify_print block not found")

path.write_text(text.replace(old, new), encoding="utf-8")
print("NOVA PHASE 4X INVENTORY CLASSIFIER PATCHED")
