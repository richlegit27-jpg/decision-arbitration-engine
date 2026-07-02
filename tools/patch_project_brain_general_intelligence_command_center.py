from pathlib import Path


TARGET = Path("nova_backend/services/project_brain_general_intelligence.py")

if not TARGET.exists():
    raise SystemExit("missing general intelligence service")

text = TARGET.read_text(encoding="utf-8-sig")

if "_nova_project_brain_command_center_question_20260702" in text:
    print("General Intelligence already routes Command Center")
    raise SystemExit(0)

anchor = '''

def build_project_brain_general_answer(user_text=""):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    if q in {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }:
        return None

    if should_handle_project_brain_general_question(user_text):
'''

insert = '''

def _nova_project_brain_command_center_question_20260702(user_text):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    exact_direct_project_state = {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }
    if q in exact_direct_project_state:
        return False

    phrases = [
        "command center",
        "project brain command center",
        "operator dashboard",
        "what smoke should we run",
        "which smoke should we run",
        "what test should we run",
        "which test should we run",
        "run checks",
        "validation",
        "what failed",
        "what does this failure mean",
        "why did this fail",
        "recent changes",
        "recent decisions",
        "decision log",
        "what changed recently",
        "what did we lock recently",
        "what got locked recently",
        "next upgrade",
        "next gangster upgrade",
        "gangster upgrade",
    ]

    if any(phrase in q for phrase in phrases):
        return True

    if q in {
        "status",
        "project status",
        "nova status",
        "current status",
        "current blocker",
        "next",
        "next move",
    }:
        return True

    return False


def build_project_brain_general_answer(user_text=""):
    q = _nova_project_brain_general_live_selector_normalize_20260702(user_text)

    if q in {
        "what are we working on",
        "what are we working on now",
        "what are we working on right now",
    }:
        return None

    if _nova_project_brain_command_center_question_20260702(user_text):
        from nova_backend.services.project_brain_command_center import (
            build_project_brain_command_center_answer,
        )

        return ProjectBrainAnswer(
            intent="command_center",
            text=build_project_brain_command_center_answer(
                user_text=str(user_text or ""),
                pasted_output="",
                changed_files=None,
            ),
        )

    if should_handle_project_brain_general_question(user_text):
'''

if anchor not in text:
    raise SystemExit("could not find general intelligence build answer anchor")

text = text.replace(anchor, insert, 1)

TARGET.write_text(text, encoding="utf-8")

print("patched General Intelligence to route Command Center prompts")
