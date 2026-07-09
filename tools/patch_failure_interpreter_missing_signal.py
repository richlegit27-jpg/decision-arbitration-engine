from pathlib import Path

path = Path("nova_backend/services/project_brain_failure_interpreter.py")
text = path.read_text(encoding="utf-8-sig")

old = '''    if "missing=[" in lower and "includes expected signals failed" in lower:
'''

new = '''    if (
        ("missing=[" in lower and "includes expected signals failed" in lower)
        or ("answer quality smoke failed" in lower and "missing expected signals" in lower)
        or ("includes expected signals" in lower and "failed" in lower)
    ):
'''

if old not in text:
    raise SystemExit("missing-signal condition anchor not found")

text = text.replace(old, new, 1)

old_evidence = '''            evidence=_evidence_lines(combined, ["includes expected signals FAILED", "missing=[", "CASE:", "ANSWER:"]),
'''

new_evidence = '''            evidence=_evidence_lines(combined, ["includes expected signals FAILED", "missing expected signals", "missing=[", "CASE:", "ANSWER:"]),
'''

if old_evidence in text:
    text = text.replace(old_evidence, new_evidence, 1)

path.write_text(text, encoding="utf-8")
print("patched failure interpreter missing-signal classification")
