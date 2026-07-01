from pathlib import Path

service_paths = [
    Path("nova_backend/services/project_brain_decision_engine.py"),
    Path("tools/patch_project_brain_decision_engine.py"),
]

branch = '''    if _contains_any(combined, [
        "what should we do next",
        "what's next",
        "next concrete move",
        "next move",
        "what now",
        "what should we do",
    ]):
        return ProjectBrainDecision(
            intent="next_move_judgment",
            confidence=0.88,
            risk="medium",
            recommended_next_move=(
                "Use the Project Brain live answer selector as the decision gate: plain status stays "
                "on freshness context, while next-move, safety, failure, memory, and app.py risk "
                "questions use Decision Engine context."
            ),
            target_layers=[
                "live answer selector",
                "decision context",
                "decision engine",
                "smoke board",
            ],
            target_files=[
                "nova_backend/services/project_brain_live_answer_selector.py",
                "nova_backend/services/project_brain_context_builder.py",
                "nova_backend/services/project_brain_decision_engine.py",
                "tools/nova_project_brain_live_answer_selector_smoke.py",
            ],
            validation=_base_validation() + [
                "python .\\\\tools\\\\nova_project_brain_live_answer_selector_smoke.py",
                "python .\\\\tools\\\\nova_project_brain_decision_context_smoke.py",
                "python .\\\\tools\\\\nova_project_brain_decision_engine_smoke.py",
            ],
            avoid=_default_avoid() + [
                "do not wire app.py until the selector intent is precise",
                "do not classify ordinary next-move questions as intelligence upgrades",
            ],
            rationale=(
                "Next-move questions should use judgment about current project state and validation, "
                "not be mistaken for a meta request to improve Nova intelligence."
            ),
        )

'''

needle = '''    if _contains_any(combined, [
        "make nova smarter",
        "decision engine",
        "intelligence",
        "smarter",
        "judgment",
        "what should we do",
        "next move",
    ]):
'''

for path in service_paths:
    if not path.exists():
        print(f"{path}: missing, skipped")
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    if 'intent="next_move_judgment"' not in text:
        text = text.replace(needle, branch + needle)

    text = text.replace(
        '        "what should we do",\n        "next move",\n',
        ''
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: patched")
    else:
        print(f"{path}: no change")

engine_smoke = Path("tools/nova_project_brain_decision_engine_smoke.py")
text = engine_smoke.read_text(encoding="utf-8")
original = text

insert_before = '''    check_case(
        name="intelligence upgrade",
        user_text="make Nova smarter with a decision engine",
        pasted_output="",
        expected_intent="intelligence_upgrade",
        expected_terms=[
            "decision layer",
            "classify intent",
            "no app.py wiring",
        ],
    )
'''

next_case = '''    check_case(
        name="next move judgment",
        user_text="what should we do next?",
        pasted_output="",
        expected_intent="next_move_judgment",
        expected_terms=[
            "live answer selector",
            "decision gate",
            "do not classify ordinary next-move",
        ],
    )

'''

if 'name="next move judgment"' not in text:
    text = text.replace(insert_before, next_case + insert_before)

if text != original:
    engine_smoke.write_text(text, encoding="utf-8")
    print(f"{engine_smoke}: patched")
else:
    print(f"{engine_smoke}: no change")

selector_smoke = Path("tools/nova_project_brain_live_answer_selector_smoke.py")
text = selector_smoke.read_text(encoding="utf-8")
original = text

text = text.replace(
'''        expected_terms=[
            "project brain decision context",
            "intent:",
            "risk:",
            "validation:",
            "avoid:",
        ],''',
'''        expected_terms=[
            "project brain decision context",
            "intent: next_move_judgment",
            "risk:",
            "validation:",
            "avoid:",
        ],'''
)

if text != original:
    selector_smoke.write_text(text, encoding="utf-8")
    print(f"{selector_smoke}: patched")
else:
    print(f"{selector_smoke}: no change")

selector_patch = Path("tools/patch_project_brain_live_answer_selector.py")
if selector_patch.exists():
    text = selector_patch.read_text(encoding="utf-8")
    original = text
    text = text.replace(
'''        expected_terms=[
            "project brain decision context",
            "intent:",
            "risk:",
            "validation:",
            "avoid:",
        ],''',
'''        expected_terms=[
            "project brain decision context",
            "intent: next_move_judgment",
            "risk:",
            "validation:",
            "avoid:",
        ],'''
    )
    if text != original:
        selector_patch.write_text(text, encoding="utf-8")
        print(f"{selector_patch}: patched")
    else:
        print(f"{selector_patch}: no change")

print("patched next-move judgment intent precision")
