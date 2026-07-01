from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OperatorPlan:
    recommended_move: str
    why: str
    work_type: str
    risk: str
    target_files: list[str]
    focused_smokes: list[str]
    avoid_rules: list[str]
    rollback_point: str
    commit_rule: str
    stop_rule: str


PROJECT_BRAIN_CORE_FILES = [
    "nova_backend/services/project_brain_operator_planner.py",
    "nova_backend/services/project_brain_mission_control.py",
    "nova_backend/services/project_brain_general_intelligence.py",
]

PROJECT_BRAIN_SAFE_AVOID_RULES = [
    "Do not add new app.py route guards unless there is no service-level path.",
    "Do not touch direct project-state recall when improving Mission Control.",
    "Do not run the full smoke stack unless route behavior changed.",
    "Do not commit patch helpers that failed or did not modify the target.",
    "Do not mix cleanup-only work with behavior-changing intelligence upgrades.",
]

DEFAULT_COMMIT_RULE = (
    "Commit only after the focused smoke passes and git status shows only intended files."
)

DEFAULT_STOP_RULE = (
    "Stop after one meaningful service-level upgrade or one focused cleanup extraction."
)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def classify_work_type(user_text: str = "", changed_files: list[str] | None = None) -> str:
    text = normalize_text(user_text)
    files = changed_files or []
    joined_files = " ".join(files).lower()

    if any(token in text for token in ("fail", "failed", "error", "traceback", "broken", "regression")):
        return "failure_repair"

    if any(token in text for token in ("smoke", "test", "regression", "checks")):
        return "smoke_selection"

    if "app.py" in text or "cleanup" in text or "extract" in text or "guard" in text:
        return "cleanup_strategy"

    if any("app.py" in file.lower() for file in files):
        return "route_cleanup" if "project_brain" in joined_files else "app_cleanup"

    if any(token in text for token in ("operator", "mission", "next", "upgrade", "gangster", "endgame", "planner")):
        return "operator_planning"

    return "operator_planning"


def select_smokes(work_type: str, changed_files: list[str] | None = None) -> list[str]:
    files = changed_files or []
    joined = " ".join(files).lower()

    if work_type == "failure_repair":
        return [
            "python .\\tools\\nova_project_brain_failure_interpreter_api_smoke.py",
            "python .\\tools\\nova_regression_smoke.py",
        ]

    if work_type == "smoke_selection":
        return [
            "python .\\tools\\nova_project_brain_operator_planner_smoke.py",
        ]

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup") or "app.py" in joined:
        return [
            "python .\\tools\\nova_project_brain_route_patch_audit_smoke.py",
            "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
            "python .\\tools\\nova_regression_smoke.py",
        ]

    if "mission_control" in joined:
        return [
            "python .\\tools\\nova_project_brain_operator_planner_smoke.py",
            "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
            "python .\\tools\\nova_regression_smoke.py",
        ]

    return [
        "python .\\tools\\nova_project_brain_operator_planner_smoke.py",
    ]


def choose_recommended_move(work_type: str) -> tuple[str, str, str, list[str]]:
    if work_type == "failure_repair":
        return (
            "Failure Interpreter v2",
            "A failing smoke should be turned into a precise repair plan before any new feature work.",
            "medium",
            [
                "nova_backend/services/project_brain_failure_interpreter.py",
                "tools/nova_project_brain_failure_interpreter_api_smoke.py",
            ],
        )

    if work_type == "smoke_selection":
        return (
            "Smoke Selector v1",
            "This kills repetitive command spam by mapping file changes to the smallest useful smoke set.",
            "low",
            [
                "nova_backend/services/project_brain_operator_planner.py",
                "tools/nova_project_brain_operator_planner_smoke.py",
            ],
        )

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        return (
            "Cleanup Strategy Engine v1",
            "Cleanup should be ranked and bounded so Nova stops doing tiny lock-the-lock commits.",
            "medium",
            [
                "nova_backend/services/project_brain_operator_planner.py",
                "tools/nova_project_brain_route_patch_audit_smoke.py",
            ],
        )

    return (
        "Project Brain Operator Planner v1",
        "Nova already knows current state; the next intelligence jump is choosing the best move, risk, files, smokes, and stop rule.",
        "low",
        PROJECT_BRAIN_CORE_FILES,
    )


def build_operator_plan(
    user_text: str = "",
    changed_files: list[str] | None = None,
    project_state: str = "",
) -> OperatorPlan:
    work_type = classify_work_type(user_text=user_text, changed_files=changed_files)
    recommended_move, why, risk, target_files = choose_recommended_move(work_type)

    smokes = select_smokes(work_type, changed_files=changed_files)

    avoid_rules = list(PROJECT_BRAIN_SAFE_AVOID_RULES)

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        avoid_rules.insert(0, "Do not clean up more than one route/guard family in the same commit.")

    if work_type == "failure_repair":
        avoid_rules.insert(0, "Do not add new behavior until the failing contract is reproduced.")

    if project_state:
        rollback_point = "Use the latest clean commit before this operator plan."
    else:
        rollback_point = "Use current HEAD as rollback point before patching."

    return OperatorPlan(
        recommended_move=recommended_move,
        why=why,
        work_type=work_type,
        risk=risk,
        target_files=target_files,
        focused_smokes=smokes,
        avoid_rules=avoid_rules,
        rollback_point=rollback_point,
        commit_rule=DEFAULT_COMMIT_RULE,
        stop_rule=DEFAULT_STOP_RULE,
    )


def build_operator_plan_dict(
    user_text: str = "",
    changed_files: list[str] | None = None,
    project_state: str = "",
) -> dict[str, Any]:
    return asdict(
        build_operator_plan(
            user_text=user_text,
            changed_files=changed_files,
            project_state=project_state,
        )
    )


def format_operator_plan(plan: OperatorPlan | dict[str, Any]) -> str:
    data = asdict(plan) if isinstance(plan, OperatorPlan) else dict(plan)

    lines = [
        "Project Brain Operator Plan:",
        f"Recommended move: {data.get('recommended_move', '')}",
        f"Why: {data.get('why', '')}",
        f"Work type: {data.get('work_type', '')}",
        f"Risk: {data.get('risk', '')}",
        "Target files:",
    ]

    for file in data.get("target_files", []) or []:
        lines.append(f"- {file}")

    lines.append("Focused smokes:")
    for smoke in data.get("focused_smokes", []) or []:
        lines.append(f"- {smoke}")

    lines.append("Avoid rules:")
    for rule in data.get("avoid_rules", []) or []:
        lines.append(f"- {rule}")

    lines.extend(
        [
            f"Rollback point: {data.get('rollback_point', '')}",
            f"Commit rule: {data.get('commit_rule', '')}",
            f"Stop rule: {data.get('stop_rule', '')}",
        ]
    )

    return "\n".join(lines)


__all__ = [
    "OperatorPlan",
    "build_operator_plan",
    "build_operator_plan_dict",
    "classify_work_type",
    "select_smokes",
    "format_operator_plan",
]
