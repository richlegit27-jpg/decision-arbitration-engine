from pathlib import Path

TARGET = Path("nova_backend/services/project_brain_operator_planner.py")

if not TARGET.exists():
    raise SystemExit("missing operator planner service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_RANK_MOVES_CHANGED_FILES_SAFE_20260702" in text:
    print("rank_moves changed_files wrapper already installed")
    raise SystemExit(0)

block = '''

# NOVA_PROJECT_BRAIN_RANK_MOVES_CHANGED_FILES_SAFE_20260702
# Allows build_operator_plan to call rank_moves(work_type, changed_files=...).
# Keeps the completed-move filter override service-only.
_NOVA_PRE_RANK_MOVES_CHANGED_FILES_SAFE_20260702 = rank_moves

def rank_moves(work_type: str, changed_files=None, **kwargs):
    return _NOVA_PRE_RANK_MOVES_CHANGED_FILES_SAFE_20260702(work_type)
'''

text = text.rstrip() + "\n" + block + "\n"

TARGET.write_text(text, encoding="utf-8")
print("patched rank_moves changed_files wrapper")
