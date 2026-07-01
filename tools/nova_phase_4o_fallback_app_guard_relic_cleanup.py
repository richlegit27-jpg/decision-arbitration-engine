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


def merge_ranges(ranges):
    if not ranges:
        return []

    ranges = sorted(ranges)
    merged = [ranges[0]]

    for start, end, labels in ranges[1:]:
        prev_start, prev_end, prev_labels = merged[-1]

        if start <= prev_end + 1:
            merged[-1] = (
                prev_start,
                max(prev_end, end),
                sorted(set(prev_labels + labels)),
            )
        else:
            merged.append((start, end, labels))

    return merged


def main():
    assert_true("app.py exists", APP.exists())

    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    plain_lines = text.splitlines()

    tree = ast.parse(text)

    removals = []

    for stmt in tree.body:
        stmt_start = getattr(stmt, "lineno", None)
        stmt_end = getattr(stmt, "end_lineno", None)

        if stmt_start is None or stmt_end is None:
            continue

        start = leading_comment_start(plain_lines, stmt_start)
        block_text = "".join(lines[start - 1:stmt_end])

        found = [
            relic
            for relic in FORBIDDEN_RELICS
            if relic in block_text
        ]

        if found:
            stmt_type = type(stmt).__name__
            assert_true(
                f"safe top-level relic statement type at line {stmt_start}",
                stmt_type in {"Try", "FunctionDef", "Assign", "Expr"},
                f"type={stmt_type} relics={found}",
            )
            removals.append((start, stmt_end, found))

    removals = merge_ranges(removals)

    assert_true("fallback relic removal ranges found", bool(removals))

    new_lines = list(lines)

    for start, end, labels in sorted(removals, reverse=True):
        print(f"REMOVE lines {start}-{end}: {labels}")
        del new_lines[start - 1:end]

    new_text = "".join(new_lines)

    remaining = [
        relic
        for relic in FORBIDDEN_RELICS
        if relic in new_text
    ]

    if remaining:
        print("")
        print("Remaining forbidden relic locations:")
        for relic in remaining:
            for line_no, line in enumerate(new_text.splitlines(), start=1):
                if relic in line:
                    print(f"{line_no}: {relic}: {line.strip()}")

    assert_true(
        "forbidden fallback relics removed",
        not remaining,
        f"remaining={remaining}",
    )

    ast.parse(new_text)

    runtime_text = new_text + "\n" + read_existing(SERVICE_SURFACES)

    for required in ADAPTER_REQUIRED:
        assert_true(
            f"adapter route still present {required}",
            required in runtime_text,
        )

    APP.write_text(new_text, encoding="utf-8")

    print("")
    print("NOVA PHASE 4O FALLBACK APP GUARD RELIC CLEANUP DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
