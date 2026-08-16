class IntelligenceRouter:


    def decide(
        self,
        text,
        context=None
    ):

        text=text.lower()


        if "remember" in text:
            return {
                "route":"memory"
            }


        if "what were we working" in text:
            return {
                "route":"continuity"
            }


        if "plan" in text:
            return {
                "route":"execution"
            }


        return {
            "route":"general"
        }