from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()

# Remove all standalone import json lines.
lines = [line for line in lines if line.strip() != "import json"]

# Insert import json immediately AFTER from __future__ import annotations.
future_index = None
for i, line in enumerate(lines):
    if line.strip() == "from __future__ import annotations":
        future_index = i
        break

if future_index is None:
    # Fallback if future import is missing.
    lines.insert(0, "import json")
    print("WARNING: no future import found; inserted import json at top")
else:
    lines.insert(future_index + 1, "import json")
    print("Moved import json after future import")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
