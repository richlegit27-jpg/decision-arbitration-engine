class ImageWebGateService:

    def is_web_intent(self, text):
        clean = " ".join(
            str(text or "").lower().split()
        )

        terms = (
            "latest news",
            "news about",
            "today in",
            "what happened today",
            "current news",
            "breaking news",
            "recent news",
            "latest tech news",
            "latest sports",
            "weather",
            "forecast",
            "current events",
        )

        return any(
            term in clean
            for term in terms
        )


image_web_gate_service = ImageWebGateService()