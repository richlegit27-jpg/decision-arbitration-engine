from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8")

old = '''def classify_project_brain_intent(user_text: object) -> Optional[str]:
    text = _lower(user_text)

    if not text:
        return None
'''

new = '''def _is_direct_project_state_recall_prompt(text: str) -> bool:
    normalized = " ".join(text.replace("?", " ").replace("!", " ").split())

    direct_prompts = {
        "what are we working on now",
        "what are we working on",
        "what are we working on right now",
    }

    return normalized in direct_prompts


def classify_project_brain_intent(user_text: object) -> Optional[str]:
    text = _lower(user_text)

    if not text:
        return None

    if _is_direct_project_state_recall_prompt(text):
        return None
'''

if old not in text:
    raise SystemExit("target block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched direct project-state recall prompt passthrough")
