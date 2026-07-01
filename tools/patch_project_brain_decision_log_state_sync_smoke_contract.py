from pathlib import Path

path = Path("tools/nova_project_brain_decision_log_state_sync_smoke.py")

text = path.read_text(encoding="utf-8-sig")

old = 'assert_true("mission control includes recent-change route", "recent-change prompts route to decision log" in blob, answer)'
new = 'assert_true("mission control includes decision log api route", "decision log api route" in blob, answer)'

if old not in text:
    raise SystemExit("target smoke assertion not found")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("patched Decision Log state-sync smoke contract")
