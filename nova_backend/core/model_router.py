class ModelRouter:


    def __init__(
        self,
        models=None,
    ):

        self.models = models or {
            "fast": "gpt-4.1-mini",
            "reasoning": "gpt-5-mini",
            "local": "llama3.1:8b",
        }



    def choose(
        self,
        user_text,
        context=None,
    ):

        text = user_text.lower()

        route = {
            "model": self.models["fast"],
            "reason": "general",
        }


        if any(
            word in text
            for word in [
                "code",
                "error",
                "bug",
                "python",
                "backend",
                "api",
            ]
        ):

            route = {
                "model": self.models["reasoning"],
                "reason": "technical",
            }


        if any(
            word in text
            for word in [
                "summarize",
                "short",
                "quick",
            ]
        ):

            route = {
                "model": self.models["fast"],
                "reason": "simple",
            }


        if context and context.get(
            "local_only"
        ):

            route = {
                "model": self.models["local"],
                "reason": "local_required",
            }


        return route