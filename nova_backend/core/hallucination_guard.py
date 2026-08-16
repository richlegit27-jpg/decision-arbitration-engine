class HallucinationGuard:


    def __init__(self):

        self.checks = []



    def evaluate(
        self,
        answer,
        context=None,
    ):

        context = context or {}

        confidence = self._calculate_confidence(
            answer,
            context,
        )

        result = {
            "approved": confidence >= 0.5,
            "confidence": confidence,
            "needs_revision": confidence < 0.5,
            "reason": self._reason(
                confidence
            ),
        }


        self.checks.append(
            result
        )

        return result



    def _calculate_confidence(
        self,
        answer,
        context,
    ):

        score = 0.5


        if context.get("memory"):
            score += 0.15


        if context.get("knowledge"):
            score += 0.15


        if context.get("conversation"):
            score += 0.1


        if not answer:
            score -= 0.3


        if len(str(answer)) < 20:
            score -= 0.1


        return max(
            0,
            min(
                score,
                1
            )
        )



    def _reason(
        self,
        confidence,
    ):

        if confidence >= 0.8:
            return "Strong context support"


        if confidence >= 0.5:
            return "Acceptable confidence"


        return "Insufficient evidence"



    def history(self):

        return self.checks