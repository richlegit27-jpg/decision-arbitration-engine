
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
    assert_true("radar best auto debug", best.name == "Patch Planner v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first auto debug", move_value(moves[0], "name") == "Patch Planner v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended auto debug", recommended_move == "Patch Planner v1", recommended_move)
    assert_true("recommended why classify tracebacks", "Turn failures into bounded file-level patch plans" in why, why)
    assert_true("recommended risk valid", risk in {"low", "medium", "high"}, risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_patch_planner.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN AUTO-DEBUG BRAIN SMOKE PASSED")


if __name__ == "__main__":
    main()
