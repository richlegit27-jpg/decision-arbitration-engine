from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

HELPER = '''
def _nova_boot_log_20260701(*args, **kwargs):
    import os as _nova_boot_log_os_20260701

    if str(_nova_boot_log_os_20260701.getenv("NOVA_VERBOSE_BOOT_LOGS", "")).strip().lower() in {"1", "true", "yes", "on"}:
        print(*args, **kwargs)


'''


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace").replace("\ufeff", "")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.replace("\ufeff", ""), encoding="utf-8")


def ensure_helper(text: str) -> str:
    if "def _nova_boot_log_20260701(" in text:
        return text

    future = "from __future__ import annotations"

    if future in text:
        future_start = text.index(future)
        future_end = text.find("\n", future_start)

        if future_end == -1:
            future_end = len(text)

        return text[:future_end + 1] + "\n" + HELPER + text[future_end + 1:]

    return HELPER + text


def main():
    text = read_text(APP)
    before = text
    text = ensure_helper(text)

    replacements = {
        'print(\n    "RESTORED RUNTIME OK",':
            '_nova_boot_log_20260701(\n    "RESTORED RUNTIME OK",',
        'print(\n    "LAST COMPRESSED OK",':
            '_nova_boot_log_20260701(\n    "LAST COMPRESSED OK",',
        '    print(\n        "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",':
            '    _nova_boot_log_20260701(\n        "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",',
        '    print(\n        "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] wrapped endpoints:",':
            '    _nova_boot_log_20260701(\n        "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] wrapped endpoints:",',
        '    print(\n        "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] wrapped endpoints:",':
            '    _nova_boot_log_20260701(\n        "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] wrapped endpoints:",',
        '    print(\n        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] wrapped endpoints:",':
            '    _nova_boot_log_20260701(\n        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] wrapped endpoints:",',
        'print("DEBUG GOAL:", _nova_exec_user_text)':
            '_nova_boot_log_20260701("DEBUG GOAL:", _nova_exec_user_text)',
        'print("DEBUG CLEAN:", _nova_exec_clean)':
            '_nova_boot_log_20260701("DEBUG CLEAN:", _nova_exec_clean)',
        'print("DEBUG LOWER:", _nova_goal_lower)':
            '_nova_boot_log_20260701("DEBUG LOWER:", _nova_goal_lower)',
    }

    total = 0

    for old, new in replacements.items():
        count = text.count(old)

        if count:
            text = text.replace(old, new)
            total += count
            print(f"PATCH app.py: {count} x {old.splitlines()[0]}")

    if total <= 0:
        raise SystemExit("No Phase 4V app debug/status replacements happened")

    if text != before:
        write_text(APP, text)

    print("")
    print(f"NOVA PHASE 4V APP DEBUG STATUS LOG PATCH DONE replacements={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
