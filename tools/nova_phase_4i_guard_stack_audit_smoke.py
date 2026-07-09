from pathlib import Path
from collections import Counter, defaultdict
import re

APP_PATH = Path("app.py")


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def line_number(text, index):
    return text.count("\n", 0, index) + 1


def main():
    text = APP_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    main_pos = text.find('if __name__ == "__main__":')
    run_pos = text.find("app.run(", main_pos if main_pos >= 0 else 0)

    assert_true("__main__ block exists", main_pos >= 0)
    assert_true("app.run exists", run_pos >= 0)

    below_run = text[run_pos:] if run_pos >= 0 else ""

    risky_below_run_markers = [
        "# NOVA_",
        "@app.after_request",
        "@app.before_request",
        "app.after_request(",
        "app.before_request(",
        "app.route(",
        "@app.route",
    ]

    print("")
    print("APP RUN ORDER")
    print("=============")
    print(f"__main__ line: {line_number(text, main_pos)}")
    print(f"app.run line:  {line_number(text, run_pos)}")

    for marker in risky_below_run_markers:
        count = below_run.count(marker)
        print(f"below app.run {marker!r}: {count}")

    assert_true(
        "no late hooks below app.run",
        all(below_run.count(marker) == 0 for marker in risky_below_run_markers),
        "late executable hook/guard code exists below app.run",
    )

    nova_markers = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("# NOVA_"):
            nova_markers.append((i, stripped))

    marker_names = [m for _, m in nova_markers]
    marker_counts = Counter(marker_names)

    print("")
    print("NOVA MARKERS")
    print("============")
    print(f"total NOVA marker comments: {len(nova_markers)}")
    print(f"unique NOVA marker comments: {len(marker_counts)}")

    duplicates = [(name, count) for name, count in marker_counts.items() if count > 1]
    if duplicates:
        print("")
        print("DUPLICATE MARKERS")
        print("=================")
        for name, count in sorted(duplicates, key=lambda item: (-item[1], item[0])):
            print(f"{count}x {name}")

    assert_true(
        "no duplicate NOVA markers",
        not duplicates,
        f"duplicates={duplicates}",
    )


    assert_true(
        "no duplicate NOVA markers",
        not duplicates,
        f"duplicates={duplicates}",
    )


    assert_true(
        "no duplicate NOVA markers",
        not duplicates,
        f"duplicates={duplicates}",
    )


    hooks = {
        "@app.after_request": [],
        "@app.before_request": [],
        "@app.route": [],
        "app.after_request(": [],
        "app.before_request(": [],
    }

    for i, line in enumerate(lines, start=1):
        for hook in hooks:
            if hook in line:
                hooks[hook].append(i)

    print("")
    print("HOOK COUNTS")
    print("===========")
    for hook, found_lines in hooks.items():
        print(f"{hook}: {len(found_lines)}")
        if found_lines:
            print(f"  lines: {found_lines[:30]}{' ...' if len(found_lines) > 30 else ''}")

    installed_patterns = defaultdict(list)
    for i, line in enumerate(lines, start=1):
        if "installed" in line and "NOVA_" in line:
            cleaned = line.strip()
            installed_patterns[cleaned].append(i)

    repeated_installs = {
        key: value
        for key, value in installed_patterns.items()
        if len(value) > 1
    }

    print("")
    print("REPEATED INSTALL LOG LINES")
    print("==========================")
    if repeated_installs:
        for key, value in sorted(repeated_installs.items(), key=lambda item: (-len(item[1]), item[0])):
            print(f"{len(value)}x lines={value}: {key[:180]}")
    else:
        print("none")

    suspicious_terms = [
        "FINAL",
        "GUARD",
        "WRAPPER",
        "BYPASS",
        "PATCH",
        "FALLBACK",
        "RECALL",
        "PROJECT_STATE",
        "AUTONOMY",
        "REPAIR_PLAN",
    ]

    buckets = defaultdict(list)
    for i, marker in nova_markers:
        upper = marker.upper()
        for term in suspicious_terms:
            if term in upper:
                buckets[term].append((i, marker))

    print("")
    print("GUARD STACK BUCKETS")
    print("===================")
    for term in suspicious_terms:
        items = buckets.get(term, [])
        print(f"{term}: {len(items)}")
        for line_no, marker in items[:12]:
            print(f"  line {line_no}: {marker[:160]}")
        if len(items) > 12:
            print("  ...")

    print("")
    print("NOVA PHASE 4I GUARD STACK AUDIT SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
