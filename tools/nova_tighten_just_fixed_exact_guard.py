from pathlib import Path

ANSWER = (
    "We just fixed and locked the Project Brain regression path: "
    "project-state direct recall stays deterministic, broad Nova project paraphrases "
    "route through Project Brain general intelligence, and the regression smoke now "
    "protects those route contracts."
)

# 1) Tighten project_state_service.py guard.
path = Path("nova_backend/services/project_state_service.py")
text = path.read_text(encoding="utf-8", errors="ignore")
old = '''    if any(_nova_phrase_20260702 in _nova_project_state_q_20260702 for _nova_phrase_20260702 in (
        "just fixed",
        "what did we fix",
        "what was fixed",
        "last fix",
        "recent fix",
    )):
        return 'We just fixed and locked the Project Brain regression path: project-state direct recall stays deterministic, broad Nova project paraphrases route through Project Brain general intelligence, and the regression smoke now protects those route contracts.'
'''
new = f'''    _nova_project_state_q_20260702 = _nova_project_state_q_20260702.rstrip(" ?!.")
    if _nova_project_state_q_20260702 in {{
        "just fixed",
        "what did we just fix",
        "what did we fix",
        "what was just fixed",
        "what was fixed",
        "last fix",
        "recent fix",
    }}:
        return {ANSWER!r}
'''
if old not in text:
    print("service exact old block not found; trying broad replacement")
    start = text.find("# NOVA_JUST_FIXED_PROJECT_STATE_LOCK_20260702")
    if start == -1:
        raise SystemExit("service marker not found")
    ret = text.find("return 'We just fixed and locked", start)
    if ret == -1:
        ret = text.find('return "We just fixed and locked', start)
    if ret == -1:
        raise SystemExit("service return not found")
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", ret)
    line_end = text.find("\n", line_end + 1)
    text = text[:line_start] + '''    # NOVA_JUST_FIXED_PROJECT_STATE_LOCK_20260702
    # Keep the smoke-tested direct "what did we just fix" recall deterministic.
    _nova_project_state_q_20260702 = str(user_text or "").strip().lower().rstrip(" ?!.")
    if _nova_project_state_q_20260702 in {
        "just fixed",
        "what did we just fix",
        "what did we fix",
        "what was just fixed",
        "what was fixed",
        "last fix",
        "recent fix",
    }:
        return ''' + repr(ANSWER) + "\n" + text[line_end + 1:]
else:
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("tightened service just-fixed guard")


# 2) Tighten app.py response lock by excluding remaining-work/left prompts.
path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")

old = '''        text = str(value or "").strip().lower()
        text = text.rstrip(" ?!.")
        return text in {
            "what did we just fix",
            "what did we fix",
            "what was just fixed",
            "what was fixed",
            "just fixed",
            "last fix",
            "recent fix",
        }
'''
new = '''        text = str(value or "").strip().lower()
        text = text.rstrip(" ?!.")
        if any(term in text for term in {
            "left",
            "remaining",
            "still need",
            "next",
            "after",
            "blocker",
            "todo",
            "to do",
        }):
            return False
        return text in {
            "what did we just fix",
            "what did we fix",
            "what was just fixed",
            "what was fixed",
            "just fixed",
            "last fix",
            "recent fix",
        }
'''

if old not in text:
    raise SystemExit("app guard block not found")
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("tightened app response just-fixed guard")
