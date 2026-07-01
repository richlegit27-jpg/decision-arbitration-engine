from __future__ import annotations

from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

FORBIDDEN_RELICS = [
    "NOVA_AUTONOMY_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_autonomy_plan_goal_20260630",
    "nova_autonomy_plan_command_guard_20260630",
    "NOVA_PATCH_BUILD_COMMAND_GUARD_20260630",
    "_nova_extract_patch_build_goal_20260630",
    "nova_patch_build_command_guard_20260630",
    "NOVA_REPAIR_PLAN_COMMAND_GUARD_20260630",
    "_nova_extract_repair_plan_goal_20260630",
    "nova_repair_plan_command_guard_20260630",
]

SERVICE_SURFACES = [
    ROOT / "nova_backend" / "services" / "autonomy_command_registry.py",
    ROOT / "nova_backend" / "services" / "autonomy_command_registry_plan.py",
    ROOT / "nova_backend" / "services" / "autonomy_plan_adapter.py",
    ROOT / "nova_backend" / "services" / "patch_build_adapter.py",
    ROOT / "nova_backend" / "services" / "repair_plan_adapter.py",
]

ADAPTER_REQUIRED = [
    "autonomy_plan_command",
    "patch_build_command",
    "repair_plan_command",
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def read_existing(paths):
    chunks = []
    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def find_first_relic(lines):
    for line_no, line in enumerate(lines, start=1):
        for relic in FORBIDDEN_RELICS:
            if relic in line:
                return line_no, relic, line.rstrip()
    return None


def ast_stmt_covering_line(text, line_no):
    tree = ast.parse(text)

    candidates = []
    for stmt in tree.body:
        start = getattr(stmt, "lineno", None)
        end = getattr(stmt, "end_lineno", None)

        if start is None or end is None:
            continue

        if start <= line_no <= end:
            candidates.append(stmt)

    if not candidates:
        return None

    return sorted(candidates, key=lambda stmt: (stmt.end_lineno - stmt.lineno, stmt.lineno))[0]


def next_ast_stmt_after_line(text, line_no):
    tree = ast.parse(text)

    candidates = []
    for stmt in tree.body:
        start = getattr(stmt, "lineno", None)
        if start is not None and start > line_no:
            candidates.append(stmt)

    if not candidates:
        return None

    return sorted(candidates, key=lambda stmt: stmt.lineno)[0]


def leading_comment_start(lines, stmt_start_line):
    start = stmt_start_line
    cursor = stmt_start_line - 1

    while cursor >= 1:
        previous = lines[cursor - 1]
        stripped = previous.strip()

        if not stripped:
            start = cursor
            cursor -= 1
            continue

        if stripped.startswith("#"):
            start = cursor
            cursor -= 1
            continue

        break

    return start


def remove_range(lines, start, end, reason):
    print(f"REMOVE lines {start}-{end}: {reason}")
    del lines[start - 1:end]


def main():
    assert_true("app.py exists", APP.exists())

    original_text = APP.read_text(encoding="utf-8", errors="replace")
    ast.parse(original_text)

    lines = original_text.splitlines(keepends=True)
    removals = 0

    while True:
        text = "".join(lines)
        found = find_first_relic(lines)

        if not found:
            break

        line_no, relic, line = found
        stripped = line.strip()

        stmt = ast_stmt_covering_line(text, line_no)

        if stmt is not None:
            stmt_type = type(stmt).__name__
            assert_true(
                f"safe covering statement for {relic}",
                stmt_type in {"Try", "FunctionDef", "Assign", "Expr", "If"},
                f"type={stmt_type} line={line_no}",
            )

            start = leading_comment_start(text.splitlines(), stmt.lineno)
            end = stmt.end_lineno
            remove_range(lines, start, end, relic)
            removals += 1
            continue

        if stripped.startswith("#"):
            next_stmt = next_ast_stmt_after_line(text, line_no)

            if next_stmt is not None:
                probe_end = min(next_stmt.end_lineno, line_no + 160)
                probe_block = "".join(lines[line_no - 1:probe_end])

                if any(item in probe_block for item in FORBIDDEN_RELICS):
                    stmt_type = type(next_stmt).__name__
                    assert_true(
                        f"safe next statement for marker-only relic {relic}",
                        stmt_type in {"Try", "FunctionDef", "Assign", "Expr", "If"},
                        f"type={stmt_type} line={line_no}",
                    )
                    remove_range(lines, line_no, next_stmt.end_lineno, relic)
                    removals += 1
                    continue

            remove_range(lines, line_no, line_no, relic)
            removals += 1
            continue

        raise AssertionError(
            f"Could not safely remove relic {relic} at line {line_no}: {line}"
        )

    new_text = "".join(lines)

    remaining = [
        relic
        for relic in FORBIDDEN_RELICS
        if relic in new_text
    ]

    assert_true(
        "forbidden fallback relics removed",
        not remaining,
        f"remaining={remaining}",
    )

    ast.parse(new_text)

    runtime_text = new_text + "\n" + read_existing(SERVICE_SURFACES)

    for required in ADAPTER_REQUIRED:
        assert_true(f"adapter route still present {required}", required in runtime_text)

    assert_true("at least one removal happened", removals > 0, f"removals={removals}")

    APP.write_text(new_text, encoding="utf-8")

    print("")
    print(f"NOVA PHASE 4O FALLBACK APP GUARD RELIC CLEANUP DONE removals={removals}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
