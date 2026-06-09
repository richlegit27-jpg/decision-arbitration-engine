# C:\Users\Owner\nova\nova_backend\services\memory_cleanup_refined.py
# NOVA_MEMORY_CLEANUP_REFINED_20260609
#
# Collapses line-based memory items into attachment-level items.

import json
from pathlib import Path

ROOT = Path(r"C:\Users\Owner\nova")
INPUT_FILE = ROOT / "data/nova_memory_clean.json"
OUTPUT_FILE = ROOT / "data/nova_memory_refined.json"

def load_memory():
    if not INPUT_FILE.exists():
        return {}
    raw = INPUT_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)

def save_memory(memory, path):
    path.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved refined memory to {path}")

def refine_memory(data):
    if not isinstance(data, dict) or "memory" not in data:
        return data

    refined = []
    attachments = {}
    
    for item in data["memory"]:
        source = item.get("source") or "unknown"
        category = item.get("category") or "preference"
        content = str(item.get("text") or item.get("content") or "")
        weight = item.get("weight") or 10

        # Group by source (e.g., file name or 'unknown')
        if source not in attachments:
            attachments[source] = {
                "category": "attachment",
                "weight": weight,
                "source": source,
                "text": content
            }
        else:
            # Append text to existing attachment entry
            attachments[source]["text"] += "\n" + content

    # Convert grouped attachments to list
    refined.extend(attachments.values())

    return {"memory": refined}

def main():
    data = load_memory()
    print(f"Loaded {len(data.get('memory', []))} memory items.")
    refined = refine_memory(data)
    print(f"Refined memory contains {len(refined.get('memory', []))} items.")
    save_memory(refined, OUTPUT_FILE)

if __name__ == "__main__":
    main()