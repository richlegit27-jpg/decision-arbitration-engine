from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8-sig")

changed = 0

mission_helper_marker = "# NOVA_PROJECT_BRAIN_MISSION_CONTROL_GENERAL_20260702"

if mission_helper_marker not in text:
    anchor = '''def _practical_project_answer() -> str:
    from nova_backend.services.project_brain_context_builder import build_practical_project_answer

    return build_practical_project_answer()
'''
    insert = anchor + '''

''' + mission_helper_marker + '''
# Service-only Mission Control answer bridge.
# No Flask wiring and no app.py dependency.
def _mission_control_answer(user_text: object) -> str:
    from nova_backend.services.project_brain_mission_control import (
        build_project_brain_mission_control_answer,
    )

    return build_project_brain_mission_control_answer(
        user_text=str(user_text or ""),
        pasted_output="",
    )
'''

    if anchor not in text:
        raise SystemExit("anchor not found for _practical_project_answer")

    text = text.replace(anchor, insert, 1)
    changed += 1
    print("patched mission control helper")

if 'return "mission_control"' not in text:
    anchor = '''    if not text:
        return None
'''
    insert = anchor + '''
    mission_terms = (
        "mission control",
        "mission card",
        "operator mode",
        "operator card",
        "mission brief",
        "mission plan",
        "give me mission",
        "show mission",
        "show me the mission",
    )

    if _has_any(text, mission_terms):
        return "mission_control"
'''

    if anchor not in text:
        raise SystemExit("anchor not found for classifier empty-text block")

    text = text.replace(anchor, insert, 1)
    changed += 1
    print("patched mission control classifier")

if 'if intent == "mission_control":' not in text:
    anchor = '''    intent = classify_project_brain_intent(user_text)

'''
    insert = anchor + '''    if intent == "mission_control":
        return ProjectBrainAnswer(intent=intent, text=_mission_control_answer(user_text))

'''

    if anchor not in text:
        raise SystemExit("anchor not found for general answer intent dispatch")

    text = text.replace(anchor, insert, 1)
    changed += 1
    print("patched mission control dispatch")

if changed == 0:
    print("mission control general intelligence wiring already present")
else:
    path.write_text(text, encoding="utf-8")
    print(f"patched project_brain_general_intelligence.py sections: {changed}")
