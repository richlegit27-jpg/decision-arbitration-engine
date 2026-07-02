
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
