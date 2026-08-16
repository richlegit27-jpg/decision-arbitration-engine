class AnswerEngine:


    def __init__(
        self,
        context_engine=None,
        memory=None,
        evaluator=None,
    ):

        self.context_engine = context_engine
        self.memory = memory
        self.evaluator = evaluator



    def analyze_request(
        self,
        user_text,
        context=None,
    ):

        analysis = {
            "question": user_text,
            "intent": self.detect_intent(
                user_text
            ),
            "requires_context": False,
            "priority": "normal",
        }


        if self._needs_context(
            user_text
        ):
            analysis["requires_context"] = True


        return analysis



    def detect_intent(
        self,
        text,
    ):

        text = text.lower()


        if any(
            x in text
            for x in [
                "error",
                "broken",
                "bug",
                "crash",
            ]
        ):
            return "debugging"


        if any(
            x in text
            for x in [
                "build",
                "create",
                "make",
            ]
        ):
            return "creation"


        if any(
            x in text
            for x in [
                "why",
                "explain",
                "how",
            ]
        ):
            return "explanation"


        return "conversation"



    def _needs_context(
        self,
        text,
    ):

        return any(
            x in text.lower()
            for x in [
                "continue",
                "again",
                "remember",
                "we were",
                "previous",
            ]
        )



    def improve_answer(
        self,
        answer,
        analysis,
    ):

        return {
            "answer": answer,
            "analysis": analysis,
            "checked": True,
        }