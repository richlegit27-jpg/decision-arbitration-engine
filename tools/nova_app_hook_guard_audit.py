from pathlib import Path
import re
from collections import Counter

APP = Path("app.py")

def read():
    return APP.read_text(encoding="utf-8-sig")

def line_no(text, index):
    return text.count("\n", 0, index) + 1

def find_lines(lines, pattern):
    regex = re.compile(pattern)
    result = []
    for i, line in enumerate(lines, start=1):
        if regex.search(line):
            result.append((i, line.rstrip()))
    return result

def print_matches(title, matches, limit=80):
    print("")
    print(title)
    print("-" * len(title))
    if not matches:
        print("none")
        return
    for line_no_value, line in matches[:limit]:
        print(f"{line_no_value:5d}: {line}")
    if len(matches) > limit:
        print(f"... {len(matches) - limit} more")

def nova_markers(lines):
    result = []
    marker_regex = re.compile(r"NOVA_[A-Z0-9_]+")
    for i, line in enumerate(lines, start=1):
        found = marker_regex.findall(line)
        for marker in found:
            result.append((i, marker, line.rstrip()))
    return result

def marker_blocks(lines):
    starts = []
    for i, line in enumerate(lines):
        if re.search(r"#\s*NOVA_[A-Z0-9_]+", line):
            starts.append(i)

    blocks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        title = lines[start].strip()
        blocks.append((end - start, start + 1, title))
    return sorted(blocks, reverse=True)

def after_request_order(lines):
    result = []
    for i, line in enumerate(lines, start=1):
        if "@app.after_request" in line:
            fn = ""
            for j in range(i, min(i + 8, len(lines))):
                m = re.search(r"def\s+([A-Za-z0-9_]+)\(", lines[j])
                if m:
                    fn = m.group(1)
                    break
            result.append((i, fn, line.rstrip()))
        elif "after_request_funcs" in line:
            result.append((i, "manual_order", line.rstrip()))
    return result

def risky_response_mutators(lines):
    patterns = [
        r"response\.set_data",
        r"set_data\(",
        r"Content-Length",
        r"Content-Type",
        r"route_taken",
        r"assistant_message",
        r"active_session_id",
        r"session_id",
        r"attachments",
    ]

    result = []
    for i, line in enumerate(lines, start=1):
        for pattern in patterns:
            if re.search(pattern, line):
                result.append((i, pattern, line.rstrip()))
                break
    return result

def duplicate_marker_report(markers):
    counts = Counter(marker for _, marker, _ in markers)
    duplicates = [
        (count, marker)
        for marker, count in counts.items()
        if count > 1
    ]
    return sorted(duplicates, reverse=True)

def main():
    text = read()
    lines = text.splitlines()

    print("NOVA APP.PY HOOK / GUARD AUDIT")
    print("==============================")
    print(f"app.py lines: {len(lines)}")
    print(f"NOVA marker tokens: {len(nova_markers(lines))}")
    print(f"unique NOVA marker tokens: {len(set(marker for _, marker, _ in nova_markers(lines)))}")

    print("")
    print("COUNTS")
    print("------")
    counts = {
        "@app.route": len(find_lines(lines, r"@app\.route")),
        "@app.after_request": len(find_lines(lines, r"@app\.after_request")),
        "@app.before_request": len(find_lines(lines, r"@app\.before_request")),
        "after_request_funcs": len(find_lines(lines, r"after_request_funcs")),
        "response.set_data": len(find_lines(lines, r"response\.set_data")),
        "json.loads": len(find_lines(lines, r"json\.loads")),
        "route_taken": len(find_lines(lines, r"route_taken")),
        "session_id": len(find_lines(lines, r"session_id")),
        "active_session_id": len(find_lines(lines, r"active_session_id")),
        "attachments": len(find_lines(lines, r"attachments")),
        "guard": len(find_lines(lines, r"guard|GUARD")),
        "fallback": len(find_lines(lines, r"fallback|FALLBACK")),
        "wrapper": len(find_lines(lines, r"wrapper|WRAPPER")),
    }
    for key, value in counts.items():
        print(f"{key}: {value}")

    print_matches("APP ROUTES", find_lines(lines, r"@app\.route"), limit=120)
    print_matches("AFTER REQUEST HOOKS", find_lines(lines, r"@app\.after_request|after_request_funcs"), limit=120)
    print_matches("BEFORE REQUEST HOOKS", find_lines(lines, r"@app\.before_request"), limit=120)

    print("")
    print("AFTER REQUEST ORDER SIGNALS")
    print("---------------------------")
    for line, fn, raw in after_request_order(lines):
        print(f"{line:5d}: {fn or '(unknown)'} :: {raw}")

    markers = nova_markers(lines)
    dupes = duplicate_marker_report(markers)

    print("")
    print("DUPLICATE NOVA MARKERS")
    print("----------------------")
    if not dupes:
        print("none")
    else:
        for count, marker in dupes[:80]:
            print(f"{count:4d}x {marker}")

    print("")
    print("LARGEST NOVA BLOCKS")
    print("-------------------")
    for size, start, title in marker_blocks(lines)[:40]:
        print(f"{size:5d} lines from {start:5d}: {title}")

    print("")
    print("HIGH-RISK RESPONSE MUTATORS")
    print("---------------------------")
    for i, pattern, line in risky_response_mutators(lines)[:200]:
        print(f"{i:5d}: [{pattern}] {line}")

    print("")
    print("RECOMMENDED CLEANUP ORDER")
    print("-------------------------")
    print("1. Inventory after_request hooks and identify overlapping JSON response mutators.")
    print("2. Extract direct project-state recall refresh out of app.py into a service-owned finalizer.")
    print("3. Consolidate session_id / active_session_id response writing into one helper.")
    print("4. Consolidate attachment response shaping into one helper.")
    print("5. Delete or quarantine duplicate historical NOVA blocks only after smoke coverage exists.")
    print("")
    print("NOVA APP.PY HOOK / GUARD AUDIT COMPLETE")

if __name__ == "__main__":
    main()
