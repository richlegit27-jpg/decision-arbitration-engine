from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_smoke_selector.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_smoke_selector_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
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
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_SELF_TEST_SELECTOR_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_SELF_TEST_SELECTOR_NEXT_V1_20260702
# After Auto-Debug Brain is locked, rank Self-Test Selector as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why=(
                "Choose the smallest correct smoke set from changed files, failure layer, "
                "intent, and route risk so Nova proves upgrades without wasting cycles."
            ),
            risk="low",
            score=120,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Turn failures into bounded file-level patch plans without adding new app.py route guards.",
            risk="medium",
            score=110,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Self-Test Selector should land first so Patch Planner can attach correct smokes to patches.",
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Convert Command Center recommendations into exact operator command blocks.",
            risk="medium",
            score=100,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
            loses_to_best_because="Launcher is stronger after Self-Test Selector decides the command list.",
        ),
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why="Auto-Debug Brain is locked; keep it available as the traceback classifier.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Self-Test Selector v1.",
        ),
        UpgradeCandidate(
            name="Project Brain Upgrade Radar v1",
            why="Upgrade Radar is locked; keep it as the ranking layer.",
            risk="low",
            score=70,
            target_files=(
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_upgrade_radar_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
            ),
            loses_to_best_because="Already locked.",
        ),
    ]


def select_best_upgrade() -> UpgradeCandidate:
    candidates = get_upgrade_candidates()
    return sorted(candidates, key=lambda item: item.score, reverse=True)[0]


def build_upgrade_radar_summary() -> str:
    candidates = get_upgrade_candidates()
    lines = ["Project Brain Upgrade Radar:"]
    for index, candidate in enumerate(sorted(candidates, key=lambda item: item.score, reverse=True), start=1):
        lines.append(f"{index}. {candidate.name} — {candidate.why}")
    return "\n".join(lines)
'''
    RADAR.write_text(radar_text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    print("patched Upgrade Radar to rank Self-Test Selector next")
else:
    print("Self-Test Selector next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_smoke_selector import (
    build_smoke_selector_answer,
    select_smokes,
)
from nova_backend.services.project_brain_upgrade_radar import select_best_upgrade
from nova_backend.services.project_brain_operator_planner import choose_recommended_move, rank_moves


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def move_value(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def main():
    print("NOVA PROJECT BRAIN SELF-TEST SELECTOR SMOKE")
    print("===========================================")

    service_selection = select_smokes(
        changed_files=[
            "nova_backend/services/project_brain_operator_planner.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ],
        failure_type="signature_mismatch",
        failing_layer="operator_planner",
        user_intent="command center",
        route_risk="low",
    )

    assert_true("py compile included", any("py_compile" in item for item in service_selection.focused_smokes), service_selection.focused_smokes)
    assert_true("service smoke included", any("general_intelligence_command_center_smoke" in item for item in service_selection.focused_smokes), service_selection.focused_smokes)
    assert_true("service reason", "Project Brain service-layer" in service_selection.reason or "Changed Python files" in service_selection.reason, service_selection.reason)

    route_selection = select_smokes(
        changed_files=["app.py"],
        failure_type="route_contract_failure",
        failing_layer="api_route_gate",
        user_intent="command_center_api",
        route_risk="medium",
    )

    assert_true("api smoke included", any("command_center_api_smoke" in item for item in route_selection.focused_smokes), route_selection.focused_smokes)
    assert_true("regression included for medium risk", any("nova_regression_smoke" in item for item in route_selection.focused_smokes), route_selection.focused_smokes)
    assert_true("medium risk preserved", route_selection.risk == "medium", route_selection.risk)

    selector_selection = select_smokes(
        changed_files=["nova_backend/services/project_brain_smoke_selector.py"],
        failing_layer="smoke_selector",
        user_intent="self-test",
        route_risk="low",
    )

    assert_true("selector smoke included", any("smoke_selector_smoke" in item for item in selector_selection.focused_smokes), selector_selection.focused_smokes)

    answer = build_smoke_selector_answer(
        changed_files=["nova_backend/services/project_brain_smoke_selector.py"],
        failing_layer="smoke_selector",
        user_intent="self-test",
    )

    assert_true("answer title", "Project Brain Self-Test Selector" in answer)
    assert_true("answer focused smokes", "Focused Smokes" in answer)

    best = select_best_upgrade()
    assert_true("radar best self-test selector", best.name == "Self-Test Selector v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first self-test", move_value(moves[0], "name") == "Self-Test Selector v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended self-test", recommended_move == "Self-Test Selector v1", recommended_move)
    assert_true("recommended why smoke set", "smoke set" in why, why)
    assert_true("recommended risk low", risk == "low", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_smoke_selector.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN SELF-TEST SELECTOR SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_upgrade_radar_smoke.py"),
    Path("tools/nova_project_brain_auto_debug_brain_smoke.py"),
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Auto-Debug Brain v1", "Self-Test Selector v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
        r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Classify tracebacks",
        "Choose the smallest correct smoke set",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_auto_debug_brain.py",
        "nova_backend/services/project_brain_smoke_selector.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Self-Test Selector v1")
