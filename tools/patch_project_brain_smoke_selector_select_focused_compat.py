from pathlib import Path

TARGET = Path("nova_backend/services/project_brain_smoke_selector.py")

if not TARGET.exists():
    raise SystemExit("missing smoke selector service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_SELECT_FOCUSED_SMOKES_COMPAT_20260702" in text:
    print("select_focused_smokes compat already installed")
    raise SystemExit(0)

block = r'''

# NOVA_PROJECT_BRAIN_SELECT_FOCUSED_SMOKES_COMPAT_20260702
# Compatibility helper for project_brain_operator_planner.select_smokes().
# Returns only the focused smoke command list, while select_smokes() keeps the richer object.
def select_focused_smokes(
    work_type: str = "",
    changed_files=None,
    failure_type: str = "",
    failing_layer: str = "",
    user_intent: str = "",
    route_risk: str = "low",
    **kwargs,
):
    intent = str(user_intent or work_type or "").strip()

    selection = select_smokes(
        changed_files=changed_files,
        failure_type=failure_type,
        failing_layer=failing_layer,
        user_intent=intent,
        route_risk=route_risk,
    )

    return list(selection.focused_smokes)
'''

TARGET.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
print("patched select_focused_smokes compatibility helper")
