from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_patch_planner.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_patch_planner_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from dataclasses import dataclass

from nova_backend.services.project_brain_auto_debug_brain import (
    AutoDebugReport,
    classify_traceback,
)
from nova_backend.services.project_brain_smoke_selector import select_smokes


@dataclass(frozen=True)
class PatchPlan:
    title: str
    failure_type: str
    target_file: str
    broken_symbol: str
    patch_move: str
    guardrails: tuple[str, ...]
    focused_smokes: tuple[str, ...]
    stop_rule: str
    risk: str
    evidence: str

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "failure_type": self.failure_type,
            "target_file": self.target_file,
            "broken_symbol": self.broken_symbol,
            "patch_move": self.patch_move,
            "guardrails": list(self.guardrails),
            "focused_smokes": list(self.focused_smokes),
            "stop_rule": self.stop_rule,
            "risk": self.risk,
            "evidence": self.evidence,
        }


def _report_from_input(pasted_output: str = "", report: AutoDebugReport | None = None) -> AutoDebugReport:
    if report is not None:
        return report
    return classify_traceback(pasted_output)


def _patch_move_for_failure(report: AutoDebugReport) -> str:
    if report.failure_type == "signature_mismatch":
        return "Patch the active wrapper/function signature to accept the caller keyword and forward safely."

    if report.failure_type == "missing_keyword_only_argument":
        return "Forward the missing keyword-only argument with a safe default at the service boundary."

    if report.failure_type == "keyword_only_called_positionally":
        return "Convert the helper call to explicit keyword arguments."

    if report.failure_type == "shape_mismatch":
        return "Add a dict/object-safe accessor before reading fields from returned moves."

    if report.failure_type == "route_contract_failure":
        return "Patch the service-level route gate/classifier, then prove the API route contract."

    if report.failure_type == "syntax_error":
        return "Fix syntax first and run py_compile before behavior smokes."

    return "Patch the smallest failing service layer shown by the final traceback frame."


def _guardrails_for_report(report: AutoDebugReport) -> tuple[str, ...]:
    guardrails = [
        "Do not add a new app.py route guard unless the failing layer is explicitly api_route_gate.",
        "Keep the patch service-level and focused on the failing symbol.",
        "Run the smallest focused smoke before regression.",
    ]

    if report.target_file == "app.py" or report.failing_layer == "api_route_gate":
        guardrails[0] = "Route-risk patch allowed only if the API smoke proves the protected route contract."

    return tuple(guardrails)


def build_patch_plan(
    pasted_output: str = "",
    report: AutoDebugReport | None = None,
    changed_files=None,
    user_intent: str = "",
    route_risk: str = "",
) -> PatchPlan:
    debug_report = _report_from_input(pasted_output=pasted_output, report=report)

    files = list(changed_files or [])
    if debug_report.target_file and debug_report.target_file not in files:
        files.insert(0, debug_report.target_file)

    smoke_selection = select_smokes(
        changed_files=files,
        failure_type=debug_report.failure_type,
        failing_layer=debug_report.failing_layer,
        user_intent=user_intent or debug_report.failing_layer,
        route_risk=route_risk or debug_report.risk,
    )

    return PatchPlan(
        title="Project Brain Patch Planner v1",
        failure_type=debug_report.failure_type,
        target_file=debug_report.target_file,
        broken_symbol=debug_report.broken_symbol,
        patch_move=_patch_move_for_failure(debug_report),
        guardrails=_guardrails_for_report(debug_report),
        focused_smokes=tuple(smoke_selection.focused_smokes),
        stop_rule=smoke_selection.stop_rule,
        risk=smoke_selection.risk,
        evidence=debug_report.evidence,
    )


def build_patch_plan_dict(
    pasted_output: str = "",
    changed_files=None,
    user_intent: str = "",
    route_risk: str = "",
) -> dict:
    return build_patch_plan(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_intent=user_intent,
        route_risk=route_risk,
    ).as_dict()


