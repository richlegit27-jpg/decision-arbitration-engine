from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OperatorMove:
    name: str
    rank: int
    why: str
    risk: str
    target_files: list[str]
    focused_smokes: list[str]
    loses_to_best_because: str


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
    exact_next_command: str
    loop_guard: str
    ranked_moves: list[dict[str, Any]]
    rejected_moves: list[dict[str, Any]]


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

DEFAULT_LOOP_GUARD = (
    "If the next step only adds a lock for an already-passing lock, stop and choose a real behavior upgrade instead."
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


def _operator_planner_smoke_work_type(work_type: str) -> str:
    text = normalize_text(work_type)

    if text == "operator_planning":
        return "operator_planner"

    if text == "smoke_selection":
        return "smoke_selector"

    return text


def select_smokes(work_type: str, changed_files: list[str] | None = None) -> list[str]:
    from nova_backend.services.project_brain_smoke_selector import (
        select_focused_smokes,
    )

    return select_focused_smokes(
        work_type=_operator_planner_smoke_work_type(work_type),
        changed_files=changed_files,
    )


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
        "Operator Plan Quality v2",
        "Nova already has an operator plan; the next jump is ranking moves, rejecting weaker moves, and giving one exact next command.",
        "low",
        [
            "nova_backend/services/project_brain_operator_planner.py",
            "nova_backend/services/project_brain_mission_control.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ],
    )


def _move(
    *,
    rank: int,
    name: str,
    why: str,
    risk: str,
    target_files: list[str],
    focused_smokes: list[str],
    loses_to_best_because: str = "",
) -> dict[str, Any]:
    return asdict(
        OperatorMove(
            name=name,
            rank=rank,
            why=why,
            risk=risk,
            target_files=target_files,
            focused_smokes=focused_smokes,
            loses_to_best_because=loses_to_best_because,
        )
    )


def rank_moves(work_type: str, changed_files: list[str] | None = None) -> list[dict[str, Any]]:
    if work_type == "failure_repair":
        return [
            _move(
                rank=1,
                name="Failure Interpreter v2",
                why="A failure must become a focused repair plan before new work continues.",
                risk="medium",
                target_files=["nova_backend/services/project_brain_failure_interpreter.py"],
                focused_smokes=select_smokes("failure_repair", changed_files),
            ),
            _move(
                rank=2,
                name="Smoke Selector v1",
                why="Useful after the failure is understood, but not before.",
                risk="low",
                target_files=["nova_backend/services/project_brain_operator_planner.py"],
                focused_smokes=["python .\\tools\\nova_project_brain_operator_planner_smoke.py"],
                loses_to_best_because="It optimizes validation but does not fix the failing contract.",
            ),
            _move(
                rank=3,
                name="Cleanup Strategy Engine v1",
                why="Cleanup can wait until green behavior is restored.",
                risk="medium",
                target_files=["nova_backend/services/project_brain_operator_planner.py"],
                focused_smokes=["python .\\tools\\nova_project_brain_route_patch_audit_smoke.py"],
                loses_to_best_because="Cleanup during a failure increases risk.",
            ),
        ]

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        return [
            _move(
                rank=1,
                name="Cleanup Strategy Engine v1",
                why="Cleanup needs boundaries, one target family, and a stop rule.",
                risk="medium",
                target_files=["nova_backend/services/project_brain_operator_planner.py"],
                focused_smokes=select_smokes(work_type, changed_files),
            ),
            _move(
                rank=2,
                name="Smoke Selector v1",
                why="It reduces repetitive validation but does not pick the cleanup target by itself.",
                risk="low",
                target_files=["nova_backend/services/project_brain_operator_planner.py"],
                focused_smokes=["python .\\tools\\nova_project_brain_operator_planner_smoke.py"],
                loses_to_best_because="The immediate need is cleanup ranking, not just smoke choice.",
            ),
            _move(
                rank=3,
                name="New app.py route guard",
                why="Only valid when no service-level path exists.",
                risk="high",
                target_files=["app.py"],
                focused_smokes=["python .\\tools\\nova_regression_smoke.py"],
                loses_to_best_because="It violates the current avoid-rule and can recreate guard stack debt.",
            ),
        ]

    return [
        _move(
            rank=1,
            name="Operator Plan Quality v2",
            why="This makes Mission Control choose, rank, reject, and stop instead of repeating commands.",
            risk="low",
            target_files=[
                "nova_backend/services/project_brain_operator_planner.py",
                "nova_backend/services/project_brain_mission_control.py",
                "tools/nova_project_brain_operator_planner_smoke.py",
            ],
            focused_smokes=[
                "python .\\tools\\nova_project_brain_operator_planner_smoke.py",
                "python .\\tools\\nova_project_brain_mission_control_api_smoke.py",
            ],
        ),
        _move(
            rank=2,
            name="Smoke Selector v1",
            why="Still valuable, but it is strongest after the plan quality fields exist.",
            risk="low",
            target_files=["nova_backend/services/project_brain_operator_planner.py"],
            focused_smokes=["python .\\tools\\nova_project_brain_operator_planner_smoke.py"],
            loses_to_best_because="It solves validation spam but not move quality.",
        ),
        _move(
            rank=3,
            name="App.py extraction",
            why="Useful cleanup, but less valuable than making Nova choose better moves first.",
            risk="medium",
            target_files=["app.py"],
            focused_smokes=[
                "python .\\tools\\nova_project_brain_route_patch_audit_smoke.py",
                "python .\\tools\\nova_regression_smoke.py",
            ],
            loses_to_best_because="Cleanup can continue after the operator brain is sharper.",
        ),
    ]


def exact_next_command_for(work_type: str) -> str:
    if work_type == "failure_repair":
        return "python .\\tools\\nova_project_brain_failure_interpreter_api_smoke.py"

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        return "python .\\tools\\nova_project_brain_route_patch_audit_smoke.py"

    if work_type == "smoke_selection":
        return "python .\\tools\\nova_project_brain_operator_planner_smoke.py"

    return "python .\\tools\\nova_project_brain_operator_planner_smoke.py"


def build_operator_plan(
    user_text: str = "",
    changed_files: list[str] | None = None,
    project_state: str = "",
) -> OperatorPlan:
    work_type = classify_work_type(user_text=user_text, changed_files=changed_files)
    recommended_move, why, risk, target_files = choose_recommended_move(work_type)
    smokes = select_smokes(work_type, changed_files=changed_files)
    moves = rank_moves(work_type, changed_files=changed_files)

    avoid_rules = list(PROJECT_BRAIN_SAFE_AVOID_RULES)

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        avoid_rules.insert(0, "Do not clean up more than one route/guard family in the same commit.")

    if work_type == "failure_repair":
        avoid_rules.insert(0, "Do not add new behavior until the failing contract is reproduced.")

    rollback_point = (
        "Use the latest clean commit before this operator plan."
        if project_state
        else "Use current HEAD as rollback point before patching."
    )

    rejected_moves = [move for move in moves if int(move.get("rank", 0)) > 1]

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
        exact_next_command=exact_next_command_for(work_type),
        loop_guard=DEFAULT_LOOP_GUARD,
        ranked_moves=moves,
        rejected_moves=rejected_moves,
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
        f"Exact next command: {data.get('exact_next_command', '')}",
        "Ranked moves:",
    ]

    for move in data.get("ranked_moves", []) or []:
        lines.append(
            f"- #{move.get('rank')}: {move.get('name')} | risk={move.get('risk')} | why={move.get('why')}"
        )

    lines.append("Rejected moves:")
    for move in data.get("rejected_moves", []) or []:
        lines.append(
            f"- {move.get('name')}: {move.get('loses_to_best_because')}"
        )

    lines.append("Target files:")
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
            f"Loop guard: {data.get('loop_guard', '')}",
        ]
    )

    return "\n".join(lines)


