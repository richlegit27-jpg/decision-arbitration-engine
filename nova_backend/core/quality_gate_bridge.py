class QualityGateBridge:


    def __init__(
        self,
        quality_checker=None,
        hallucination_guard=None,
    ):

        self.quality_checker = (
            quality_checker
        )

        self.hallucination_guard = (
            hallucination_guard
        )



    def check(
        self,
        answer,
        context=None,
    ):

        result = {

            "approved": True,

            "score": 0,

            "issues": [],

            "answer": answer,

        }


        if self.hallucination_guard:

            try:

                guard_result = (
                    self.hallucination_guard.check(
                        answer,
                        context,
                    )
                )

                if guard_result is False:

                    result["approved"] = False

                    result["issues"].append(
                        "hallucination_check_failed"
                    )


            except Exception as exc:

                result["issues"].append(
                    str(exc)
                )



        if self.quality_checker:

            try:

                quality_result = (
                    self.quality_checker.evaluate(
                        answer
                    )
                )

                if isinstance(
                    quality_result,
                    dict,
                ):

                    result.update(
                        quality_result
                    )


            except Exception as exc:

                result["issues"].append(
                    str(exc)
                )



        if not answer or not str(answer).strip():

            result["approved"] = False

            result["issues"].append(
                "empty_response"
            )


        return result