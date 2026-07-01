from pathlib import Path
import json


LIVE_CODE_FILES = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
]

MEMORY_FILE = Path("data/nova_memory.json")

REPLACEMENTS = {
    "finish Nova project brain answer quality":
        "Project Brain answer freshness v2",

    "make `what's next?` return project context instead of generic chat fallback":
        "use the Project Brain freshness snapshot as the context builder source of truth",

    "harden `tools/nova_project_brain_live_answer_sample.py` so the smoke fails if idle/generic fallback text appears":
        "keep next move, blocker, fallback priority, and safe move answers fresh through the context-builder path",

    "harden `tools/nova_project_brain_live_answer_sample.py` so idle fallback text fails the smoke":
        "keep next move, blocker, fallback priority, and safe move answers fresh through the context-builder path",

    "then harden `tools/nova_project_brain_live_answer_sample.py` so idle fallback text fails the smoke":
        "then keep next move, blocker, fallback priority, and safe move answers fresh through the context-builder path",

    "larger Nova answer-quality 95 smoke now passes 20/20 with retry handling for Flask reload connection resets":
        "Project Brain answer freshness v2 is the current blocker: fallback-route priority, the context-builder path, next move, recent commits, and validation state should come from the freshness snapshot",

    "Recent commits include `Add Nova answer quality 95 policy` and `Make Nova answer quality smoke retry reload resets`.":
        "Recent commits now include the direct project-state freshness bridge, service extraction, and hardened freshness smoke.",

    "Current checkpoint: measured answer-policy intelligence is 100% on the 20-case board, but real general intelligence still needs improvement by moving direct policy behavior into cleaner prompt, intent, and project-brain layers instead of adding more app.py guards.":
        "Current checkpoint: Project Brain routing, classifier broadening, context-builder answers, direct freshness, and freshness snapshot validation are protected by dedicated smokes.",

    "Next useful direction: generalize the 95 policy layer and reduce reliance on direct before_request patches.":
        "Next useful direction / safe move: use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next concrete move / safe move, latest commits, and available smoke files.",
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
    text = path.read_text(encoding="utf-8")
    patched, changed = patch_text(text)
    if changed:
        path.write_text(patched, encoding="utf-8")
    print(f"{path}: {changed} replacement(s)")
    return changed


def patch_json_strings(value):
    if isinstance(value, str):
        patched, changed = patch_text(value)
        return patched, changed

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


total_live = 0
for path in LIVE_CODE_FILES:
    total_live += patch_file(path)

if MEMORY_FILE.exists():
    data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    patched_data, memory_changes = patch_json_strings(data)
    if memory_changes:
        MEMORY_FILE.write_text(
            json.dumps(patched_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(f"{MEMORY_FILE}: {memory_changes} replacement(s)")
else:
    memory_changes = 0
    print(f"{MEMORY_FILE}: missing, skipped")

if total_live <= 0:
    raise SystemExit("no live app/chat_service stale project-context replacements were made")

print("patched stale project answer sources")
