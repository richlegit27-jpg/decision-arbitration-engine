from __future__ import annotations

from pathlib import Path


path = Path("tools/nova_phase_5c_remaining_repair_script_review_smoke.py")
text = path.read_text(encoding="utf-8", errors="replace")

old = '''    for path in TOOLS.glob("*.py"):
        if path.name == filename:
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        if filename in text:
            refs.append(str(path.relative_to(ROOT)))
'''

new = '''    for path in TOOLS.glob("*.py"):
        if path.name == filename:
            continue

        if path.name == "nova_phase_5c_remaining_repair_script_review_smoke.py":
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        if filename in text:
            refs.append(str(path.relative_to(ROOT)))
'''

if old not in text:
    raise SystemExit("references_to block not found")

path.write_text(text.replace(old, new), encoding="utf-8")
print("NOVA PHASE 5C REVIEW SELF-REFERENCE REPAIR DONE")
