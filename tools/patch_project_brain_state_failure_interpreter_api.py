from pathlib import Path

byte_targets = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("tools/nova_project_brain_freshness_snapshot_smoke.py"),
    Path("tools/nova_answer_quality_smoke.py"),
]

byte_replacements = [
    (
        b"Mission Control v1.1",
        b"Mission Control v1.2 / Failure Interpreter API",
    ),
    (
        b"No active Decision Engine blocker is open, and no active Mission Control blocker is open. ",
        b"No active Decision Engine blocker is open, no active Mission Control blocker is open, and no active Failure Interpreter blocker is open. ",
    ),
    (
        b"explicit operator Mission Control prompts, and avoiding another app.py guard.",
        b"explicit operator Mission Control prompts, pasted failure interpretation, and avoiding another app.py guard.",
    ),
    (
        b"explicit operator Mission Control prompts, and consolidate",
        b"explicit operator Mission Control prompts, pasted failure interpretation, and consolidate",
    ),
]

total = 0

for path in byte_targets:
    if not path.exists():
        continue

    data = path.read_bytes()
    original = data
    file_total = 0

    for old, new in byte_replacements:
        count = data.count(old)
        if count:
            data = data.replace(old, new)
            total += count
            file_total += count

    if data != original:
        path.write_bytes(data)
        print(f"patched {path}: {file_total} byte replacement(s)")

if total == 0:
    raise SystemExit("no Mission Control v1.2 state wording replacements applied")


fresh_path = Path("tools/nova_project_brain_freshness_snapshot_smoke.py")
fresh = fresh_path.read_text(encoding="utf-8-sig")
fresh_changed = 0

fresh_replacements = {
    '    assert_true("mission control locked", "mission control v1.2 / failure interpreter api" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n':
        '    assert_true("mission control locked", "mission control v1.2 / failure interpreter api" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n'
        '    assert_true("failure interpreter locked", "failure interpreter api" in snapshot.checkpoint.lower(), snapshot.checkpoint)\n',

    '    assert_true("mission blocker closed", "mission control blocker" in snapshot.blocker.lower(), snapshot.blocker)\n':
        '    assert_true("mission blocker closed", "mission control blocker" in snapshot.blocker.lower(), snapshot.blocker)\n'
        '    assert_true("failure interpreter blocker closed", "failure interpreter blocker" in snapshot.blocker.lower(), snapshot.blocker)\n',

    '    assert_true("next move preserves Mission Control", "mission control v1.2 / failure interpreter api" in snapshot.next_move.lower(), snapshot.next_move)\n':
        '    assert_true("next move preserves Mission Control", "mission control v1.2 / failure interpreter api" in snapshot.next_move.lower(), snapshot.next_move)\n'
        '    assert_true("next move preserves failure interpretation", "pasted failure interpretation" in snapshot.next_move.lower(), snapshot.next_move)\n',

    '    assert_true("direct answer has Mission Control", "mission control v1.2 / failure interpreter api" in direct_lower, direct_answer)\n':
        '    assert_true("direct answer has Mission Control", "mission control v1.2 / failure interpreter api" in direct_lower, direct_answer)\n'
        '    assert_true("direct answer has Failure Interpreter", "failure interpreter api" in direct_lower, direct_answer)\n',

    '    assert_true("api answer has Mission Control", "mission control v1.2 / failure interpreter api" in api_lower, api_answer)\n':
        '    assert_true("api answer has Mission Control", "mission control v1.2 / failure interpreter api" in api_lower, api_answer)\n'
        '    assert_true("api answer has Failure Interpreter", "failure interpreter api" in api_lower, api_answer)\n',
}

for old, new in fresh_replacements.items():
    if old in fresh and new not in fresh:
        fresh = fresh.replace(old, new, 1)
        fresh_changed += 1

if fresh_changed:
    fresh_path.write_text(fresh, encoding="utf-8")
    print(f"patched freshness smoke failure-interpreter assertions: {fresh_changed}")


quality_path = Path("tools/nova_answer_quality_smoke.py")
quality = quality_path.read_text(encoding="utf-8-sig")
quality_changed = 0

quality_replacements = {
    '            "Mission Control blocker",\n':
        '            "Mission Control blocker",\n'
        '            "Failure Interpreter blocker",\n',

    '            "avoiding another app.py guard",\n':
        '            "pasted failure interpretation",\n'
        '            "avoiding another app.py guard",\n',
}

for old, new in quality_replacements.items():
    if old in quality and new not in quality:
        quality = quality.replace(old, new, 1)
        quality_changed += 1

if quality_changed:
    quality_path.write_text(quality, encoding="utf-8")
    print(f"patched answer-quality failure-interpreter terms: {quality_changed}")

print("Project Brain state synced to Mission Control v1.2 / Failure Interpreter API")
