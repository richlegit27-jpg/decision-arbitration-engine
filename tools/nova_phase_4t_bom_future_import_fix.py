from pathlib import Path


TARGETS = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
    Path("nova_backend/services/project_state_service.py"),
]


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    before = text

    text = text.replace("\ufeff", "")

    future = "from __future__ import annotations"
    helper_start = "def _nova_boot_log_20260701("
    helper_end_marker = "\n\n"

    if future in text and helper_start in text:
        future_index = text.index(future)
        helper_index = text.index(helper_start)

        if helper_index < future_index:
            # Extract helper block.
            helper_block_start = helper_index
            helper_block_end = text.find("\n\n\n", helper_block_start)

            if helper_block_end == -1:
                helper_block_end = text.find("\n\n", helper_block_start)

            if helper_block_end == -1:
                raise SystemExit(f"Could not locate helper block end in {path}")

            helper_block_end += 3 if text[helper_block_end:helper_block_end + 3] == "\n\n\n" else 2

            helper_block = text[helper_block_start:helper_block_end]
            text = text[:helper_block_start] + text[helper_block_end:]

            # Put helper after future import line.
            future_line_start = text.index(future)
            future_line_end = text.find("\n", future_line_start)

            if future_line_end == -1:
                future_line_end = len(text)

            text = text[:future_line_end + 1] + "\n" + helper_block + text[future_line_end + 1:]

    if text != before:
        path.write_text(text, encoding="utf-8")
        print(f"FIXED {path}")
        return True

    print(f"UNCHANGED {path}")
    return False


def main():
    changed = False

    for path in TARGETS:
        changed = fix_file(path) or changed

    if not changed:
        raise SystemExit("No files changed")

    print("NOVA PHASE 4T BOM/FUTURE IMPORT FIX DONE")


if __name__ == "__main__":
    main()
