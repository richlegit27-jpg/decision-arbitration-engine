from __future__ import annotations

from pathlib import Path


path = Path("tools/nova_master_quality_gate.py")
text = path.read_text(encoding="utf-8", errors="replace")

smoke = "nova_phase_4y_quiet_boot_log_lock_smoke.py"

if smoke in text:
    print("NOVA PHASE 4Z MASTER GATE ALREADY WIRED")
    raise SystemExit(0)

anchor = "nova_openai_key_log_safety_smoke.py"

if anchor not in text:
    raise SystemExit("Could not find OpenAI key log safety smoke anchor")

lines = text.splitlines()
new_lines = []
inserted = False

for line in lines:
    new_lines.append(line)

    if anchor in line and not inserted:
        indent = line[: len(line) - len(line.lstrip())]

        new_lines.append(f'{indent}[str(ROOT / "tools" / "{smoke}")],')

        inserted = True

if not inserted:
    raise SystemExit("Failed to insert quiet boot log lock smoke")

path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("NOVA PHASE 4Z MASTER GATE WIRED")
