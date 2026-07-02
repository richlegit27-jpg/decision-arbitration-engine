from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SmokeSelection:
    work_type: str
    changed_files: list[str]
    focused_smokes: list[str]
    reason: str
    run_regression: bool
    run_api_smoke: bool
    stop_rule: str


DEFAULT_STOP_RULE = (
    "Run only the selected focused smokes. Add regression only when route/API behavior changed."
)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_files(changed_files: list[str] | None = None) -> list[str]:
    result = []
    seen = set()

    for file in changed_files or []:
        text = str(file or "").strip().replace("/", "\\")
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return result


def classify_smoke_work_type(
    user_text: str = "",
    changed_files: list[str] | None = None,
) -> str:
    text = normalize_text(user_text)
    files = normalize_files(changed_files)
    joined = " ".join(files).lower()

    if any(token in text for token in ("fail", "failed", "traceback", "broken", "assertionerror")):
        return "failure_repair"

    if "app.py" in joined:
        return "route_cleanup"

    if any(token in joined for token in ("mission_control", "general_intelligence", "decision_log_route_contract")):
        return "mission_control_api"

    if "decision_engine" in joined:
        return "decision_engine"

    if "operator_planner" in joined:
        return "operator_planner"

    if "smoke_selector" in joined:
        return "smoke_selector"

    if any(token in text for token in ("app.py", "route", "guard", "cleanup", "extract")):
        return "route_cleanup"

    if any(token in text for token in ("operator", "planner", "next move", "gangster", "endgame")):
        return "operator_planner"

    if any(token in text for token in ("decision", "judgment", "what should we do")):
        return "decision_engine"

    return "service_only"


def select_focused_smokes(
    work_type: str = "",
    changed_files: list[str] | None = None,
) -> list[str]:
    kind = normalize_text(work_type) or classify_smoke_work_type(changed_files=changed_files)
    files = normalize_files(changed_files)
    joined = " ".join(files).lower()

    if kind == "failure_repair":
        return [
            "python .\\tools\\nova_project_brain_failure_interpreter_api_smoke.py",
            "python .\\tools\\nova_regression_smoke.py",
        ]

    if kind == "route_cleanup":
        return [
            "python .\\tools\\nova_project_brain_route_patch_audit_smoke.py",
            "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
            "python .\\tools\\nova_regression_smoke.py",
        ]

    if kind == "mission_control_api":
        return [
            "python .\\tools\\nova_project_brain_mission_control_operator_plan_smoke.py",
            "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
            "python .\\tools\\nova_regression_smoke.py",
        ]

    if kind == "decision_engine":
        return [
            "python .\\tools\\nova_project_brain_decision_engine_operator_planner_smoke.py",
            "python .\\tools\\nova_project_brain_decision_engine_smoke.py",
        ]

    if kind == "operator_planner":
        return [
            "python .\\tools\\nova_project_brain_operator_planner_smoke.py",
        ]

    if kind == "smoke_selector":
        return [
            "python .\\tools\\nova_project_brain_smoke_selector_smoke.py",
        ]

    if "mission_control" in joined:
        return [
            "python .\\tools\\nova_project_brain_mission_control_operator_plan_smoke.py",
            "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
        ]

    return [
        "python -m py_compile <changed python files>",
    ]


def build_smoke_selection(
    user_text: str = "",
    changed_files: list[str] | None = None,
    work_type: str = "",
) -> SmokeSelection:
    files = normalize_files(changed_files)
    kind = normalize_text(work_type) or classify_smoke_work_type(
        user_text=user_text,
        changed_files=files,
    )
    smokes = select_focused_smokes(kind, files)

    run_regression = any("nova_regression_smoke.py" in smoke for smoke in smokes)
    run_api_smoke = any("_api_smoke.py" in smoke for smoke in smokes)

    if kind == "route_cleanup":
        reason = "app.py or route cleanup can steal priority, so use audit + API + regression."
    elif kind == "mission_control_api":
        reason = "Mission Control output changed, so use service smoke + live API smoke + regression."
    elif kind == "decision_engine":
        reason = "Decision Engine changed, so use decision-engine focused smokes before broader route checks."
    elif kind == "operator_planner":
        reason = "Operator Planner changed, so the planner smoke is the smallest useful contract."
    elif kind == "failure_repair":
        reason = "A failure repair must reproduce the failure and keep regression green."
    elif kind == "smoke_selector":
        reason = "Smoke Selector changed, so validate selector mapping directly."
    else:
        reason = "Service-only changes start with py_compile or the nearest focused service smoke."

    return SmokeSelection(
        work_type=kind,
        changed_files=files,
        focused_smokes=smokes,
        reason=reason,
        run_regression=run_regression,
        run_api_smoke=run_api_smoke,
        stop_rule=DEFAULT_STOP_RULE,
    )


def build_smoke_selection_dict(
    user_text: str = "",
    changed_files: list[str] | None = None,
    work_type: str = "",
) -> dict[str, Any]:
    return asdict(
        build_smoke_selection(
            user_text=user_text,
            changed_files=changed_files,
            work_type=work_type,
        )
    )


def format_smoke_selection(selection: SmokeSelection | dict[str, Any]) -> str:
    data = asdict(selection) if isinstance(selection, SmokeSelection) else dict(selection)

    lines = [
        "Project Brain Smoke Selection:",
        f"Work type: {data.get('work_type', '')}",
        f"Reason: {data.get('reason', '')}",
        f"Run regression: {data.get('run_regression', False)}",
        f"Run API smoke: {data.get('run_api_smoke', False)}",
        "Focused smokes:",
    ]

    for smoke in data.get("focused_smokes", []) or []:
        lines.append(f"- {smoke}")

    lines.append(f"Stop rule: {data.get('stop_rule', '')}")

    return "\n".join(lines)


__all__ = [
    "SmokeSelection",
    "build_smoke_selection",
    "build_smoke_selection_dict",
    "classify_smoke_work_type",
    "select_focused_smokes",
    "format_smoke_selection",
    "normalize_files",
]
