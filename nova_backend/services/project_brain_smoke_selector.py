
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeSelection:
    focused_smokes: tuple[str, ...]
    reason: str
    risk: str
    stop_rule: str

    def as_dict(self) -> dict:
        return {
            "focused_smokes": list(self.focused_smokes),
            "reason": self.reason,
            "risk": self.risk,
            "stop_rule": self.stop_rule,
        }


def _clean(value: str) -> str:
    return str(value or "").strip()


def _normalize_path(path: str) -> str:
    value = _clean(path).replace("\\", "/")

    for marker in ("nova_backend/", "tools/", "app.py"):
        if marker in value:
            if marker == "app.py":
                return "app.py"
            return value[value.index(marker):]

    return value


def _windows_path(path: str) -> str:
    return ".\\" + _normalize_path(path).replace("/", "\\")


def _py_files(changed_files) -> list[str]:
    result = []

    for item in changed_files or []:
        path = _normalize_path(str(item or ""))

        if path.endswith(".py"):
            result.append(path)

    return result


def _dedupe(commands: list[str]) -> tuple[str, ...]:
    result = []
    seen = set()

    for command in commands:
        value = _clean(command)

        if not value or value in seen:
            continue

        seen.add(value)
        result.append(value)

    return tuple(result)


def select_smokes(
    changed_files=None,
    failure_type: str = "",
    failing_layer: str = "",
    user_intent: str = "",
    route_risk: str = "low",
) -> SmokeSelection:
    files = [_normalize_path(item) for item in changed_files or [] if _clean(item)]
    py_files = _py_files(files)
    failure = _clean(failure_type).lower()
    layer = _clean(failing_layer).lower()
    intent = _clean(user_intent).lower()
    risk = _clean(route_risk).lower() or "low"

    commands: list[str] = []
    reason = "Default to regression when no safer focused smoke is known."
    stop_rule = "Stop after the smallest smoke set that proves the changed behavior."

    if py_files:
        commands.extend([f"python -m py_compile {_windows_path(path)}" for path in py_files])
        reason = "Changed Python files require py_compile before behavior smokes."

    if (
        "route_contract" in failure
        or "api_route" in layer
        or "route" in intent
        or "command_center_api" in intent
    ):
        commands.append(r"python .\tools\nova_project_brain_command_center_api_smoke.py")
        reason = "Route-risk changes require the focused API contract smoke."
        risk = "medium" if risk == "low" else risk

    elif (
        "operator_planner" in layer
        or "command_center" in layer
        or "general_intelligence" in layer
        or "signature_mismatch" in failure
        or "shape_mismatch" in failure
        or "missing_keyword" in failure
    ):
        commands.append(r"python .\tools\nova_project_brain_general_intelligence_command_center_smoke.py")
        reason = "Project Brain service-layer failures require the Command Center service smoke."

    elif "auto_debug" in layer or "auto-debug" in intent or "traceback" in intent:
        commands.append(r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py")
        reason = "Auto-Debug Brain changes require the focused auto-debug smoke."

    elif "smoke_selector" in layer or "self-test" in intent or "smoke" in intent:
        commands.append(r"python .\tools\nova_project_brain_smoke_selector_smoke.py")
        reason = "Smoke selector changes require the focused selector smoke."

    elif "upgrade_radar" in layer or "next upgrade" in intent:
        commands.append(r"python .\tools\nova_project_brain_upgrade_radar_smoke.py")
        reason = "Upgrade ranking changes require the focused Upgrade Radar smoke."

    if not commands:
        commands.append(r"python .\tools\nova_regression_smoke.py")

    if risk in {"medium", "high"}:
        commands.append(r"python .\tools\nova_regression_smoke.py")
        stop_rule = "Run the focused smoke first, then regression because route risk is elevated."

    return SmokeSelection(
        focused_smokes=_dedupe(commands),
        reason=reason,
        risk=risk,
        stop_rule=stop_rule,
    )


def build_smoke_selector_answer(
    changed_files=None,
    failure_type: str = "",
    failing_layer: str = "",
    user_intent: str = "",
    route_risk: str = "low",
) -> str:
    selection = select_smokes(
        changed_files=changed_files,
        failure_type=failure_type,
        failing_layer=failing_layer,
        user_intent=user_intent,
        route_risk=route_risk,
    )

    return "\n".join([
        "Project Brain Self-Test Selector:",
        "Focused Smokes:",
        *[f"- {item}" for item in selection.focused_smokes],
        f"Reason: {selection.reason}",
        f"Risk: {selection.risk}",
        f"Stop Rule: {selection.stop_rule}",
    ])


# NOVA_PROJECT_BRAIN_SMOKE_SELECTION_DICT_COMPAT_20260702
# Command Center compatibility helper.
# Keeps selector output usable by older Command Center formatting code.
def build_smoke_selection_dict(
    changed_files=None,
    failure_type: str = "",
    failing_layer: str = "",
    user_intent: str = "",
    route_risk: str = "low",
) -> dict:
    selection = select_smokes(
        changed_files=changed_files,
        failure_type=failure_type,
        failing_layer=failing_layer,
        user_intent=user_intent,
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
    }


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

