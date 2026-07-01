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

INTERESTING_RE = re.compile(
    r"def |ChatService\.handle|_NOVA_|print\(|route|execution|planner|command|next|continue|run step|run all|stop|cancel",
    re.IGNORECASE,
)


def line_no_for_offset(text, offset):
    return text[:offset].count("\n") + 1


def block_end(text, start):
    match = BOUNDARY_RE.search(text, start + 1)
    return match.start() if match else len(text)


def main():
    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    print("=== NOVA PHASE 4J EXECUTION GUARD DUPLICATE REPORT ===")

    for marker in TARGET_MARKERS:
        print("")
        print("=" * 90)
        print(f"MARKER: {marker}")
        print("=" * 90)

        matches = list(re.finditer(re.escape(marker), text))
        print(f"count: {len(matches)}")

        for index, match in enumerate(matches, start=1):
            start = match.start()
            end = block_end(text, start)
            start_line = line_no_for_offset(text, start)
            end_line = line_no_for_offset(text, end)

            block_lines = lines[start_line - 1:end_line - 1]
            interesting = []

            for offset, line in enumerate(block_lines, start=start_line):
                if INTERESTING_RE.search(line):
                    interesting.append((offset, line.rstrip()))

            print("")
            print(f"--- occurrence #{index} lines {start_line}-{end_line - 1} ({len(block_lines)} lines) ---")
            print("marker line:")
            print(f"{start_line}: {lines[start_line - 1].rstrip()}")

            print("")
            print("interesting lines:")
            for line_no, line in interesting[:80]:
                print(f"{line_no}: {line}")

            if len(interesting) > 80:
                print(f"... truncated {len(interesting) - 80} more interesting lines")

            print("")
            print("tail:")
            for line_no in range(max(start_line, end_line - 8), end_line):
                print(f"{line_no}: {lines[line_no - 1].rstrip()}")

    print("")
    print("NOVA PHASE 4J EXECUTION GUARD DUPLICATE REPORT DONE")


if __name__ == "__main__":
    main()
