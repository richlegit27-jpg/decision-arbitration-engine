from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_mission_control.py")

if not TARGET.exists():
    raise SystemExit("missing mission control service")

text = TARGET.read_text(encoding="utf-8-sig")

if "operator_plan:" in text:
    print("Mission Control already has operator plan wiring")
    raise SystemExit(0)

text = text.replace(
    "    failure_next_command: str\n    failure_evidence: list[str]\n",
    "    failure_next_command: str\n    failure_evidence: list[str]\n    operator_plan: dict[str, Any]\n",
)

text = text.replace(
    "    from nova_backend.services.project_brain_failure_interpreter import (\n        interpret_project_brain_failure,\n    )\n",
    "    from nova_backend.services.project_brain_failure_interpreter import (\n        interpret_project_brain_failure,\n    )\n    from nova_backend.services.project_brain_operator_planner import (\n        build_operator_plan_dict,\n    )\n",
)

text = text.replace(
    "    failure = interpret_project_brain_failure(\n        user_text=user_text,\n        pasted_output=pasted_output,\n    )\n\n    return ProjectBrainMissionCard(\n",
    "    failure = interpret_project_brain_failure(\n        user_text=user_text,\n        pasted_output=pasted_output,\n    )\n    operator_plan = build_operator_plan_dict(\n        user_text=user_text,\n        changed_files=list(decision.target_files),\n        project_state=str(snapshot.checkpoint or \"\"),\n    )\n\n    return ProjectBrainMissionCard(\n",
)

text = text.replace(
    "        failure_next_command=failure.next_command,\n        failure_evidence=list(failure.evidence),\n    )\n",
    "        failure_next_command=failure.next_command,\n        failure_evidence=list(failure.evidence),\n        operator_plan=operator_plan,\n    )\n",
)

text = text.replace(
    "    failure_evidence = \"; \".join(card.failure_evidence) if card.failure_evidence else \"none\"\n\n    return (\n",
    "    failure_evidence = \"; \".join(card.failure_evidence) if card.failure_evidence else \"none\"\n    operator_plan = card.operator_plan or {}\n    operator_target_files = \", \".join(operator_plan.get(\"target_files\", []) or [])\n    operator_smokes = \"; \".join(operator_plan.get(\"focused_smokes\", []) or [])\n    operator_avoid = \"; \".join(operator_plan.get(\"avoid_rules\", []) or [])\n\n    return (\n",
)

text = text.replace(
    "        f\"Failure evidence: {failure_evidence}\\n\"\n        f\"Rationale: {card.rationale}\"\n",
    "        f\"Failure evidence: {failure_evidence}\\n\"\n        f\"Rationale: {card.rationale}\\n\"\n        \"Operator Plan:\\n\"\n        f\"Operator recommended move: {operator_plan.get('recommended_move', '')}\\n\"\n        f\"Operator why: {operator_plan.get('why', '')}\\n\"\n        f\"Operator work type: {operator_plan.get('work_type', '')}\\n\"\n        f\"Operator risk: {operator_plan.get('risk', '')}\\n\"\n        f\"Operator target files: {operator_target_files}\\n\"\n        f\"Operator focused smokes: {operator_smokes}\\n\"\n        f\"Operator avoid rules: {operator_avoid}\\n\"\n        f\"Operator stop rule: {operator_plan.get('stop_rule', '')}\"\n",
)

TARGET.write_text(text, encoding="utf-8")

print("wired Operator Planner into Mission Control")
