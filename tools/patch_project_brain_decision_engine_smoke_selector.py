from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_decision_engine.py")

if not TARGET.exists():
    raise SystemExit("missing decision engine service")

text = TARGET.read_text(encoding="utf-8-sig")

if "_build_decision_smoke_selection" in text:
    print("Decision Engine already uses Smoke Selector directly")
    raise SystemExit(0)

old = '''def _apply_operator_plan_to_decision(
    decision: ProjectBrainDecision,
    user_text: str = "",
) -> ProjectBrainDecision:
'''

new = '''def _build_decision_smoke_selection(
    decision: ProjectBrainDecision,
    user_text: str = "",
) -> dict:
    try:
        from nova_backend.services.project_brain_smoke_selector import (
            build_smoke_selection_dict,
        )

        return build_smoke_selection_dict(
            user_text=user_text,
            changed_files=list(decision.target_files),
            work_type=decision.intent,
        )
    except Exception:
        return {}


def _apply_operator_plan_to_decision(
    decision: ProjectBrainDecision,
    user_text: str = "",
) -> ProjectBrainDecision:
'''

if old not in text:
    raise SystemExit("could not find operator plan application function anchor")

text = text.replace(old, new)

old = '''    recommended_move = str(operator_plan.get("recommended_move") or "").strip()
    operator_why = str(operator_plan.get("why") or "").strip()
    exact_next_command = str(operator_plan.get("exact_next_command") or "").strip()
    loop_guard = str(operator_plan.get("loop_guard") or "").strip()
'''

new = '''    smoke_selection = _build_decision_smoke_selection(
        decision=decision,
        user_text=user_text,
    )

    recommended_move = str(operator_plan.get("recommended_move") or "").strip()
    operator_why = str(operator_plan.get("why") or "").strip()
    exact_next_command = str(operator_plan.get("exact_next_command") or "").strip()
    loop_guard = str(operator_plan.get("loop_guard") or "").strip()
    smoke_reason = str(smoke_selection.get("reason") or "").strip()
'''

if old not in text:
    raise SystemExit("could not find operator plan local variable anchor")

text = text.replace(old, new)

old = '''    validation = _unique_text(
        list(decision.validation)
        + list(operator_plan.get("focused_smokes", []) or [])
        + ([exact_next_command] if exact_next_command else [])
    )
'''

new = '''    validation = _unique_text(
        list(decision.validation)
        + list(smoke_selection.get("focused_smokes", []) or [])
        + list(operator_plan.get("focused_smokes", []) or [])
        + ([exact_next_command] if exact_next_command else [])
    )
'''

if old not in text:
    raise SystemExit("could not find validation merge anchor")

text = text.replace(old, new)

old = '''        f"Exact next command: {exact_next_command}" if exact_next_command else "",
        f"Ranked moves: {ranked_summary}" if ranked_summary else "",
'''

new = '''        f"Exact next command: {exact_next_command}" if exact_next_command else "",
        f"Smoke Selector reason: {smoke_reason}" if smoke_reason else "",
        f"Ranked moves: {ranked_summary}" if ranked_summary else "",
'''

if old not in text:
    raise SystemExit("could not find rationale smoke selector anchor")

text = text.replace(old, new)

TARGET.write_text(text, encoding="utf-8")

print("patched Decision Engine to use Smoke Selector directly")
