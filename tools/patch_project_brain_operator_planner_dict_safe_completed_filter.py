from pathlib import Path

TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_DICT_SAFE_20260702" in text:
    print("Dict-safe completed move filter already installed")
    raise SystemExit(0)

block = '''

# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_DICT_SAFE_20260702
# Final shape-safe override for completed-move filtering.
# Handles _move returning either dicts or objects.
# Service-only. No app.py route guard.
def _nova_dict_safe_move_20260702(
    rank,
    name,
    why,
    target_files,
    focused_smokes,
    loses_to_best_because="",
    risk="low",
):
    return _move(
        rank=rank,
        name=str(name or "").strip(),
        why=str(why or "").strip(),
        risk=str(risk or "low").strip() or "low",
        target_files=list(target_files or []),
        focused_smokes=list(focused_smokes or []),
        loses_to_best_because=str(loses_to_best_because or "").strip(),
    )


def _nova_dict_safe_value_20260702(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def _nova_dict_safe_list_20260702(value):
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    try:
        return [str(item) for item in value if str(item or "").strip()]
    except Exception:
        return []


def _nova_dict_safe_name_20260702(move):
    return str(_nova_dict_safe_value_20260702(move, "name", "") or "").strip()


def _nova_dict_safe_risk_20260702(move, default="low"):
    return str(_nova_dict_safe_value_20260702(move, "risk", default) or default).strip() or default


def _nova_dict_safe_risky_app_move_20260702(move):
    name = normalize_text(_nova_dict_safe_name_20260702(move))
    return "app.py extraction" in name or "new app.py route guard" in name


def _nova_dict_safe_cleanup_move_20260702(rank=1):
    return _nova_dict_safe_move_20260702(
        rank=rank,
        name="Cleanup Strategy Engine v1",
        why="Completed upgrades are now filtered out; the next useful move is bounded cleanup ranking so Nova stops doing tiny lock-the-lock commits.",
        risk="medium",
        target_files=[
            "nova_backend/services/project_brain_operator_planner.py",
            "nova_backend/services/project_brain_completed_move_filter.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ],
        focused_smokes=select_smokes("cleanup_strategy"),
    )


def _nova_dict_safe_normalize_move_20260702(move, rank):
    name = _nova_dict_safe_name_20260702(move) or "Cleanup Strategy Engine v1"
    why = str(_nova_dict_safe_value_20260702(move, "why", "") or "").strip()
    risk = _nova_dict_safe_risk_20260702(move, "low")

    target_files = _nova_dict_safe_list_20260702(
        _nova_dict_safe_value_20260702(move, "target_files", [])
    )
    focused_smokes = _nova_dict_safe_list_20260702(
        _nova_dict_safe_value_20260702(move, "focused_smokes", [])
    )
    loses_to_best_because = str(
        _nova_dict_safe_value_20260702(move, "loses_to_best_because", "") or ""
    ).strip()

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

    return _nova_dict_safe_move_20260702(
        rank=rank,
        name=name,
        why=why,
        risk=risk,
        target_files=target_files,
        focused_smokes=focused_smokes,
        loses_to_best_because=loses_to_best_because,
    )


def rank_moves(work_type: str):
    raw_ranker = globals().get("_NOVA_PRE_COMPLETED_MOVE_FILTER_RANK_MOVES_20260702")

    try:
        raw_moves = raw_ranker(work_type) if callable(raw_ranker) else []
    except Exception:
        raw_moves = []

    if not raw_moves:
        raw_moves = [_nova_dict_safe_cleanup_move_20260702()]

    try:
        from nova_backend.services.project_brain_completed_move_filter import (
            filter_completed_moves,
        )

        result = filter_completed_moves([
            _nova_dict_safe_name_20260702(move)
            for move in raw_moves
        ])
        completed_items = result.get("completed_moves", []) or []
        completed_by_name = {
            str(item.get("move_name") or ""): item
            for item in completed_items
        }
        completed_names = set(completed_by_name)
    except Exception:
        completed_by_name = {}
        completed_names = set()

    active = [
        move
        for move in raw_moves
        if _nova_dict_safe_name_20260702(move) not in completed_names
        and not _nova_dict_safe_risky_app_move_20260702(move)
    ]

    if not active:
        active = [_nova_dict_safe_cleanup_move_20260702()]
    elif (
        completed_names
        and not any(_nova_dict_safe_name_20260702(move) == "Cleanup Strategy Engine v1" for move in active)
    ):
        active.insert(0, _nova_dict_safe_cleanup_move_20260702())

    rejected = []

    for move in raw_moves:
        name = _nova_dict_safe_name_20260702(move)

        if name in completed_names:
            signal = completed_by_name.get(name, {})
            evidence = str(signal.get("evidence") or "already locked").strip()
            replacement = str(signal.get("replacement_hint") or "").strip()

            rejected.append(
                _nova_dict_safe_move_20260702(
                    rank=0,
                    name=name,
                    why=str(_nova_dict_safe_value_20260702(move, "why", "") or "").strip(),
                    risk=_nova_dict_safe_risk_20260702(move),
                    target_files=_nova_dict_safe_list_20260702(
                        _nova_dict_safe_value_20260702(move, "target_files", [])
                    ),
                    focused_smokes=_nova_dict_safe_list_20260702(
                        _nova_dict_safe_value_20260702(move, "focused_smokes", [])
                    ),
                    loses_to_best_because=f"Already locked: {evidence}. {replacement}".strip(),
                )
            )
        elif _nova_dict_safe_risky_app_move_20260702(move):
            rejected.append(
                _nova_dict_safe_move_20260702(
                    rank=0,
                    name=name,
                    why=str(_nova_dict_safe_value_20260702(move, "why", "") or "").strip(),
                    risk=_nova_dict_safe_risk_20260702(move),
                    target_files=_nova_dict_safe_list_20260702(
                        _nova_dict_safe_value_20260702(move, "target_files", [])
                    ),
                    focused_smokes=_nova_dict_safe_list_20260702(
                        _nova_dict_safe_value_20260702(move, "focused_smokes", [])
                    ),
                    loses_to_best_because="Completed-move filtering prefers bounded service cleanup before app.py extraction.",
                )
            )

    combined = []
    seen = set()

    for move in active + rejected:
        item = _nova_dict_safe_normalize_move_20260702(move, len(combined) + 1)
        item_name = _nova_dict_safe_name_20260702(item)

        if item_name in seen:
            continue

        seen.add(item_name)
        combined.append(item)

    return [
        _nova_dict_safe_normalize_move_20260702(move, index)
        for index, move in enumerate(combined, start=1)
    ]


def choose_recommended_move(work_type: str):
    ranked = rank_moves(work_type)
    best = ranked[0] if ranked else _nova_dict_safe_cleanup_move_20260702()

    risk = _nova_dict_safe_risk_20260702(best, "low")

    if work_type in ("cleanup_strategy", "route_cleanup", "app_cleanup"):
        risk = "medium"

    return (
        _nova_dict_safe_name_20260702(best),
        str(_nova_dict_safe_value_20260702(best, "why", "") or "").strip(),
        risk,
        _nova_dict_safe_list_20260702(
            _nova_dict_safe_value_20260702(best, "target_files", [])
        ),
    )
'''

text = text.rstrip() + "\n" + block + "\n"

TARGET.write_text(text, encoding="utf-8")

print("patched dict-safe completed move filter override")
