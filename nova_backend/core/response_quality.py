class ResponseQualityJudge:


    def __init__(self):

        self.history = []



    def judge(
        self,
        question,
        answer,
        context=None,
    ):

        context = context or {}

        score = 0


        checks = {
            "has_answer": self._has_answer(answer),
            "matches_question": self._matches_question(
                question,
                answer,
            ),
            "uses_context": bool(
                context
            ),
            "clear": self._is_clear(answer),
        }


        for value in checks.values():

            if value:
                score += 25



        result = {
            "score": score,
            "approved": score >= 75,
            "checks": checks,
            "action": self._action(
                score
            ),
        }


        self.history.append(
            result
        )


        return result



    def _has_answer(
        self,
        answer,
    ):

        return bool(
            str(answer).strip()
        )



    def _matches_question(
        self,
        question,
        answer,
    ):

        question_words = set(
            str(question)
            .lower()
            .split()
        )

        answer_words = set(
            str(answer)
            .lower()
            .split()
        )


        return bool(
            question_words
            .intersection(answer_words)
        )



    def _is_clear(
        self,
        answer,
    ):

        text = str(answer)

        return len(text.strip()) > 20



    def _action(
        self,
        score,
    ):

        if score >= 90:
            return "deliver"

        if score >= 75:
            return "deliver_with_confidence"

        if score >= 50:
            return "improve"

        return "retry"



    def get_history(self):

        return self.history