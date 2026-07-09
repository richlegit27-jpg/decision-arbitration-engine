from pathlib import Path
from collections import defaultdict

ROOT = Path.cwd()
FILES = [
    ROOT / "app.py",
    ROOT / "nova_backend" / "services" / "chat_service.py",
]

PREFIXES = [
    "NOVA_REPAIR_PLAN",
    "NOVA_PATCH_BUILD",
    "NOVA_AUTONOMY_PLAN",
    "NOVA_PHASE4G",
    "NOVA_PHASE4F",
    "NOVA_IMAGE_ATTACHMENT_WEB_BLOCK",
    "NOVA_FINAL",
]

def collect_markers(text):
    found = defaultdict(list)

    for line_no, line in enumerate(text.splitlines(), start=1):
        for prefix in PREFIXES:
            if prefix in line:
                found[prefix].append((line_no, line.strip()))

    return found

def main():
    print("NOVA PHASE 6E GUARD DUPLICATE REVIEW")
    print("")

    for path in FILES:
        print(f"=== {path} ===")

        if not path.exists():
            print("missing")
            print("")
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        found = collect_markers(text)

        for prefix in PREFIXES:
            rows = found.get(prefix, [])
            print(f"- {prefix}: {len(rows)} occurrence(s)")

            for line_no, line in rows[:12]:
                print(f"  {line_no}: {line}")

            if len(rows) > 12:
                print(f"  ... {len(rows) - 12} more")

        print("")

    print("NOVA PHASE 6E GUARD DUPLICATE REVIEW DONE")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
