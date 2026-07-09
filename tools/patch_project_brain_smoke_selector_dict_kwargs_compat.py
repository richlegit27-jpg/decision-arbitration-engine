from pathlib import Path

TARGET = Path("nova_backend/services/project_brain_smoke_selector.py")

if not TARGET.exists():
    raise SystemExit("missing smoke selector service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_SMOKE_SELECTION_DICT_KWARGS_COMPAT_20260702" in text:
    print("smoke selection dict kwargs compat already installed")
    raise SystemExit(0)

block = r'''

# NOVA_PROJECT_BRAIN_SMOKE_SELECTION_DICT_KWARGS_COMPAT_20260702
# Command Center passes user_text= and work_type=.
# This override accepts both old and new selector call shapes.
def build_smoke_selection_dict(
    *args,
    user_text: str = "",
    changed_files=None,
    work_type: str = "",
    failure_type: str = "",
    failing_layer: str = "",
    user_intent: str = "",
    route_risk: str = "low",
    **kwargs,
) -> dict:
    if args:
        first = args[0]
        if isinstance(first, (list, tuple, set)):
            changed_files = list(first)
        elif isinstance(first, str) and not user_intent:
            user_intent = first

    intent = str(user_intent or work_type or user_text or "").strip()

    selection = select_smokes(
        changed_files=changed_files,
        failure_type=failure_type,
        failing_layer=failing_layer,
        user_intent=intent,
        route_risk=route_risk,
    )

    focused_smokes = list(selection.focused_smokes)
    exact_next_command = focused_smokes[0] if focused_smokes else ""

    return {
        "focused_smokes": focused_smokes,
        "smokes": focused_smokes,
        "exact_next_command": exact_next_command,
        "command": exact_next_command,
        "reason": selection.reason,
        "smoke_selector_reason": selection.reason,
        "risk": selection.risk,
        "stop_rule": selection.stop_rule,
        "user_intent": intent,
        "work_type": str(work_type or "").strip(),
    }
'''

TARGET.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
print("patched build_smoke_selection_dict kwargs compatibility")
