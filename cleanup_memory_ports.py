import json
from pathlib import Path

path = Path(r".\data\nova_memory.json")

data = json.loads(
    path.read_text(encoding="utf-8")
)

memory = data.get("memory", [])

cleaned = []
seen = False

for item in memory:
    text = str(item.get("text") or "")

    if text.startswith("Nova backend runs on port"):
        if not seen:
            cleaned.append(item)
            seen = True
        continue

    cleaned.append(item)

data["memory"] = cleaned

path.write_text(
    json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("Port fact cleanup complete")
print("Remaining memory items:", len(cleaned))