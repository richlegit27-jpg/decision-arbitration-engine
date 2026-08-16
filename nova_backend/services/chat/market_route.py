def install_market_route(ChatService):
    original_decide_route = ChatService._decide_route

    def _nova_final_live_market_price_attachments_20260630(args, kwargs):
        value = kwargs.get("attachments")

        if value:
            return value

        if len(args) >= 2:
            return args[1]

        return None

    def _nova_is_live_market_price_request_20260630(value):
        text = " ".join(
            str(value or "").lower().replace("?", " ").split()
        )

        if not text:
            return False

        market_terms = (
            "bitcoin",
            "btc",
            "crypto",
            "stock",
            "stocks",
            "share",
            "shares",
        )

        price_terms = (
            "price",
            "worth",
            "trading at",
            "right now",
            "today",
            "current",
            "live",
            "market",
        )

        return (
            any(term in text for term in market_terms)
            and any(term in text for term in price_terms)
        )

    def _nova_final_live_market_price_decide_20260630(
        self,
        *args,
        **kwargs,
    ):
        user_text = kwargs.get("user_text") or ""

        attachments = _nova_final_live_market_price_attachments_20260630(
            args,
            kwargs,
        )

        if (
            not attachments
            and _nova_is_live_market_price_request_20260630(user_text)
        ):
            return {
                "route": "web_fetch",
                "mode": "web_fetch",
                "confidence": 1.0,
                "reasons": [
                    "final_live_market_price_route_authority",
                ],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
                "query": user_text,
            }

        return original_decide_route(
            self,
            *args,
            **kwargs,
        )

    ChatService._decide_route = (
        _nova_final_live_market_price_decide_20260630
    )