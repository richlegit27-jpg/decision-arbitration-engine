from pathlib import Path

path = Path("tools/nova_answer_quality_smoke.py")
text = path.read_text(encoding="utf-8")

replacements = {
    '''            "Project Brain",
            "answer freshness",
            "fallback",
            "context-builder",
            "freshness snapshot",
''': '''            "Project Brain",
            "Decision Engine v1",
            "No active Decision Engine blocker",
            "cleanup/consolidation",
            "move intelligence into services",
''',

    '''            "freshness snapshot",
            "context builder",
            "source of truth",
            "safe move",
''': '''            "Decision Engine v1",
            "Project Brain cleanup/consolidation",
            "direct recall",
            "broad Project Brain routing",
            "avoiding another app.py guard",
''',
}

changed = 0
for old, new in replacements.items():
    count = text.count(old)
    if count:
        text = text.replace(old, new)
        changed += count
        print(f"patched answer-quality block: {count}")

if changed == 0:
    raise SystemExit("no answer-quality contract blocks patched; inspect tools/nova_answer_quality_smoke.py")

path.write_text(text, encoding="utf-8")
print(f"patched answer-quality contract blocks: {changed}")
