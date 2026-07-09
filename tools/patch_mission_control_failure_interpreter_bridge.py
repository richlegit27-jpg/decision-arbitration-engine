from pathlib import Path

path = Path("nova_backend/services/project_brain_mission_control.py")
text = path.read_text(encoding="utf-8-sig")

changed = 0

old_fields = '''    commit_rule: str
    rationale: str
'''

new_fields = '''    commit_rule: str
    rationale: str
    failure_type: str
    failure_severity: str
    failure_patch_target: str
    failure_next_command: str
    failure_evidence: list[str]
'''

if old_fields in text and new_fields not in text:
    text = text.replace(old_fields, new_fields, 1)
    changed += 1
    print("patched mission card failure fields")

old_import_block = '''    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )

    snapshot = build_project_brain_freshness_snapshot()
    decision = decide_project_brain_next_move(
'''

new_import_block = '''    from nova_backend.services.project_brain_freshness_snapshot import (
        build_project_brain_freshness_snapshot,
    )
    from nova_backend.services.project_brain_failure_interpreter import (
        interpret_project_brain_failure,
    )

    snapshot = build_project_brain_freshness_snapshot()
    decision = decide_project_brain_next_move(
'''

if old_import_block in text and new_import_block not in text:
    text = text.replace(old_import_block, new_import_block, 1)
    changed += 1
    print("patched failure interpreter import")

old_decision_block = '''    decision = decide_project_brain_next_move(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    return ProjectBrainMissionCard(
'''

new_decision_block = '''    decision = decide_project_brain_next_move(
        user_text=user_text,
        pasted_output=pasted_output,
    )
    failure = interpret_project_brain_failure(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    return ProjectBrainMissionCard(
'''

if old_decision_block in text and new_decision_block not in text:
    text = text.replace(old_decision_block, new_decision_block, 1)
    changed += 1
    print("patched failure interpretation call")

old_constructor_tail = '''        commit_rule="Do not commit until py_compile and the focused smoke pass; then check git status --short.",
        rationale=decision.rationale,
    )
'''

new_constructor_tail = '''        commit_rule="Do not commit until py_compile and the focused smoke pass; then check git status --short.",
        rationale=decision.rationale,
        failure_type=failure.failure_type,
        failure_severity=failure.severity,
        failure_patch_target=failure.patch_target,
        failure_next_command=failure.next_command,
        failure_evidence=list(failure.evidence),
    )
'''

if old_constructor_tail in text and new_constructor_tail not in text:
    text = text.replace(old_constructor_tail, new_constructor_tail, 1)
    changed += 1
    print("patched mission card failure constructor fields")

old_format_vars = '''    target_layers = ", ".join(card.target_layers)
    target_files = ", ".join(card.target_files)
    avoid = "; ".join(card.avoid)

    return (
'''

new_format_vars = '''    target_layers = ", ".join(card.target_layers)
    target_files = ", ".join(card.target_files)
    avoid = "; ".join(card.avoid)
    failure_evidence = "; ".join(card.failure_evidence) if card.failure_evidence else "none"

    return (
'''

if old_format_vars in text and new_format_vars not in text:
    text = text.replace(old_format_vars, new_format_vars, 1)
    changed += 1
    print("patched format failure vars")

old_format_tail = '''        f"Commit rule: {card.commit_rule}\\n"
        f"Rationale: {card.rationale}"
    )
'''

new_format_tail = '''        f"Commit rule: {card.commit_rule}\\n"
        f"Failure type: {card.failure_type}\\n"
        f"Failure severity: {card.failure_severity}\\n"
        f"Failure patch target: {card.failure_patch_target}\\n"
        f"Failure next command: {card.failure_next_command}\\n"
        f"Failure evidence: {failure_evidence}\\n"
        f"Rationale: {card.rationale}"
    )
'''

if old_format_tail in text and new_format_tail not in text:
    text = text.replace(old_format_tail, new_format_tail, 1)
    changed += 1
    print("patched format failure output")

if changed == 0:
    raise SystemExit("no Mission Control failure interpreter sections patched")

path.write_text(text, encoding="utf-8")
print(f"patched Mission Control failure interpreter sections: {changed}")
