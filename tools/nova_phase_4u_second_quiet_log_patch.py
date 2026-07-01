from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

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
    text = text.replace("\ufeff", "")

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


def patch_app() -> int:
    path = ROOT / "app.py"
    text = read_text(path)
    before = text

    text = ensure_helper(text)

    replacements = {
        'print("RESTORED RUNTIME OK",': '_nova_boot_log_20260701("RESTORED RUNTIME OK",',
        'print("LAST COMPRESSED OK",': '_nova_boot_log_20260701("LAST COMPRESSED OK",',
        'print("[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",': '_nova_boot_log_20260701("[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",',
        'print("[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] wrapped endpoints:",': '_nova_boot_log_20260701("[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] wrapped endpoints:",',
        'print("[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] wrapped endpoints:",': '_nova_boot_log_20260701("[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] wrapped endpoints:",',
        'print("[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] wrapped endpoints:",': '_nova_boot_log_20260701("[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] wrapped endpoints:",',
    }

    count = 0

    for old, new in replacements.items():
        hits = text.count(old)
        if hits:
            text = text.replace(old, new)
            count += hits
            print(f"PATCH app.py: {hits} x {old}")

    if text != before:
        write_text(path, text)

    return count


def patch_chat_service() -> int:
    path = ROOT / "nova_backend" / "services" / "chat_service.py"
    text = read_text(path)
    before = text

    text = ensure_helper(text)

    old = '''    print(
        "[NOVA_FINAL_LIVE_MARKET_PRICE_ALL_ROUTE_AUTHORITY_20260630] installed:",
        ",".join(_nova_all_live_market_price_installed_20260630) or "none",
    )'''

    new = '''    _nova_boot_log_20260701(
        "[NOVA_FINAL_LIVE_MARKET_PRICE_ALL_ROUTE_AUTHORITY_20260630] installed:",
        ",".join(_nova_all_live_market_price_installed_20260630) or "none",
    )'''

    count = text.count(old)

    if count:
        text = text.replace(old, new)
        print(f"PATCH chat_service.py: {count} x live market all installed")

    if text != before:
        write_text(path, text)

    return count


def patch_artifact_service() -> int:
    path = ROOT / "nova_backend" / "services" / "artifact_service.py"
    text = read_text(path)
    before = text

    text = ensure_helper(text)

    old = 'print("ARTIFACT FILE PATH =", self.artifacts_file)'
    new = '_nova_boot_log_20260701("ARTIFACT FILE PATH =", self.artifacts_file)'

    count = text.count(old)

    if count:
        text = text.replace(old, new)
        print(f"PATCH artifact_service.py: {count} x artifact file path")

    if text != before:
        write_text(path, text)

    return count


def patch_chat_execution_service() -> int:
    path = ROOT / "nova_backend" / "services" / "chat_execution_service.py"
    text = read_text(path)
    before = text

    text = ensure_helper(text)

    replacements = {
        'print("[NOVA_EXECUTION_CANCEL_COMPAT_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_EXECUTION_CANCEL_COMPAT_20260630] installed")',
    }

    count = 0

    for old, new in replacements.items():
        hits = text.count(old)
        if hits:
            text = text.replace(old, new)
            count += hits
            print(f"PATCH chat_execution_service.py: {hits} x {old}")

    old_block = '''        print(
            "[NOVA_EXECUTION_EMPTY_COMPLETE_NORMALIZER_20260630] installed:",
            ",".join(_nova_execution_normalized_methods_20260630) or "none",
        )'''

    new_block = '''        _nova_boot_log_20260701(
            "[NOVA_EXECUTION_EMPTY_COMPLETE_NORMALIZER_20260630] installed:",
            ",".join(_nova_execution_normalized_methods_20260630) or "none",
        )'''

    hits = text.count(old_block)

    if hits:
        text = text.replace(old_block, new_block)
        count += hits
        print("PATCH chat_execution_service.py: 1 x empty complete normalizer installed")

    if text != before:
        write_text(path, text)

    return count


def main():
    total = 0
    total += patch_app()
    total += patch_chat_service()
    total += patch_artifact_service()
    total += patch_chat_execution_service()

    if total <= 0:
        raise SystemExit("No Phase 4U replacements happened")

    print("")
    print(f"NOVA PHASE 4U SECOND QUIET LOG PATCH DONE replacements={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
