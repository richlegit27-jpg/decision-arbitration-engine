from pathlib import Path
from collections import defaultdict
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

REQUIRED_SINGLETONS = [
    "NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701",
    "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611",
    "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611",
]

FORBIDDEN_MARKERS = [
    "NOVA_PHASE4F_NORMAL_CHAT_PROJECT_STATE_BLEED_GUARD_20260701",
    "NOVA_PHASE4F_FINAL_NORMAL_CHAT_PROJECT_STATE_BLEED_GUARD_20260701",
]

EXECUTION_OWNER = "api_chat"
EXECUTION_MARKERS = [
    "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611",
    "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611",
]

NON_OWNER_EXECUTION_ENDPOINTS = {
    "api_sessions_new",
    "api_sessions_switch",
    "api_sessions_rename",
    "api_sessions_pin",
    "api_sessions_delete",
    "api_recon_analyze",
}


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def collect_marker_lines(lines):
    marker_lines = defaultdict(list)

    for line_no, line in enumerate(lines, start=1):
        if "NOVA_" not in line:
            continue

        for token in line.replace("#", " ").replace(":", " ").replace("(", " ").replace(")", " ").split():
            if token.startswith("NOVA_"):
                marker_lines[token].append(line_no)

    return marker_lines


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def function_source(lines, fn):
    return "".join(lines[fn.lineno - 1:fn.end_lineno])


def main():
    assert_true("app.py exists", APP.exists())

    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    keep_lines = text.splitlines(keepends=True)
    marker_lines = collect_marker_lines(lines)

    for marker in REQUIRED_SINGLETONS:
        locs = marker_lines.get(marker, [])
        assert_true(
            f"required singleton {marker}",
            len(locs) == 1,
            f"lines={locs}",
        )

    for marker in FORBIDDEN_MARKERS:
        locs = marker_lines.get(marker, [])
        assert_true(
            f"forbidden relic absent {marker}",
            len(locs) == 0,
            f"lines={locs}",
        )

    main_pos = text.find('if __name__ == "__main__":')
    assert_true("main block exists", main_pos != -1)

    phase4f_pos = text.find("NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701")
    assert_true("Phase 4F guard above main", phase4f_pos != -1 and phase4f_pos < main_pos)

    tree = ast.parse(text)

    owner = find_function(tree, EXECUTION_OWNER)
    assert_true("execution owner exists api_chat", owner is not None)

    owner_text = function_source(keep_lines, owner)
    for marker in EXECUTION_MARKERS:
        assert_true(
            f"execution marker owned by api_chat {marker}",
            marker in owner_text,
        )

    for fn_name in sorted(NON_OWNER_EXECUTION_ENDPOINTS):
        fn = find_function(tree, fn_name)
        assert_true(f"non-owner endpoint exists {fn_name}", fn is not None)

        fn_text = function_source(keep_lines, fn)
        for marker in EXECUTION_MARKERS:
            assert_true(
                f"execution marker absent from {fn_name} {marker}",
                marker not in fn_text,
            )

    print("")
    print("NOVA PHASE 4I GUARD STACK AUDIT SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
