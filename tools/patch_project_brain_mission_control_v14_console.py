from pathlib import Path
import re


TARGET = Path("nova_backend/services/project_brain_mission_control.py")

if not TARGET.exists():
    raise SystemExit("missing mission control service")

text = TARGET.read_text(encoding="utf-8-sig")

if "Mission Control v1.4 Operator Console" in text:
    print("Mission Control already has v1.4 console formatter")
    raise SystemExit(0)

pattern = re.compile(
    r"\n\ndef format_project_brain_mission_card\(card: ProjectBrainMissionCard\) -> str:"
    r".*?"
    r"\n\ndef build_project_brain_mission_control_answer\(",
    re.DOTALL,
)

match = pattern.search(text)
if not match:
    raise SystemExit("could not isolate format_project_brain_mission_card function")

replacement = r'''

def _join_nonempty(values: list[str] | tuple[str, ...] | None, separator: str = ", ") -> str:
    result = []

    for value in values or []:
        text = str(value or "").strip()
        if text:
            result.append(text)

    return separator.join(result)


def _operator_plan_summary(operator_plan: dict[str, Any]) -> dict[str, str]:
    plan = operator_plan or {}

    ranked_moves = "; ".join(
        f"#{move.get('rank')}: {move.get('name')}"
        for move in (plan.get("ranked_moves", []) or [])
        if move.get("name")
    )

    rejected_moves = "; ".join(
        f"{move.get('name')} loses because {move.get('loses_to_best_because')}"
        for move in (plan.get("rejected_moves", []) or [])
        if move.get("name")
    )

    return {
        "recommended_move": str(plan.get("recommended_move") or "").strip(),
        "why": str(plan.get("why") or "").strip(),
        "work_type": str(plan.get("work_type") or "").strip(),
        "risk": str(plan.get("risk") or "").strip(),
        "target_files": _join_nonempty(plan.get("target_files", []) or []),
        "focused_smokes": _join_nonempty(plan.get("focused_smokes", []) or [], "; "),
        "avoid_rules": _join_nonempty(plan.get("avoid_rules", []) or [], "; "),
        "exact_next_command": str(plan.get("exact_next_command") or "").strip(),
        "ranked_moves": ranked_moves,
        "rejected_moves": rejected_moves,
        "stop_rule": str(plan.get("stop_rule") or "").strip(),
        "loop_guard": str(plan.get("loop_guard") or "").strip(),
    }


def format_project_brain_mission_card(card: ProjectBrainMissionCard) -> str:
    """Mission Control v1.4 Operator Console formatter.

    Keeps the legacy smoke-contract labels while moving the most useful operator
    fields near the top.
    """

    target_layers = _join_nonempty(card.target_layers)
    target_files = _join_nonempty(card.target_files)
    validation = _join_nonempty(card.validation, "; ")
    avoid = _join_nonempty(card.avoid, "; ")
    failure_evidence = _join_nonempty(card.failure_evidence, "; ") or "none"
    operator = _operator_plan_summary(card.operator_plan)

    return (
        "Project Brain Mission Control:\n"
        "Mission Control v1.4 Operator Console\n"
        f"State: {card.current_state}\n"
        f"Blocker/Risk: {card.current_blocker}\n"
        f"Best Move: {operator.get('recommended_move') or card.recommended_move}\n"
        f"Why: {operator.get('why') or card.rationale}\n"
        f"Exact Next Command: {operator.get('exact_next_command') or card.focused_smoke}\n"
        f"Focused Smokes: {operator.get('focused_smokes') or card.focused_smoke}\n"
        f"Stop Rule: {operator.get('stop_rule')}\n"
        f"Loop Guard: {operator.get('loop_guard')}\n"
        "\n"
        "Legacy Contract:\n"
        f"Current state: {card.current_state}\n"
        f"Current blocker/risk: {card.current_blocker}\n"
        f"Intent: {card.intent}\n"
        f"Risk: {card.risk}\n"
        f"Confidence: {card.confidence:.2f}\n"
        f"Recommended move: {card.recommended_move}\n"
        f"Target layers: {target_layers}\n"
        f"Target files: {target_files}\n"
        f"Focused smoke: {card.focused_smoke}\n"
        f"Validation: {validation}\n"
        f"Avoid: {avoid}\n"
        f"Commit rule: {card.commit_rule}\n"
        f"Failure type: {card.failure_type}\n"
        f"Failure severity: {card.failure_severity}\n"
        f"Failure patch target: {card.failure_patch_target}\n"
        f"Failure next command: {card.failure_next_command}\n"
        f"Failure evidence: {failure_evidence}\n"
        f"Rationale: {card.rationale}\n"
        "Operator Plan:\n"
        f"Operator recommended move: {operator.get('recommended_move')}\n"
        f"Operator why: {operator.get('why')}\n"
        f"Operator work type: {operator.get('work_type')}\n"
        f"Operator risk: {operator.get('risk')}\n"
        f"Operator target files: {operator.get('target_files')}\n"
        f"Operator focused smokes: {operator.get('focused_smokes')}\n"
        f"Operator avoid rules: {operator.get('avoid_rules')}\n"
        f"Operator exact next command: {operator.get('exact_next_command')}\n"
        f"Operator ranked moves: {operator.get('ranked_moves')}\n"
        f"Operator rejected moves: {operator.get('rejected_moves')}\n"
        f"Operator stop rule: {operator.get('stop_rule')}\n"
        f"Operator loop guard: {operator.get('loop_guard')}"
    )


def build_project_brain_mission_control_answer('''

new_text = text[:match.start()] + replacement + text[match.end():]
TARGET.write_text(new_text, encoding="utf-8")

print("patched Mission Control v1.4 Operator Console formatter")
