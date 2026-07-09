from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

HELPER = '''
def _nova_boot_log_20260701(*args, **kwargs):
    import os as _nova_boot_log_os_20260701

    if str(_nova_boot_log_os_20260701.getenv("NOVA_VERBOSE_BOOT_LOGS", "")).strip().lower() in {"1", "true", "yes", "on"}:
        print(*args, **kwargs)


'''


REPLACEMENTS = {
    ROOT / "app.py": {
        'print(f"[NOVA ROUTE REPAIR] /api/chat endpoint={_nova_rule.endpoint} rebound to api_chat")':
            '_nova_boot_log_20260701(f"[NOVA ROUTE REPAIR] /api/chat endpoint={_nova_rule.endpoint} rebound to api_chat")',
        'print("[NOVA AUTH] safe compat alias routes installed:", installed)':
            '_nova_boot_log_20260701("[NOVA AUTH] safe compat alias routes installed:", installed)',
        'print("[NOVA ATTACHMENT SYNC] wrapped /api/chat endpoints:", wrapped)':
            '_nova_boot_log_20260701("[NOVA ATTACHMENT SYNC] wrapped /api/chat endpoints:", wrapped)',
        'print("[NOVA_WEB_FETCH_BRIDGE_ORDER] forced bridge to run last")':
            '_nova_boot_log_20260701("[NOVA_WEB_FETCH_BRIDGE_ORDER] forced bridge to run last")',
        'print("[NOVA_FINAL_SESSION_DETAIL_CACHE] forced final hook to run last")':
            '_nova_boot_log_20260701("[NOVA_FINAL_SESSION_DETAIL_CACHE] forced final hook to run last")',
        'print("[NOVA_FINAL_TITLE_GUARD_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_TITLE_GUARD_20260630] installed")',
        'print("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] installed")',
        'print("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] installed")':
            '_nova_boot_log_20260701("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] installed")',
        'print("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] installed")':
            '_nova_boot_log_20260701("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] installed")',
        'print(f"[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] wrapped endpoints: {_nova_phase4a_wrapped_count_20260701}")':
            '_nova_boot_log_20260701(f"[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] wrapped endpoints: {_nova_phase4a_wrapped_count_20260701}")',
        'print("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] installed")':
            '_nova_boot_log_20260701("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] installed")',
        'print("[NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701] installed")':
            '_nova_boot_log_20260701("[NOVA_PHASE4G_NORMAL_CHAT_AUTONOMY_CARRYOVER_GUARD_20260701] installed")',
        'print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] forced final hook")':
            '_nova_boot_log_20260701("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] forced final hook")',
        'print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] installed")':
            '_nova_boot_log_20260701("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] installed")',
    },
    ROOT / "nova_backend" / "services" / "chat_service.py": {
        'print("[NOVA ATTACHMENT SYNC] ChatService.handle attachment text sync installed")':
            '_nova_boot_log_20260701("[NOVA ATTACHMENT SYNC] ChatService.handle attachment text sync installed")',
        'print("[Nova] non-web source leak guard installed")':
            '_nova_boot_log_20260701("[Nova] non-web source leak guard installed")',
        'print("[NOVA_FINAL_ATTACHMENT_ROUTE_BEATS_WEB_LOCK_V2_20260624] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_ATTACHMENT_ROUTE_BEATS_WEB_LOCK_V2_20260624] installed")',
        'print("[NOVA_INTENT_AUTHORITY_DECIDE_ROUTE_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_INTENT_AUTHORITY_DECIDE_ROUTE_20260630] installed")',
        'print("[NOVA_FINAL_RESPONSE_MOJIBAKE_CLEANUP_V4_20260624] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_RESPONSE_MOJIBAKE_CLEANUP_V4_20260624] installed")',
        'print("[NOVA_IMAGE_GENERATION_RESPONSE_POLISH_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_IMAGE_GENERATION_RESPONSE_POLISH_20260630] installed")',
        'print("[NOVA_IMAGE_GENERATION_RESPONSE_POLISH_20260630_FINAL] installed")':
            '_nova_boot_log_20260701("[NOVA_IMAGE_GENERATION_RESPONSE_POLISH_20260630_FINAL] installed")',
        'print("[NOVA_IMAGE_GENERATION_FINAL_TEXT_SYNC_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_IMAGE_GENERATION_FINAL_TEXT_SYNC_20260630] installed")',
        'print("[NOVA_ACCIDENTAL_INPUT_GUARD_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_ACCIDENTAL_INPUT_GUARD_20260630] installed")',
        'print("[NOVA_FINAL_LIVE_MARKET_PRICE_ROUTE_AUTHORITY_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_LIVE_MARKET_PRICE_ROUTE_AUTHORITY_20260630] installed")',
        'print("[NOVA_FINAL_LIVE_MARKET_PRICE_HANDLE_REDIRECT_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_LIVE_MARKET_PRICE_HANDLE_REDIRECT_20260630] installed")',
        'print("[NOVA_FINAL_LIVE_MARKET_PRICE_GENERAL_CHAT_ESCAPE_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_FINAL_LIVE_MARKET_PRICE_GENERAL_CHAT_ESCAPE_20260630] installed")',
        'print("[NOVA_PROJECT_STATE_RECALL_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_PROJECT_STATE_RECALL_20260630] installed")',
        'print("[NOVA_PROJECT_STATE_RECALL_FINAL_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_PROJECT_STATE_RECALL_FINAL_20260630] installed")',
        'print("[NOVA_PROJECT_STATE_IDLE_NEXT_FALLBACK_REPAIR_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_PROJECT_STATE_IDLE_NEXT_FALLBACK_REPAIR_20260630] installed")',
        'print("[NOVA_PROJECT_STATE_IDLE_NEXT_RESPONSE_REPAIR_FINAL_20260630] installed")':
            '_nova_boot_log_20260701("[NOVA_PROJECT_STATE_IDLE_NEXT_RESPONSE_REPAIR_FINAL_20260630] installed")',
    },
    ROOT / "nova_backend" / "services" / "project_state_service.py": {
        'print("[NOVA_PROJECT_STATE_COMPACT_CONTEXT_20260701] installed")':
            '_nova_boot_log_20260701("[NOVA_PROJECT_STATE_COMPACT_CONTEXT_20260701] installed")',
    },
}


def ensure_helper(text: str) -> str:
    if "def _nova_boot_log_20260701(" in text:
        return text

    lines = text.splitlines(keepends=True)

    if lines and lines[0].startswith("from __future__ import"):
        return "".join([lines[0], "\n", HELPER, *lines[1:]])

    return HELPER + text


def main():
    total_replacements = 0

    for path, replacements in REPLACEMENTS.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        changed = False

        for old, new in replacements.items():
            count = text.count(old)

            if count:
                text = text.replace(old, new)
                total_replacements += count
                changed = True
                print(f"PATCH {path.relative_to(ROOT)}: {count} x {old}")

        if changed:
            text = ensure_helper(text)
            path.write_text(text, encoding="utf-8")

    if total_replacements <= 0:
        raise SystemExit("No boot log replacements happened")

    print("")
    print(f"NOVA PHASE 4T BOOT LOG VERBOSE FLAG PATCHED replacements={total_replacements}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
