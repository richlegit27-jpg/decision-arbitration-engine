from pathlib import Path

decision_path = Path("nova_backend/services/project_brain_decision_engine.py")
decision_text = decision_path.read_text(encoding="utf-8-sig")

changed = 0

if 'intent="mission_control"' not in decision_text:
    anchor = '    combined = f"{user}\\n{output}"\n\n'
    insert = anchor + '''    if _contains_any(combined, [
        "mission control",
        "mission card",
        "operator mode",
        "operator card",
        "mission brief",
        "mission plan",
        "give me mission",
        "show mission",
        "show me the mission",
    ]):
        return ProjectBrainDecision(
            intent="mission_control",
            confidence=0.93,
            risk="low",
            recommended_next_move=(
                "Use Project Brain Mission Control as the operator card: summarize current state, "
                "classify the request, choose the focused smoke, list target files, and preserve "
                "avoid-rules before any commit."
            ),
            target_layers=[
                "mission control service",
                "general intelligence bridge",
                "api contract smoke",
            ],
            target_files=[
                "nova_backend/services/project_brain_mission_control.py",
                "nova_backend/services/project_brain_general_intelligence.py",
                "tools/nova_project_brain_mission_control_smoke.py",
                "tools/nova_project_brain_mission_control_general_smoke.py",
                "tools/nova_project_brain_mission_control_api_smoke.py",
            ],
            validation=_base_validation() + [
                "python .\\\\tools\\\\nova_project_brain_mission_control_smoke.py",
                "python .\\\\tools\\\\nova_project_brain_mission_control_general_smoke.py",
                "python .\\\\tools\\\\nova_project_brain_mission_control_api_smoke.py",
                "python .\\\\tools\\\\nova_regression_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not route explicit operator requests to general_project_answer",
                "do not add app.py wiring for Mission Control",
            ],
            rationale=(
                "Explicit operator requests should return the Mission Control card itself, not the "
                "generic Project Brain answer intent."
            ),
        )

'''

    if anchor not in decision_text:
        raise SystemExit("decision engine combined anchor not found")

    decision_text = decision_text.replace(anchor, insert, 1)
    decision_path.write_text(decision_text, encoding="utf-8")
    changed += 1
    print("patched decision engine mission_control intent")

service_smoke_path = Path("tools/nova_project_brain_mission_control_smoke.py")
service_smoke = service_smoke_path.read_text(encoding="utf-8")

if 'name="explicit mission control"' not in service_smoke:
    anchor = '''    run_case(
        name="next move mission",
'''
    insert = '''    run_case(
        name="explicit mission control",
        user_text="give me mission control",
        pasted_output="",
        expected_intent="mission_control",
        expected_terms=[
            "Decision Engine v1",
            "Project Brain Mission Control",
            "mission_control",
            "focused smoke",
            "do not commit",
        ],
    )

''' + anchor

    if anchor not in service_smoke:
        raise SystemExit("mission control service smoke insertion anchor not found")

    service_smoke = service_smoke.replace(anchor, insert, 1)
    service_smoke_path.write_text(service_smoke, encoding="utf-8")
    changed += 1
    print("patched service smoke explicit mission_control case")

general_smoke_path = Path("tools/nova_project_brain_mission_control_general_smoke.py")
general_smoke = general_smoke_path.read_text(encoding="utf-8")

old_general = '    assert_true(f"{question} intent field", "intent:" in lower, text)\n'
new_general = old_general + '    assert_true(f"{question} mission control intent", "intent: mission_control" in lower, text)\n'

if "mission control intent" not in general_smoke:
    if old_general not in general_smoke:
        raise SystemExit("general smoke intent assertion anchor not found")
    general_smoke = general_smoke.replace(old_general, new_general, 1)
    general_smoke_path.write_text(general_smoke, encoding="utf-8")
    changed += 1
    print("patched general smoke mission_control intent assertion")

api_smoke_path = Path("tools/nova_project_brain_mission_control_api_smoke.py")
api_smoke = api_smoke_path.read_text(encoding="utf-8")

old_api = '    assert_true(f"{question} intent", "intent:" in lower, answer)\n'
new_api = old_api + '    assert_true(f"{question} mission control intent", "intent: mission_control" in lower, answer)\n'

if "mission control intent" not in api_smoke:
    if old_api not in api_smoke:
        raise SystemExit("api smoke intent assertion anchor not found")
    api_smoke = api_smoke.replace(old_api, new_api, 1)
    api_smoke_path.write_text(api_smoke, encoding="utf-8")
    changed += 1
    print("patched api smoke mission_control intent assertion")

if changed == 0:
    print("mission_control v1.1 patches already present")
else:
    print(f"patched mission_control v1.1 sections: {changed}")
