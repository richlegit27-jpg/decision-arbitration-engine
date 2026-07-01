import json
import re
from pathlib import Path
from collections import Counter

MEMORY_PATH = Path("data/nova_memory.json")

NOISE_PATTERNS = [
    r"project_brain_api_next_test_\d+",
    r"project_brain_test_client_\d+",
    r"NOVA_API_CHAT_PROJECT_NEXT",
    r"NOVA_PROJECT_NEXT",
    r"wrapper",
    r"wrapped endpoints",
    r"SyntaxError",
    r"chat_service\.handle",
    r"\b[0-9a-f]{7,40}\b",
    r"line \d+",
]

USEFUL_PATTERNS = [
    r"user preference",
    r"Richard",
    r"current focus",
    r"current task",
    r"current project",
    r"Nova",
    r"decision",
    r"last stable",
    r"blocker",
    r"mobile",
    r"memory",
    r"execution",
]

def load_memory():
    if not MEMORY_PATH.exists():
        raise SystemExit(f"missing memory file: {MEMORY_PATH}")

    data = json.loads(MEMORY_PATH.read_text(encoding="utf-8") or "{}")
    return data

def flatten_items(data):
    items = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                items.append(item)
        return items

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        copied = dict(item)
                        copied.setdefault("_bucket", key)
                        items.append(copied)
            elif isinstance(value, dict):
                copied = dict(value)
                copied.setdefault("_bucket", key)
                items.append(copied)

    return items

def item_text(item):
    parts = []
    for key in ("text", "content", "summary", "value", "memory", "note", "title", "type", "category", "_bucket"):
        value = item.get(key)
        if value:
            parts.append(str(value))
    return "\n".join(parts)

def score_patterns(text, patterns):
    hits = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits

def main():
    data = load_memory()
    items = flatten_items(data)

    print("NOVA MEMORY AUDIT")
    print("=================")
    print(f"path: {MEMORY_PATH}")
    print(f"top-level type: {type(data).__name__}")
    print(f"items found: {len(items)}")
    print("")

    buckets = Counter(str(item.get("_bucket") or item.get("type") or item.get("category") or "unknown") for item in items)
    print("Buckets / categories:")
    for name, count in buckets.most_common(20):
        print(f"- {name}: {count}")
    print("")

    noisy = []
    useful = []

    for index, item in enumerate(items):
        text = item_text(item)
        noise_hits = score_patterns(text, NOISE_PATTERNS)
        useful_hits = score_patterns(text, USEFUL_PATTERNS)

        if noise_hits:
            noisy.append((index, noise_hits, text[:500].replace("\n", " ")))

        if useful_hits:
            useful.append((index, useful_hits, text[:500].replace("\n", " ")))

    print(f"Potential debug/noise memories: {len(noisy)}")
    for index, hits, preview in noisy[:30]:
        print(f"- #{index} hits={hits} :: {preview}")
    print("")

    print(f"Potential useful project/user memories: {len(useful)}")
    for index, hits, preview in useful[:30]:
        print(f"- #{index} hits={hits} :: {preview}")
    print("")

    print("Recommended memory rule:")
    print("- Keep durable preferences, project focus, current blocker, and major decisions.")
    print("- Move temporary patch/test/session details to session history, not long-term memory.")
    print("- Keep one clean project_state summary instead of many wrapper/debug memories.")

if __name__ == "__main__":
    main()
