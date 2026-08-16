class EvaluatorEngine:


    def __init__(self):
        self.evaluations = []


    def evaluate(
        self,
        goal,
        output,
        context=None,
    ):

        score = self._score_output(
            goal,
            output,
        )

        result = {
            "goal": goal,
            "output": output,
            "score": score,
            "status": self._status(score),
            "improvements": self._suggest_improvements(score),
            "context": context or {},
        }

        self.evaluations.append(result)

        return result



    def _score_output(
        self,
        goal,
        output,
    ):

        if not output:
            return 0


        goal_words = set(
            str(goal)
            .lower()
            .split()
        )

        output_words = set(
            str(output)
            .lower()
            .split()
        )


        overlap = len(
            goal_words.intersection(output_words)
        )


        if not goal_words:
            return 50


        score = int(
            (overlap / len(goal_words))
            * 100
        )


        return min(score, 100)



    def _status(
        self,
        score,
    ):

        if score >= 80:
            return "excellent"

        if score >= 50:
            return "acceptable"

        return "needs_improvement"



    def _suggest_improvements(
        self,
        score,
    ):

        if score >= 80:
            return [
                "Maintain strategy",
                "Optimize execution speed",
            ]


        if score >= 50:
            return [
                "Add more context",
                "Improve reasoning depth",
            ]


        return [
            "Re-plan objective",
            "Gather more information",
        ]



    def history(self):

        return self.evaluations