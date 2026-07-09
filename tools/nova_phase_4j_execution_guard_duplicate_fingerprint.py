from pathlib import Path
import hashlib
import re
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

TARGET_MARKERS = [
    "NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611",
    "NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611",
]


def block_end(text, start):
    candidates = []

    for pattern in ("\n# NOVA_", "\n@app.", "\ndef ", "\nif __name__"):
        pos = text.find(pattern, start + 1)
        if pos != -1:
            candidates.append(pos)

    if not candidates:
        return len(text)

    return min(candidates)


def normalize_block(block):
    # Remove only line-number-sensitive whitespace noise.
    lines = [line.rstrip() for line in block.strip().splitlines()]
    return "\n".join(lines).strip()


def main():
    text = APP.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    print("=== NOVA PHASE 4J EXECUTION GUARD DUPLICATE FINGERPRINT ===")

    all_ok = True

    for marker in TARGET_MARKERS:
        print("")
        print(f"MARKER: {marker}")

        starts = []
        for match in re.finditer(re.escape("# " + marker), text):
            line_no = text[:match.start()].count("\n") + 1
            starts.append((match.start(), line_no))

        print(f"count: {len(starts)}")

        hashes = defaultdict(list)

        for index, (start, line_no) in enumerate(starts, start=1):
            end = block_end(text, start)
            block = text[start:end]
            normalized = normalize_block(block)
            digest = hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:16]
            block_lines = normalized.count("\n") + 1 if normalized else 0

            hashes[digest].append((index, line_no, block_lines))
            print(f"  #{index}: line={line_no} lines={block_lines} hash={digest}")

        print("hash groups:")
        for digest, entries in sorted(hashes.items()):
            print(f"  {digest}: {entries}")

        if len(starts) < 2:
            print(f"FAIL: expected duplicates for {marker}")
            all_ok = False

        if len(hashes) == 1:
            print("exact duplicate family: YES")
        else:
            print("exact duplicate family: NO - cleanup needs manual grouping")
            all_ok = False

    if not all_ok:
        raise SystemExit("NOVA PHASE 4J EXECUTION GUARD DUPLICATE FINGERPRINT FAILED")

    print("")
    print("NOVA PHASE 4J EXECUTION GUARD DUPLICATE FINGERPRINT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
