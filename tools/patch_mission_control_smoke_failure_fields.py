from pathlib import Path

path = Path("tools/nova_project_brain_mission_control_smoke.py")
text = path.read_text(encoding="utf-8")

changed = 0

old_common = '''    assert_true(f"{name} has commit rule", "do not commit" in card.commit_rule.lower(), card.commit_rule)

    for term in expected_terms:
'''

new_common = '''    assert_true(f"{name} has commit rule", "do not commit" in card.commit_rule.lower(), card.commit_rule)
    assert_true(f"{name} has failure type", bool(card.failure_type), card)
    assert_true(f"{name} has failure next command", bool(card.failure_next_command), card)

    for term in expected_terms:
'''

if old_common in text and new_common not in text:
    text = text.replace(old_common, new_common, 1)
    changed += 1
    print("patched card failure field assertions")

old_format = '''    assert_true(f"{name} formatted commit rule", "commit rule:" in lower, answer)
'''

new_format = '''    assert_true(f"{name} formatted commit rule", "commit rule:" in lower, answer)
    assert_true(f"{name} formatted failure type", "failure type:" in lower, answer)
    assert_true(f"{name} formatted failure next", "failure next command:" in lower, answer)
'''

if old_format in text and new_format not in text:
    text = text.replace(old_format, new_format, 1)
    changed += 1
    print("patched formatted failure assertions")

old_terms = '''        expected_terms=[
            "diagnose_failed_smoke",
            "failing",
            "focused smoke",
            "do not weaken the smoke",
        ],
'''

new_terms = '''        expected_terms=[
            "diagnose_failed_smoke",
            "smoke_contract_mismatch",
            "failing",
            "focused smoke",
            "failure next command",
            "do not weaken the smoke",
        ],
'''

if old_terms in text and new_terms not in text:
    text = text.replace(old_terms, new_terms, 1)
    changed += 1
    print("patched failed smoke expected terms")

if changed == 0:
    raise SystemExit("no mission control smoke failure assertions patched")

path.write_text(text, encoding="utf-8")
print(f"patched mission control smoke failure sections: {changed}")
