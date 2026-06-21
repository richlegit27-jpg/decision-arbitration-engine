from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


MEMORY_PATH = Path(r"C:\Users\Owner\nova\data\nova_memory.json")


def load_json(path: Path):
    if not path.exists():
        return {"memory": []}

    return json.loads(path.read_text(encoding="utf-8-sig"))


def extract_items(data):
    if isinstance(data, list):
        return data, "list"

    if isinstance(data, dict):
        for key in ("memory", "items", "memories", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value, key

    return [], "memory"


def item_text(item) -> str:
    if not isinstance(item, dict):
        return str(item or "")

    parts = []
    for key in ("text", "content", "summary", "value", "note", "description"):
        value = item.get(key)
        if value:
            parts.append(str(value))

    return " ".join(parts)


def main() -> None:
    if not MEMORY_PATH.exists():
        print(f"SKIPPED: memory file not found: {MEMORY_PATH}")
        return

    backup = MEMORY_PATH.with_suffix(
        MEMORY_PATH.suffix + f".BAK_before_pong_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(MEMORY_PATH, backup)

    data = load_json(MEMORY_PATH)
    items, container_key = extract_items(data)

    cleaned = []
    removed = []

    for item in items:
        text = item_text(item).lower()

        if "pong" in text or "say pong only" in text:
            removed.append(item)
            continue

        cleaned.append(item)

    if isinstance(data, list):
        output = cleaned
    elif isinstance(data, dict):
        data[container_key] = cleaned
        output = data
    else:
        output = {"memory": cleaned}

    MEMORY_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"BACKUP: {backup}")
    print(f"REMOVED: {len(removed)} pong memory items")
    print(f"KEPT: {len(cleaned)} memory items")


if __name__ == "__main__":
    main()


