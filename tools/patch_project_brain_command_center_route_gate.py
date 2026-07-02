from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_general_intelligence.py")

if not TARGET.exists():
    raise SystemExit("missing general intelligence service")

text = TARGET.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_COMMAND_CENTER_ROUTE_GATE_20260702" in text:
    print("Command Center route gate already installed")
    raise SystemExit(0)

block = '''

# NOVA_PROJECT_BRAIN_COMMAND_CENTER_ROUTE_GATE_20260702
# Keeps Command Center prompts on the Project Brain general-intelligence route.
# Service-level gate only. No app.py route guard.
_NOVA_PRE_COMMAND_CENTER_ROUTE_GATE_SHOULD_HANDLE_20260702 = should_handle_project_brain_general_question


def should_handle_project_brain_general_question(user_text):
    try:
        if _nova_project_brain_command_center_question_20260702(user_text):
            return True
    except Exception:
        pass

    return _NOVA_PRE_COMMAND_CENTER_ROUTE_GATE_SHOULD_HANDLE_20260702(user_text)
'''

text = text.rstrip() + "\n" + block + "\n"

TARGET.write_text(text, encoding="utf-8")

print("patched General Intelligence Command Center route gate")
