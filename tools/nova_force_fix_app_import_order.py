from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()

cleaned = []
for line in lines:
    normalized = line.replace("\ufeff", "").strip()
    if normalized == "import json":
        continue
    if normalized == "from __future__ import annotations":
        continue
    cleaned.append(line)

# Remove leading blank lines so future import is truly first.
while cleaned and not cleaned[0].strip():
    cleaned.pop(0)

fixed = [
    "from __future__ import annotations",
    "import json",
    "",
] + cleaned

path.write_text("\n".join(fixed) + "\n", encoding="utf-8")
print("fixed app.py import order")
