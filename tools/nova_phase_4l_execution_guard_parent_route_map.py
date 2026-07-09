from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

TARGET_MARKERS = [
    "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611",
    "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611",
]

DEF_RE = re.compile(r"(?m)^def\s+([A-Za-z0-9_]+)\s*\(")
ROUTE_RE = re.compile(r"@app\.(route|get|post|put|delete|patch)\((.*?)\)")
BOUNDARY_RE = re.compile(r"(?m)^[ \t]*# NOVA_|^[ \t]*@app\.|^def |^if __name__")


def line_no_for_offset(text, offset):
    return text[:offset].count("\n") + 1


def block_end(text, start):
    match = BOUNDARY_RE.search(text, start + 1)
    return match.start() if match else len(text)


def find_parent_def(text, offset):
    defs = list(DEF_RE.finditer(text, 0, offset))
    if not defs:
        return None

    parent = defs[-1]
    name = parent.group(1)
    def_start = parent.start()
    def_line = line_no_for_offset(text, def_start)

    previous_def = defs[-2] if len(defs) >= 2 else None
    scan_start = previous_def.end() if previous_def else 0
    prefix = text[scan_start:def_start]

    routes = []
    for route_match in ROUTE_RE.finditer(prefix):
        route_line = line_no_for_offset(text, scan_start + route_match.start())
        routes.append((route_line, route_match.group(0).strip()))

    return {
        "name": name,
        "line": def_line,
        "routes": routes,
    }


def main():
    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    print("=== NOVA PHASE 4L EXECUTION GUARD PARENT ROUTE MAP ===")

    for marker in TARGET_MARKERS:
        print("")
        print("=" * 90)
        print(f"MARKER: {marker}")
        print("=" * 90)

        matches = list(re.finditer(re.escape("# " + marker), text))
        print(f"count: {len(matches)}")

        for index, match in enumerate(matches, start=1):
            start = match.start()
            start_line = line_no_for_offset(text, start)
            end = block_end(text, start)
            end_line = line_no_for_offset(text, end)
            parent = find_parent_def(text, start)

            print("")
            print(f"--- occurrence #{index} lines {start_line}-{end_line - 1} ---")
            print(f"marker: {lines[start_line - 1].strip()}")

            if parent:
                print(f"parent def: {parent['name']} at line {parent['line']}")
                if parent["routes"]:
                    print("routes/decorators:")
                    for route_line, route in parent["routes"][-8:]:
                        print(f"  {route_line}: {route}")
                else:
                    print("routes/decorators: NONE")
            else:
                print("parent def: NONE")

            print("nearby header:")
            for line_no in range(max(1, start_line - 12), start_line):
                line = lines[line_no - 1].rstrip()
                if line.strip():
                    print(f"  {line_no}: {line}")

            print("nearby tail:")
            for line_no in range(end_line, min(len(lines), end_line + 10)):
                line = lines[line_no - 1].rstrip()
                if line.strip():
                    print(f"  {line_no}: {line}")

    print("")
    print("NOVA PHASE 4L EXECUTION GUARD PARENT ROUTE MAP DONE")


if __name__ == "__main__":
    main()
