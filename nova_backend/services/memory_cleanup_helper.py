# C:\Users\Owner\nova\nova_backend\services\memory_cleanup_helper.py
# NOVA_MEMORY_CLEANUP_HELPER_20260609
#
# Splits large memory entries (like attachments) into smaller usable memory records.

import json
from pathlib import Path

ROOT = Path(r"C:\Users\Owner\nova")
MEMORY_FILE = ROOT / "data/nova_memory.json"
CLEAN_FILE = ROOT / "data/nova_memory_clean.json"

def load_memory():
    if not MEMORY_FILE.exists():
        return {}
    raw = MEMORY_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)

def save_memory(memory, path):
    path.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved cleaned memory to {path}")

def split_attachment_item(item):
    """Breaks a large attachment memory item into smaller items per line/paragraph."""
    content = str(item.get("content") or "")
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    new_items = []
    for i, line in enumerate(lines):
        new_items.append({
            "category": item.get("category") or "attachment_line",
            "weight": item.get("weight") or 1,
            "source": item.get("source") or item.get("file") or "unknown",
            "text": line,
        })
    return new_items

def cleanup_memory(data):
    if not isinstance(data, dict) or "memory" not in data:
        return data
    cleaned = []
    for item in data["memory"]:
        if "Attachment" in str(item.get("content") or "") or len(str(item.get("content") or "")) > 500:
            cleaned.extend(split_attachment_item(item))
        else:
            cleaned.append(item)
    return {"memory": cleaned}

def main():
    data = load_memory()
    print(f"Loaded {len(data.get('memory', []))} memory items.")
    cleaned = cleanup_memory(data)
    print(f"Cleaned memory contains {len(cleaned.get('memory', []))} items.")
    save_memory(cleaned, CLEAN_FILE)

if __name__ == "__main__":
    main()