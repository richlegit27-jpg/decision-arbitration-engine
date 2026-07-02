
from __future__ import annotations

from dataclasses import dataclass

from nova_backend.services.project_brain_auto_debug_brain import (
    AutoDebugReport,
    classify_traceback,
)
from nova_backend.services.project_brain_smoke_selector import select_smokes


@dataclass(frozen=True)
class PatchPlan:
    title: str
    failure_type: str
    target_file: str
    broken_symbol: str
    patch_move: str
    guardrails: tuple[str, ...]
    focused_smokes: tuple[str, ...]
    stop_rule: str
    risk: str
    evidence: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "failure_type": self.failure_type,
            "target_file": self.target_file,
            "broken_symbol": self.broken_symbol,
            "patch_move": self.patch_move,
            "guardrails": list(self.guardrails),
            "focused_smokes": list(self.focused_smokes),
            "stop_rule": self.stop_rule,
            "risk": self.risk,
            "evidence": self.evidence,
        }


def _report_from_input(pasted_output: str = "", report: AutoDebugReport | None = None) -> AutoDebugReport:
    if report is not None:
        return report
    return classify_traceback(pasted_output)


def _patch_move_for_failure(report: AutoDebugReport) -> str:
    if report.failure_type == "signature_mismatch":
        return "Patch the active wrapper/function signature to accept the caller keyword and forward safely."

    if report.failure_type == "missing_keyword_only_argument":
        return "Forward the missing keyword-only argument with a safe default at the service boundary."

    if report.failure_type == "keyword_only_called_positionally":
        return "Convert the helper call to explicit keyword arguments."

    if report.failure_type == "shape_mismatch":
        return "Add a dict/object-safe accessor before reading fields from returned moves."

    if report.failure_type == "route_contract_failure":
        return "Patch the service-level route gate/classifier, then prove the API route contract."

    if report.failure_type == "syntax_error":
        return "Fix syntax first and run py_compile before behavior smokes."

    return "Patch the smallest failing service layer shown by the final traceback frame."


def _guardrails_for_report(report: AutoDebugReport) -> tuple[str, ...]:
    guardrails = [
        "Do not add a new app.py route guard unless the failing layer is explicitly api_route_gate.",
        "Keep the patch service-level and focused on the failing symbol.",
        "Run the smallest focused smoke before regression.",
    ]

    if report.target_file == "app.py" or report.failing_layer == "api_route_gate":
        guardrails[0] = "Route-risk patch allowed only if the API smoke proves the protected route contract."

    return tuple(guardrails)


def build_patch_plan(
    pasted_output: str = "",
    report: AutoDebugReport | None = None,
    changed_files=None,
    user_intent: str = "",
    route_risk: str = "",
) -> PatchPlan:
    debug_report = _report_from_input(pasted_output=pasted_output, report=report)

    files = list(changed_files or [])
    if debug_report.target_file and debug_report.target_file not in files:
        files.insert(0, debug_report.target_file)

    smoke_selection = select_smokes(
        changed_files=files,
        failure_type=debug_report.failure_type,
        failing_layer=debug_report.failing_layer,
        user_intent=user_intent or debug_report.failing_layer,
        route_risk=route_risk or debug_report.risk,
    )

    return PatchPlan(
        title="Project Brain Patch Planner v1",
        failure_type=debug_report.failure_type,
        target_file=debug_report.target_file,
        broken_symbol=debug_report.broken_symbol,
        patch_move=_patch_move_for_failure(debug_report),
        guardrails=_guardrails_for_report(debug_report),
        focused_smokes=tuple(smoke_selection.focused_smokes),
        stop_rule=smoke_selection.stop_rule,
        risk=smoke_selection.risk,
        evidence=debug_report.evidence,
    )


def build_patch_plan_dict(
    pasted_output: str = "",
    changed_files=None,
    user_intent: str = "",
    route_risk: str = "",
) -> dict:
    return build_patch_plan(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_intent=user_intent,
        route_risk=route_risk,
    ).as_dict()


def build_patch_planner_answer(
    pasted_output: str = "",
    changed_files=None,
    user_intent: str = "",
    route_risk: str = "",
) -> str:
    plan = build_patch_plan(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_intent=user_intent,
        route_risk=route_risk,
    )

    return "\n".join([
        "Project Brain Patch Planner:",
        f"Failure Type: {plan.failure_type}",
        f"Target File: {plan.target_file}",
        f"Broken Symbol: {plan.broken_symbol}",
        f"Patch Move: {plan.patch_move}",
        "Guardrails:",
        *[f"- {item}" for item in plan.guardrails],
        "Focused Smokes:",
        *[f"- {item}" for item in plan.focused_smokes],
        f"Stop Rule: {plan.stop_rule}",
        f"Risk: {plan.risk}",
        f"Evidence: {plan.evidence}",
    ])
