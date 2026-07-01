from pathlib import Path

path = Path("nova_backend/services/project_brain_freshness_snapshot.py")
text = path.read_text(encoding="utf-8")

needle = "    return ProjectBrainFreshnessSnapshot(\n"

insert = '''    from nova_backend.services.project_brain_current_state_adapter import (
        build_project_brain_current_state,
    )

    current_state = build_project_brain_current_state(
        default_checkpoint=checkpoint,
        default_blocker=blocker,
        default_next_move=next_move,
    )

    checkpoint = current_state.checkpoint
    blocker = current_state.blocker
    next_move = current_state.next_move

'''

if needle not in text:
    raise SystemExit("snapshot return target not found")

text = text.replace(needle, insert + needle, 1)
path.write_text(text, encoding="utf-8")
print("wired freshness snapshot to current-state adapter")
