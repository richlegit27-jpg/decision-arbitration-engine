from pathlib import Path

TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_RISK_SAFE_20260702" in text:
    print("Risk-safe completed move filter already installed")
    raise SystemExit(0)

old = '''# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_KEYWORD_SAFE_20260702
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
'''

new = '''# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_KEYWORD_SAFE_20260702
# NOVA_PROJECT_BRAIN_COMPLETED_MOVE_FILTER_RISK_SAFE_20260702
# Fixes completed-move filtering to call keyword-only _move correctly.
# Service-only. No app.py route guard.
def _nova_keyword_safe_move_20260702(
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
        name=name,
        why=why,
        risk=str(risk or "low"),
        target_files=list(target_files or []),
        focused_smokes=list(focused_smokes or []),
        loses_to_best_because=str(loses_to_best_because or ""),
    )
'''

if old not in text:
    raise SystemExit("expected keyword-safe helper block not found")

text = text.replace(old, new, 1)

TARGET.write_text(text, encoding="utf-8")
print("patched completed move filter risk keyword")
