from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_decision_engine.py")

if not TARGET.exists():
    raise SystemExit("missing decision engine service")

text = TARGET.read_text(encoding="utf-8-sig")

if "_apply_operator_plan_to_decision" in text:
    print("Decision Engine already uses Operator Planner")
    raise SystemExit(0)

old = "def decide_project_brain_next_move("
if old not in text:
    raise SystemExit("could not find decide_project_brain_next_move")

text = text.replace(old, "def _decide_project_brain_next_move_base(", 1)

anchor = "\ndef format_project_brain_decision(decision: ProjectBrainDecision) -> str:"
if anchor not in text:
    raise SystemExit("could not find format_project_brain_decision anchor")

wrapper = r'''

def _unique_text(values):
    result = []
    seen = set()

    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return result


def _apply_operator_plan_to_decision(
    decision: ProjectBrainDecision,
    user_text: str = "",
) -> ProjectBrainDecision:
    try:
        from nova_backend.services.project_brain_operator_planner import (
            build_operator_plan_dict,
        )

        operator_plan = build_operator_plan_dict(
            user_text=user_text,
            changed_files=list(decision.target_files),
            project_state=decision.recommended_next_move,
        )
    except Exception:
        return decision

    recommended_move = str(operator_plan.get("recommended_move") or "").strip()
    operator_why = str(operator_plan.get("why") or "").strip()
    exact_next_command = str(operator_plan.get("exact_next_command") or "").strip()
    loop_guard = str(operator_plan.get("loop_guard") or "").strip()

    ranked_moves = operator_plan.get("ranked_moves", []) or []
    rejected_moves = operator_plan.get("rejected_moves", []) or []

    ranked_summary = "; ".join(
        f"#{move.get('rank')}: {move.get('name')}"
        for move in ranked_moves
        if move.get("name")
    )

    rejected_summary = "; ".join(
        f"{move.get('name')} loses because {move.get('loses_to_best_because')}"
        for move in rejected_moves
        if move.get("name")
    )

    next_move = decision.recommended_next_move
    if recommended_move and recommended_move not in next_move:
        next_move = (
            f"{next_move} Operator Planner v2 recommends: "
            f"{recommended_move} - {operator_why}"
        ).strip()

    validation = _unique_text(
        list(decision.validation)
        + list(operator_plan.get("focused_smokes", []) or [])
        + ([exact_next_command] if exact_next_command else [])
    )

    avoid = _unique_text(
        list(decision.avoid)
        + list(operator_plan.get("avoid_rules", []) or [])
        + ([f"Operator loop guard: {loop_guard}"] if loop_guard else [])
    )

    target_layers = _unique_text(
        list(decision.target_layers)
        + [
            "operator planner",
            "smoke selector",
            "cleanup strategy",
        ]
    )

    target_files = _unique_text(
        list(decision.target_files)
        + list(operator_plan.get("target_files", []) or [])
    )

    rationale_parts = [
        decision.rationale,
        f"Operator Planner v2 selected {recommended_move}." if recommended_move else "",
        f"Exact next command: {exact_next_command}" if exact_next_command else "",
        f"Ranked moves: {ranked_summary}" if ranked_summary else "",
        f"Rejected moves: {rejected_summary}" if rejected_summary else "",
        f"Loop guard: {loop_guard}" if loop_guard else "",
    ]

    rationale = " ".join(part for part in rationale_parts if part).strip()

    return ProjectBrainDecision(
        intent=decision.intent,
        confidence=decision.confidence,
        risk=decision.risk,
        recommended_next_move=next_move,
        target_layers=target_layers,
        target_files=target_files,
        validation=validation,
        avoid=avoid,
        rationale=rationale,
    )


def decide_project_brain_next_move(
    user_text: str = "",
    pasted_output: str = "",
) -> ProjectBrainDecision:
    decision = _decide_project_brain_next_move_base(
        user_text=user_text,
        pasted_output=pasted_output,
    )

    return _apply_operator_plan_to_decision(
        decision,
        user_text=user_text,
    )
'''

text = text.replace(anchor, wrapper + anchor)

TARGET.write_text(text, encoding="utf-8")

print("patched Decision Engine to use Operator Planner v2")
