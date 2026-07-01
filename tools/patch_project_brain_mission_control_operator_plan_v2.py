from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_mission_control.py")

if not TARGET.exists():
    raise SystemExit("missing mission control service")

text = TARGET.read_text(encoding="utf-8-sig")

if "Operator exact next command:" in text:
    print("Mission Control already displays Operator Plan v2 fields")
    raise SystemExit(0)

old = '''    operator_target_files = ", ".join(operator_plan.get("target_files", []) or [])
    operator_smokes = "; ".join(operator_plan.get("focused_smokes", []) or [])
    operator_avoid = "; ".join(operator_plan.get("avoid_rules", []) or [])
'''

new = '''    operator_target_files = ", ".join(operator_plan.get("target_files", []) or [])
    operator_smokes = "; ".join(operator_plan.get("focused_smokes", []) or [])
    operator_avoid = "; ".join(operator_plan.get("avoid_rules", []) or [])
    operator_ranked_moves = "; ".join(
        f"#{move.get('rank')}: {move.get('name')}"
        for move in (operator_plan.get("ranked_moves", []) or [])
    )
    operator_rejected_moves = "; ".join(
        f"{move.get('name')} loses because {move.get('loses_to_best_because')}"
        for move in (operator_plan.get("rejected_moves", []) or [])
    )
'''

if old not in text:
    raise SystemExit("could not find operator plan local variable block")

text = text.replace(old, new)

old = '''        f"Operator focused smokes: {operator_smokes}\\n"
        f"Operator avoid rules: {operator_avoid}\\n"
        f"Operator stop rule: {operator_plan.get('stop_rule', '')}"
'''

new = '''        f"Operator focused smokes: {operator_smokes}\\n"
        f"Operator avoid rules: {operator_avoid}\\n"
        f"Operator exact next command: {operator_plan.get('exact_next_command', '')}\\n"
        f"Operator ranked moves: {operator_ranked_moves}\\n"
        f"Operator rejected moves: {operator_rejected_moves}\\n"
        f"Operator stop rule: {operator_plan.get('stop_rule', '')}\\n"
        f"Operator loop guard: {operator_plan.get('loop_guard', '')}"
'''

if old not in text:
    raise SystemExit("could not find operator plan output block")

text = text.replace(old, new)

TARGET.write_text(text, encoding="utf-8")

print("patched Mission Control to display Operator Plan v2 fields")
