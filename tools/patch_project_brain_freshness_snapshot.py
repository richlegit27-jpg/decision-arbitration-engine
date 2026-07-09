from pathlib import Path

path = Path("nova_backend/services/project_brain_context_builder.py")
text = path.read_text(encoding="utf-8")

start = text.index("def build_project_brain_context() -> ProjectBrainContext:")
end = text.index("\n\ndef _completed_text", start)

new_func = '''def build_project_brain_context() -> ProjectBrainContext:
    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )

    snapshot = build_project_brain_freshness_snapshot()

    return ProjectBrainContext(
        project_name="Nova",
        local_app="local Nova Flask app",
        completed=snapshot.completed,
        active_checkpoint=snapshot.checkpoint,
        blocker=snapshot.blocker,
        next_move=snapshot.next_move,
        validation=snapshot.validation,
        recent_commits=snapshot.recent_commits,
    )
'''

text = text[:start] + new_func + text[end:]
path.write_text(text, encoding="utf-8")
print("wired Project Brain context builder to freshness snapshot")
