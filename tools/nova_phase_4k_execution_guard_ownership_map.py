from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

TARGET_MARKERS = [
    "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611",
    "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611",
]

BOUNDARY_RE = re.compile(
    r"(?m)^[ \t]*# NOVA_|^[ \t]*@app\.|^def |^if __name__"
)

PATTERNS = {
    "backup_assignments": re.compile(r"(_NOVA_[A-Z0-9_]+)\s*=\s*ChatService\.handle"),
    "handle_assignments": re.compile(r"ChatService\.handle\s*=\s*([A-Za-z0-9_]+)"),
    "wrapper_defs": re.compile(r"def\s+([A-Za-z0-9_]+)\s*\("),
    "backup_calls": re.compile(r"(_NOVA_[A-Z0-9_]+)\s*\("),
    "prints": re.compile(r"print\((.*?)\)"),
}


def line_no_for_offset(text, offset):
    return text[:offset].count("\n") + 1


def block_end(text, start):
    match = BOUNDARY_RE.search(text, start + 1)
    return match.start() if match else len(text)


def compact(value):
    value = " ".join(str(value).split())
    return value[:180]


def scan_block(block):
    found = {}

    for name, pattern in PATTERNS.items():
        found[name] = []
        for match in pattern.finditer(block):
            found[name].append(match.group(1))

    return found


def main():
    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    print("=== NOVA PHASE 4K EXECUTION GUARD OWNERSHIP MAP ===")

    for marker in TARGET_MARKERS:
        print("")
        print("=" * 90)
        print(f"MARKER: {marker}")
        print("=" * 90)

        starts = []
        for match in re.finditer(re.escape("# " + marker), text):
            starts.append((match.start(), line_no_for_offset(text, match.start())))

        print(f"count: {len(starts)}")

        for index, (start, start_line) in enumerate(starts, start=1):
            end = block_end(text, start)
            end_line = line_no_for_offset(text, end)
            block = text[start:end]
            found = scan_block(block)

            print("")
            print(f"--- occurrence #{index} lines {start_line}-{end_line - 1} ---")
            print(f"marker: {lines[start_line - 1].strip()}")

            wrapper_defs = found["wrapper_defs"]
            backup_assignments = found["backup_assignments"]
            handle_assignments = found["handle_assignments"]
            backup_calls = found["backup_calls"]
            prints = [compact(p) for p in found["prints"]]

            print(f"wrapper defs: {wrapper_defs or 'NONE'}")
            print(f"backs up ChatService.handle into: {backup_assignments or 'NONE'}")
            print(f"sets ChatService.handle to: {handle_assignments or 'NONE'}")
            print(f"calls backup handle vars: {backup_calls or 'NONE'}")
            print(f"install/error prints: {prints or 'NONE'}")

            if handle_assignments:
                print("classification: WRAPPER OWNER CANDIDATE")
            elif wrapper_defs:
                print("classification: HELPER / INLINE FORMATTER CANDIDATE")
            else:
                print("classification: UNKNOWN / NEED MANUAL REVIEW")

    print("")
    print("NOVA PHASE 4K EXECUTION GUARD OWNERSHIP MAP DONE")


if __name__ == "__main__":
    main()
