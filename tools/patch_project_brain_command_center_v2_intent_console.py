from pathlib import Path
import re


TARGET = Path("nova_backend/services/project_brain_command_center.py")

if not TARGET.exists():
    raise SystemExit("missing command center service")

text = TARGET.read_text(encoding="utf-8-sig")

if "Command Center v2 Intent Console" in text:
    print("Command Center already has v2 intent console")
    raise SystemExit(0)

anchor = '''

def format_project_brain_command_center(card: ProjectBrainCommandCenterCard | dict[str, Any]) -> str:
    data = card.to_dict() if isinstance(card, ProjectBrainCommandCenterCard) else dict(card)

    focused_smokes = _join(data.get("focused_smokes", []))
    target_files = _join(data.get("target_files", []))
    avoid_rules = _join(data.get("avoid_rules", []))

    return (
        "Project Brain Command Center:\\n"
        f"Command intent: {data.get('command_intent', '')}\\n"
        f"Status: {data.get('status', '')}\\n"
        f"Blocker/Risk: {data.get('blocker', '')}\\n"
        f"Best Move: {data.get('best_move', '')}\\n"
        f"Why: {data.get('why', '')}\\n"
        f"Risk: {data.get('risk', '')}\\n"
        f"Exact Next Command: {data.get('exact_next_command', '')}\\n"
        f"Focused Smokes: {focused_smokes}\\n"
        f"Smoke Selector Reason: {data.get('smoke_reason', '')}\\n"
        f"Target Files: {target_files}\\n"
        f"Avoid Rules: {avoid_rules}\\n"
        f"Stop Rule: {data.get('stop_rule', '')}\\n"
        f"Loop Guard: {data.get('loop_guard', '')}\\n"
        f"Failure Type: {data.get('failure_type', '')}\\n"
        f"Failure Severity: {data.get('failure_severity', '')}\\n"
        f"Failure Patch Target: {data.get('failure_patch_target', '')}\\n"
        f"Failure Next Command: {data.get('failure_next_command', '')}\\n"
        f"Recent Changes: {data.get('recent_changes', '')}"
    )
'''

replacement = '''

def _command_center_primary_section(data: dict[str, Any]) -> str:
    intent = str(data.get("command_intent") or "").strip()
    focused_smokes = _join(data.get("focused_smokes", []))
    target_files = _join(data.get("target_files", []))

    if intent == "smoke_selection":
        return (
            "Primary Answer: run the focused smoke set first.\\n"
            f"Focused Smokes: {focused_smokes}\\n"
            f"Smoke Selector Reason: {data.get('smoke_reason', '')}\\n"
            f"Exact Next Command: {data.get('exact_next_command', '')}\\n"
            f"Stop Rule: {data.get('stop_rule', '')}"
        )

    if intent == "recent_changes":
        return (
            "Primary Answer: recent Project Brain changes.\\n"
            f"Recent Changes: {data.get('recent_changes', '')}\\n"
            f"Best Move: {data.get('best_move', '')}\\n"
            f"Exact Next Command: {data.get('exact_next_command', '')}"
        )

    if intent == "failure":
        return (
            "Primary Answer: diagnose the failure before patching.\\n"
            f"Failure Type: {data.get('failure_type', '')}\\n"
            f"Failure Severity: {data.get('failure_severity', '')}\\n"
            f"Failure Patch Target: {data.get('failure_patch_target', '')}\\n"
            f"Failure Next Command: {data.get('failure_next_command', '')}"
        )

    if intent == "status":
        return (
            "Primary Answer: current Project Brain status.\\n"
            f"Status: {data.get('status', '')}\\n"
            f"Blocker/Risk: {data.get('blocker', '')}\\n"
            f"Best Move: {data.get('best_move', '')}\\n"
            f"Exact Next Command: {data.get('exact_next_command', '')}"
        )

    return (
        "Primary Answer: next best Project Brain move.\\n"
        f"Best Move: {data.get('best_move', '')}\\n"
        f"Why: {data.get('why', '')}\\n"
        f"Risk: {data.get('risk', '')}\\n"
        f"Exact Next Command: {data.get('exact_next_command', '')}\\n"
        f"Target Files: {target_files}"
    )


def format_project_brain_command_center(card: ProjectBrainCommandCenterCard | dict[str, Any]) -> str:
    data = card.to_dict() if isinstance(card, ProjectBrainCommandCenterCard) else dict(card)

    focused_smokes = _join(data.get("focused_smokes", []))
    target_files = _join(data.get("target_files", []))
    avoid_rules = _join(data.get("avoid_rules", []))
    primary = _command_center_primary_section(data)

    return (
        "Project Brain Command Center:\\n"
        "Command Center v2 Intent Console\\n"
        f"Command intent: {data.get('command_intent', '')}\\n"
        f"{primary}\\n"
        "\\n"
        "Command Center Contract:\\n"
        f"Status: {data.get('status', '')}\\n"
        f"Blocker/Risk: {data.get('blocker', '')}\\n"
        f"Best Move: {data.get('best_move', '')}\\n"
        f"Why: {data.get('why', '')}\\n"
        f"Risk: {data.get('risk', '')}\\n"
        f"Exact Next Command: {data.get('exact_next_command', '')}\\n"
        f"Focused Smokes: {focused_smokes}\\n"
        f"Smoke Selector Reason: {data.get('smoke_reason', '')}\\n"
        f"Target Files: {target_files}\\n"
        f"Avoid Rules: {avoid_rules}\\n"
        f"Stop Rule: {data.get('stop_rule', '')}\\n"
        f"Loop Guard: {data.get('loop_guard', '')}\\n"
        f"Failure Type: {data.get('failure_type', '')}\\n"
        f"Failure Severity: {data.get('failure_severity', '')}\\n"
        f"Failure Patch Target: {data.get('failure_patch_target', '')}\\n"
        f"Failure Next Command: {data.get('failure_next_command', '')}\\n"
        f"Recent Changes: {data.get('recent_changes', '')}"
    )
'''

if anchor not in text:
    raise SystemExit("could not find command center formatter anchor")

text = text.replace(anchor, replacement, 1)

TARGET.write_text(text, encoding="utf-8")

print("patched Command Center v2 Intent Console")
