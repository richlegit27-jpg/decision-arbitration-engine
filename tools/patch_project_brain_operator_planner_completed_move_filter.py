from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_OPERATOR_PLANNER_20260702" in text:
    print("Operator Planner already has completed move filtering")
    raise SystemExit(0)

block = '''

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
'''

text = text.rstrip() + "\n" + block + "\n"
TARGET.write_text(text, encoding="utf-8")

print("patched Operator Planner with completed-move filtering")
