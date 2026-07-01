import json
from datetime import datetime, timezone
from pathlib import Path

MEMORY_PATH = Path("data/nova_memory.json")

PROJECT_STATE_ID = "memory_nova_project_state_current"
WORKFLOW_PREF_ID = "memory_richard_workflow_preference"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_store():
    if MEMORY_PATH.exists():
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8") or "{}")
    return {"memory": []}

def save_store(store):
    MEMORY_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

def upsert_memory(items, item):
    target_id = item["id"]
    for index, existing in enumerate(items):
        if isinstance(existing, dict) and existing.get("id") == target_id:
            preserved = dict(existing)
            preserved.update(item)
            preserved["created_at"] = existing.get("created_at") or item["created_at"]
            preserved["updated_at"] = now_iso()
            preserved["count"] = int(existing.get("count") or 1) + 1
            items[index] = preserved
            return "updated"

    items.append(item)
    return "added"

def main():
    store = load_store()
    items = store.setdefault("memory", [])

    now = now_iso()

    project_state = {
        "id": PROJECT_STATE_ID,
        "text": (
            "Current Nova project state: Richard is working on the local Nova Flask app with Joe. "
            "Current focus is improving memory quality and clarifying the boundary between memory, execution, and normal chat. "
            "Recent decision: stop chasing the exact `what's next?` route bug for now because wrapper/route-order work was not moving the needle. "
            "Current architectural risk: app.py has too many stacked guards/wrappers; future fixes should avoid more blind route patches. "
            "Next useful direction: build a clean project_state memory layer that stores current focus, current blocker, last decision, and next move."
        ),
        "kind": "project_state",
        "category": "project_state",
        "source": "manual_project_state_seed",
        "session_id": "",
        "weight": 10.0,
        "pinned": True,
        "created_at": now,
        "updated_at": now,
        "count": 1,
    }

    workflow_pref = {
        "id": WORKFLOW_PREF_ID,
        "text": (
            "Richard's Nova workflow preference: be direct, use exact Windows/PowerShell commands, exact file paths, "
            "avoid fluff, avoid giant patch stacks, avoid unnecessary commits, and prefer small verified steps that compile or smoke-test before commit."
        ),
        "kind": "preference",
        "category": "workflow_preference",
        "source": "manual_project_state_seed",
        "session_id": "",
        "weight": 10.0,
        "pinned": True,
        "created_at": now,
        "updated_at": now,
        "count": 1,
    }

    project_result = upsert_memory(items, project_state)
    pref_result = upsert_memory(items, workflow_pref)

    save_store(store)

    print("NOVA MEMORY PROJECT STATE SEED PASSED")
    print(f"- project_state: {project_result}")
    print(f"- workflow_preference: {pref_result}")
    print(f"- total memories: {len(items)}")
    print(MEMORY_PATH)

if __name__ == "__main__":
    main()
