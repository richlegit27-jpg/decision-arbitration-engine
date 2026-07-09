from pathlib import Path

path = Path("nova_backend/services/project_brain_context_builder.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    '''    blocker = (
        "The current blocker is answer freshness: project-brain answers are still partly "
        "static, so they can say yesterday's blocker even after the route and classifier "
        "smokes are green."
    )
''',
    '''    blocker = (
        "The current blocker is Project Brain answer freshness: fallback-route priority is protected, "
        "but project-brain answers can still become stale if status, blocker, next move, and validation "
        "text are repeated as hardcoded paragraphs instead of built from one context source."
    )
''',
)

text = text.replace(
    '''    next_move = (
        "Move project-brain answer text into a context builder so status, blocker, next move, "
        "and validation guidance come from one reusable source instead of repeated hardcoded paragraphs."
    )
''',
    '''    next_move = (
        "Move Project Brain answer text into the context builder so status, blocker, next move, "
        "fallback priority notes, and validation guidance come from one reusable source instead of "
        "repeated hardcoded paragraphs."
    )
''',
)

text = text.replace(
    '''        "Then check `git status --short` and commit the clean patch."
''',
    '''        "Then check `git status --short` and commit only after the board is green."
''',
)

text = text.replace(
    '''        f"Next concrete move: {context.next_move} "
''',
    '''        f"Next concrete move: {context.next_move} "
''',
)

path.write_text(text, encoding="utf-8")
print("patched Project Brain context builder smoke terms")
