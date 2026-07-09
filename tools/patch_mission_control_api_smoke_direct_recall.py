from pathlib import Path

path = Path("tools/nova_project_brain_mission_control_api_smoke.py")
text = path.read_text(encoding="utf-8")

old = '''    assert_true("direct recall not mission control", "project brain mission control" not in lower, answer)
    assert_true("direct recall has project state", "current nova project state" in lower, answer)
'''

new = '''    assert_true("direct recall not mission card title", not lower.startswith("project brain mission control:"), answer)
    assert_true("direct recall has no mission fields", "focused smoke:" not in lower and "commit rule:" not in lower, answer)
    assert_true("direct recall has project state", "current nova project state" in lower, answer)
'''

if old not in text:
    raise SystemExit("target direct-recall assertion block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched mission control api smoke direct-recall assertion")
