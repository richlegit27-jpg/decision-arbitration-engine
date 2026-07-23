# =========================================================
# NOVA_NON_WEB_SOURCE_LEAK_GUARD_20260622
# Prevent latest-news / live-source cards from leaking into normal chat
# =========================================================

import re as _nova_re_20260622


_NOVA_CURRENT_WEB_INTENT_20260622 = None


def _nova_text_from_args_20260622(args, kwargs):
    for key in ("user_text", "text", "message", "prompt", "query"):
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for value in args:
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _nova_wants_live_web_20260622(text):
    t = str(text or "").lower().strip()

    if not t:
        return False

    if _nova_re_20260622.search(r"https?://|www\.|site:", t):
        return True

    explicit_web = (
        "latest",
        "today's",
        "todays",
        "current",
        "right now",
        "breaking",
        "news",
        "headline",
        "headlines",
        "look up",
        "lookup",
        "search",
        "web fetch",
        "browse",
        "google",
        "online",
        "recent",
        "source",
        "sources",
        "article",
        "reports say",
        "who won",
        "score",
        "weather",
        "stock price",
        "share price",
        "bitcoin price",
        "btc price",
        "crypto price",
        "price right now",
        "market price",
    )

    return any(term in t for term in explicit_web)


def _nova_strip_source_payload_20260622(obj):
    source_keys = {
        "sources",
        "source",
        "source_cards",
        "sourcecards",
        "web_sources",
        "web_results",
        "web_results_clean",
        "live_sources",
        "live_source_cards",
        "news_results",
        "search_results",
        "citations",
        "citation_cards",
        "cards",
    }

    if isinstance(obj, dict):
        for key in list(obj.keys()):
            low = str(key).lower()

            if low in source_keys or "source_card" in low or "web_result" in low:
                if isinstance(obj[key], list):
                    obj[key] = []
                elif isinstance(obj[key], dict):
                    obj[key] = {}
                else:
                    obj[key] = None
                continue

            _nova_strip_source_payload_20260622(obj[key])

    elif isinstance(obj, list):
        for item in obj:
            _nova_strip_source_payload_20260622(item)

    return obj


def install_non_web_source_leak_guard(ChatService):

    global _NOVA_CURRENT_WEB_INTENT_20260622

    try:

        for method_name in (
            "_should_use_web",
            "_needs_web",
            "_should_fetch_web",
            "_should_run_web_fetch",
            "_is_web_request",
        ):
            if hasattr(ChatService, method_name):

                original_method = getattr(
                    ChatService,
                    method_name,
                )

                def make_guard(original):

                    def guarded(self, *args, **kwargs):

                        if _NOVA_CURRENT_WEB_INTENT_20260622 is False:
                            return False

                        text = _nova_text_from_args_20260622(
                            args,
                            kwargs,
                        )

                        if text and not _nova_wants_live_web_20260622(text):
                            return False

                        return original(
                            self,
                            *args,
                            **kwargs,
                        )

                    return guarded

                setattr(
                    ChatService,
                    method_name,
                    make_guard(original_method),
                )


        if hasattr(ChatService, "_execute_web_fetch"):

            original_execute = (
                ChatService._execute_web_fetch
            )

            def guarded_execute(
                self,
                *args,
                **kwargs,
            ):

                if _NOVA_CURRENT_WEB_INTENT_20260622 is False:
                    return []

                text = _nova_text_from_args_20260622(
                    args,
                    kwargs,
                )

                if text and not _nova_wants_live_web_20260622(text):
                    return []

                return original_execute(
                    self,
                    *args,
                    **kwargs,
                )

            ChatService._execute_web_fetch = guarded_execute


        if hasattr(ChatService, "handle"):

            original_handle = ChatService.handle


            def guarded_handle(
                self,
                *args,
                **kwargs,
            ):

                global _NOVA_CURRENT_WEB_INTENT_20260622

                user_text = _nova_text_from_args_20260622(
                    args,
                    kwargs,
                )

                wants_web = _nova_wants_live_web_20260622(
                    user_text
                )

                previous = _NOVA_CURRENT_WEB_INTENT_20260622

                _NOVA_CURRENT_WEB_INTENT_20260622 = wants_web

                try:
                    result = original_handle(
                        self,
                        *args,
                        **kwargs,
                    )

                finally:
                    _NOVA_CURRENT_WEB_INTENT_20260622 = previous


                if not wants_web:
                    _nova_strip_source_payload_20260622(
                        result
                    )

                return result


            ChatService.handle = guarded_handle


        print(
            "[Nova] non-web source leak guard installed"
        )

    except Exception as error:

        print(
            "[Nova] non-web source leak guard skipped:",
            error,
        )