__all__ = [
    "OperatorMove",
    "OperatorPlan",
    "build_operator_plan",
    "build_operator_plan_dict",
    "classify_work_type",
    "select_smokes",
    "rank_moves",
    "exact_next_command_for",
    "format_operator_plan",
]


# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_OPERATOR_PLANNER_20260702
# Filters already-locked upgrades out of Operator Planner recommendations.
# Service-only. No app.py route wiring.
_NOVA_PRE_COMPLETED_MOVE_FILTER_RANK_MOVES_20260702 = rank_moves
_NOVA_PRE_COMPLETED_MOVE_FILTER_CHOOSE_RECOMMENDED_MOVE_20260702 = choose_recommended_move


def _nova_completed_move_cleanup_strategy_move_20260702() -> OperatorMove:
    return _move(
        1,
        "Cleanup Strategy Engine v1",
        "Completed upgrades are now filtered out; the next useful move is bounded cleanup ranking so Nova stops doing tiny lock-the-lock commits.",
        [
            "nova_backend/services/project_brain_operator_planner.py",
            "nova_backend/services/project_brain_completed_move_filter.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ],
        select_smokes("cleanup_strategy"),
    )


def _nova_completed_move_is_risky_app_move_20260702(move: OperatorMove) -> bool:
    name = normalize_text(move.name)
    return "app.py extraction" in name or "new app.py route guard" in name


def _nova_completed_move_filter_ranked_moves_20260702(moves: list[OperatorMove]) -> list[OperatorMove]:
    try:
        from nova_backend.services.project_brain_completed_move_filter import (
            filter_completed_moves,
        )

        result = filter_completed_moves([move.name for move in moves])
        completed_by_name = {
            str(item.get("move_name") or ""): item
            for item in result.get("completed_moves", [])
        }
        completed_names = set(completed_by_name)

        active = [
            move
            for move in moves
            if move.name not in completed_names
            and not _nova_completed_move_is_risky_app_move_20260702(move)
        ]

        if not active:
            active = [_nova_completed_move_cleanup_strategy_move_20260702()]
        elif (
            ("Operator Plan Quality v2" in completed_names or "Smoke Selector v1" in completed_names)
            and active[0].name != "Cleanup Strategy Engine v1"
        ):
            if not any(move.name == "Cleanup Strategy Engine v1" for move in active):
                active.insert(0, _nova_completed_move_cleanup_strategy_move_20260702())

        rejected: list[OperatorMove] = []

        for move in moves:
            if move.name in completed_names:
                signal = completed_by_name.get(move.name, {})
                evidence = str(signal.get("evidence") or "already locked").strip()
                replacement = str(signal.get("replacement_hint") or "").strip()
                rejected.append(
                    _move(
                        0,
                        move.name,
                        move.why,
                        move.target_files,
                        move.focused_smokes,
                        f"Already locked: {evidence}. {replacement}".strip(),
                    )
                )
            elif _nova_completed_move_is_risky_app_move_20260702(move):
                rejected.append(
                    _move(
                        0,
                        move.name,
                        move.why,
                        move.target_files,
                        move.focused_smokes,
                        "Completed-move filtering prefers the bounded cleanup service path before app.py extraction.",
                    )
                )

        seen = set()
        combined: list[OperatorMove] = []

        for move in active + rejected:
            if move.name in seen:
                continue
            seen.add(move.name)
            combined.append(move)

        reranked: list[OperatorMove] = []
        for index, move in enumerate(combined, start=1):
            reranked.append(
                _move(
                    index,
                    move.name,
                    move.why,
                    move.target_files,
                    move.focused_smokes,
                    move.loses_to_best_because,
                )
            )

        return reranked

    except Exception:
        return moves


def rank_moves(work_type: str) -> list[OperatorMove]:
    return _nova_completed_move_filter_ranked_moves_20260702(
        _NOVA_PRE_COMPLETED_MOVE_FILTER_RANK_MOVES_20260702(work_type)
    )


def choose_recommended_move(work_type: str):
    base = _NOVA_PRE_COMPLETED_MOVE_FILTER_CHOOSE_RECOMMENDED_MOVE_20260702(work_type)
    ranked = rank_moves(work_type)

    if not ranked:
        return base

    best = ranked[0]

    if isinstance(base, tuple):
        if len(base) >= 3:
            return (best.name, best.why, best.target_files) + tuple(base[3:])
        if len(base) == 2:
            return (best.name, best.why)
        if len(base) == 1:
            return (best.name,)

    if isinstance(base, dict):
        updated = dict(base)
        updated["recommended_move"] = best.name
        updated["why"] = best.why
        updated["target_files"] = list(best.target_files)
        return updated

    return best.name


# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_MOVE_NORMALIZER_20260702
# Normalizes ranked moves after completed-move filtering so downstream callers
# always receive OperatorMove objects, even if an older wrapper returns dicts.
_NOVA_PRE_COMPLETED_MOVE_FILTER_NORMALIZED_RANK_MOVES_20260702 = rank_moves


def _nova_move_value_20260702(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def _nova_move_list_20260702(value):
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    try:
        return [str(item) for item in value if str(item or "").strip()]
    except Exception:
        return []


def _nova_normalize_operator_move_20260702(move, rank):
    name = str(_nova_move_value_20260702(move, "name", "") or "").strip()
    why = str(_nova_move_value_20260702(move, "why", "") or "").strip()
    target_files = _nova_move_list_20260702(
        _nova_move_value_20260702(move, "target_files", [])
    )
    focused_smokes = _nova_move_list_20260702(
        _nova_move_value_20260702(move, "focused_smokes", [])
    )
    loses_to_best_because = str(
        _nova_move_value_20260702(move, "loses_to_best_because", "") or ""
    ).strip()

    if not name:
        name = "Cleanup Strategy Engine v1"

    if not why:
        why = "Use the next unfinished service-level move instead of repeating completed upgrades."

    if not target_files:
        target_files = [
            "nova_backend/services/project_brain_operator_planner.py",
            "nova_backend/services/project_brain_completed_move_filter.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ]

    if not focused_smokes:
        focused_smokes = select_smokes("cleanup_strategy")

    return _move(
        rank,
        name,
        why,
        target_files,
        focused_smokes,
        loses_to_best_because,
    )


def rank_moves(work_type: str) -> list[OperatorMove]:
    raw_moves = _NOVA_PRE_COMPLETED_MOVE_FILTER_NORMALIZED_RANK_MOVES_20260702(work_type)

    normalized = []
    seen = set()

    for move in raw_moves or []:
        item = _nova_normalize_operator_move_20260702(move, len(normalized) + 1)

        if item.name in seen:
            continue

        seen.add(item.name)
        normalized.append(item)

    if not normalized:
        normalized.append(
            _move(
                1,
                "Cleanup Strategy Engine v1",
                "Use bounded cleanup ranking as the next unfinished service-level move.",
                [
                    "nova_backend/services/project_brain_operator_planner.py",
                    "nova_backend/services/project_brain_completed_move_filter.py",
                    "tools/nova_project_brain_operator_planner_smoke.py",
                ],
                select_smokes("cleanup_strategy"),
            )
        )

    return [
        _move(
            index,
            move.name,
            move.why,
            move.target_files,
            move.focused_smokes,
            move.loses_to_best_because,
        )
        for index, move in enumerate(normalized, start=1)
    ]


def choose_recommended_move(work_type: str):
    try:
        base = _NOVA_PRE_COMPLETED_MOVE_FILTER_CHOOSE_RECOMMENDED_MOVE_20260702(work_type)
    except Exception:
        base = None

    ranked = rank_moves(work_type)
    best = ranked[0]

    risk = "low"
    if isinstance(base, tuple) and len(base) >= 3 and isinstance(base[2], str):
        risk = base[2]
    elif work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        risk = "medium"

    return (
        best.name,
        best.why,
        risk,
        list(best.target_files),
    )

