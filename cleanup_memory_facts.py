import json
from pathlib import Path

path = Path("./data/nova_memory.json")

data = json.loads(
    path.read_text(encoding="utf-8")
)

memory = data.get("memory", [])

cleaned = []

kept_backend_port = False

for item in memory:
    text = str(item.get("text") or "")

    if text.startswith("Nova backend runs on port"):
        if not kept_backend_port:
            item["text"] = "Nova backend runs on port 23000"
            item["fact_key"] = "nova_backend_port"
            cleaned.append(item)
            kept_backend_port = True
        else:
            continue
    else:
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

print("Memory cleanup complete")
print("Remaining items:", len(cleaned))