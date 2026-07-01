from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

LIVE_FILES = [
    ROOT / "app.py",
    ROOT / "nova_backend" / "services" / "chat_service.py",
    ROOT / "nova_backend" / "services" / "project_state_service.py",
    ROOT / "nova_backend" / "services" / "web_service.py",
    ROOT / "nova_backend" / "services" / "execution_daemon.py",
    ROOT / "nova_backend" / "services" / "safe_unified_runtime.py",
    ROOT / "nova_backend" / "services" / "python_runner_service.py",
]

PRINT_RE = re.compile(r"print\s*\(")
MARKER_RE = re.compile(r"\[(NOVA|Nova)[^\]]+\]")

BOOT_HINTS = [
    "installed",
    "wrapped",
    "forced",
    "loaded",
    "configured",
    "rebound",
    "ready",
    "active",
    "ARTIFACT FILE PATH",
    "RESTORED RUNTIME",
    "LAST COMPRESSED",
]

DEBUG_HINTS = [
    "DEBUG",
    "FAILED",
    "ERROR",
    "COUNT",
    "decision",
    "GOAL",
    "CLEAN",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def classify_print(line: str) -> str:
    upper = line.upper()

    if any(hint.upper() in upper for hint in BOOT_HINTS):
        return "boot"

    if any(hint.upper() in upper for hint in DEBUG_HINTS):
        return "debug/error"

    return "other"


def main():
    rows = []
    marker_counts = defaultdict(int)
    class_counts = defaultdict(int)

    for path in LIVE_FILES:
        if not path.exists():
            continue

        rel = path.relative_to(ROOT)
        lines = read_text(path).splitlines()

        for line_no, line in enumerate(lines, start=1):
            if "print" not in line:
                continue

            if not PRINT_RE.search(line):
                continue

            marker_match = MARKER_RE.search(line)
            marker = marker_match.group(0) if marker_match else ""
            category = classify_print(line)

            rows.append(
                {
                    "file": str(rel),
                    "line": line_no,
                    "category": category,
                    "marker": marker,
                    "text": line.strip(),
                }
            )

            class_counts[category] += 1

            if marker:
                marker_counts[marker] += 1

    print("NOVA PHASE 4T LIVE BOOT LOG INVENTORY")
    print("")
    print(f"Live files scanned: {len([path for path in LIVE_FILES if path.exists()])}")
    print(f"Print statements found: {len(rows)}")
    print("")

    print("Print categories:")
    for category, count in sorted(class_counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"- {count:03d} {category}")

    print("")
    print("Top marker groups:")
    for marker, count in sorted(marker_counts.items(), key=lambda item: (-item[1], item[0]))[:40]:
        print(f"- {count:03d} {marker}")

    print("")
    print("Boot-like print locations:")
    for row in rows:
        if row["category"] != "boot":
            continue

        marker = f" {row['marker']}" if row["marker"] else ""
        print(f"{row['file']}:{row['line']}:{marker} {row['text']}")

    print("")
    print("Debug/error print locations:")
    for row in rows:
        if row["category"] != "debug/error":
            continue

        marker = f" {row['marker']}" if row["marker"] else ""
        print(f"{row['file']}:{row['line']}:{marker} {row['text']}")

    print("")
    print("NOVA PHASE 4T LIVE BOOT LOG INVENTORY DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
