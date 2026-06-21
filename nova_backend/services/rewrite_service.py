# C:\Users\Owner\nova\nova_backend\services\rewrite_service.py


class RewriteService:
    def __init__(self):
        pass

    def rewrite(
        self,
        text: str = "",
        user_text: str = "",
        route: str = "",
        intent: str = "",
    ) -> str:
        text = str(text or "").strip()
        route = str(route or "").strip().lower()
        intent = str(intent or "").strip().lower()

        if not text:
            return ""

        # Never crush useful technical/debugging answers.
        if intent in ("debugging", "coding") or route in ("debugging", "coding"):
            return text

        return text

