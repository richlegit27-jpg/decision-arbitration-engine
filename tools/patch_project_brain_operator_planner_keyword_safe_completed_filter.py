from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_KEYWORD_SAFE_20260702" in text:
    print("Keyword-safe completed move filter already installed")
    raise SystemExit(0)

block = '''

# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_KEYWORD_SAFE_20260702
# Fixes completed-move filtering to call keyword-only _move correctly.
# Service-only. No app.py route guard.
def _nova_keyword_safe_move_20260702(
    rank,
    name,
    why,
    target_files,
    focused_smokes,
    loses_to_best_because="",
):
    return _move(
        rank=rank,
        name=name,
        why=why,
        target_files=list(target_files or []),
        focused_smokes=list(focused_smokes or []),
        loses_to_best_because=str(loses_to_best_because or ""),
    )


def _nova_keyword_safe_move_value_20260702(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def _nova_keyword_safe_move_list_20260702(value):
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    try:
        return [str(item) for item in value if str(item or "").strip()]
    except Exception:
        return []


def _nova_keyword_safe_move_name_20260702(move):
    return str(_nova_keyword_safe_move_value_20260702(move, "name", "") or "").strip()


def _nova_keyword_safe_risky_app_move_20260702(move):
    name = normalize_text(_nova_keyword_safe_move_name_20260702(move))
    return "app.py extraction" in name or "new app.py route guard" in name


def _nova_keyword_safe_cleanup_move_20260702(rank=1):
    return _nova_keyword_safe_move_20260702(
        rank=rank,
        name="Cleanup Strategy Engine v1",
        why="Completed upgrades are now filtered out; the next useful move is bounded cleanup ranking so Nova stops doing tiny lock-the-lock commits.",
        target_files=[
            "nova_backend/services/project_brain_operator_planner.py",
            "nova_backend/services/project_brain_completed_move_filter.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ],
        focused_smokes=select_smokes("cleanup_strategy"),
    )


def _nova_keyword_safe_normalize_move_20260702(move, rank):
    name = _nova_keyword_safe_move_name_20260702(move) or "Cleanup Strategy Engine v1"
    why = str(_nova_keyword_safe_move_value_20260702(move, "why", "") or "").strip()
    target_files = _nova_keyword_safe_move_list_20260702(
        _nova_keyword_safe_move_value_20260702(move, "target_files", [])
    )
    focused_smokes = _nova_keyword_safe_move_list_20260702(
        _nova_keyword_safe_move_value_20260702(move, "focused_smokes", [])
    )
    loses_to_best_because = str(
        _nova_keyword_safe_move_value_20260702(move, "loses_to_best_because", "") or ""
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

    return _nova_keyword_safe_move_20260702(
        rank=rank,
        name=name,
        why=why,
        target_files=target_files,
        focused_smokes=focused_smokes,
        loses_to_best_because=loses_to_best_because,
    )


def rank_moves(work_type: str) -> list[OperatorMove]:
    raw_ranker = globals().get("_NOVA_PRE_COMPLETED_MOVE_FILTER_RANK_MOVES_20260702")

    try:
        raw_moves = raw_ranker(work_type) if callable(raw_ranker) else []
    except Exception:
        raw_moves = []

    if not raw_moves:
        raw_moves = [_nova_keyword_safe_cleanup_move_20260702()]

    try:
        from nova_backend.services.project_brain_completed_move_filter import (
            filter_completed_moves,
        )

        result = filter_completed_moves([
            _nova_keyword_safe_move_name_20260702(move)
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
        if _nova_keyword_safe_move_name_20260702(move) not in completed_names
        and not _nova_keyword_safe_risky_app_move_20260702(move)
    ]

    if not active:
        active = [_nova_keyword_safe_cleanup_move_20260702()]
    elif (
        completed_names
        and not any(_nova_keyword_safe_move_name_20260702(move) == "Cleanup Strategy Engine v1" for move in active)
    ):
        active.insert(0, _nova_keyword_safe_cleanup_move_20260702())

    rejected = []

    for move in raw_moves:
        name = _nova_keyword_safe_move_name_20260702(move)

        if name in completed_names:
            signal = completed_by_name.get(name, {})
            evidence = str(signal.get("evidence") or "already locked").strip()
            replacement = str(signal.get("replacement_hint") or "").strip()

            rejected.append(
                _nova_keyword_safe_move_20260702(
                    rank=0,
                    name=name,
                    why=str(_nova_keyword_safe_move_value_20260702(move, "why", "") or "").strip(),
                    target_files=_nova_keyword_safe_move_list_20260702(
                        _nova_keyword_safe_move_value_20260702(move, "target_files", [])
                    ),
                    focused_smokes=_nova_keyword_safe_move_list_20260702(
                        _nova_keyword_safe_move_value_20260702(move, "focused_smokes", [])
                    ),
                    loses_to_best_because=f"Already locked: {evidence}. {replacement}".strip(),
                )
            )
        elif _nova_keyword_safe_risky_app_move_20260702(move):
            rejected.append(
                _nova_keyword_safe_move_20260702(
                    rank=0,
                    name=name,
                    why=str(_nova_keyword_safe_move_value_20260702(move, "why", "") or "").strip(),
                    target_files=_nova_keyword_safe_move_list_20260702(
                        _nova_keyword_safe_move_value_20260702(move, "target_files", [])
                    ),
                    focused_smokes=_nova_keyword_safe_move_list_20260702(
                        _nova_keyword_safe_move_value_20260702(move, "focused_smokes", [])
                    ),
                    loses_to_best_because="Completed-move filtering prefers bounded service cleanup before app.py extraction.",
                )
            )

    combined = []
    seen = set()

    for move in active + rejected:
        item = _nova_keyword_safe_normalize_move_20260702(move, len(combined) + 1)

        if item.name in seen:
            continue

        seen.add(item.name)
        combined.append(item)

    return [
        _nova_keyword_safe_move_20260702(
            rank=index,
            name=move.name,
            why=move.why,
            target_files=move.target_files,
            focused_smokes=move.focused_smokes,
            loses_to_best_because=move.loses_to_best_because,
        )
        for index, move in enumerate(combined, start=1)
    ]


def choose_recommended_move(work_type: str):
    base_chooser = globals().get("_NOVA_PRE_COMPLETED_MOVE_FILTER_CHOOSE_RECOMMENDED_MOVE_20260702")

    try:
        base = base_chooser(work_type) if callable(base_chooser) else None
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

print("patched keyword-safe completed move filter override")
