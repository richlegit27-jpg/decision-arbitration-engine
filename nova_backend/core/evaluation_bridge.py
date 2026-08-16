class EvaluationBridge:


    def __init__(
        self,
        evaluator=None,
    ):

        self.evaluator = (
            evaluator
        )



    def evaluate(
        self,
        task,
        result,
    ):

        evaluation = {

            "task": task,

            "result": result,

            "score": 0,

            "status": "unknown",

            "feedback": [],

        }


        if self.evaluator:

            try:

                checked = (
                    self.evaluator.evaluate(
                        task,
                        result,
                    )
                )

                if isinstance(
                    checked,
                    dict,
                ):

                    evaluation.update(
                        checked
                    )


            except Exception as exc:

                evaluation["feedback"].append(
                    str(exc)
                )


        if evaluation["score"] == 0:

            if result:

                evaluation["score"] = 0.5

                evaluation["status"] = (
                    "partial"
                )

            else:

                evaluation["status"] = (
                    "failed"
                )


        return evaluation