def build_patch_planner_answer(
    pasted_output: str = "",
    changed_files=None,
    user_intent: str = "",
    route_risk: str = "",
) -> str:
    plan = build_patch_plan(
        pasted_output=pasted_output,
        changed_files=changed_files,
        user_intent=user_intent,
        route_risk=route_risk,
    )

    return "\n".join([
        "Project Brain Patch Planner:",
        f"Failure Type: {plan.failure_type}",
        f"Target File: {plan.target_file}",
        f"Broken Symbol: {plan.broken_symbol}",
        f"Patch Move: {plan.patch_move}",
        "Guardrails:",
        *[f"- {item}" for item in plan.guardrails],
        "Focused Smokes:",
        *[f"- {item}" for item in plan.focused_smokes],
        f"Stop Rule: {plan.stop_rule}",
        f"Risk: {plan.risk}",
        f"Evidence: {plan.evidence}",
    ])
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_PATCH_PLANNER_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_PATCH_PLANNER_NEXT_V1_20260702
# After Self-Test Selector is locked, rank Patch Planner as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Patch Planner v1",
            why=(
                "Turn failures into bounded file-level patch plans with target file, likely cause, "
                "guardrails, focused smokes, and stop rule without adding new app.py route guards."
            ),
            risk="medium",
            score=130,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Operator Command Launcher v1",
            why="Convert Command Center recommendations into exact operator command blocks.",
            risk="medium",
            score=120,
            target_files=(
                "nova_backend/services/project_brain_operator_command_launcher.py",
                "tools/nova_project_brain_operator_command_launcher_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_operator_command_launcher_smoke.py",
            ),
            loses_to_best_because="Patch Planner should land first so launched commands are based on bounded patch plans.",
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why="Self-Test Selector is locked; keep it as the smoke decision layer.",
            risk="low",
            score=90,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Patch Planner v1.",
        ),
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why="Auto-Debug Brain is locked; keep it as the traceback classifier.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
            loses_to_best_because="Already locked.",
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
    print("patched Upgrade Radar to rank Patch Planner next")
else:
    print("Patch Planner next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_patch_planner import (
    build_patch_plan,
    build_patch_plan_dict,
    build_patch_planner_answer,
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
    print("NOVA PROJECT BRAIN PATCH PLANNER SMOKE")
    print("======================================")

    signature_trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 304, in build_operator_plan
    moves = rank_moves(work_type, changed_files=changed_files)
TypeError: rank_moves() got an unexpected keyword argument 'changed_files'
"""

    plan = build_patch_plan(
        pasted_output=signature_trace,
        user_intent="command center",
        route_risk="low",
    )
    plan_dict = build_patch_plan_dict(
        pasted_output=signature_trace,
        user_intent="command center",
        route_risk="low",
    )
    answer = build_patch_planner_answer(
        pasted_output=signature_trace,
        user_intent="command center",
        route_risk="low",
    )

    assert_true("plan title", plan.title == "Project Brain Patch Planner v1", plan.title)
    assert_true("signature failure carried", plan.failure_type == "signature_mismatch", plan.failure_type)
    assert_true("target file carried", plan.target_file == "nova_backend/services/project_brain_operator_planner.py", plan.target_file)
    assert_true("patch move signature", "signature" in plan.patch_move or "keyword" in plan.patch_move, plan.patch_move)
    assert_true("guardrail service level", any("service-level" in item for item in plan.guardrails), plan.guardrails)
    assert_true("py compile included", any("py_compile" in item for item in plan.focused_smokes), plan.focused_smokes)
    assert_true("command center smoke included", any("general_intelligence_command_center_smoke" in item for item in plan.focused_smokes), plan.focused_smokes)
    assert_true("dict focused smokes", bool(plan_dict.get("focused_smokes")), plan_dict)
    assert_true("answer title", "Project Brain Patch Planner" in answer)
    assert_true("answer patch move", "Patch Move" in answer)

    route_trace = "AssertionError: command center route FAILED chat"
    route_plan = build_patch_plan(
        pasted_output=route_trace,
        changed_files=["app.py"],
        user_intent="command_center_api",
        route_risk="medium",
    )

    assert_true("route failure carried", route_plan.failure_type == "route_contract_failure", route_plan.failure_type)
    assert_true("route api smoke included", any("command_center_api_smoke" in item for item in route_plan.focused_smokes), route_plan.focused_smokes)
    assert_true("route regression included", any("nova_regression_smoke" in item for item in route_plan.focused_smokes), route_plan.focused_smokes)
    assert_true("route risk medium", route_plan.risk == "medium", route_plan.risk)

    best = select_best_upgrade()
    assert_true("radar best patch planner", best.name == "Patch Planner v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first patch planner", move_value(moves[0], "name") == "Patch Planner v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended patch planner", recommended_move == "Patch Planner v1", recommended_move)
    assert_true("recommended why patch plans", "patch plans" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_patch_planner.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN PATCH PLANNER SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_smoke_selector_smoke.py"),
    Path("tools/nova_project_brain_upgrade_radar_smoke.py"),
    Path("tools/nova_project_brain_auto_debug_brain_smoke.py"),
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Self-Test Selector v1", "Patch Planner v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
        r"python .\tools\nova_project_brain_patch_planner_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "Choose the smallest correct smoke set",
        "Turn failures into bounded file-level patch plans",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_smoke_selector.py",
        "nova_backend/services/project_brain_patch_planner.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Patch Planner v1")
