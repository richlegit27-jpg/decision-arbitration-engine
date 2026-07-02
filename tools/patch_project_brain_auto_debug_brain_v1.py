from pathlib import Path

SERVICE = Path("nova_backend/services/project_brain_auto_debug_brain.py")
RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_project_brain_auto_debug_brain_smoke.py")

SERVICE.parent.mkdir(parents=True, exist_ok=True)
SMOKE.parent.mkdir(parents=True, exist_ok=True)

SERVICE.write_text(r'''
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AutoDebugReport:
    failure_type: str
    failing_layer: str
    target_file: str
    broken_symbol: str
    likely_cause: str
    recommended_move: str
    focused_smoke: str
    risk: str
    evidence: str

    def as_dict(self) -> dict:
        return {
            "failure_type": self.failure_type,
            "failing_layer": self.failing_layer,
            "target_file": self.target_file,
            "broken_symbol": self.broken_symbol,
            "likely_cause": self.likely_cause,
            "recommended_move": self.recommended_move,
            "focused_smoke": self.focused_smoke,
            "risk": self.risk,
            "evidence": self.evidence,
        }


def normalize_path(path: str) -> str:
    value = str(path or "").replace("\\", "/").strip()

    marker = "nova_backend/"
    if marker in value:
        return value[value.index(marker):]

    marker = "tools/"
    if marker in value:
        return value[value.index(marker):]

    return value


def _extract_traceback_files(text: str) -> list[tuple[str, str]]:
    matches = re.findall(r'File "([^"]+)", line \d+, in ([^\n\r]+)', text or "")
    return [(normalize_path(path), str(symbol or "").strip()) for path, symbol in matches]


def _last_error_line(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for line in reversed(lines):
        if (
            line.startswith("TypeError:")
            or line.startswith("AttributeError:")
            or line.startswith("AssertionError:")
            or line.startswith("SyntaxError:")
            or line.startswith("ImportError:")
            or line.startswith("ModuleNotFoundError:")
            or line.startswith("NameError:")
        ):
            return line
    return lines[-1] if lines else ""


def _infer_layer(target_file: str, text: str) -> str:
    haystack = f"{target_file}\n{text}".lower()

    if "operator_planner" in haystack:
        return "operator_planner"
    if "command_center" in haystack:
        return "command_center"
    if "general_intelligence" in haystack:
        return "project_brain_general_intelligence"
    if "completed_move_filter" in haystack:
        return "completed_move_filter"
    if "app.py" in haystack or "route failed" in haystack:
        return "api_route_gate"
    if "chat_service" in haystack:
        return "chat_service"
    if "memory" in haystack:
        return "memory_service"
    if "session" in haystack:
        return "session_service"

    return "unknown"


def _focused_smoke_for_layer(layer: str) -> str:
    if layer in {"operator_planner", "command_center", "project_brain_general_intelligence"}:
        return r"python .\tools\nova_project_brain_general_intelligence_command_center_smoke.py"

    if layer == "api_route_gate":
        return r"python .\tools\nova_project_brain_command_center_api_smoke.py"

    if layer == "completed_move_filter":
        return r"python .\tools\nova_project_brain_operator_planner_smoke.py"

    return r"python .\tools\nova_regression_smoke.py"


def classify_traceback(pasted_output: str) -> AutoDebugReport:
    text = str(pasted_output or "")
    files = _extract_traceback_files(text)
    target_file = files[-1][0] if files else ""
    broken_symbol = files[-1][1] if files else ""
    error_line = _last_error_line(text)
    layer = _infer_layer(target_file, text)
    focused_smoke = _focused_smoke_for_layer(layer)

    lower = error_line.lower()

    if "got an unexpected keyword argument" in lower:
        keyword = ""
        match = re.search(r"unexpected keyword argument '([^']+)'", error_line)
        if match:
            keyword = match.group(1)

        return AutoDebugReport(
            failure_type="signature_mismatch",
            failing_layer=layer,
            target_file=target_file,
            broken_symbol=broken_symbol,
            likely_cause=f"Caller passed keyword `{keyword}` but the active function/wrapper signature does not accept it.",
            recommended_move="Add a compatibility wrapper or update the function signature without changing route behavior.",
            focused_smoke=focused_smoke,
            risk="low",
            evidence=error_line,
        )

    if "missing 1 required keyword-only argument" in lower:
        keyword = ""
        match = re.search(r"required keyword-only argument: '([^']+)'", error_line)
        if match:
            keyword = match.group(1)

        return AutoDebugReport(
            failure_type="missing_keyword_only_argument",
            failing_layer=layer,
            target_file=target_file,
            broken_symbol=broken_symbol,
            likely_cause=f"Constructor/helper now requires keyword-only `{keyword}` but a wrapper is not forwarding it.",
            recommended_move="Forward the missing keyword with a safe default and preserve the focused smoke contract.",
            focused_smoke=focused_smoke,
            risk="low",
            evidence=error_line,
        )

    if "takes 0 positional arguments" in lower and "were given" in lower:
        return AutoDebugReport(
            failure_type="keyword_only_called_positionally",
            failing_layer=layer,
            target_file=target_file,
            broken_symbol=broken_symbol,
            likely_cause="A keyword-only helper was called with positional arguments.",
            recommended_move="Convert the helper call to explicit keyword arguments.",
            focused_smoke=focused_smoke,
            risk="low",
            evidence=error_line,
        )

    if "object has no attribute" in lower:
        return AutoDebugReport(
            failure_type="shape_mismatch",
            failing_layer=layer,
            target_file=target_file,
            broken_symbol=broken_symbol,
            likely_cause="Code expects an object attribute but received a dict-shaped value.",
            recommended_move="Normalize through a dict/object-safe accessor before reading fields.",
            focused_smoke=focused_smoke,
            risk="low",
            evidence=error_line,
        )

    if "assertionerror:" in lower and "route failed" in lower:
        return AutoDebugReport(
            failure_type="route_contract_failure",
            failing_layer="api_route_gate",
            target_file=target_file or "app.py",
            broken_symbol=broken_symbol,
            likely_cause="The API route selected the wrong route for a protected Project Brain intent.",
            recommended_move="Patch the service-level route gate/classifier, then run API smoke and regression.",
            focused_smoke=r"python .\tools\nova_project_brain_command_center_api_smoke.py",
            risk="medium",
            evidence=error_line,
        )

    if "syntaxerror:" in lower:
        return AutoDebugReport(
            failure_type="syntax_error",
            failing_layer=layer,
            target_file=target_file,
            broken_symbol=broken_symbol,
            likely_cause="Python could not parse the changed file.",
            recommended_move="Fix syntax first, then run py_compile before any API smoke.",
            focused_smoke=f"python -m py_compile .\\{target_file.replace('/', '\\\\')}" if target_file else r"python -m py_compile <changed file>",
            risk="low",
            evidence=error_line,
        )

    return AutoDebugReport(
        failure_type="unknown_traceback",
        failing_layer=layer,
        target_file=target_file,
        broken_symbol=broken_symbol,
        likely_cause="Auto-Debug Brain did not match a known failure pattern yet.",
        recommended_move="Read the last traceback frame and add a new failure pattern smoke.",
        focused_smoke=focused_smoke,
        risk="medium",
        evidence=error_line,
    )


def build_auto_debug_answer(pasted_output: str) -> str:
    report = classify_traceback(pasted_output)

    return "\n".join([
        "Project Brain Auto-Debug Brain:",
        f"Failure Type: {report.failure_type}",
        f"Failing Layer: {report.failing_layer}",
        f"Target File: {report.target_file}",
        f"Broken Symbol: {report.broken_symbol}",
        f"Likely Cause: {report.likely_cause}",
        f"Recommended Move: {report.recommended_move}",
        f"Focused Smoke: {report.focused_smoke}",
        f"Risk: {report.risk}",
        f"Evidence: {report.evidence}",
    ])
''', encoding="utf-8")

