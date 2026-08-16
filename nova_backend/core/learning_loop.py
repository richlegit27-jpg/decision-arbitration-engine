class LearningLoop:


    def __init__(
        self,
    ):

        self.experiences = []



    def record(
        self,
        task,
        decision,
        result,
        score=None,
    ):

        experience = {

            "task": task,

            "decision": decision,

            "result": result,

            "score": score,

        }


        self.experiences.append(
            experience
        )


        return experience



    def analyze(
        self,
    ):

        successful = []

        failed = []


        for item in self.experiences:

            if item.get("score", 0) >= 0.7:

                successful.append(item)

            else:

                failed.append(item)


        return {

            "successful_patterns":
                successful,

            "failed_patterns":
                failed,

            "total":
                len(self.experiences),

        }



    def suggest_improvement(
        self,
        task,
    ):

        matches = [

            x for x in self.experiences

            if x.get("task") == task

        ]


        if not matches:

            return {
                "suggestion":
                    "No previous experience"
            }


        best = max(
            matches,
            key=lambda x:
                x.get("score", 0)
        )


        return {

            "suggestion":
                "Reuse successful strategy",

            "previous":
                best,

        }