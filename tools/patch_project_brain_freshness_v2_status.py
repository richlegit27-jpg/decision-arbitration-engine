from pathlib import Path

path = Path("nova_backend/services/project_brain_context_builder.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    '''    blocker = (
        "The current blocker is Project Brain answer freshness: fallback-route priority is protected, "
        "but project-brain answers can still become stale if status, blocker, next move, and validation "
        "text are repeated as hardcoded paragraphs instead of built from one context source."
    )
''',
    '''    blocker = (
        "The current blocker is Project Brain freshness v2: the context-builder path is protected, "
        "but the builder still needs a cleaner source-of-truth model so checkpoint, blocker, next move, "
        "recent commits, and validation state can update without another wording patch."
    )
''',
)

text = text.replace(
    '''    next_move = (
        "Move Project Brain answer text into the context builder so status, blocker, next move, "
        "fallback priority notes, and validation guidance come from one reusable source instead of "
        "repeated hardcoded paragraphs."
    )
''',
    '''    next_move = (
        "Add a Project Brain freshness snapshot so the context builder can report current checkpoint, "
        "blocker, next move, latest commits, and available smoke files from one structured source."
    )
''',
)

path.write_text(text, encoding="utf-8")
print("advanced Project Brain context builder to freshness v2")
