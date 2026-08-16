class ReflectionEngine:


    def __init__(self):

        self.reflections = []



    def review(
        self,
        task,
        answer,
        result=None,
    ):

        reflection = {

            "task": task,

            "answer_quality":
                self._check_answer(
                    answer
                ),

            "result":
                result,

            "lessons": [],

        }


        reflection["lessons"] = (
            self._extract_lessons(
                reflection
            )
        )


        self.reflections.append(
            reflection
        )


        return reflection



    def _check_answer(
        self,
        answer,
    ):

        text = str(answer).strip()


        if not text:
            return "failed"


        if len(text) < 20:
            return "weak"


        return "acceptable"



    def _extract_lessons(
        self,
        reflection,
    ):

        lessons = []


        if reflection["answer_quality"] == "failed":

            lessons.append(
                "Need stronger response generation"
            )


        elif reflection["answer_quality"] == "weak":

            lessons.append(
                "Need more context or detail"
            )


        else:

            lessons.append(
                "Strategy produced usable result"
            )


        return lessons



    def history(
        self,
    ):

        return self.reflections