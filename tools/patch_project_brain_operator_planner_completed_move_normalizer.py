from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_MOVE_NORMALIZER_20260702" in text:
    print("Operator Planner completed-move normalizer already installed")
    raise SystemExit(0)

block = '''

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
'''

text = text.rstrip() + "\n" + block + "\n"

TARGET.write_text(text, encoding="utf-8")

print("patched Operator Planner completed-move normalization")