if not RADAR.exists():
    raise SystemExit("missing upgrade radar service")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_PROJECT_BRAIN_AUTO_DEBUG_NEXT_V1_20260702" not in radar_text:
    block = r'''

# NOVA_PROJECT_BRAIN_AUTO_DEBUG_NEXT_V1_20260702
# After Upgrade Radar is locked, rank Auto-Debug Brain as the next gangster upgrade.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Auto-Debug Brain v1",
            why=(
                "Classify tracebacks, identify the failing service layer, name the likely broken symbol, "
                "recommend the smallest safe patch, and choose the focused smoke automatically."
            ),
            risk="medium",
            score=110,
            target_files=(
                "nova_backend/services/project_brain_auto_debug_brain.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_auto_debug_brain_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="Self-Test Selector v1",
            why="Choose the smallest correct smoke set from changed files, intent, and route risk.",
            risk="low",
            score=100,
            target_files=(
                "nova_backend/services/project_brain_smoke_selector.py",
                "tools/nova_project_brain_smoke_selector_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_smoke_selector_smoke.py",
            ),
            loses_to_best_because="Auto-Debug Brain should land first so test selection can use failure classifications.",
        ),
        UpgradeCandidate(
            name="Patch Planner v1",
            why="Turn failures into bounded file-level patch plans without adding new app.py route guards.",
            risk="medium",
            score=95,
            target_files=(
                "nova_backend/services/project_brain_patch_planner.py",
                "tools/nova_project_brain_patch_planner_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_patch_planner_smoke.py",
            ),
            loses_to_best_because="Patch Planner becomes stronger after Auto-Debug Brain names the failure pattern.",
        ),
        UpgradeCandidate(
            name="Project Brain Upgrade Radar v1",
            why="Upgrade Radar is locked; keep it as the ranking layer but do not repeat it as the next move.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_upgrade_radar.py",
                "tools/nova_project_brain_upgrade_radar_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
            ),
            loses_to_best_because="Already locked; next gangster upgrade is Auto-Debug Brain v1.",
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
    print("patched Upgrade Radar to rank Auto-Debug Brain next")
else:
    print("Auto-Debug next ranking already installed")

SMOKE.write_text(r'''
from nova_backend.services.project_brain_auto_debug_brain import (
    build_auto_debug_answer,
    classify_traceback,
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
    print("NOVA PROJECT BRAIN AUTO-DEBUG BRAIN SMOKE")
    print("=========================================")

    signature_trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 304, in build_operator_plan
    moves = rank_moves(work_type, changed_files=changed_files)
TypeError: rank_moves() got an unexpected keyword argument 'changed_files'
"""

    report = classify_traceback(signature_trace)
    answer = build_auto_debug_answer(signature_trace)

    assert_true("signature mismatch classified", report.failure_type == "signature_mismatch", report.failure_type)
    assert_true("operator planner layer", report.failing_layer == "operator_planner", report.failing_layer)
    assert_true("operator planner target", report.target_file == "nova_backend/services/project_brain_operator_planner.py", report.target_file)
    assert_true("changed_files evidence", "changed_files" in report.likely_cause, report.likely_cause)
    assert_true("focused command center smoke", "general_intelligence_command_center_smoke" in report.focused_smoke, report.focused_smoke)
    assert_true("answer title", "Project Brain Auto-Debug Brain" in answer)

    risk_trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 701, in _nova_keyword_safe_move_20260702
    return _move(rank=rank, name=name)
TypeError: _move() missing 1 required keyword-only argument: 'risk'
"""

    risk_report = classify_traceback(risk_trace)
    assert_true("missing keyword classified", risk_report.failure_type == "missing_keyword_only_argument", risk_report.failure_type)
    assert_true("risk keyword evidence", "risk" in risk_report.likely_cause, risk_report.likely_cause)

    shape_trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 883, in rank_moves
    if item.name in seen:
AttributeError: 'dict' object has no attribute 'name'
"""

    shape_report = classify_traceback(shape_trace)
    assert_true("shape mismatch classified", shape_report.failure_type == "shape_mismatch", shape_report.failure_type)
    assert_true("shape recommendation accessor", "dict/object-safe accessor" in shape_report.recommended_move, shape_report.recommended_move)

    route_trace = """
AssertionError: command center route FAILED chat
"""

    route_report = classify_traceback(route_trace)
    assert_true("route failure classified", route_report.failure_type == "route_contract_failure", route_report.failure_type)
    assert_true("route failure layer", route_report.failing_layer == "api_route_gate", route_report.failing_layer)
    assert_true("route api smoke", "command_center_api_smoke" in route_report.focused_smoke, route_report.focused_smoke)

    best = select_best_upgrade()
    assert_true("radar best auto debug", best.name == "Auto-Debug Brain v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first auto debug", move_value(moves[0], "name") == "Auto-Debug Brain v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended auto debug", recommended_move == "Auto-Debug Brain v1", recommended_move)
    assert_true("recommended why classify tracebacks", "Classify tracebacks" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_auto_debug_brain.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN AUTO-DEBUG BRAIN SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

for smoke_path in [
    Path("tools/nova_project_brain_upgrade_radar_smoke.py"),
    Path("tools/nova_project_brain_command_center_api_smoke.py"),
    Path("tools/nova_project_brain_general_intelligence_command_center_smoke.py"),
]:
    if not smoke_path.exists():
        continue

    smoke_text = smoke_path.read_text(encoding="utf-8-sig")
    smoke_text = smoke_text.replace("Project Brain Upgrade Radar v1", "Auto-Debug Brain v1")
    smoke_text = smoke_text.replace(
        r"python .\tools\nova_project_brain_upgrade_radar_smoke.py",
        r"python .\tools\nova_project_brain_auto_debug_brain_smoke.py",
    )
    smoke_text = smoke_text.replace(
        "high-impact intelligence upgrades",
        "Classify tracebacks",
    )
    smoke_text = smoke_text.replace(
        "nova_backend/services/project_brain_upgrade_radar.py",
        "nova_backend/services/project_brain_auto_debug_brain.py",
    )
    smoke_path.write_text(smoke_text, encoding="utf-8")
    print(f"patched smoke expectations: {smoke_path}")

print("installed Project Brain Auto-Debug Brain v1")
