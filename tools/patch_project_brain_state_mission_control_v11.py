from pathlib import Path

snapshot_path = Path("nova_backend/services/project_brain_freshness_snapshot.py")
snapshot = snapshot_path.read_text(encoding="utf-8-sig")

old_checkpoint = '''        "Decision Engine v1 and broad Project Brain routing are locked: exact project-state recall stays "
        "on direct recall, broad Nova project paraphrases route through Project Brain general intelligence, "
        "answer quality is 100%, and regression now protects both route contracts."
    )'''

new_checkpoint = '''        "Decision Engine v1, broad Project Brain routing, and Mission Control v1.1 are locked: "
        "exact project-state recall stays on direct recall, broad Nova project paraphrases route through "
        "Project Brain general intelligence, explicit operator prompts route to Mission Control, answer "
        "quality is 100%, and regression now protects the route contracts."
    )'''

old_blocker = '''        "No active Decision Engine blocker is open. The remaining risk is cleanup/consolidation: app.py still "
        "has many historical guards and wrappers, so future work should avoid new route-layer patches and move "
        "intelligence into services."
    )'''

new_blocker = '''        "No active Decision Engine blocker is open, and no active Mission Control blocker is open. "
        "The remaining risk is cleanup/consolidation: app.py still has many historical guards and wrappers, "
        "so future work should avoid new route-layer patches and move intelligence into services."
    )'''

old_next = '''        "Start Project Brain cleanup/consolidation: keep the locked Decision Engine v1 behavior, preserve "
        "direct recall and broad Project Brain routing, and consolidate stale route/context wording without "
        "adding another app.py guard."
    )'''

new_next = '''        "Start Project Brain cleanup/consolidation: keep the locked Decision Engine v1 and Mission Control "
        "v1.1 behavior, preserve direct recall, broad Project Brain routing, and explicit operator Mission "
        "Control prompts, and consolidate stale route/context wording without adding another app.py guard."
    )'''

changed = 0

for old, new, label in [
    (old_checkpoint, new_checkpoint, "checkpoint"),
    (old_blocker, new_blocker, "blocker"),
    (old_next, new_next, "next_move"),
]:
    count = snapshot.count(old)
    if count:
        snapshot = snapshot.replace(old, new)
        changed += count
        print(f"patched snapshot {label}: {count}")

snapshot_replacements = {
    '["Decision Engine v1", "Project Brain routing"]':
        '["Decision Engine v1", "Project Brain routing", "Mission Control v1.1"]',

    '["No active Decision Engine blocker", "cleanup/consolidation"]':
        '["No active Decision Engine blocker", "Mission Control blocker", "cleanup/consolidation"]',

    '["Project Brain cleanup/consolidation", "without adding another app.py guard"]':
        '["Project Brain cleanup/consolidation", "Mission Control v1.1", "without adding another app.py guard"]',
}

for old, new in snapshot_replacements.items():
    count = snapshot.count(old)
    if count:
        snapshot = snapshot.replace(old, new)
        changed += count
        print(f"patched sanitizer requirement: {old}")

if changed == 0:
    raise SystemExit("no snapshot state fields patched")

snapshot_path.write_text(snapshot, encoding="utf-8")


fresh_smoke_path = Path("tools/nova_project_brain_freshness_snapshot_smoke.py")
fresh = fresh_smoke_path.read_text(encoding="utf-8")

fresh_replacements = {
    '    assert_true("routing locked", "project brain routing" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n':
        '    assert_true("routing locked", "project brain routing" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n'
        '    assert_true("mission control locked", "mission control v1.1" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n'
        '    assert_true("operator prompts locked", "operator prompts" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n',

    '    assert_true("blocker closed", "no active decision engine blocker" in snapshot.blocker.lower(), snapshot.blocker)\n':
        '    assert_true("blocker closed", "no active decision engine blocker" in snapshot.blocker.lower(), snapshot.blocker)\n'
        '    assert_true("mission blocker closed", "mission control blocker" in snapshot.blocker.lower(), snapshot.blocker)\n',

    '    assert_true("next move cleanup", "project brain cleanup/consolidation" in snapshot.next_move.lower(), snapshot.next_move)\n':
        '    assert_true("next move cleanup", "project brain cleanup/consolidation" in snapshot.next_move.lower(), snapshot.next_move)\n'
        '    assert_true("next move preserves Mission Control", "mission control v1.1" in snapshot.next_move.lower(), snapshot.next_move)\n',

    '    assert_true("direct answer has Decision Engine", "decision engine v1" in direct_lower, direct_answer)\n':
        '    assert_true("direct answer has Decision Engine", "decision engine v1" in direct_lower, direct_answer)\n'
        '    assert_true("direct answer has Mission Control", "mission control v1.1" in direct_lower, direct_answer)\n',

    '    assert_true("api answer has Decision Engine", "decision engine v1" in api_lower, api_answer)\n':
        '    assert_true("api answer has Decision Engine", "decision engine v1" in api_lower, api_answer)\n'
        '    assert_true("api answer has Mission Control", "mission control v1.1" in api_lower, api_answer)\n',
}

fresh_changed = 0
for old, new in fresh_replacements.items():
    if old in fresh and new not in fresh:
        fresh = fresh.replace(old, new, 1)
        fresh_changed += 1

if fresh_changed:
    fresh_smoke_path.write_text(fresh, encoding="utf-8")
    print(f"patched freshness smoke sections: {fresh_changed}")


answer_quality_path = Path("tools/nova_answer_quality_smoke.py")
quality = answer_quality_path.read_text(encoding="utf-8")

quality_replacements = {
    '''            "Decision Engine v1",
            "Project Brain cleanup/consolidation",
''': '''            "Decision Engine v1",
            "Mission Control v1.1",
            "Project Brain cleanup/consolidation",
''',

    '''            "No active Decision Engine blocker",
            "cleanup/consolidation",
''': '''            "No active Decision Engine blocker",
            "Mission Control blocker",
            "cleanup/consolidation",
''',
}

quality_changed = 0
for old, new in quality_replacements.items():
    if old in quality and new not in quality:
        quality = quality.replace(old, new, 1)
        quality_changed += 1

if quality_changed:
    answer_quality_path.write_text(quality, encoding="utf-8")
    print(f"patched answer-quality sections: {quality_changed}")

print("Project Brain state synced to Mission Control v1.1")
