from pathlib import Path


TARGET = Path("tools/nova_project_brain_route_patch_audit_smoke.py")

if not TARGET.exists():
    raise SystemExit("missing route patch audit smoke")

text = TARGET.read_text(encoding="utf-8-sig")

if "stale decision log keyword helper removed" in text.lower():
    print("audit already protects stale Decision Log helper removal")
    raise SystemExit(0)

needle = 'assert_true("decision log service exists",'
insert = '''    assert_true(
        "stale decision log keyword helper removed",
        "NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_KEYWORDS_20260701" not in read_text(APP),
    )

'''

index = text.find(needle)
if index < 0:
    raise SystemExit("could not find insertion anchor in audit smoke")

text = text[:index] + insert + text[index:]

TARGET.write_text(text, encoding="utf-8")

print("patched route patch audit smoke to protect stale Decision Log helper removal")
