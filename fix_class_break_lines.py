from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
lines = p.read_text(encoding="utf-8-sig").splitlines()

out = []
i = 0

while i < len(lines):
    line = lines[i]

    if line.strip() == "import threading" and i + 2 < len(lines):
        if lines[i + 1].strip() == "import time" and lines[i + 2].startswith("def _start_execution_worker"):
            out.append("")
            out.append("    def _start_execution_worker(self, session_id: str):")
            i += 3
            continue

    out.append(line)
    i += 1

p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("LINE_REPAIR_DONE")
