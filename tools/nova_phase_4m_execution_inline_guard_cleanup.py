from __future__ import annotations

from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

OWNER_FUNCTION = "api_chat"

REMOVE_FROM_FUNCTIONS = {
    "api_chat",
}

COMMAND_MARKER = "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611"
FORMATTER_MARKER = "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def function_source(lines, fn):
    return "".join(lines[fn.lineno - 1:fn.end_lineno])


def first_real_stmt(fn):
    if not fn.body:
        return None

    first = fn.body[0]

    # Skip function docstring if one exists.
    if (
        isinstance(first, ast.Expr)
        and isinstance(getattr(first, "value", None), ast.Constant)
        and isinstance(first.value.value, str)
        and len(fn.body) > 1
    ):
        return fn.body[1]

    return first


def marker_start_line(lines, fn, stmt):
    start = stmt.lineno

    for line_no in range(fn.lineno, fn.end_lineno + 1):
        if COMMAND_MARKER in lines[line_no - 1]:
            return line_no

    return None


def main():
    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)

    removals = []

    owner = find_function(tree, OWNER_FUNCTION)
    assert_true("owner function exists", owner is not None, OWNER_FUNCTION)

    owner_text = function_source(lines, owner)
    assert_true("owner keeps command marker", COMMAND_MARKER in owner_text)
    assert_true("owner keeps formatter marker", FORMATTER_MARKER in owner_text)

    for fn_name in sorted(REMOVE_FROM_FUNCTIONS):
        fn = find_function(tree, fn_name)
        assert_true(f"{fn_name} exists", fn is not None)

        stmt = first_real_stmt(fn)
        assert_true(f"{fn_name} has body", stmt is not None)

        fn_text = function_source(lines, fn)

        if COMMAND_MARKER not in fn_text and FORMATTER_MARKER not in fn_text:
            print(f"SKIP {fn_name}: no execution guard markers")
            continue

        assert_true(
            f"{fn_name} first statement is guard try",
            isinstance(stmt, ast.Try),
            f"first={type(stmt).__name__}",
        )

        source = function_source(lines, fn)

        assert_true(
            f"{fn_name} contains execution command variables",
            "_nova_exec_payload2" in source
            and "_nova_exec_commands2" in source,
        )

        start_line = marker_start_line(lines, fn, stmt)
        assert_true(f"{fn_name} marker start found", start_line is not None)

        end_line = stmt.end_lineno
        assert_true(f"{fn_name} end line found", end_line is not None)

        removals.append((start_line, end_line, fn_name))


    assert_true("removals found", len(removals) == len(REMOVE_FROM_FUNCTIONS), removals)

    for start_line, end_line, fn_name in sorted(removals, reverse=True):
        print(f"REMOVE {fn_name}: lines {start_line}-{end_line}")
        del lines[start_line - 1:end_line]

    new_text = "".join(lines)
    ast.parse(new_text)

    APP.write_text(new_text, encoding="utf-8")

    final_text = APP.read_text(encoding="utf-8", errors="replace")
    assert_true("command marker count now one", final_text.count(COMMAND_MARKER) == 1)
    assert_true("formatter marker count now one", final_text.count(FORMATTER_MARKER) == 1)

    print("")
    print("NOVA PHASE 4M EXECUTION INLINE GUARD CLEANUP DONE")


if __name__ == "__main__":
    main()
