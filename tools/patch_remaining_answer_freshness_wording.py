from pathlib import Path
import json


TEXT_FILES = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("nova_backend/services/project_brain_context_builder.py"),
    Path("nova_backend/services/project_state_direct_freshness_bridge.py"),
]

MEMORY_FILE = Path("data/nova_memory.json")

REPLACEMENTS = {
    "Current task: Project Brain answer freshness v2.\nNext move: use the Project Brain freshness snapshot as the context builder source of truth, then harden `tools/nova_project_brain_live_answer_sample.py` so the smoke fails if idle/generic fallback text appears.":
        "Current task: Project Brain answer freshness v2.\nNext move / safe move: use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next move, fallback priority, recent commits, validation state, and available smoke files.",

    "Current task: Project Brain answer freshness v2.\nNext move: use the Project Brain freshness snapshot as the context builder source of truth, then harden `tools/nova_project_brain_live_answer_sample.py` so idle fallback text fails the smoke.":
        "Current task: Project Brain answer freshness v2.\nNext move / safe move: use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next move, fallback priority, recent commits, validation state, and available smoke files.",

    "Next move: use the Project Brain freshness snapshot as the context builder source of truth, then harden `tools/nova_project_brain_live_answer_sample.py` so the smoke fails if idle/generic fallback text appears.":
        "Next move / safe move: use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next move, fallback priority, recent commits, validation state, and available smoke files.",

    "Next move: use the Project Brain freshness snapshot as the context builder source of truth, then harden `tools/nova_project_brain_live_answer_sample.py` so idle fallback text fails the smoke.":
        "Next move / safe move: use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next move, fallback priority, recent commits, validation state, and available smoke files.",

    "then harden `tools/nova_project_brain_live_answer_sample.py` so the smoke fails if idle/generic fallback text appears":
        "then use the Project Brain freshness snapshot as the context builder source of truth for the next safe move",

    "then harden `tools/nova_project_brain_live_answer_sample.py` so idle fallback text fails the smoke":
        "then use the Project Brain freshness snapshot as the context builder source of truth for the next safe move",

    "`tools/nova_project_brain_live_answer_sample.py` so the smoke fails if idle/generic fallback text appears":
        "the Project Brain freshness snapshot as the context builder source of truth for the next safe move",

    "`tools/nova_project_brain_live_answer_sample.py` so idle fallback text fails the smoke":
        "the Project Brain freshness snapshot as the context builder source of truth for the next safe move",

    "fallback-route priority, the context-builder path, next move, recent commits, and validation state should come from the freshness snapshot.":
        "Project Brain answer freshness v2: fallback-route priority, the context-builder path, next move, recent commits, and validation state should come from the freshness snapshot.",

    "Current blocker: fallback-route priority, the context-builder path, next move, recent commits, and validation state should come from the freshness snapshot.":
        "Current blocker: Project Brain answer freshness v2: fallback-route priority, the context-builder path, next move, recent commits, and validation state should come from the freshness snapshot.",

    "Current blocker: The current blocker is Project Brain answer freshness v2: Project Brain answer freshness v2:":
        "Current blocker: Project Brain answer freshness v2:",
}


def patch_text(text):
    changed = 0
    for old, new in REPLACEMENTS.items():
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            changed += count

    return text, changed


def patch_file(path):
    if not path.exists():
        print(f"{path}: missing, skipped")
        return 0

    text = path.read_text(encoding="utf-8")
    patched, changed = patch_text(text)

    if changed:
        path.write_text(patched, encoding="utf-8")

    print(f"{path}: {changed} replacement(s)")
    return changed


def patch_json_strings(value):
    if isinstance(value, str):
        return patch_text(value)

    if isinstance(value, list):
        total = 0
        new_items = []
        for item in value:
            patched_item, changed = patch_json_strings(item)
            total += changed
            new_items.append(patched_item)
        return new_items, total

    if isinstance(value, dict):
        total = 0
        new_obj = {}
        for key, item in value.items():
            patched_item, changed = patch_json_strings(item)
            total += changed
            new_obj[key] = patched_item
        return new_obj, total

    return value, 0


total = 0

for path in TEXT_FILES:
    total += patch_file(path)

if MEMORY_FILE.exists():
    data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    patched_data, changed = patch_json_strings(data)

    if changed:
        MEMORY_FILE.write_text(
            json.dumps(patched_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"{MEMORY_FILE}: {changed} replacement(s), ignored by git")
else:
    print(f"{MEMORY_FILE}: missing, skipped")

if total <= 0:
    raise SystemExit("no tracked source replacements made")

print("patched remaining answer freshness wording")
